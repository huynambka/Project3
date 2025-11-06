"""HTTP message models for parsing requests and responses."""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional


@dataclass
class HTTPRequest:
    """Parsed HTTP request."""

    method: str
    path: str
    version: str
    headers: Dict[str, str]
    body: Optional[Any] = None
    raw: str = ""

    @property
    def has_json_body(self) -> bool:
        """Check if request has JSON body."""
        content_type = self.headers.get("Content-Type", "")
        return "application/json" in content_type and self.body is not None


@dataclass
class HTTPResponse:
    """Parsed HTTP response."""

    version: str
    status_code: int
    status_message: str
    headers: Dict[str, str]
    body: Optional[Any] = None
    raw: str = ""

    @property
    def has_json_body(self) -> bool:
        """Check if response has JSON body."""
        content_type = self.headers.get("Content-Type", "")
        return "application/json" in content_type and self.body is not None


@dataclass
class HTTPMessage:
    """Combined HTTP request and response pair."""

    request: HTTPRequest
    response: HTTPResponse
    timestamp: str

    @property
    def endpoint_pattern(self) -> str:
        """Extract endpoint pattern from path (replace numeric IDs with {id})."""
        import re

        path = self.request.path
        # Replace numeric path segments with {id}
        pattern = re.sub(r'/\d+', '/{id}', path)
        # Replace UUID-like segments
        pattern = re.sub(
            r'/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}',
            '/{id}',
            pattern,
            flags=re.IGNORECASE,
        )
        return pattern
