"""Load Gemini-converted data into Neo4j graph."""

import logging
from typing import Dict, Any, List
from ..graph_db import Neo4jClient

logger = logging.getLogger(__name__)


class GeminiGraphLoader:
    """Load graph data from Gemini conversion into Neo4j."""

    def __init__(self, neo4j_client: Neo4jClient):
        """Initialize loader with Neo4j client."""
        self.client = neo4j_client

    def load_graph_data(self, data: Dict[str, Any]) -> None:
        """Load converted graph data into Neo4j.

        Args:
            data: Dict with 'nodes' key containing endpoints, requests, responses, etc.
        """
        if not data or 'nodes' not in data:
            logger.error("Invalid graph data format: missing 'nodes' key")
            return

        nodes = data['nodes']

        logger.info("Starting to write graph data to Neo4j database...")

        # Load in order: endpoints first, then requests, responses, parameters, sessions, resources
        self._load_endpoints(nodes.get('endpoints', []))
        self._load_requests(nodes.get('requests', []))
        self._load_responses(nodes.get('responses', []))
        self._load_parameters(nodes.get('parameters', []))
        self._load_sessions(nodes.get('sessions', []))
        self._load_resources(nodes.get('resources', []))

        logger.info("Graph data successfully written to Neo4j database")

    def _load_endpoints(self, endpoints: List[Dict[str, Any]]) -> None:
        """Load endpoint nodes."""
        if endpoints:
            logger.info(
                f"Writing {len(endpoints)} endpoint nodes to database..."
            )
        for ep in endpoints:
            try:
                self.client.create_node(
                    "Endpoint",
                    ep['id'],
                    {
                        'path': ep.get('path', ''),
                        'pattern': ep.get('pattern', ''),
                        'method': ep.get('method', ''),
                    },
                )
            except Exception as e:
                logger.error(f"Error loading endpoint {ep.get('id')}: {e}")

    def _load_requests(self, requests: List[Dict[str, Any]]) -> None:
        """Load request nodes and relationships to endpoints."""
        if requests:
            logger.info(f"Writing {len(requests)} request nodes to database...")
        for req in requests:
            try:
                # Create request node
                self.client.create_node(
                    "Request",
                    req['id'],
                    {
                        'headers': req.get('headers', {}),
                        'body': req.get('body'),
                    },
                )

                # Create relationship to endpoint
                if 'endpoint_id' in req:
                    self.client.create_relationship(
                        req['id'],
                        req['endpoint_id'],
                        "Request",
                        "Endpoint",
                        "TARGETS",
                    )
            except Exception as e:
                logger.error(f"Error loading request {req.get('id')}: {e}")

    def _load_responses(self, responses: List[Dict[str, Any]]) -> None:
        """Load response nodes and relationships to requests."""
        if responses:
            logger.info(
                f"Writing {len(responses)} response nodes to database..."
            )
        for resp in responses:
            try:
                # Create response node
                self.client.create_node(
                    "Response",
                    resp['id'],
                    {
                        'statusCode': resp.get('statusCode'),
                        'body': resp.get('body'),
                    },
                )

                # Create relationship to request
                if 'request_id' in resp:
                    self.client.create_relationship(
                        resp['id'],
                        resp['request_id'],
                        "Response",
                        "Request",
                        "FOR_REQUEST",
                    )
            except Exception as e:
                logger.error(f"Error loading response {resp.get('id')}: {e}")

    def _load_parameters(self, parameters: List[Dict[str, Any]]) -> None:
        """Load parameter nodes and relationships to requests."""
        if parameters:
            logger.info(
                f"Writing {len(parameters)} parameter nodes to database..."
            )
        for param in parameters:
            try:
                # Create parameter node
                self.client.create_node(
                    "Parameter",
                    param['id'],
                    {
                        'type': param.get('type', ''),
                        'key': param.get('key', ''),
                        'value': param.get('value'),
                    },
                )

                # Create relationship to request
                if 'request_id' in param:
                    self.client.create_relationship(
                        param['id'],
                        param['request_id'],
                        "Parameter",
                        "Request",
                        "OF_REQUEST",
                    )
            except Exception as e:
                logger.error(f"Error loading parameter {param.get('id')}: {e}")

    def _load_sessions(self, sessions: List[Dict[str, Any]]) -> None:
        """Load user session nodes."""
        if sessions:
            logger.info(f"Writing {len(sessions)} session nodes to database...")
        for session in sessions:
            try:
                self.client.create_node(
                    "UserSession",
                    session['id'],
                    {
                        'user_id': session.get('user_id'),
                        'username': session.get('username'),
                        'token': session.get('token'),
                    },
                )
            except Exception as e:
                logger.error(f"Error loading session {session.get('id')}: {e}")

    def _load_resources(self, resources: List[Dict[str, Any]]) -> None:
        """Load resource nodes and link to sessions."""
        if resources:
            logger.info(
                f"Writing {len(resources)} resource nodes to database..."
            )
        for resource in resources:
            try:
                props = {
                    'type': resource.get('type', ''),
                    'data': resource.get('data', {}),
                }
                if 'data_id' in resource:
                    props['data_id'] = resource['data_id']

                self.client.create_node("Resource", resource['id'], props)

                # Link sessions to this resource by user_id
                if 'data_id' in resource:
                    # Find sessions with matching user_id and create relationships
                    # This is handled by a separate query
                    self._link_sessions_to_resource(
                        resource['id'], resource['data_id']
                    )

            except Exception as e:
                logger.error(
                    f"Error loading resource {resource.get('id')}: {e}"
                )

    def _link_sessions_to_resource(
        self, resource_id: str, data_id: Any
    ) -> None:
        """Link sessions to resources by matching user_id."""
        try:
            with self.client.driver.session() as session:
                session.execute_write(
                    lambda tx: tx.run(
                        """
                        MATCH (s:UserSession), (r:Resource {id: $resource_id})
                        WHERE s.user_id = $data_id
                        MERGE (s)-[:BELONGS_TO]->(r)
                        """,
                        resource_id=resource_id,
                        data_id=data_id,
                    )
                )
        except Exception as e:
            logger.error(
                f"Error linking sessions to resource {resource_id}: {e}"
            )
