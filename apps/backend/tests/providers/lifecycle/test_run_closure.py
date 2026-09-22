"""S6d：Run 收束——结束后不留可用凭据、关闭状态不可被后续操作改写、重启不重置额度。

本层能证的只有这些。**"崩溃后是否允许续跑"不在这一层**：那取决于已持久化的 Job 证据，
属于 worker（S9）。这里要钉住的是前提条件：一个结束的 Run 不再持有令牌、不再接受请求，
而"新起的代理 + 同一个账本"必须继承已花费的额度而不是从零开始。
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest

from eval_platform.adapters.execution.provider_access.budget import (
    UNKNOWN_USAGE_REASON,
    BudgetLedger,
)
from eval_platform.adapters.execution.provider_access.server import (
    ProviderProxyService,
    ProviderRejection,
    ProxyIdentity,
    RunRunner,
)
from eval_platform.adapters.execution.provider_access.server.closure import (
    RUN_FINISHED,
    RunClosure,
)
from providers.contract.support.fake_responses import FAKE_USAGE
from providers.contract.support.responses_events import completed
from providers.lifecycle.support import (
    BUDGET,
    CLIENT_TOKEN,
    MODEL,
    RUN_ID,
    make_harness,
    platform_verified,
    request_body,
)

REAUTHORISED_TOKEN = "FAKE-T05-REAUTHORISED-TOKEN"


def frames() -> list[bytes]:
    return completed("resp_1", MODEL, "FAKE-ANSWER", FAKE_USAGE)


def sender_of(*chunks: bytes, error: Exception | None = None):
    def send(_request: object) -> Iterator[bytes]:
        yield from chunks
        if error is not None:
            raise error

    return send


def test_ending_a_run_leaves_no_usable_credential(tmp_path):
    harness = make_harness(tmp_path)
    relay = RunRunner(harness.ledger, sender=sender_of(*frames())).relay(
        harness.decide()
    )
    b"".join(relay)
    closure = RunClosure(harness.registry, harness.ledger, run_id=RUN_ID)

    closing = closure.close()

    assert closing.revoked is True
    assert closing.reason == RUN_FINISHED
    assert closing.consumed_output_tokens == FAKE_USAGE["output_tokens"]
    assert closure.closed is True
    with pytest.raises(ProviderRejection, match="PROVIDER_TOKEN_UNKNOWN"):
        harness.decide()
    assert harness.registry.active_run_ids() == ()


def test_a_closed_run_keeps_its_first_reason(tmp_path):
    harness = make_harness(tmp_path)
    relay = RunRunner(harness.ledger, sender=sender_of(error=TimeoutError())).relay(
        harness.decide()
    )
    with pytest.raises(TimeoutError):
        b"".join(relay)
    closure = RunClosure(harness.registry, harness.ledger, run_id=RUN_ID)

    first = closure.close(RUN_FINISHED)
    second = closure.close("another-reason")

    assert first.reason == UNKNOWN_USAGE_REASON
    assert second.reason == UNKNOWN_USAGE_REASON
    assert second.revoked is False
    assert harness.ledger.closed_reason == UNKNOWN_USAGE_REASON
    with pytest.raises(ProviderRejection, match="PROVIDER_TOKEN_UNKNOWN"):
        harness.decide()


def test_a_revived_proxy_inherits_what_was_spent(tmp_path):
    """Re-authorising a run after a restart must not hand back the spent allowance."""

    harness = make_harness(tmp_path, tokens=(CLIENT_TOKEN, REAUTHORISED_TOKEN))
    relay = RunRunner(harness.ledger, sender=sender_of(*frames())).relay(
        harness.decide(body=request_body(max_output_tokens=8_000))
    )
    b"".join(relay)
    spent = harness.ledger.consumed_output_tokens
    RunClosure(harness.registry, harness.ledger, run_id=RUN_ID).close()

    revived_ledger = BudgetLedger(
        BUDGET,
        consumed_input_tokens=harness.ledger.consumed_input_tokens,
        consumed_output_tokens=spent,
    )
    revived = ProviderProxyService(
        ProxyIdentity(
            run_id=RUN_ID,
            allowed_tools=frozenset({"shell"}),
            profile_path=harness.private,
            profile_id="t05-fake-provider",
        ),
        registry=harness.registry,
        ledger=revived_ledger,
        verify_access=platform_verified,
    )
    assert revived_ledger.remaining_output_tokens == 32_000 - spent
    # A fresh credential is a deliberate re-authorisation; it still sees only the rest.
    harness.registry.issue(
        run_id=RUN_ID,
        provider="internal_test_fake",
        model=MODEL,
        ttl_seconds=900.0,
        budget=BUDGET,
    )
    admission = revived.decide(
        method="POST",
        path="/responses",
        raw_body=request_body(),
        headers={"Authorization": f"Bearer {REAUTHORISED_TOKEN}"},
    )
    assert admission.reservation.max_output_tokens == 32_000 - spent


def test_a_failed_run_is_not_retried_by_itself(tmp_path):
    """Nothing here re-sends after a failure: the run is closed, not resumed."""

    harness = make_harness(tmp_path)
    relay = RunRunner(harness.ledger, sender=sender_of(*frames()[:2])).relay(
        harness.decide()
    )
    b"".join(relay)
    assert relay.outcome is not None and relay.outcome.ended is False

    with pytest.raises(ProviderRejection, match="BUDGET_RUN_CLOSED"):
        harness.decide()
    RunClosure(harness.registry, harness.ledger, run_id=RUN_ID).close()
    with pytest.raises(ProviderRejection, match="PROVIDER_TOKEN_UNKNOWN"):
        harness.decide()
