"""Flask application factory."""

from flask import Flask, request, jsonify
from typing import Optional
from ..config import Settings
from ..ai import BatchProcessor


def create_app(
    settings: Settings, batch_processor: Optional[BatchProcessor] = None
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
        return jsonify({"status": "healthy"}), 200

    @app.route('/status', methods=['GET'])
    def status():
        """Get batch processor status."""
        if batch_processor:
            return jsonify(batch_processor.get_status()), 200
        return jsonify({"error": "Batch processor not configured"}), 503

    @app.route('/analyze', methods=['POST'])
    def analyze():
        """Receive HTTP traffic from BurpSuite extension."""
        try:
            data = request.get_json()

            if not data or 'request' not in data or 'response' not in data:
                return jsonify({"error": "Missing request or response"}), 400

            request_raw = data['request']
            response_raw = data['response']
            timestamp = data.get('timestamp', '')

            if not batch_processor:
                return jsonify({"error": "Batch processor not configured"}), 503

            # Add message to batch queue
            result = batch_processor.add_message(
                request_raw, response_raw, timestamp
            )

            return jsonify(result), 200

        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route('/flush', methods=['POST'])
    def flush():
        """Force process current batch even if not full."""
        try:
            if not batch_processor:
                return jsonify({"error": "Batch processor not configured"}), 503

            count = batch_processor.flush()
            if count is None:
                return (
                    jsonify(
                        {"status": "empty", "message": "No messages to flush"}
                    ),
                    200,
                )

            return (
                jsonify(
                    {
                        "status": "flushed",
                        "message": f"Flushed {count} messages for processing",
                    }
                ),
                200,
            )

        except Exception as e:
            return jsonify({"error": str(e)}), 500

    return app


def run_server(app: Flask, settings: Settings) -> None:
    """Run the Flask server."""
    app.run(
        host=settings.server_host,
        port=settings.server_port,
        debug=settings.debug,
    )
