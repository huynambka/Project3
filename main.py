"""Main entry point for IDOR Detection Tool."""

import argparse
import logging
import sys
from src.config import get_settings
from src.utils import setup_logging
from src.graph_db import Neo4jClient, GraphBuilder
from src.server import create_app, run_server
from src.parsers import HTTPParser
from src.models import HTTPMessage
from src.ai import GeminiClient, BatchProcessor
from src.ai.gemini_graph_loader import GeminiGraphLoader

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
    """Run Flask server to receive traffic from BurpSuite with AI batch processing."""
    logger.info(
        f"Starting server on {settings.server_host}:{settings.server_port}"
    )
    logger.info(f"Batch size: {settings.batch_size} messages")

    # Connect to Neo4j and create constraints
    neo4j_client.connect()
    neo4j_client.create_constraints()
    logger.info("Neo4j constraints created")

    # Initialize Gemini client
    gemini_client = GeminiClient(settings)
    graph_loader = GeminiGraphLoader(neo4j_client)

    # Define batch processing callback
    def process_batch(batch):
        """Process a complete batch of messages."""
        logger.info(f"Processing batch of {len(batch)} messages with Gemini...")

        # Convert batch to graph data using Gemini
        graph_data = gemini_client.convert_batch_to_graph_data(batch)

        if graph_data:
            # Load into Neo4j
            logger.info("Loading graph data into Neo4j...")
            graph_loader.load_graph_data(graph_data)
            logger.info("Batch processing complete!")
        else:
            logger.error("Failed to convert batch to graph data")

    # Create batch processor
    batch_processor = BatchProcessor(settings, process_batch)

    # Create and run Flask app
    app = create_app(settings, batch_processor)
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
