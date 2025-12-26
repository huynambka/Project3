"""
Rule-based graph loader using YAML parser.
Loads HTTP requests into Neo4j without relying on external AI services.
"""

from typing import List, Dict, Any
from ..parsers.yaml_rule_parser import YAMLRuleBasedParser
from ..models.http_models import HTTPRequest
from ..graph_db.neo4j_client import Neo4jClient
from ..utils.logger import get_logger


logger = get_logger(__name__)


class RuleBasedGraphLoader:
    """
    Load HTTP requests into Neo4j graph using rule-based parsing.
    This replaces AI-dependent parsing with deterministic rule-based approach.
    """

    def __init__(self, neo4j_client: Neo4jClient, rules_path: str = None):
        """
        Initialize rule-based graph loader.

        Args:
            neo4j_client: Neo4j client instance
            rules_path: Optional path to custom YAML rules file
        """
        self.neo4j_client = neo4j_client
        self.parser = YAMLRuleBasedParser(rules_path)
        # Track last request ID per user for temporal ordering
        self.user_last_request = {}  # {user_id: (request_id, timestamp)}
        logger.info("Rule-based graph loader initialized")

    def load_requests(self, requests: List[HTTPRequest]) -> Dict[str, Any]:
        """
        Parse and load multiple HTTP requests into Neo4j graph.

        Args:
            requests: List of HTTP requests to process

        Returns:
            Dict with loading statistics
        """
        stats = {
            'total_requests': len(requests),
            'loaded_count': 0,
            'failed_count': 0,
            'total_nodes': 0,
            'total_relationships': 0,
            'errors': [],
        }

        logger.info(f"Starting to load {len(requests)} requests")

        for idx, request in enumerate(requests, 1):
            try:
                result = self.load_request(request)
                stats['loaded_count'] += 1
                stats['total_nodes'] += result['nodes_created']
                stats['total_relationships'] += result['relationships_created']

                if idx % 10 == 0:
                    logger.info(f"Processed {idx}/{len(requests)} requests")

            except Exception as e:
                stats['failed_count'] += 1
                error_msg = f"Failed to load request {idx}: {str(e)}"
                stats['errors'].append(error_msg)
                logger.error(error_msg, exc_info=True)

        logger.info(
            f"Loading complete: {stats['loaded_count']} successful, "
            f"{stats['failed_count']} failed"
        )

        return stats

    def load_request(self, http_request: HTTPRequest) -> Dict[str, Any]:
        """
        Parse and load a single HTTP request into Neo4j graph.

        Args:
            http_request: HTTP request to process

        Returns:
            Dict with loading results
        """
        # Parse request using YAML rules
        graph_data = self.parser.parse_request(http_request)

        nodes_created = 0
        relationships_created = 0

        # Create nodes
        for node in graph_data['nodes']:
            self._create_node(node)
            nodes_created += 1

        # Create relationships
        for rel in graph_data['relationships']:
            self._create_relationship(rel)
            relationships_created += 1

        # Find User node and Request node to create temporal ordering
        request_node = None
        user_node = None
        
        for node in graph_data['nodes']:
            if 'Request' in node['labels']:
                request_node = node
            elif 'User' in node['labels']:
                user_node = node
        
        # Create FOLLOWS relationship if this user had a previous request
        if user_node and request_node:
            user_id = user_node['properties'].get('user_id')
            current_timestamp = request_node['properties'].get('timestamp', '')
            
            if user_id and user_id in self.user_last_request:
                prev_request_id, prev_timestamp = self.user_last_request[user_id]
                
                # Calculate time delta
                time_delta = 0
                try:
                    from datetime import datetime
                    if current_timestamp and prev_timestamp:
                        curr_dt = datetime.fromisoformat(current_timestamp.replace('Z', '+00:00'))
                        prev_dt = datetime.fromisoformat(prev_timestamp.replace('Z', '+00:00'))
                        time_delta = int((curr_dt - prev_dt).total_seconds())
                except Exception:
                    pass
                
                # Create FOLLOWS relationship
                follows_rel = {
                    'source_id': prev_request_id,
                    'target_id': request_node['id'],
                    'type': 'FOLLOWS',
                    'properties': {
                        'time_delta': time_delta,
                        'request_sequence': 'next'
                    }
                }
                self._create_relationship(follows_rel)
                relationships_created += 1
            
            # Update last request for this user
            if user_id:
                self.user_last_request[user_id] = (request_node['id'], current_timestamp)

        logger.debug(
            f"Loaded request {http_request.method} {http_request.url}: "
            f"{nodes_created} nodes, {relationships_created} relationships"
        )

        return {
            'nodes_created': nodes_created,
            'relationships_created': relationships_created,
        }

    def _create_node(self, node: Dict[str, Any]) -> None:
        """
        Create a node in Neo4j.

        Args:
            node: Node data with id, labels, and properties
        """
        labels = ':'.join(node['labels'])
        properties = node['properties']

        query = f"""
        MERGE (n:{labels} {{id: $id}})
        SET n += $properties
        RETURN n
        """

        try:
            self.neo4j_client.execute_query(
                query, {'id': node['id'], 'properties': properties}
            )
        except Exception as e:
            logger.error(f"Failed to create node {node['id']}: {e}")
            raise

    def _create_relationship(self, rel: Dict[str, Any]) -> None:
        """
        Create a relationship in Neo4j.

        Args:
            rel: Relationship data with source_id, target_id, type, and properties
        """
        rel_type = rel['type']
        properties = rel.get('properties', {})

        # Build SET clause for properties
        set_clause = ""
        if properties:
            set_clause = "SET r += $properties"

        query = f"""
        MATCH (a {{id: $source_id}})
        MATCH (b {{id: $target_id}})
        MERGE (a)-[r:{rel_type}]->(b)
        {set_clause}
        RETURN r
        """

        params = {'source_id': rel['source_id'], 'target_id': rel['target_id']}

        if properties:
            params['properties'] = properties

        try:
            self.neo4j_client.execute_query(query, params)
        except Exception as e:
            logger.error(
                f"Failed to create relationship {rel['source_id']} -[{rel_type}]-> "
                f"{rel['target_id']}: {e}"
            )
            raise

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about the loaded graph data.

        Returns:
            Dict with graph statistics
        """
        query = """
        MATCH (n)
        WITH labels(n) as nodeLabels, count(*) as count
        UNWIND nodeLabels as label
        RETURN label, sum(count) as total
        ORDER BY total DESC
        """

        try:
            node_stats = self.neo4j_client.execute_query(query)

            rel_query = """
            MATCH ()-[r]->()
            RETURN type(r) as relationship_type, count(*) as count
            ORDER BY count DESC
            """

            rel_stats = self.neo4j_client.execute_query(rel_query)

            return {
                'nodes': [dict(record) for record in node_stats],
                'relationships': [dict(record) for record in rel_stats],
            }

        except Exception as e:
            logger.error(f"Failed to get statistics: {e}")
            return {'nodes': [], 'relationships': []}

    def clear_graph(self) -> None:
        """Clear all nodes and relationships from the graph."""
        query = "MATCH (n) DETACH DELETE n"

        try:
            self.neo4j_client.execute_query(query)
            logger.info("Graph cleared successfully")
        except Exception as e:
            logger.error(f"Failed to clear graph: {e}")
            raise
