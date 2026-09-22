#!/usr/bin/env python
"""Start a real proxy on a port, so a controlled failure can be reproduced by hand.

The lifecycle tests already drive a genuine server on a genuine port; this is the same
wiring with a fixed address and printed instructions. It exists so anyone -- the Web
side checking presentation, or the integration slice -- can see a real controlled
refusal and a real streamed answer without reading the tests.

Nothing here is product code and nothing here is a secret: the provider file is
generated in a temporary directory from fake values, and the client token is printed
on purpose.

    python tests/providers/lifecycle/serve_proxy.py --port 18124

Then, in another shell, using the printed token (TOKEN=FAKE-T05-CLIENT-TOKEN). The
body must be well formed -- the policy refuses an empty `input` before any egress --
so the three cases differ by credential and model, not by shape:

    BODY='{"model":"deepseek-flash","stream":true,"input":[{"role":"user","content":"hello"}],"tools":[{"type":"shell"}]}'

    # a real controlled refusal: no credential at all
    curl -i -X POST http://127.0.0.1:18124/responses \\
      -H 'Content-Type: application/json' --data "$BODY"

    # a real controlled refusal: the run's token, but a model it is not bound to
    curl -i -X POST http://127.0.0.1:18124/responses \\
      -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \\
      --data "${BODY/deepseek-flash/kimi-k3}"

    # a real answer, relayed from the fake upstream: the bound model
    curl -i -X POST http://127.0.0.1:18124/responses \\
      -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \\
      --data "$BODY"

Measured (2026-09-22, this machine): case 1 is 403 PROVIDER_ACCESS_DENIED, case 2 is
400 PROVIDER_REQUEST_REJECTED, case 3 is a 200 event stream ending in
`response.completed`. Every refusal is decided before any egress. The upstream prints
one line per request that actually reaches it, so the refusals print nothing and the
answer prints exactly one line.
"""

from __future__ import annotations

import argparse
import sys
import tempfile
import threading
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # apps/backend/tests

from providers.contract.support.fake_responses import FakeUpstream, Script  # noqa: E402
from providers.lifecycle.support import (  # noqa: E402
    CLIENT_TOKEN,
    MODEL,
    PROFILE_ID,
    served_proxy,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=18124)
    options = parser.parse_args(argv)

    def note(recorded) -> None:
        # One line per request that reached the upstream. Refusals print nothing, which
        # is what "zero egress" looks like from the outside.
        print(
            f"  [upstream] request #{len(upstream.requests)}: {recorded.method} "
            f"{recorded.path} model={(recorded.body or {}).get('model')}",
            flush=True,
        )

    upstream = FakeUpstream(on_request=note).start()
    upstream.script(*[Script() for _ in range(1000)])
    with tempfile.TemporaryDirectory(prefix="t05-proxy-") as workspace:
        with served_proxy(upstream, Path(workspace), port=options.port) as served:
            harness, base_url, _ = served
            print(f"proxy listening on {base_url}/responses", flush=True)
            print(f"bound model: {MODEL}   profile: {PROFILE_ID}", flush=True)
            print(f"client token (fake, on purpose): {CLIENT_TOKEN}", flush=True)
            print(f"bound run: {harness.binding.run_id}", flush=True)
            print("Ctrl+C to stop. A refusal prints no [upstream] line.", flush=True)
            try:
                while True:
                    threading.Event().wait(0.5)
            except KeyboardInterrupt:
                return 0
            finally:
                upstream.stop()


if __name__ == "__main__":
    raise SystemExit(main())
