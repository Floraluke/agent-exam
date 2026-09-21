"""A fake Responses upstream that records what reached it.

Two jobs, both about evidence rather than convenience:

1. Prove egress happened, or did not. The acceptance rule is that "zero outbound
requests" is shown by this service's own request log, never inferred from log text. So
every request is recorded with method, path, header *names* (plus the credential
separately) and body. 2. Make failures reproducible: 401/429/5xx, a stream cut mid-
answer, a timeout, and a completion carrying no usage are all scripted outcomes here,
not accidents.

Plain HTTP on purpose: the CLI was observed to send to a plain-HTTP custom provider,
so the workload-to-proxy leg needs no TLS. The proxy-to-upstream leg does (transport
refuses non-HTTPS upstreams), so pointing the real proxy at this fake needs a TLS
wrapper -- that belongs to the integration slice and is recorded as a known gap, not
hidden here."""

from __future__ import annotations

import json
import sys
import threading
from collections.abc import Callable
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from .responses_events import completed, incomplete, tool_call

STREAM_CONTENT_TYPE = "text/event-stream"
# Long enough that the caller's own timeout always wins when a script holds the line.
UPSTREAM_HOLD_SECONDS = 60
FAKE_USAGE = {"input_tokens": 7, "output_tokens": 3, "total_tokens": 10}
CLIENT_GONE = (BrokenPipeError, ConnectionResetError, ConnectionAbortedError)


@dataclass
class Script:
    """What the next request gets. The default answers a short text stream."""

    status: int = 200
    text: str = "FAKE-ANSWER"
    tool: str | None = None
    arguments: str = "{}"
    usage: dict | None = field(default_factory=lambda: dict(FAKE_USAGE))
    cut_after: int | None = None
    end_early_at: int | None = None
    hang: bool = False
    incomplete_reason: str | None = None


@dataclass
class RecordedRequest:
    method: str
    path: str
    header_names: tuple[str, ...]
    authorization: str | None
    body: dict | None


class _QuietServer(ThreadingHTTPServer):
    """A client that vanished mid-answer is a scripted case here, not a traceback."""

    def handle_error(self, request: object, client_address: object) -> None:
        if not isinstance(sys.exc_info()[1], CLIENT_GONE):
            super().handle_error(request, client_address)


class FakeUpstream:
    """Threaded fake server with a request log and a script queue."""

    def __init__(
        self,
        port: int = 0,
        on_request: Callable[[RecordedRequest], None] | None = None,
    ) -> None:
        self.scripts: list[Script] = []
        self.requests: list[RecordedRequest] = []
        self._port = port
        self._on_request = on_request
        self._httpd: ThreadingHTTPServer | None = None
        self._thread: threading.Thread | None = None
        self.base_url = ""

    def script(self, *scripts: Script) -> None:
        self.scripts.extend(scripts)

    @property
    def request_count(self) -> int:
        return len(self.requests)

    def next_script(self) -> Script:
        return self.scripts.pop(0) if self.scripts else Script()

    def start(self) -> FakeUpstream:
        upstream = self

        class Handler(BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.1"

            def log_message(self, *args: object) -> None:
                pass  # Never write request detail anywhere; the log is the evidence.

            def do_POST(self) -> None:  # noqa: N802 - http.server naming
                length = int(self.headers.get("Content-Length") or 0)
                raw = self.rfile.read(length) if length else b""
                try:
                    body = json.loads(raw or b"{}")
                except json.JSONDecodeError:
                    body = None
                recorded = RecordedRequest(
                    self.command,
                    self.path,
                    tuple(sorted(self.headers.keys())),
                    self.headers.get("Authorization"),
                    body if isinstance(body, dict) else None,
                )
                upstream.requests.append(recorded)
                if upstream._on_request is not None:
                    upstream._on_request(recorded)
                script = upstream.next_script()
                if script.hang:
                    # Hold the connection open and never answer, so the caller's own
                    # timeout is what ends it; returning here would close the socket
                    # instead.
                    threading.Event().wait(UPSTREAM_HOLD_SECONDS)
                    return
                if script.status != 200:
                    payload = b'{"error":{"code":"scripted"}}'
                    self.send_response(script.status)
                    self.send_header("Content-Type", "application/json")
                    self.send_header("Content-Length", str(len(payload)))
                    self.end_headers()
                    self.wfile.write(payload)
                    return
                events = self._events(script, body)
                self.send_response(200)
                self.send_header("Content-Type", STREAM_CONTENT_TYPE)
                self.send_header("Transfer-Encoding", "chunked")
                self.end_headers()
                for index, event in enumerate(events):
                    if script.cut_after is not None and index >= script.cut_after:
                        self.close_connection = True
                        return  # Reset: the reader sees a dropped connection.
                    if script.end_early_at is not None and index >= script.end_early_at:
                        break
                    self.wfile.write(b"%x\r\n%s\r\n" % (len(event), event))
                self.wfile.write(b"0\r\n\r\n")

            def _events(self, script: Script, body: dict | None) -> list[bytes]:
                model = str((body or {}).get("model", "fake-model"))
                response_id = f"resp_{upstream.request_count}"
                if script.incomplete_reason:
                    return incomplete(response_id, model, script.incomplete_reason)
                if script.tool:
                    return tool_call(
                        response_id, model, script.tool, script.arguments, script.usage
                    )
                return completed(response_id, model, script.text, script.usage)

        self._httpd = _QuietServer(("127.0.0.1", self._port), Handler)
        self.base_url = f"http://127.0.0.1:{self._httpd.server_port}"
        self._thread = threading.Thread(target=self._httpd.serve_forever, daemon=True)
        self._thread.start()
        return self

    def stop(self) -> None:
        if self._httpd is not None:
            self._httpd.shutdown()
            self._httpd.server_close()
        if self._thread is not None:
            self._thread.join(timeout=5)
        self._httpd = None
        self._thread = None

    def __enter__(self) -> FakeUpstream:
        return self.start()

    def __exit__(self, *_: object) -> None:
        self.stop()
