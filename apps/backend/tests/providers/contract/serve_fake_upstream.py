#!/usr/bin/env python
"""Start the fake Responses upstream on a fixed port, for the owner machine.

The contract tests drive the fake in-process; this entry lets the fixed CLI be
pointed at it for the S2 field-name check without writing product code there.
Plain HTTP, one scripted answer per request, every request printed as it arrives.

    python tests/providers/contract/serve_fake_upstream.py --port 8123
    python tests/providers/contract/serve_fake_upstream.py --port 8123 --answer error

Only the method, path, header count and the body's *keys* are printed, never the
Authorization value and never the body itself, so a terminal capture stays safe to paste
back. Pass --dump-body when the field names are what is being checked.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # apps/backend/tests

from providers.contract.support.fake_responses import (  # noqa: E402
    FakeUpstream,
    RecordedRequest,
    Script,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8123)
    parser.add_argument("--answer", choices=("text", "tool", "error"), default="text")
    parser.add_argument("--status", type=int, default=401)
    parser.add_argument("--tool", default="shell")
    parser.add_argument("--arguments", default="{}")
    parser.add_argument("--dump-body", action="store_true")
    options = parser.parse_args(argv)

    def script() -> Script:
        answer = Script()
        if options.answer == "tool":
            answer.tool = options.tool
            answer.arguments = options.arguments
        elif options.answer == "error":
            answer.status = options.status
        return answer

    def report(recorded: RecordedRequest, *, dump: bool = options.dump_body) -> None:
        keys = sorted((recorded.body or {}).keys())
        print(
            f"{recorded.method} {recorded.path} headers={len(recorded.header_names)} "
            f"body_keys={keys}",
            flush=True,
        )
        if dump:
            print(json.dumps(recorded.body, sort_keys=True), flush=True)

    upstream = FakeUpstream(port=options.port, on_request=report)
    upstream.start()
    print(f"listening on {upstream.base_url}/responses (Ctrl+C to stop)", flush=True)
    try:
        while True:
            upstream.script(script())  # one answer queued ahead of each request
            _wait_for_requests(upstream)
    except KeyboardInterrupt:
        return 0
    finally:
        upstream.stop()


def _wait_for_requests(upstream: FakeUpstream, interval: float = 0.2) -> None:
    seen = upstream.request_count
    while upstream.request_count == seen:
        time.sleep(interval)


if __name__ == "__main__":
    raise SystemExit(main())
