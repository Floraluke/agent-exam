"""S6b：额度预留与结算——终止、未知、断流、超时、客户端离开都必须有明确交代。

四条不可让步的语义在这里被钉住：

1. **未知 usage 按整笔预留全额计费**（不退款为零），并**关闭该 Run**；
2. **"客户端没收到"不等于"没计费"**——中途停下也结算；
3. **不重试、不换模型、不追加上限**：这里的发送方是注入的，异常一律向上抛给调用方，
   但结算必须先发生；
4. **每个预留只结算一次**。

发送方在本片是**替身**（按真实假上游的字节形状产出），真实 socket 路径属 S6c。
"""

from __future__ import annotations

import threading
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor

import pytest

from eval_platform.adapters.execution.provider_access.budget import (
    UNKNOWN_USAGE_REASON,
)
from eval_platform.adapters.execution.provider_access.server import (
    ProviderRejection,
    RunRunner,
)
from eval_platform.adapters.execution.provider_access.server.stream import (
    MAX_SCAN_BYTES,
    TerminalScanner,
)
from eval_platform.adapters.execution.provider_access.transport import OutboundRequest
from providers.contract.support.fake_responses import FAKE_USAGE
from providers.contract.support.responses_events import completed, incomplete
from providers.lifecycle.support import MODEL, make_harness, request_body


def frames(usage: dict | None = FAKE_USAGE) -> list[bytes]:
    return completed("resp_1", MODEL, "FAKE-ANSWER", usage)


def sender_of(*chunks: bytes, error: Exception | None = None):
    """A sender that yields the given chunks and then optionally fails."""

    def send(request: OutboundRequest) -> Iterator[bytes]:
        assert request.max_attempts == 1
        yield from chunks
        if error is not None:
            raise error

    return send


def drain(relay) -> bytes:
    return b"".join(relay)


def test_a_completed_stream_pays_what_the_upstream_reported(tmp_path):
    harness = make_harness(tmp_path)
    admission = harness.decide(body=request_body(max_output_tokens=8_000))
    relay = RunRunner(harness.ledger, sender=sender_of(*frames())).relay(admission)

    relayed = drain(relay)

    assert relayed == b"".join(frames())  # byte-for-byte pass-through
    outcome = relay.outcome
    assert outcome is not None and outcome.ended is True
    assert outcome.usage is not None
    assert outcome.usage.n_input_tokens == FAKE_USAGE["input_tokens"]
    assert outcome.usage.n_output_tokens == FAKE_USAGE["output_tokens"]
    assert outcome.settlement.measured is True
    assert harness.ledger.consumed_output_tokens == FAKE_USAGE["output_tokens"]
    assert harness.ledger.closed_reason is None
    # The hold is released, so the run may continue with further requests.
    remaining = 32_000 - FAKE_USAGE["output_tokens"]
    assert harness.ledger.remaining_output_tokens == remaining
    assert (
        harness.decide(
            body=request_body(max_output_tokens=8_000)
        ).reservation.max_output_tokens
        == 8_000
    )


def test_a_completion_without_usage_charges_the_whole_hold_and_stops_the_run(tmp_path):
    harness = make_harness(tmp_path)
    admission = harness.decide(body=request_body(max_output_tokens=8_000))
    relay = RunRunner(harness.ledger, sender=sender_of(*frames(usage=None))).relay(
        admission
    )
    drain(relay)

    outcome = relay.outcome
    assert outcome is not None and outcome.ended is True and outcome.usage is None
    assert outcome.settlement.measured is False
    assert outcome.settlement.input_tokens == admission.reservation.input_tokens
    assert outcome.settlement.output_tokens == 8_000
    assert harness.ledger.closed_reason == UNKNOWN_USAGE_REASON
    with pytest.raises(ProviderRejection, match="BUDGET_RUN_CLOSED"):
        harness.decide()


def test_a_stream_that_ends_without_a_terminal_event_is_not_free(tmp_path):
    harness = make_harness(tmp_path)
    admission = harness.decide()
    relay = RunRunner(harness.ledger, sender=sender_of(*frames()[:2])).relay(admission)
    drain(relay)

    outcome = relay.outcome
    assert outcome is not None and outcome.ended is False
    assert outcome.settlement.measured is False
    assert harness.ledger.closed_reason == UNKNOWN_USAGE_REASON


def test_a_cut_stream_pays_before_the_error_reaches_the_caller(tmp_path):
    harness = make_harness(tmp_path)
    admission = harness.decide()
    sender = sender_of(*frames()[:2], error=ConnectionResetError("reset"))
    relay = RunRunner(harness.ledger, sender=sender).relay(admission)
    with pytest.raises(ConnectionResetError):
        drain(relay)

    assert relay.outcome is not None
    assert relay.outcome.settlement.measured is False
    assert harness.ledger.closed_reason == UNKNOWN_USAGE_REASON


def test_a_held_stream_that_times_out_pays_too(tmp_path):
    harness = make_harness(tmp_path)
    admission = harness.decide()
    relay = RunRunner(harness.ledger, sender=sender_of(error=TimeoutError())).relay(
        admission
    )
    with pytest.raises(TimeoutError):
        drain(relay)

    assert relay.outcome is not None
    assert relay.outcome.settlement.measured is False
    hold = admission.reservation.max_output_tokens
    assert harness.ledger.consumed_output_tokens == hold


