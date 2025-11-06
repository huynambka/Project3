"""Flask server for receiving HTTP traffic from BurpSuite."""

from .app import create_app, run_server

__all__ = ["create_app", "run_server"]
