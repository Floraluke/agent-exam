"""Shared doubles for the lifecycle layer: one proxy per run, fixed tokens, real ledger.

Not product code: these wire the reviewed pieces together the way the runtime will, so a
test can speak to the pipeline the same way the task container will.
"""

from __future__ import annotations

import json
import threading
from collections.abc import Callable, Mapping, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from http.client import HTTPConnection
from pathlib import Path
from typing import Any

from eval_platform.adapters.execution.provider_access.binding import (
    RunBinding,
    TokenRegistry,
)
from eval_platform.adapters.execution.provider_access.budget import (
    BudgetLedger,
    RunBudget,
)
from eval_platform.adapters.execution.provider_access.failures import (
    ProviderAccessError,
)
from eval_platform.adapters.execution.provider_access.server import (
    Admission,
    ProviderProxyService,
    ProxyIdentity,
    RunOutcome,
    RunRunner,
    build_server,
)
from eval_platform.adapters.execution.provider_access.server.egress import (
    open_stream,
)
from eval_platform.domain.agent import INTERNAL_TEST_PROVIDER, INTERNAL_TEST_UPSTREAM

RUN_ID = "run-1"
MODEL = "deepseek-flash"
PROFILE_ID = "t05-fake-provider"
ALLOWED_TOOLS = frozenset({"shell"})
CLIENT_TOKEN = "FAKE-T05-CLIENT-TOKEN"
OTHER_RUN_TOKEN = "FAKE-T05-OTHER-RUN-TOKEN"
FAKE_SECRET = "FAKE-T05-PROVIDER-SECRET"
BUDGET = RunBudget(
    input_tokens_limit=300_000, output_tokens_limit=32_000, deadline_seconds=900
)


def profile_document(**entry_overrides: Any) -> dict[str, Any]:
    entry: dict[str, Any] = {
        "provider": INTERNAL_TEST_PROVIDER,
        "model": MODEL,
        "upstream_base_url": INTERNAL_TEST_UPSTREAM,
        "secret": FAKE_SECRET,
    }
    entry.update(entry_overrides)
    return {"version": 1, "profiles": {PROFILE_ID: entry}}


def request_body(**overrides: Any) -> bytes:
    body: dict[str, Any] = {
        "model": MODEL,
        "stream": True,
        "input": [{"role": "user", "content": "hello"}],
        "tools": [{"type": "shell"}],
    }
    body.update(overrides)
    return json.dumps(body).encode("utf-8")


def platform_verified(path: Path) -> None:
    """Stands in for the platform proof that the private file is owner-only."""


def owner_unverifiable(path: Path) -> None:
    raise ProviderAccessError("PRIVATE_ACCESS_UNVERIFIABLE")


def permissions_too_wide(path: Path) -> None:
    raise ProviderAccessError("PRIVATE_FILE_PERMISSIONS_TOO_WIDE")


@dataclass
class Harness:
    """The service under test, wired with deterministic tokens and a real ledger."""

    service: ProviderProxyService
    registry: TokenRegistry
    ledger: BudgetLedger
    binding: RunBinding
    private: Path

    def decide(
        self,
        body: bytes | dict[str, Any] | None = None,
        *,
        method: str = "POST",
        path: str = "/responses",
        token: str = CLIENT_TOKEN,
        authorization: bool = True,
        headers: Mapping[str, str] | None = None,
    ) -> Admission:
        raw = request_body() if body is None else body
        sent: dict[str, str] = dict(headers or {})
        if authorization:
            sent["Authorization"] = f"Bearer {token}"
        return self.service.decide(
            method=method,
            path=path,
            raw_body=raw if isinstance(raw, bytes) else json.dumps(raw).encode("utf-8"),
            headers=sent,
        )


def issue_binding(registry: TokenRegistry, run_id: str = RUN_ID) -> RunBinding:
    return registry.issue(
        run_id=run_id,
        provider=INTERNAL_TEST_PROVIDER,
        model=MODEL,
        ttl_seconds=BUDGET.deadline_seconds,
        budget=BUDGET,
    )


def make_harness(
    tmp_path: Path,
    *,
    document: Mapping[str, Any] | None = None,
    profile_id: str = PROFILE_ID,
    verify_access: Callable[[Path], None] = platform_verified,
    clock: Callable[[], float] | None = None,
    consumed: tuple[int, int] = (0, 0),
    tokens: Sequence[str] = (CLIENT_TOKEN,),
) -> Harness:
    tmp_path.mkdir(parents=True, exist_ok=True)
    private = tmp_path / "provider-private.json"
    private.write_text(
        json.dumps(dict(document or profile_document())), encoding="utf-8"
    )
    remaining = list(tokens)
    injection: dict[str, Any] = {} if clock is None else {"clock": clock}
    registry = TokenRegistry(token_factory=lambda: remaining.pop(0), **injection)
    binding = issue_binding(registry)
    ledger = BudgetLedger(
        BUDGET,
        consumed_input_tokens=consumed[0],
        consumed_output_tokens=consumed[1],
        **injection,
    )
    identity = ProxyIdentity(
        run_id=RUN_ID,
        allowed_tools=ALLOWED_TOOLS,
        profile_path=private,
        profile_id=profile_id,
    )
    return Harness(
        ProviderProxyService(
            identity,
            registry=registry,
            ledger=ledger,
            verify_access=verify_access,
        ),
        registry,
        ledger,
        binding,
        private,
    )


def port_of(upstream) -> int:
    """The fake upstream's listening port, taken from the address it published."""

    return int(upstream.base_url.rsplit(":", 1)[1])


def sender_for(upstream, *, timeout: float = 5.0):
    """A sender that dials the fake upstream, standing in for the TLS wrapper."""

    host, port = "127.0.0.1", port_of(upstream)

    def dial(_host: str, _port: int, _timeout: float) -> HTTPConnection:
        return HTTPConnection(host, port, timeout=timeout)

    def send(request):
        return open_stream(request, connector=dial, timeout=timeout)

    return send


@contextmanager
def served_proxy(upstream, tmp_path: Path, *, timeout: float = 5.0, port: int = 0):
    """A running proxy surface around one run, closed when the block exits.

    `port=0` lets the OS pick, which is what tests want; serve_proxy.py passes a
    fixed one so a human can point curl at it.
    """

    harness = make_harness(tmp_path)
    outcomes: list[RunOutcome] = []
    server = build_server(
        harness.service,
        RunRunner(harness.ledger, sender=sender_for(upstream, timeout=timeout)),
        host="127.0.0.1",
        port=port,
        on_outcome=outcomes.append,
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield harness, f"http://127.0.0.1:{server.server_port}", outcomes
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
