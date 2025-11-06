"""Build graph from HTTP messages."""

import re
from typing import Dict, List, Optional, Any
from ..models import (
    HTTPMessage,
    Endpoint,
    Request,
    Response,
    UserSession,
    Resource,
    Parameter,
)
from ..parsers import HTTPParser
from .neo4j_client import Neo4jClient


class GraphBuilder:
    """Build knowledge graph from HTTP traffic."""

    def __init__(self, neo4j_client: Neo4jClient):
        """Initialize graph builder with Neo4j client."""
        self.client = neo4j_client
        self.endpoint_cache: Dict[str, str] = (
            {}
        )  # (method, pattern) -> endpoint_id

    def process_message(self, message: HTTPMessage) -> None:
        """Process an HTTP message and add to graph."""
        # 1. Create or get endpoint
        endpoint = self._get_or_create_endpoint(message)

        # 2. Create request node
        request = Request.create(
            endpoint_id=endpoint.id,
            headers=message.request.headers,
            body=message.request.body,
        )
        self._create_request_node(request)

        # 3. Create response node
        response = Response.create(
            request_id=request.id,
            status_code=message.response.status_code,
            body=message.response.body,
        )
        self._create_response_node(response)

        # 4. Extract and create parameters
        self._extract_parameters(message, request.id)

        # 5. Extract user session if present (from auth tokens)
        session = self._extract_session(message)
        if session:
            self._create_session_node(session)

        # 6. Extract resources from response body
        resources = self._extract_resources(message)
        for resource in resources:
            self._create_resource_node(resource)
            if session and resource.data.get('id'):
                # Link session to resource if user_id matches
                if session.user_id == resource.data.get('id'):
                    self.client.create_relationship(
                        session.id,
                        resource.id,
                        "UserSession",
                        "Resource",
                        "BELONGS_TO",
                    )

    def _get_or_create_endpoint(self, message: HTTPMessage) -> Endpoint:
        """Get or create endpoint node."""
        method = message.request.method
        path = message.request.path
        pattern = message.endpoint_pattern

        cache_key = f"{method}:{pattern}"

        if cache_key not in self.endpoint_cache:
            endpoint = Endpoint.create(
                path=path, pattern=pattern, method=method
            )
            self.client.create_node(
                "Endpoint",
                endpoint.id,
                {"path": path, "pattern": pattern, "method": method},
            )
            self.endpoint_cache[cache_key] = endpoint.id

        endpoint_id = self.endpoint_cache[cache_key]
        return Endpoint(
            id=endpoint_id, path=path, pattern=pattern, method=method
        )

    def _create_request_node(self, request: Request) -> None:
        """Create request node and relationship to endpoint."""
        self.client.create_node(
            "Request",
            request.id,
            {"headers": request.headers, "body": request.body},
        )
        self.client.create_relationship(
            request.id, request.endpoint_id, "Request", "Endpoint", "TARGETS"
        )

    def _create_response_node(self, response: Response) -> None:
        """Create response node and relationship to request."""
        self.client.create_node(
            "Response",
            response.id,
            {"statusCode": response.status_code, "body": response.body},
        )
        self.client.create_relationship(
            response.id,
            response.request_id,
            "Response",
            "Request",
            "FOR_REQUEST",
        )

    def _extract_parameters(
        self, message: HTTPMessage, request_id: str
    ) -> None:
        """Extract and create parameter nodes."""
        # Path parameters
        path_params = HTTPParser.extract_path_params(
            message.request.path, message.endpoint_pattern
        )
        for key, value in path_params.items():
            param = Parameter.create(request_id, "path", key, value)
            self._create_parameter_node(param)

        # Body parameters (if JSON)
        if message.request.has_json_body and isinstance(
            message.request.body, dict
        ):
            for key, value in message.request.body.items():
                param = Parameter.create(request_id, "body", key, value)
                self._create_parameter_node(param)

    def _create_parameter_node(self, param: Parameter) -> None:
        """Create parameter node and relationship to request."""
        self.client.create_node(
            "Parameter",
            param.id,
            {"type": param.type, "key": param.key, "value": param.value},
        )
        self.client.create_relationship(
            param.id, param.request_id, "Parameter", "Request", "OF_REQUEST"
        )

    def _extract_session(self, message: HTTPMessage) -> Optional[UserSession]:
        """Extract user session from auth headers or response."""
        # Check for JWT in Authorization header
        auth_header = message.request.headers.get("Authorization", "")
        token = None
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]

        # Try to extract user info from response (login endpoint)
        user_id = None
        username = None

        if message.response.has_json_body and isinstance(
            message.response.body, dict
        ):
            # Check if this is a login response
            if "token" in message.response.body:
                token = message.response.body["token"]

            # Extract user info
            user_data = message.response.body.get("user", {})
            if isinstance(user_data, dict):
                user_id = user_data.get("id")
                username = user_data.get("username")

        # Decode JWT to get user info if we have a token but no user data
        if token and not user_id:
            user_info = self._decode_jwt_payload(token)
            if user_info:
                user_id = user_info.get("id")
                username = user_info.get("username")

        if token or user_id:
            return UserSession.create(
                user_id=user_id, username=username, token=token
            )

        return None

    def _decode_jwt_payload(self, token: str) -> Optional[Dict[str, Any]]:
        """Decode JWT payload (basic, without verification)."""
        import json
        import base64

        try:
            parts = token.split('.')
            if len(parts) != 3:
                return None

            # Decode payload (add padding if needed)
            payload = parts[1]
            padding = 4 - len(payload) % 4
            if padding != 4:
                payload += '=' * padding

            decoded = base64.urlsafe_b64decode(payload)
            return json.loads(decoded)
        except Exception:
            return None

    def _extract_resources(self, message: HTTPMessage) -> List[Resource]:
        """Extract resource objects from response body."""
        resources = []

        if not message.response.has_json_body:
            return resources

        body = message.response.body
        if not isinstance(body, dict):
            return resources

        # Check if response contains user data
        if "id" in body and "username" in body:
            resource = Resource.create("user_details", body)
            resources.append(resource)
        elif "user" in body and isinstance(body["user"], dict):
            resource = Resource.create("user", body["user"])
            resources.append(resource)

        return resources

    def _create_session_node(self, session: UserSession) -> None:
        """Create user session node."""
        props = {
            "user_id": session.user_id,
            "username": session.username,
            "token": session.token,
        }
        self.client.create_node("UserSession", session.id, props)

    def _create_resource_node(self, resource: Resource) -> None:
        """Create resource node."""
        props = {"type": resource.type, "data": resource.data}
        if isinstance(resource.data, dict) and "id" in resource.data:
            props["data_id"] = resource.data["id"]

        self.client.create_node("Resource", resource.id, props)
