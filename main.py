"""Main entry point for IDOR Detection Tool."""

import argparse
import logging
import sys
from src.config import get_settings
from src.utils import setup_logging
from src.utils.batch_processor import BatchProcessor
from src.graph_db import Neo4jClient, GraphBuilder
from src.graph_db.rule_based_loader import RuleBasedGraphLoader
from src.server import create_app, run_server
from src.parsers import HTTPParser
from src.models import HTTPMessage

logger = logging.getLogger(__name__)


def main():
    """Main application entry point."""
    parser = argparse.ArgumentParser(
        description="IDOR Vulnerability Detection Tool"
    )
    parser.add_argument(
        '--mode',
        choices=['server', 'load', 'present'],
        default='server',
        help='Operation mode: server (run Flask server), load (load JSON file), present (show graph)',
    )
    parser.add_argument(
        '--file', type=str, help='JSON file to load (for load mode)'
    )

    args = parser.parse_args()

    # Load settings
    settings = get_settings()
    setup_logging(settings.log_level)

    logger.info(f"Starting IDOR Detection Tool in {args.mode} mode")
    logger.info(f"Neo4j URI: {settings.neo4j_uri}")

    # Initialize Neo4j client
    neo4j_client = Neo4jClient(settings)

    try:
        if args.mode == 'server':
            run_server_mode(settings, neo4j_client)
        elif args.mode == 'load':
            run_load_mode(args.file, neo4j_client)
        elif args.mode == 'present':
            run_present_mode(neo4j_client)
    except KeyboardInterrupt:
        logger.info("Shutting down...")
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        sys.exit(1)
    finally:
        neo4j_client.close()


def run_server_mode(settings, neo4j_client: Neo4jClient):
    """Run Flask server to receive traffic from BurpSuite with rule-based parsing."""
    logger.info(
        f"Starting server on {settings.server_host}:{settings.server_port}"
    )
    logger.info("Using RULE-BASED parsing (no AI dependency)")
    logger.info("Processing requests in REAL-TIME (no batching needed)")

    # Connect to Neo4j and create constraints
    neo4j_client.connect()
    neo4j_client.create_constraints()
    logger.info("Neo4j constraints created")

    # Initialize rule-based loader
    graph_loader = RuleBasedGraphLoader(neo4j_client, settings.rules_file_path)
    logger.info(f"Loaded parsing rules from {settings.rules_file_path}")

    # Create and run Flask app
    app = create_app(settings, neo4j_client, graph_loader)
    run_server(app, settings)


def run_load_mode(file_path: str, neo4j_client: Neo4jClient):
    """Load data from JSON file into Neo4j."""
    import json

    if not file_path:
        logger.error("--file argument required for load mode")
        sys.exit(1)

    logger.info(f"Loading data from {file_path}")

    neo4j_client.connect()
    neo4j_client.create_constraints()
    logger.info("Neo4j constraints created")

    graph_builder = GraphBuilder(neo4j_client)

    # Read file - support both JSON array and JSONL (newline-delimited JSON)
    with open(file_path, 'r', encoding='utf-8') as f:
        first_char = f.read(1)
        f.seek(0)

        if first_char == '[':
            # Standard JSON array
            data = json.load(f)
        else:
            # JSONL format - one JSON object per line
            data = []
            for line in f:
                line = line.strip()
                if line:
                    data.append(json.loads(line))

    # Process each message
    for item in data:
        if 'request' in item and 'response' in item:
            message = HTTPParser.parse_message(
                item['request'], item['response'], item.get('timestamp', '')
            )
            logger.info(
                f"Processing: {message.request.method} {message.request.path}"
            )
            graph_builder.process_message(message)

    logger.info(f"Data loaded successfully - processed {len(data)} messages")


def run_present_mode(neo4j_client: Neo4jClient):
    """Present graph statistics."""
    logger.info("Connecting to Neo4j...")
    neo4j_client.connect()

    # Get node counts
    counts = neo4j_client.get_node_counts()
    print("\n=== Node Counts ===")
    for label, count in counts.items():
        print(f"  {label}: {count}")

    # Get relationships
    relationships = neo4j_client.get_relationships(limit=25)
    print(f"\n=== Relationships (showing {len(relationships)}) ===")
    for rel in relationships:
        from_label = rel['from_labels'][0] if rel['from_labels'] else 'Unknown'
        to_label = rel['to_labels'][0] if rel['to_labels'] else 'Unknown'
        print(
            f"  {from_label}({rel['from_id']}) -[{rel['rel_type']}]-> {to_label}({rel['to_id']})"
        )

    print(f"\nNeo4j Browser: http://localhost:7474")


if __name__ == '__main__':
    main()
