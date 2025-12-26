"""
Rule-based parser using YAML configuration for HTTP request analysis.
This parser converts HTTP requests to Neo4j graph structure without relying on AI.
"""

import re
import yaml
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from urllib.parse import urlparse, parse_qs
import json

from ..models.http_models import HTTPRequest
from ..utils.logger import get_logger


logger = get_logger(__name__)


class YAMLRuleBasedParser:
    """Parse HTTP requests using YAML-defined rules."""

    def __init__(self, rules_path: Optional[str] = None):
        """
        Initialize parser with YAML rules.

        Args:
            rules_path: Path to YAML rules file. If None, uses default config/parsing_rules.yaml
        """
        if rules_path is None:
            rules_path = str(
                Path(__file__).parent.parent.parent
                / "config"
                / "parsing_rules.yaml"
            )

        self.rules_path = Path(rules_path)
        self.rules = self._load_rules()
        logger.info(f"Loaded parsing rules from {self.rules_path}")

    def _load_rules(self) -> Dict[str, Any]:
        """Load rules from YAML file."""
        try:
            with open(self.rules_path, 'r', encoding='utf-8') as f:
                rules = yaml.safe_load(f)
                logger.debug(f"Successfully loaded {len(rules)} rule sections")
                return rules
        except Exception as e:
            logger.error(f"Failed to load rules from {self.rules_path}: {e}")
            raise

    def reload_rules(self) -> None:
        """Reload rules from YAML file."""
        self.rules = self._load_rules()
        logger.info("Rules reloaded successfully")

    def parse_request(self, http_request: HTTPRequest) -> Dict[str, Any]:
        """
        Parse HTTP request into graph components using YAML rules.

        Args:
            http_request: HTTP request to parse

        Returns:
            Dict with 'nodes', 'relationships', and 'metadata' keys
        """
        nodes = []
        relationships = []

        try:
            # Parse URL
            parsed_url = urlparse(http_request.url)

            # Create Request node
            request_node = self._create_request_node(http_request)
            nodes.append(request_node)

            # Extract parameters
            param_nodes, param_rels = self._extract_parameters(
                http_request, request_node['id'], parsed_url
            )
            nodes.extend(param_nodes)
            relationships.extend(param_rels)

            # Extract headers
            header_nodes, header_rels = self._extract_headers(
                http_request, request_node['id']
            )
            nodes.extend(header_nodes)
            relationships.extend(header_rels)

            # Extract body
            body_nodes, body_rels = self._extract_body(
                http_request, request_node['id']
            )
            nodes.extend(body_nodes)
            relationships.extend(body_rels)

            # Create Endpoint node
            endpoint_node = self._create_endpoint_node(
                parsed_url, http_request.method
            )
            nodes.append(endpoint_node)

            # Create Request -> Endpoint relationship
            relationships.append(
                {
                    'source_id': request_node['id'],
                    'target_id': endpoint_node['id'],
                    'type': 'TARGETS',
                    'properties': {'timestamp': http_request.timestamp or ''},
                }
            )

            # Extract User information
            user_nodes, user_rels = self._extract_user(
                http_request, request_node['id']
            )
            nodes.extend(user_nodes)
            relationships.extend(user_rels)

            # Extract Resource information
            resource_nodes, resource_rels = self._extract_resources(
                http_request, request_node['id'], parsed_url
            )
            nodes.extend(resource_nodes)
            relationships.extend(resource_rels)

            logger.info(
                f"Parsed request: {len(nodes)} nodes, {len(relationships)} relationships"
            )

            return {
                'nodes': nodes,
                'relationships': relationships,
                'metadata': {
                    'total_nodes': len(nodes),
                    'total_relationships': len(relationships),
                    'parser': 'yaml_rule_based',
                },
            }

        except Exception as e:
            logger.error(f"Failed to parse request: {e}", exc_info=True)
            raise

    def _create_request_node(self, http_request: HTTPRequest) -> Dict[str, Any]:
        """Create Request node based on template."""
        template = self.rules['node_templates']['Request']

        node_id = f"request_{hash(http_request.url + http_request.method + str(http_request.timestamp))}"

        properties = {
            'method': http_request.method,
            'url': http_request.url,
            'timestamp': http_request.timestamp or '',
            'protocol': http_request.protocol or 'HTTP/1.1',
        }

        return {
            'id': node_id,
            'labels': ['Request'] + template.get('additional_labels', []),
            'properties': properties,
        }

    def _classify_parameter(
        self, param_name: str, param_value: str
    ) -> Dict[str, Any]:
        """Classify parameter using YAML patterns."""
        param_patterns = self.rules['parameter_patterns']

        # Try to match patterns in order
        for param_type, config in param_patterns.items():
            if param_type == 'GENERIC':
                continue  # Skip GENERIC, use as fallback

            for pattern in config['patterns']:
                try:
                    if re.search(pattern, param_name, re.IGNORECASE):
                        return {
                            'type': param_type,
                            'description': config['description'],
                        }
                except re.error as e:
                    logger.warning(f"Invalid regex pattern '{pattern}': {e}")
                    continue

        # Fallback to GENERIC
        generic = param_patterns['GENERIC']
        return {
            'type': 'GENERIC',
            'description': generic['description'],
        }

    def _extract_parameters(
        self, http_request: HTTPRequest, request_id: str, parsed_url
    ) -> Tuple[List[Dict], List[Dict]]:
        """Extract and classify URL parameters."""
        nodes = []
        relationships = []

        query_params = parse_qs(parsed_url.query)
        template = self.rules['node_templates']['Parameter']

        for param_name, param_values in query_params.items():
            for idx, param_value in enumerate(param_values):
                classification = self._classify_parameter(
                    param_name, param_value
                )

                param_id = f"param_{hash(request_id + param_name + param_value + str(idx))}"

                param_node = {
                    'id': param_id,
                    'labels': ['Parameter', classification['type']]
                    + template.get('additional_labels', []),
                    'properties': {
                        'name': param_name,
                        'value': param_value,
                        'type': classification['type'],
                        'location': 'query',
                    },
                }
                nodes.append(param_node)

                relationships.append(
                    {
                        'source_id': request_id,
                        'target_id': param_id,
                        'type': 'HAS_PARAMETER',
                        'properties': {'position': idx, 'required': False},
                    }
                )

        return nodes, relationships

    def _classify_header(self, header_name: str) -> Optional[Dict[str, Any]]:
        """Classify header using YAML patterns. Returns None if header doesn't match any pattern."""
        header_patterns = self.rules['header_patterns']

        for category, config in header_patterns.items():
            if header_name in config['headers']:
                return {
                    'category': category,
                    'is_sensitive': config['is_sensitive'],
                    'description': config['description'],
                }

        # Return None for unmatched headers - they will be skipped
        return None

    def _extract_headers(
        self, http_request: HTTPRequest, request_id: str
    ) -> Tuple[List[Dict], List[Dict]]:
        """Extract and classify HTTP headers."""
        nodes = []
        relationships = []

        if not http_request.headers:
            return nodes, relationships

        template = self.rules['node_templates']['Header']

        for idx, (header_name, header_value) in enumerate(
            http_request.headers.items()
        ):
            classification = self._classify_header(header_name)
            
            # Skip headers that don't match any defined pattern
            if classification is None:
                continue

            header_id = f"header_{hash(request_id + header_name + str(idx))}"

            display_value = str(header_value)[:100]  # Truncate long values

            header_node = {
                'id': header_id,
                'labels': ['Header', classification['category']]
                + template.get('additional_labels', []),
                'properties': {
                    'name': header_name,
                    'value': display_value,
                    'is_sensitive': classification['is_sensitive'],
                    'category': classification['category'],
                },
            }
            nodes.append(header_node)

            relationships.append(
                {
                    'source_id': request_id,
                    'target_id': header_id,
                    'type': 'HAS_HEADER',
                    'properties': {'order': idx},
                }
            )
        return nodes, relationships

    def _extract_body(
        self, http_request: HTTPRequest, request_id: str
    ) -> Tuple[List[Dict], List[Dict]]:
        """Extract request body."""
        nodes = []
        relationships = []

        if not http_request.body:
            return nodes, relationships

        template = self.rules['node_templates']['Body']
        body_id = f"body_{hash(request_id + str(http_request.body))}"

        body_str = str(http_request.body)

        body_node = {
            'id': body_id,
            'labels': ['Body'] + template.get('additional_labels', []),
            'properties': {
                'content_type': (
                    http_request.headers.get('Content-Type', 'unknown')
                    if http_request.headers
                    else 'unknown'
                ),
                'size': len(body_str),
            },
        }
        nodes.append(body_node)

        relationships.append(
            {
                'source_id': request_id,
                'target_id': body_id,
                'type': 'HAS_BODY',
                'properties': {
                    'encoding': (
                        'json'
                        if isinstance(http_request.body, dict)
                        else 'text'
                    )
                },
            }
        )

        # Parse JSON fields
        if isinstance(http_request.body, dict):
            field_nodes, field_rels = self._parse_body_fields(
                http_request.body, body_id
            )
            nodes.extend(field_nodes)
            relationships.extend(field_rels)

        return nodes, relationships

    def _parse_body_fields(
        self, json_data: Dict, parent_id: str, prefix: str = '', depth: int = 0
    ) -> Tuple[List[Dict], List[Dict]]:
        """Recursively parse JSON body fields."""
        nodes = []
        relationships = []

        if depth > 5:  # Limit recursion depth
            return nodes, relationships

        for key, value in json_data.items():
            field_path = f"{prefix}.{key}" if prefix else key
            classification = self._classify_parameter(key, str(value))

            field_id = f"field_{hash(parent_id + field_path)}"

            field_node = {
                'id': field_id,
                'labels': ['BodyField', classification['type']],
                'properties': {
                    'name': key,
                    'value': (
                        str(value)[:100]
                        if not isinstance(value, (dict, list))
                        else None
                    ),
                    'type': classification['type'],
                    'path': field_path,
                },
            }
            nodes.append(field_node)

            relationships.append(
                {
                    'source_id': parent_id,
                    'target_id': field_id,
                    'type': 'HAS_FIELD',
                    'properties': {'depth': depth},
                }
            )

            # Recursively parse nested objects
            if isinstance(value, dict):
                nested_nodes, nested_rels = self._parse_body_fields(
                    value, field_id, field_path, depth + 1
                )
                nodes.extend(nested_nodes)
                relationships.extend(nested_rels)

        return nodes, relationships

    def _create_endpoint_node(self, parsed_url, method: str) -> Dict[str, Any]:
        """Create Endpoint node with pattern matching."""
        template = self.rules['node_templates']['Endpoint']
        path = parsed_url.path or '/'

        # Match endpoint patterns
        endpoint_type = 'GENERIC'
        requires_auth = False

        for pattern_config in self.rules['endpoint_patterns']:
            try:
                if re.match(pattern_config['pattern'], path):
                    endpoint_type = pattern_config['type']
                    requires_auth = pattern_config.get('requires_auth', False)
                    break
            except re.error as e:
                logger.warning(
                    f"Invalid regex pattern '{pattern_config['pattern']}': {e}"
                )
                continue

        endpoint_id = f"endpoint_{method}_{hash(path)}"

        return {
            'id': endpoint_id,
            'labels': ['Endpoint', endpoint_type]
            + template.get('additional_labels', []),
            'properties': {
                'path': path,
                'method': method,
                'domain': parsed_url.netloc,
                'type': endpoint_type,
                'requires_auth': requires_auth,
            },
        }

    def _decode_jwt_payload(self, token: str) -> Optional[Dict[str, Any]]:
        """Decode JWT payload (basic, without verification)."""
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

    def _extract_user(
        self, http_request: HTTPRequest, request_id: str
    ) -> Tuple[List[Dict], List[Dict]]:
        """Extract user information from auth headers."""
        nodes = []
        relationships = []

        if not self.rules.get('user_extraction'):
            return nodes, relationships

        user_config = self.rules['user_extraction']
        user_id = None
        username = None
        auth_method = None
        token_preview = None

        # Extract from Authorization header (JWT)
        if user_config.get('jwt', {}).get('enabled'):
            auth_header = http_request.headers.get('Authorization', '')
            prefix = user_config['jwt'].get('header_prefix', 'Bearer ')
            
            if auth_header.startswith(prefix):
                token = auth_header[len(prefix):]
                token_preview = token[:20] + '...' if len(token) > 20 else token
                payload = self._decode_jwt_payload(token)
                
                if payload:
                    # Extract user_id from JWT claims
                    for claim in user_config['jwt'].get('user_id_claims', []):
                        if claim in payload:
                            user_id = str(payload[claim])
                            break
                    
                    # Extract username from JWT claims  
                    for claim in user_config['jwt'].get('username_claims', []):
                        if claim in payload:
                            username = str(payload[claim])
                            break
                    
                    if user_id or username:
                        auth_method = 'jwt'

        # Extract from Cookie header
        if not user_id and user_config.get('cookie', {}).get('enabled'):
            cookie_header = http_request.headers.get('Cookie', '')
            patterns = user_config['cookie'].get('patterns', [])
            
            for pattern in patterns:
                try:
                    match = re.search(pattern, cookie_header)
                    if match:
                        if 'userId' in pattern or 'user_id' in pattern:
                            user_id = match.group(1)
                            auth_method = 'cookie'
                        elif 'username' in pattern:
                            username = match.group(1)
                            auth_method = 'cookie'
                except re.error:
                    continue

        # Create User node if we found user info
        if user_id or username:
            template = self.rules['node_templates'].get('User', {})
            # Use actual user_id for deterministic node ID (avoid duplicates)
            user_node_id = f"user_{user_id or username}"
            
            user_node = {
                'id': user_node_id,
                'labels': ['User'] + template.get('additional_labels', []),
                'properties': {
                    'user_id': user_id or 'unknown',
                    'username': username or 'unknown',
                    'auth_method': auth_method or 'unknown',
                    'token_preview': token_preview or ''
                },
            }
            nodes.append(user_node)

            # Create AUTHENTICATED_AS relationship
            relationships.append(
                {
                    'source_id': request_id,
                    'target_id': user_node_id,
                    'type': 'AUTHENTICATED_AS',
                    'properties': {
                        'auth_method': auth_method or 'unknown',
                        'timestamp': http_request.timestamp or '',
                    },
                }
            )

        return nodes, relationships

    def _extract_resources(
        self, http_request: HTTPRequest, request_id: str, parsed_url
    ) -> Tuple[List[Dict], List[Dict]]:
        """Extract resource information from URL and parameters."""
        nodes = []
        relationships = []

        if not self.rules.get('resource_extraction'):
            return nodes, relationships

        resource_config = self.rules['resource_extraction']
        resources_found = {}  # {(type, id): operation}

        # Extract from URL patterns
        path = parsed_url.path or '/'
        method = http_request.method.upper()
        
        for pattern_config in resource_config.get('url_patterns', []):
            try:
                match = re.match(pattern_config['pattern'], path)
                if match:
                    resource_type = pattern_config['resource_type']
                    id_group = pattern_config.get('id_group', 1)
                    resource_id = match.group(id_group)
                    
                    # Determine operation from HTTP method
                    operation_map = {
                        'GET': 'read',
                        'POST': 'create',
                        'PUT': 'update',
                        'PATCH': 'update',
                        'DELETE': 'delete'
                    }
                    operation = operation_map.get(method, 'access')
                    
                    resources_found[(resource_type, resource_id)] = operation
                    break
            except (re.error, IndexError):
                continue

        # Extract from parameters
        param_patterns = resource_config.get('parameter_patterns', {})
        query_params = parse_qs(parsed_url.query)
        
        for resource_type, param_names in param_patterns.items():
            for param_name in param_names:
                if param_name in query_params:
                    resource_id = query_params[param_name][0]
                    if (resource_type, resource_id) not in resources_found:
                        resources_found[(resource_type, resource_id)] = 'access'

        # Create Resource nodes
        template = self.rules['node_templates'].get('Resource', {})
        
        for (resource_type, resource_id), operation in resources_found.items():
            # Use resource_type and ID for deterministic node ID (avoid duplicates)
            resource_node_id = f"resource_{resource_type}_{resource_id}"
            
            resource_node = {
                'id': resource_node_id,
                'labels': ['Resource', resource_type.upper()]
                + template.get('additional_labels', []),
                'properties': {
                    'resource_id': str(resource_id),
                    'resource_type': resource_type,
                    'operation': operation,
                },
            }
            nodes.append(resource_node)

            # Create ACCESSES relationship
            relationships.append(
                {
                    'source_id': request_id,
                    'target_id': resource_node_id,
                    'type': 'ACCESSES',
                    'properties': {
                        'operation': operation,
                        'access_type': 'direct',
                    },
                }
            )

        return nodes, relationships