def test_a_client_that_walks_away_still_pays(tmp_path):
    """The dangerous shape: a well-formed prefix, then the reader stops reading."""

    harness = make_harness(tmp_path)
    admission = harness.decide()
    relay = RunRunner(harness.ledger, sender=sender_of(*frames())).relay(admission)

    first = next(iter(relay))
    assert first == frames()[0]
    relay.close()

    assert relay.outcome is not None
    assert relay.outcome.settlement.measured is False
    assert harness.ledger.closed_reason == UNKNOWN_USAGE_REASON


def test_a_reservation_is_settled_exactly_once(tmp_path):
    harness = make_harness(tmp_path)
    admission = harness.decide()
    relay = RunRunner(harness.ledger, sender=sender_of(*frames())).relay(admission)
    drain(relay)
    settled = relay.outcome
    consumed = (
        harness.ledger.consumed_input_tokens,
        harness.ledger.consumed_output_tokens,
    )

    relay.close()  # closing twice is what a disconnect-after-end looks like
    relay.close()

    assert relay.outcome is settled
    assert (
        harness.ledger.consumed_input_tokens,
        harness.ledger.consumed_output_tokens,
    ) == consumed
    with pytest.raises(ValueError, match="BUDGET_RESERVATION_UNKNOWN"):
        harness.ledger.settle(admission.reservation, None)


def test_a_terminal_event_split_across_chunks_is_still_read(tmp_path):
    """Framing must survive a boundary in the middle of the terminal event."""

    harness = make_harness(tmp_path)
    admission = harness.decide()
    whole = frames()
    split = whole[-1][: len(whole[-1]) // 2], whole[-1][len(whole[-1]) // 2 :]
    relay = RunRunner(harness.ledger, sender=sender_of(*whole[:-1], *split)).relay(
        admission
    )
    drain(relay)

    assert relay.outcome is not None
    assert relay.outcome.settlement.measured is True


def test_only_a_terminal_event_is_interpreted(tmp_path):
    """A usage-looking payload on a non-terminal event must not become the charge."""

    harness = make_harness(tmp_path)
    admission = harness.decide()
    decoy = (
        b'event: response.output_text.delta\ndata: {"type":"response.output_text.'
        b'delta","response":{"usage":{"input_tokens":1,"output_tokens":1}}}\n\n'
    )
    relay = RunRunner(harness.ledger, sender=sender_of(decoy)).relay(admission)
    drain(relay)

    assert relay.outcome is not None
    assert relay.outcome.settlement.measured is False
    assert harness.ledger.closed_reason == UNKNOWN_USAGE_REASON


def test_an_incomplete_answer_is_a_terminal_event_without_usage(tmp_path):
    harness = make_harness(tmp_path)
    admission = harness.decide()
    relay = RunRunner(
        harness.ledger, sender=sender_of(*incomplete("resp_1", MODEL, "timeout"))
    ).relay(admission)
    drain(relay)

    assert relay.outcome is not None and relay.outcome.ended is True
    assert relay.outcome.settlement.measured is False
    assert harness.ledger.closed_reason == UNKNOWN_USAGE_REASON


def test_the_scanner_stops_buffering_at_its_cap(tmp_path):
    """A frame that never ends must not grow the buffer; complete frames never do."""

    scanner = TerminalScanner(max_bytes=256)
    scanner.feed(b"x" * 1_025)
    assert scanner.overflowed is True
    assert scanner.terminal is None

    harness = make_harness(tmp_path)
    admission = harness.decide()
    huge = b'event: response.output_text.delta\ndata: {"delta":"' + b"x" * (
        MAX_SCAN_BYTES + 1
    )
    relay = RunRunner(harness.ledger, sender=sender_of(huge)).relay(admission)
    relayed = drain(relay)

    assert relayed == huge  # relaying is not affected by the parsing budget
    assert relay.outcome is not None
    assert relay.outcome.settlement.measured is False
    assert harness.ledger.closed_reason == UNKNOWN_USAGE_REASON


def test_malformed_frames_never_raise_into_the_request_path(tmp_path):
    for broken in (
        b"data: {not json}\n\n",
        b"event: response.completed\n\n",
        b"event: response.completed\ndata: []\n\n",
        b'event: response.completed\ndata: {"response":{"usage":"7"}}\n\n',
        b'event: response.completed\ndata: {"response":{"usage":{"input_tokens":-1,'
        b'"output_tokens":3}}}\n\n',
    ):
        harness = make_harness(tmp_path)
        admission = harness.decide()
        relay = RunRunner(harness.ledger, sender=sender_of(broken)).relay(admission)
        drain(relay)  # must not raise
        assert relay.outcome is not None
        assert relay.outcome.settlement.measured is False


def test_the_ledger_admits_exactly_up_to_the_ceiling_under_concurrency(tmp_path):
    """Eight requests for 8,000 output tokens against a 32,000 ceiling: four get in."""

    harness = make_harness(tmp_path)
    start = threading.Barrier(8)
    admitted: list[str] = []
    lock = threading.Lock()

    def attempt() -> None:
        start.wait()
        try:
            harness.decide(body=request_body(max_output_tokens=8_000))
            result = "admitted"
        except ProviderRejection as refusal:
            result = refusal.internal_code
        with lock:
            admitted.append(result)

    with ThreadPoolExecutor(max_workers=8) as pool:
        for _ in range(8):
            pool.submit(attempt)

    assert sorted(admitted) == ["BUDGET_OUTPUT_EXCEEDED"] * 4 + ["admitted"] * 4
    assert harness.ledger.remaining_output_tokens == 0
