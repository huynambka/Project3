"""Google Gemini API client for data conversion."""

import json
import logging
import uuid
from typing import List, Dict, Any, Optional
import google.generativeai as genai
from ..config import Settings

logger = logging.getLogger(__name__)


class GeminiClient:
    """Client for Google Gemini API to convert HTTP traffic to graph data."""

    CONVERSION_PROMPT = """You are a data conversion expert. Convert HTTP request/response pairs into structured graph database format.

INPUT FORMAT: You will receive a list of HTTP request/response pairs in raw format.

OUTPUT FORMAT: Return ONLY a valid JSON object (no markdown, no explanation) with this exact structure:
{
  "nodes": {
    "endpoints": [{"path": "/actual/path", "pattern": "/pattern/{id}", "method": "GET"}],
    "requests": [{"endpoint_index": 0, "headers": {"Authorization": "Bearer ...", "Cookie": "..."}, "body": {...}}],
    "responses": [{"request_index": 0, "statusCode": 200, "headers": {"Set-Cookie": "...", "Content-Type": "..."}, "body": {...}}],
    "sessions": [{"user_id": 1, "username": "alice", "token": "..."}],
    "resources": [{"type": "user", "data": {...}, "data_id": 1, "session_token": "...", "request_index": 0}],
    "parameters": [{"request_index": 0, "type": "path", "key": "id", "value": "1"}]
  }
}

IMPORTANT RULES:
1. DO NOT generate any "id" fields - IDs will be generated automatically as UUIDs
2. Use array indexes for relationships:
   - "endpoint_index": position in endpoints array (0, 1, 2, ...)
   - "request_index": position in requests array (0, 1, 2, ...)
3. Extract endpoint patterns by replacing IDs with {id} (e.g., /api/users/123 → /api/users/{id})
4. Parse JSON bodies if Content-Type is application/json
5. ALWAYS extract important headers from requests:
   - Authorization (Bearer tokens, Basic auth, API keys)
   - Cookie (session cookies, auth cookies)
   - Content-Type
   - X-API-Key or any custom authentication headers
   Store these in the "headers" object for each request
6. ALWAYS extract important headers from responses:
   - Set-Cookie (session establishment, auth tokens)
   - Content-Type
   - Authorization (if present in response)
   Store these in the "headers" object for each response
7. Extract Authorization tokens (Bearer, JWT) into sessions
8. Decode JWT tokens to get user_id and username if possible
9. Identify resources from response bodies (users, objects with id fields)
10. Extract path parameters by comparing actual path vs pattern
11. Extract body parameters from JSON request bodies
12. Store data_id in resources for linking (from data.id field)
13. For each resource, extract session information:
   - Store "session_token" field with the token value from Authorization header or Cookie
   - Store "request_index" field to link resource to its originating request
   This allows linking resources to sessions later
14. Each request must reference its endpoint by index
15. Each response must reference its request by index
16. Each parameter must reference its request by index
17. Headers object must NOT be empty - extract at least Content-Type if no auth headers present

Now convert this data:"""

    def __init__(self, settings: Settings):
        """Initialize Gemini client."""
        self.settings = settings
        if not settings.gemini_api_key:
            logger.warning(
                "GEMINI_API_KEY not set, AI conversion will not work"
            )
            self.model = None
        else:
            genai.configure(api_key=settings.gemini_api_key)
            self.model = genai.GenerativeModel('gemini-2.5-flash')
            logger.info("Gemini client initialized")

    def convert_batch_to_graph_data(
        self, batch: List[Dict[str, str]]
    ) -> Optional[Dict[str, Any]]:
        """Convert a batch of HTTP messages to graph database format using Gemini.

        Args:
            batch: List of dicts with 'request', 'response', 'timestamp' keys

        Returns:
            Dict with 'nodes' key containing all graph entities, or None on error
        """
        if not self.model:
            logger.error("Gemini model not initialized (missing API key)")
            return None

        try:
            # Format batch for Gemini
            batch_text = self._format_batch(batch)

            # Create full prompt
            full_prompt = f"{self.CONVERSION_PROMPT}\n\n{batch_text}"

            logger.info(
                f"Sending batch of {len(batch)} messages to Gemini AI for conversion..."
            )
            logger.debug(f"Prompt length: {len(full_prompt)} characters")

            # Call Gemini API
            response = self.model.generate_content(full_prompt)

            logger.info(f"Received response from Gemini AI")

            if not response or not response.text:
                logger.error("Empty response from Gemini")
                return None

            # Parse JSON response
            result_text = response.text.strip()

            # Remove markdown code blocks if present
            if result_text.startswith("```"):
                lines = result_text.split('\n')
                result_text = '\n'.join(lines[1:-1])
            if result_text.startswith("```json"):
                result_text = result_text[7:]
            if result_text.endswith("```"):
                result_text = result_text[:-3]

            result = json.loads(result_text.strip())

            # Add UUIDs to all nodes
            result_with_ids = self._add_uuids(result)

            # Link resources to sessions based on token matching
            result_with_relations = self._link_resources_to_sessions(result_with_ids)

            logger.info(f"Successfully converted batch to graph data")
            logger.debug(f"Result: {json.dumps(result_with_relations, indent=2)}")

            return result_with_relations

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Gemini response as JSON: {e}")
            logger.debug(
                f"Response text: {response.text if response else 'None'}"
            )
            return None
        except Exception as e:
            logger.error(f"Error calling Gemini API: {e}", exc_info=True)
            return None

    def _format_batch(self, batch: List[Dict[str, str]]) -> str:
        """Format batch for Gemini prompt."""
        formatted = []
        for i, item in enumerate(batch, 1):
            formatted.append(f"\n--- Message {i} ---")
            formatted.append(f"REQUEST:\n{item['request']}")
            formatted.append(f"\nRESPONSE:\n{item['response']}")
            formatted.append(f"\nTIMESTAMP: {item.get('timestamp', '')}")

        return '\n'.join(formatted)

    def _add_uuids(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Add UUID IDs to all nodes and convert index references to ID references.

        Args:
            data: Graph data with index-based references

        Returns:
            Graph data with UUID IDs and ID-based references
        """
        if 'nodes' not in data:
            return data

        nodes = data['nodes']

        # Generate UUIDs for all node types and create index->ID mappings
        endpoint_ids = []
        request_ids = []

        # Add UUIDs to endpoints
        if 'endpoints' in nodes:
            for endpoint in nodes['endpoints']:
                endpoint_id = str(uuid.uuid4())
                endpoint['id'] = endpoint_id
                endpoint_ids.append(endpoint_id)

        # Add UUIDs to requests and convert endpoint references
        if 'requests' in nodes:
            for request in nodes['requests']:
                request_id = str(uuid.uuid4())
                request['id'] = request_id
                request_ids.append(request_id)

                # Convert endpoint_index to endpoint_id
                if 'endpoint_index' in request:
                    idx = request['endpoint_index']
                    if 0 <= idx < len(endpoint_ids):
                        request['endpoint_id'] = endpoint_ids[idx]
                    del request['endpoint_index']

        # Add UUIDs to responses and convert request references
        if 'responses' in nodes:
            for response in nodes['responses']:
                response['id'] = str(uuid.uuid4())

                # Convert request_index to request_id
                if 'request_index' in response:
                    idx = response['request_index']
                    if 0 <= idx < len(request_ids):
                        response['request_id'] = request_ids[idx]
                    del response['request_index']

        # Add UUIDs to sessions
        if 'sessions' in nodes:
            for session in nodes['sessions']:
                session['id'] = str(uuid.uuid4())

        # Add UUIDs to resources
        if 'resources' in nodes:
            for resource in nodes['resources']:
                resource['id'] = str(uuid.uuid4())

        # Add UUIDs to parameters and convert request references
        if 'parameters' in nodes:
            for parameter in nodes['parameters']:
                parameter['id'] = str(uuid.uuid4())

                # Convert request_index to request_id
                if 'request_index' in parameter:
                    idx = parameter['request_index']
                    if 0 <= idx < len(request_ids):
                        parameter['request_id'] = request_ids[idx]
                    del parameter['request_index']

        return data

    def _link_resources_to_sessions(
        self, data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Link resources to sessions based on token matching.

        Args:
            data: Graph data with UUIDs

        Returns:
            Graph data with session_id references in resources
        """
        if 'nodes' not in data:
            return data

        nodes = data['nodes']

        # Build token -> session_id mapping
        token_to_session = {}
        if 'sessions' in nodes:
            for session in nodes['sessions']:
                if 'token' in session and 'id' in session:
                    token_to_session[session['token']] = session['id']

        # Build request_id -> session mapping via request headers
        request_to_session = {}
        if 'requests' in nodes:
            for request in nodes['requests']:
                if 'id' not in request:
                    continue

                request_id = request['id']
                headers = request.get('headers', {})

                # Extract token from Authorization header
                auth_header = headers.get('Authorization', '')
                if auth_header.startswith('Bearer '):
                    token = auth_header[7:].strip()
                    if token in token_to_session:
                        request_to_session[request_id] = token_to_session[token]
                        continue

                # Extract token from Cookie header
                cookie_header = headers.get('Cookie', '')
                if cookie_header:
                    # Try to match any token in cookies to sessions
                    for token in token_to_session:
                        if token in cookie_header:
                            request_to_session[request_id] = token_to_session[token]
                            break

        # Link resources to sessions
        if 'resources' in nodes:
            for resource in nodes['resources']:
                # If resource has session_token, find matching session
                if 'session_token' in resource:
                    token = resource['session_token']
                    if token in token_to_session:
                        resource['session_id'] = token_to_session[token]
                    # Remove session_token as we now have session_id
                    del resource['session_token']

                # If resource has request_id, link via request's session
                elif 'request_id' in resource:
                    request_id = resource['request_id']
                    if request_id in request_to_session:
                        resource['session_id'] = request_to_session[request_id]

        logger.info(
            f"Linked {sum(1 for r in nodes.get('resources', []) if 'session_id' in r)} "
            f"resources to sessions"
        )

        return data
