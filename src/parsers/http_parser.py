"""Parser for raw HTTP messages."""

import json
import re
from typing import Dict, Any, Optional, Tuple
from ..models import HTTPRequest, HTTPResponse, HTTPMessage


class HTTPParser:
    """Parse raw HTTP request and response strings."""

    @staticmethod
    def parse_request(raw: str, timestamp: str = "") -> HTTPRequest:
        """Parse raw HTTP request string."""
        lines = raw.split('\r\n')

        # Parse request line
        request_line = lines[0]
        parts = request_line.split(' ', 2)
        if len(parts) != 3:
            raise ValueError(f"Invalid request line: {request_line}")

        method, path, version = parts

        # Parse headers
        headers = {}
        body_start = 0
        for i, line in enumerate(lines[1:], 1):
            if line == '':
                body_start = i + 1
                break
            if ':' in line:
                key, value = line.split(':', 1)
                headers[key.strip()] = value.strip()

        # Parse body
        body_raw = (
            '\r\n'.join(lines[body_start:]) if body_start < len(lines) else ''
        )
        body = HTTPParser._parse_body(body_raw, headers.get('Content-Type', ''))

        return HTTPRequest(
            method=method,
            path=path,
            version=version,
            headers=headers,
            body=body,
            raw=raw,
            timestamp=timestamp,
        )

    @staticmethod
    def parse_response(raw: str) -> HTTPResponse:
        """Parse raw HTTP response string."""
        lines = raw.split('\r\n')

        # Parse status line
        status_line = lines[0]
        parts = status_line.split(' ', 2)
        if len(parts) < 2:
            raise ValueError(f"Invalid status line: {status_line}")

        version = parts[0]
        status_code = int(parts[1])
        status_message = parts[2] if len(parts) > 2 else ''

        # Parse headers
        headers = {}
        body_start = 0
        for i, line in enumerate(lines[1:], 1):
            if line == '':
                body_start = i + 1
                break
            if ':' in line:
                key, value = line.split(':', 1)
                headers[key.strip()] = value.strip()

        # Parse body
        body_raw = (
            '\r\n'.join(lines[body_start:]) if body_start < len(lines) else ''
        )
        body = HTTPParser._parse_body(body_raw, headers.get('Content-Type', ''))

        return HTTPResponse(
            version=version,
            status_code=status_code,
            status_message=status_message,
            headers=headers,
            body=body,
            raw=raw,
        )

    @staticmethod
    def parse_message(
        request_raw: str, response_raw: str, timestamp: str
    ) -> HTTPMessage:
        """Parse both request and response into an HTTPMessage."""
        request = HTTPParser.parse_request(request_raw)
        response = HTTPParser.parse_response(response_raw)
        return HTTPMessage(
            request=request,
            response=response,
            timestamp=timestamp,
        )

    @staticmethod
    def _parse_body(body_raw: str, content_type: str) -> Optional[Any]:
        """Parse body based on content type."""
        if not body_raw or not body_raw.strip():
            return None

        if 'application/json' in content_type:
            try:
                return json.loads(body_raw)
            except json.JSONDecodeError:
                return body_raw

        return body_raw

    @staticmethod
    def extract_path_params(path: str, pattern: str) -> Dict[str, str]:
        """Extract path parameters by comparing actual path with pattern."""
        # Convert pattern like /api/users/{id} to regex
        regex_pattern = re.sub(r'\{(\w+)\}', r'(?P<\1>[^/]+)', pattern)
        regex_pattern = f"^{regex_pattern}$"

        match = re.match(regex_pattern, path)
        if match:
            return match.groupdict()
        return {}
