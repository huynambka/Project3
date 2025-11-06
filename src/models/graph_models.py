"""Graph database node and relationship models."""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List
from uuid import uuid4


@dataclass
class Endpoint:
    """API endpoint node."""

    id: str
    path: str
    pattern: str
    method: str

    @classmethod
    def create(cls, path: str, pattern: str, method: str) -> "Endpoint":
        """Create new endpoint with generated ID."""
        return cls(
            id=f"endpoint_{uuid4().hex[:8]}",
            path=path,
            pattern=pattern,
            method=method,
        )


@dataclass
class Request:
    """HTTP request node."""

    id: str
    endpoint_id: str
    headers: Dict[str, str]
    body: Optional[Any] = None

    @classmethod
    def create(
        cls,
        endpoint_id: str,
        headers: Dict[str, str],
        body: Optional[Any] = None,
    ) -> "Request":
        """Create new request with generated ID."""
        return cls(
            id=f"request_{uuid4().hex[:8]}",
            endpoint_id=endpoint_id,
            headers=headers,
            body=body,
        )


@dataclass
class Response:
    """HTTP response node."""

    id: str
    request_id: str
    status_code: int
    body: Optional[Any] = None

    @classmethod
    def create(
        cls, request_id: str, status_code: int, body: Optional[Any] = None
    ) -> "Response":
        """Create new response with generated ID."""
        return cls(
            id=f"response_{uuid4().hex[:8]}",
            request_id=request_id,
            status_code=status_code,
            body=body,
        )


@dataclass
class UserSession:
    """User session node."""

    id: str
    user_id: Optional[int]
    username: Optional[str]
    token: Optional[str]

    @classmethod
    def create(
        cls,
        user_id: Optional[int] = None,
        username: Optional[str] = None,
        token: Optional[str] = None,
    ) -> "UserSession":
        """Create new session with generated ID."""
        return cls(
            id=f"session_{uuid4().hex[:8]}",
            user_id=user_id,
            username=username,
            token=token,
        )


@dataclass
class Resource:
    """Resource node (user data, objects accessed)."""

    id: str
    type: str
    data: Dict[str, Any]

    @classmethod
    def create(cls, resource_type: str, data: Dict[str, Any]) -> "Resource":
        """Create new resource with generated ID."""
        return cls(
            id=f"resource_{uuid4().hex[:8]}",
            type=resource_type,
            data=data,
        )


@dataclass
class Parameter:
    """Request parameter node."""

    id: str
    request_id: str
    type: str  # "body", "path", "query", "header"
    key: str
    value: Any

    @classmethod
    def create(
        cls, request_id: str, param_type: str, key: str, value: Any
    ) -> "Parameter":
        """Create new parameter with generated ID."""
        return cls(
            id=f"param_{uuid4().hex[:8]}",
            request_id=request_id,
            type=param_type,
            key=key,
            value=value,
        )
