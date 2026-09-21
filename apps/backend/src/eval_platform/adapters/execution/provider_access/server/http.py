"""The inbound HTTP surface: one POST per request, answered with the upstream's bytes.

Everything that can be decided is decided before a byte is written, by the pipeline in
`service`. This module owns three things only: the request framing, the controlled
error reply, and making sure a client that goes away still closes its relay, which
settles the hold. Errors are answered with the controlled pair from `failures` — never
an upstream body, an exception string, a path or a topology word. Once the answer has
started, closing the connection is the only honest failure signal left.

Chunked framing is written by hand because the answer length is not known in advance; it
matches what the fake upstream emits.
"""

from __future__ import annotations

import json
import sys
from collections.abc import Callable
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

from eval_platform.adapters.execution.provider_access.server.contracts import (
    MAX_BODY_BYTES,
    Admission,
    ProviderRejection,
)
from eval_platform.adapters.execution.provider_access.server.runner import (
    RunOutcome,
    RunRunner,
)
from eval_platform.adapters.execution.provider_access.server.service import (
    ProviderProxyService,
)

SERVER_NAME = "agentexam-provider-proxy"
CHUNKED_END = b"0\r\n\r\n"
CLIENT_GONE = (BrokenPipeError, ConnectionResetError, ConnectionAbortedError)
_STATUS_BY_FAILURE = {
    "PROVIDER_ACCESS_DENIED": 403,
    "PROVIDER_REQUEST_REJECTED": 400,
    "PROVIDER_BUDGET_EXHAUSTED": 429,
    "PROVIDER_CREDENTIAL_UNAVAILABLE": 502,
    "PROVIDER_UPSTREAM_FAILED": 502,
    "PROVIDER_ACCESS_FAILED": 500,
}
DEFAULT_ERROR_STATUS = 500
METHOD_NOT_ALLOWED_STATUS = 405


def build_server(
    service: ProviderProxyService,
    runner: RunRunner,
    *,
    host: str,
    port: int,
    on_outcome: Callable[[RunOutcome], None] | None = None,
) -> ThreadingHTTPServer:
    """A threaded server for one run's proxy; the caller owns its lifetime."""

    handler = _handler_class(service, runner, on_outcome)
    return QuietServer((host, port), handler)


class QuietServer(ThreadingHTTPServer):
    """A client that vanished mid-request is normal here, not a traceback."""

    def handle_error(self, request: Any, client_address: Any) -> None:
        if not isinstance(sys.exc_info()[1], CLIENT_GONE):
            super().handle_error(request, client_address)


def _status_for(refusal: ProviderRejection) -> int:
    if refusal.internal_code == "REQUEST_METHOD_NOT_ALLOWED":
        return METHOD_NOT_ALLOWED_STATUS
    return _STATUS_BY_FAILURE.get(refusal.failure_code, DEFAULT_ERROR_STATUS)


def _handler_class(
    service: ProviderProxyService,
    runner: RunRunner,
    on_outcome: Callable[[RunOutcome], None] | None,
) -> type[BaseHTTPRequestHandler]:
    class ProxyHandler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"
        server_version = SERVER_NAME
        sys_version = ""

        def log_message(self, *_: object) -> None:
            pass  # The request line carries a path and possibly a token: never log it.

        def do_POST(self) -> None:  # noqa: N802 - http.server naming
            body = self._read_body()
            if body is None:
                return
            try:
                admission = service.decide(
                    method=self.command,
                    path=self.path,
                    raw_body=body,
                    headers=dict(self.headers.items()),
                )
            except ProviderRejection as refusal:
                self.answer_error(refusal)
                return
            self._relay(admission)

        def refuse(self) -> None:
            """Every method but POST is refused here, with the pipeline's own code."""

            try:
                service.decide(
                    method=self.command,
                    path=self.path,
                    raw_body=b"",
                    headers=dict(self.headers.items()),
                )
            except ProviderRejection as refusal:
                self.answer_error(refusal)

        do_GET = refuse
        do_HEAD = refuse
        do_PUT = refuse
        do_PATCH = refuse
        do_DELETE = refuse
        do_OPTIONS = refuse

        def _read_body(self) -> bytes | None:
            # No usable Content-Length means refusal, not reading unbounded: an inbound
            # chunked body is unsupported, so it fails closed.
            declared = self.headers.get("Content-Length")
            if declared is None or not declared.isdigit():
                self.answer_error(ProviderRejection("REQUEST_BODY_MALFORMED"))
                return None
            if int(declared) > MAX_BODY_BYTES:
                self.answer_error(ProviderRejection("REQUEST_BODY_TOO_LARGE"))
                return None
            return self.rfile.read(int(declared))

        def answer_error(self, refusal: ProviderRejection) -> None:
            payload = json.dumps(
                {
                    "error": {
                        "code": refusal.failure_code,
                        "message": refusal.failure_summary,
                    }
                }
            ).encode("utf-8")
            self.send_response(_status_for(refusal))
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.send_header("Connection", "close")
            try:
                self.end_headers()
                if self.command != "HEAD":
                    self.wfile.write(payload)
            except CLIENT_GONE:
                pass  # A client that is gone cannot be told anything; hang up instead.
            finally:
                self.close_connection = True

        def _relay(self, admission: Admission) -> None:
            relay = runner.relay(admission)
            started = False
            try:
                for chunk in relay:
                    if not started:
                        self.send_response(200)
                        self.send_header("Content-Type", "text/event-stream")
                        self.send_header("Transfer-Encoding", "chunked")
                        self.end_headers()
                        started = True
                    self.wfile.write(b"%x\r\n%s\r\n" % (len(chunk), chunk))
                    self.wfile.flush()
            except ProviderRejection as refusal:
                if not started:
                    self.answer_error(refusal)
            except CLIENT_GONE:
                pass  # The client is gone; the relay below still settles the hold.
            finally:
                relay.close()
                if started:
                    try:
                        self.wfile.write(CHUNKED_END)
                        self.wfile.flush()
                    except CLIENT_GONE:
                        pass
                if on_outcome is not None and relay.outcome is not None:
                    on_outcome(relay.outcome)

    return ProxyHandler
