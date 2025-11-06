"""Neo4j database client."""

import json
from typing import Dict, Any, List, Optional
from neo4j import GraphDatabase, Driver, Session
from ..config import Settings


class Neo4jClient:
    """Neo4j database connection and operations."""

    def __init__(self, settings: Settings):
        """Initialize Neo4j client with settings."""
        self.settings = settings
        self.driver: Optional[Driver] = None

    def connect(self) -> None:
        """Establish connection to Neo4j."""
        self.driver = GraphDatabase.driver(
            self.settings.neo4j_uri,
            auth=(self.settings.neo4j_user, self.settings.neo4j_password),
        )

    def close(self) -> None:
        """Close Neo4j connection."""
        if self.driver:
            self.driver.close()

    def __enter__(self) -> "Neo4jClient":
        """Context manager entry."""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit."""
        self.close()

    def create_constraints(self) -> None:
        """Create uniqueness constraints for node types."""
        labels = [
            "Endpoint",
            "Request",
            "Response",
            "UserSession",
            "Resource",
            "Parameter",
        ]

        with self.driver.session() as session:
            for label in labels:
                session.execute_write(
                    lambda tx: tx.run(
                        f"CREATE CONSTRAINT IF NOT EXISTS FOR (n:{label}) REQUIRE n.id IS UNIQUE"
                    )
                )

    def create_node(
        self, label: str, node_id: str, properties: Dict[str, Any]
    ) -> None:
        """Create or update a node."""
        props = self._serialize_properties(properties)

        with self.driver.session() as session:
            session.execute_write(
                lambda tx: tx.run(
                    f"MERGE (n:{label} {{id: $id}}) SET n += $props",
                    id=node_id,
                    props=props,
                )
            )

    def create_relationship(
        self,
        from_id: str,
        to_id: str,
        from_label: str,
        to_label: str,
        rel_type: str,
    ) -> None:
        """Create a relationship between two nodes."""
        with self.driver.session() as session:
            session.execute_write(
                lambda tx: tx.run(
                    f"MATCH (a:{from_label} {{id: $from_id}}), (b:{to_label} {{id: $to_id}}) "
                    f"MERGE (a)-[:{rel_type}]->(b)",
                    from_id=from_id,
                    to_id=to_id,
                )
            )

    def get_node_counts(self) -> Dict[str, int]:
        """Get count of nodes by label."""
        labels = [
            "Endpoint",
            "Request",
            "Response",
            "UserSession",
            "Resource",
            "Parameter",
        ]
        counts = {}

        with self.driver.session() as session:
            for label in labels:
                result = session.run(f"MATCH (n:{label}) RETURN count(n) AS c")
                counts[label] = result.single().get("c", 0)

        return counts

    def get_relationships(self, limit: int = 25) -> List[Dict[str, Any]]:
        """Get sample relationships."""
        with self.driver.session() as session:
            query = """
            MATCH (a)-[r]->(b) 
            RETURN labels(a) AS from_labels, a.id AS from_id, 
                   type(r) AS rel_type, 
                   labels(b) AS to_labels, b.id AS to_id 
            LIMIT $limit
            """
            result = session.run(query, limit=limit)
            return [dict(record) for record in result]

    @staticmethod
    def _serialize_properties(props: Dict[str, Any]) -> Dict[str, Any]:
        """Convert nested dicts/lists to JSON strings for Neo4j compatibility."""
        result = {}
        for k, v in props.items():
            if isinstance(v, (dict, list)):
                result[k] = json.dumps(v)
            elif v is not None:
                result[k] = v
        return result
