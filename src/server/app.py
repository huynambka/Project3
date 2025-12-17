"""Flask application factory."""

from flask import Flask, request, jsonify
from typing import Optional
from ..config import Settings
from ..graph_db import Neo4jClient
from ..graph_db.rule_based_loader import RuleBasedGraphLoader
from ..parsers import HTTPParser
from ..models import HTTPMessage
import logging

logger = logging.getLogger(__name__)


def create_app(
    settings: Settings,
    neo4j_client: Optional[Neo4jClient] = None,
    graph_loader: Optional[RuleBasedGraphLoader] = None,
) -> Flask:
    """Create and configure Flask application.

    Args:
        settings: Application settings
        batch_processor: Optional batch processor for handling messages in batches
    """
    app = Flask(__name__)

    @app.route('/health', methods=['GET'])
    def health():
        """Health check endpoint."""
        return (
            jsonify({"status": "healthy", "parsing_method": "rule-based"}),
            200,
        )

    @app.route('/analyze', methods=['POST'])
    def analyze():
        """Receive and analyze HTTP traffic from BurpSuite extension in real-time."""
        try:
            data = request.get_json()

            if not data or 'request' not in data or 'response' not in data:
                return jsonify({"error": "Missing request or response"}), 400

            if not neo4j_client or not graph_loader:
                return jsonify({"error": "Server not properly configured"}), 503

            request_raw = data['request']
            response_raw = data['response']
            timestamp = data.get('timestamp', '')

            # Parse HTTP request
            http_parser = HTTPParser()
            http_request = http_parser.parse_request(request_raw, timestamp)

            # Process immediately (real-time)
            result = graph_loader.load_request(http_request)

            logger.info(
                f"Processed {http_request.method} {http_request.url}: "
                f"{result['nodes_created']} nodes, {result['relationships_created']} relationships"
            )

            return (
                jsonify(
                    {
                        "status": "success",
                        "message": "Request analyzed and loaded into graph",
                        "nodes_created": result['nodes_created'],
                        "relationships_created": result[
                            'relationships_created'
                        ],
                    }
                ),
                200,
            )

        except Exception as e:
            logger.error(f"Error analyzing request: {e}", exc_info=True)
            return jsonify({"error": str(e)}), 500

    @app.route('/statistics', methods=['GET'])
    def get_statistics():
        """Get graph statistics."""
        try:
            if not neo4j_client:
                return jsonify({"error": "Neo4j client not configured"}), 503

            from ..graph_db.rule_based_loader import RuleBasedGraphLoader

            loader = RuleBasedGraphLoader(neo4j_client)

            stats = loader.get_statistics()

            return jsonify(stats), 200

        except Exception as e:
            logger.error(f"Error getting statistics: {e}", exc_info=True)
            return jsonify({"error": str(e)}), 500

    @app.route('/config', methods=['GET'])
    def get_config():
        """Get current parser configuration."""
        return (
            jsonify(
                {
                    "parsing_method": "rule-based",
                    "rules_file": settings.rules_file_path,
                    "processing_mode": "real-time",
                    "debug": settings.debug,
                }
            ),
            200,
        )

    return app


def run_server(app: Flask, settings: Settings) -> None:
    """Run the Flask server."""
    app.run(
        host=settings.server_host,
        port=settings.server_port,
        debug=settings.debug,
    )
