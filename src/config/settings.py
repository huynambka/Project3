"""Application settings and configuration."""

import os
from dataclasses import dataclass
from typing import Optional
from pathlib import Path

# Load .env file if it exists
try:
    from dotenv import load_dotenv

    env_path = Path(__file__).parent.parent.parent / '.env'
    load_dotenv(env_path)
except ImportError:
    pass  # dotenv not installed, will use system env vars


@dataclass
class Settings:
    """Application configuration settings."""

    # Neo4j settings
    neo4j_uri: str
    neo4j_user: str
    neo4j_password: str

    # Google Gemini settings
    gemini_api_key: str

    # Server settings
    server_host: str
    server_port: int

    # Application settings
    debug: bool = False
    log_level: str = "INFO"
    batch_size: int = 5

    @classmethod
    def from_env(cls) -> "Settings":
        """Load settings from environment variables."""
        return cls(
            neo4j_uri=os.getenv("NEO4J_URI", "bolt://localhost:7687"),
            neo4j_user=os.getenv("NEO4J_USER", "neo4j"),
            neo4j_password=os.getenv("NEO4J_PASSWORD", "neo4j"),
            gemini_api_key=os.getenv("GEMINI_API_KEY", ""),
            server_host=os.getenv("SERVER_HOST", "0.0.0.0"),
            server_port=int(os.getenv("SERVER_PORT", "5000")),
            debug=os.getenv("DEBUG", "false").lower() == "true",
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            batch_size=int(os.getenv("BATCH_SIZE", "5")),
        )


_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """Get the global settings instance."""
    global _settings
    if _settings is None:
        _settings = Settings.from_env()
    return _settings
