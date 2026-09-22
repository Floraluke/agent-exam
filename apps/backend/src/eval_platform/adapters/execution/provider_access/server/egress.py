"""The only place the proxy opens a socket: one HTTPS POST, exactly once.

The request type already refuses retrying and following redirects; this module adds the
socket facts — one connection, one attempt, a read timeout — and turns whatever the
upstream answers into a fixed code instead of a second call. No byte of the answer is
logged, kept or reinterpreted: the body is handed to the caller unchanged.

This module does not decide which client headers travel. `service` drops the headers the
proxy's own inbound connection owns and `request_policy` forwards only its whitelisted
set, so `OutboundRequest.headers` is already the minimal business set and nothing here
can collide with the `Host`, `Content-Length` and `Accept-Encoding` the library adds.

The connector is injectable because the proxy-to-upstream leg must be TLS while the fake
upstream is plain HTTP: the integration slice supplies the wrapper, and no path here
pretends that wrapper already exists.
"""

from __future__ import annotations

import http.client
from collections.abc import Callable, Iterator
from urllib.parse import urlsplit

from eval_platform.adapters.execution.provider_access.server.contracts import (
    ProviderRejection,
)
from eval_platform.adapters.execution.provider_access.transport import OutboundRequest

READ_CHUNK_BYTES = 8 * 1024
UPSTREAM_TIMEOUT_SECONDS = 300.0
OK_STATUS = 200
REDIRECT_STATUSES = frozenset(range(300, 400))
UNAUTHORIZED_STATUSES = frozenset({401, 403})
RATE_LIMITED_STATUS = 429

Connector = Callable[[str, int, float], http.client.HTTPConnection]


class UpstreamFailure(ProviderRejection):
    """The call left the proxy and no answer came back that a client may read."""


def https_connector(host: str, port: int, timeout: float) -> http.client.HTTPConnection:
    """The production connector: TLS, with certificate verification at its default."""

    return http.client.HTTPSConnection(host, port, timeout=timeout)


def open_stream(
    request: OutboundRequest,
    *,
    connector: Connector = https_connector,
    timeout: float = UPSTREAM_TIMEOUT_SECONDS,
) -> Iterator[bytes]:
    """Perform the single permitted call and yield the answer bytes unchanged."""

    parts = urlsplit(request.url)
    if parts.scheme != "https" or not parts.hostname:
        raise UpstreamFailure("TRANSPORT_UPSTREAM_NOT_ENCRYPTED")
    try:
        connection = connector(parts.hostname, parts.port or 443, timeout)
    except (OSError, http.client.HTTPException):
        raise UpstreamFailure("TRANSPORT_CONNECTION_FAILED") from None
    try:
        response = _answer(connection, request, parts.path or "/")
        while True:
            try:
                chunk = response.read(READ_CHUNK_BYTES)
            except TimeoutError:
                raise UpstreamFailure("TRANSPORT_UPSTREAM_TIMEOUT") from None
            except (OSError, http.client.HTTPException):
                raise UpstreamFailure("TRANSPORT_STREAM_INTERRUPTED") from None
            if not chunk:
                return
            yield chunk
    finally:
        connection.close()


def _answer(
    connection: http.client.HTTPConnection, request: OutboundRequest, path: str
) -> http.client.HTTPResponse:
    headers = dict(request.send_headers())
    try:
        # `request` rather than hand-written headers: it supplies the Content-Length,
        # Host and Accept-Encoding nobody else may set, so framing cannot drift.
        connection.request(
            "POST", path, body=request.payload, headers=headers, encode_chunked=False
        )
        response = connection.getresponse()
    except TimeoutError:
        raise UpstreamFailure("TRANSPORT_UPSTREAM_TIMEOUT") from None
    except (OSError, http.client.HTTPException):
        raise UpstreamFailure("TRANSPORT_CONNECTION_FAILED") from None
    if response.status in REDIRECT_STATUSES:
        response.close()
        raise UpstreamFailure("TRANSPORT_REDIRECT_NOT_PERMITTED")
    if response.status != OK_STATUS:
        response.close()
        raise UpstreamFailure(code_for_status(response.status))
    return response


def code_for_status(status: int) -> str:
    """The fixed code for an upstream status; never the status text or body."""

    if status in UNAUTHORIZED_STATUSES:
        return "TRANSPORT_UPSTREAM_UNAUTHORIZED"
    if status == RATE_LIMITED_STATUS:
        return "TRANSPORT_UPSTREAM_RATE_LIMITED"
    if status >= 500:
        return "TRANSPORT_UPSTREAM_UNAVAILABLE"
    return "TRANSPORT_UPSTREAM_REFUSED"
