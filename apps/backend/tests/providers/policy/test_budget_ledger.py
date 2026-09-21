from __future__ import annotations

import threading

import pytest

from eval_platform.adapters.execution.provider_access.budget import (
    BudgetLedger,
    RunBudget,
    conservative_input_tokens,
)
from eval_platform.domain.result import UsageSummary

BUDGET = RunBudget(
    input_tokens_limit=300_000, output_tokens_limit=32_000, deadline_seconds=900
)
PAYLOAD = {
    "model": "deepseek-flash",
    "stream": True,
    "input": "repair the failing test",
}


def ledger(clock=None, **consumed: int) -> BudgetLedger:
    arguments = {"consumed_input_tokens": 0, "consumed_output_tokens": 0}
    arguments.update(consumed)
    if clock is not None:
        arguments["clock"] = clock
    return BudgetLedger(BUDGET, **arguments)


def test_reserves_the_input_bound_plus_the_requested_output():
    subject = ledger()
    reservation = subject.reserve(PAYLOAD, max_output_tokens=4096)
    assert reservation.input_tokens == conservative_input_tokens(PAYLOAD)
    assert reservation.max_output_tokens == 4096
    assert subject.remaining_output_tokens == 32_000 - 4096


def test_the_input_bound_is_an_upper_bound_not_a_character_count():
    ascii_payload = {"input": "a" * 100}
    wide_payload = {"input": "修" * 100}
    assert conservative_input_tokens(ascii_payload) >= 100
    # A byte-level tokenizer may emit one token per byte, so wide text must not
    # be charged less than its UTF-8 length.
    assert conservative_input_tokens(wide_payload) >= 300
    assert conservative_input_tokens(wide_payload) > conservative_input_tokens(
        ascii_payload
    )


def test_unserializable_payload_is_rejected():
    with pytest.raises(ValueError, match="BUDGET_PAYLOAD_NOT_SERIALIZABLE"):
        conservative_input_tokens({"input": object()})


def test_input_and_output_ceilings_are_both_enforced():
    subject = ledger()
    with pytest.raises(ValueError, match="BUDGET_OUTPUT_REQUEST_INVALID"):
        subject.reserve(PAYLOAD, max_output_tokens=0)
    with pytest.raises(ValueError, match="BUDGET_OUTPUT_EXCEEDED"):
        subject.reserve(PAYLOAD, max_output_tokens=32_001)
    subject.close("test")
    assert subject.closed_reason == "test"


def test_input_ceiling_uses_the_carried_total():
    subject = ledger(consumed_input_tokens=299_000)
    with pytest.raises(ValueError, match="BUDGET_INPUT_EXCEEDED"):
        subject.reserve({"input": "x" * 5_000}, max_output_tokens=1)


def test_deadline_is_measured_from_the_ledger_start():
    ticks = iter([0.0, 901.0])
    subject = ledger(clock=lambda: next(ticks))
    with pytest.raises(ValueError, match="BUDGET_DEADLINE_EXCEEDED"):
        subject.reserve(PAYLOAD, max_output_tokens=1)


def test_a_measured_settlement_charges_the_reported_usage():
    subject = ledger()
    reservation = subject.reserve(PAYLOAD, max_output_tokens=4096)
    settlement = subject.settle(
        reservation, UsageSummary(n_input_tokens=1200, n_output_tokens=800)
    )
    assert settlement.measured is True
    assert (settlement.input_tokens, settlement.output_tokens) == (1200, 800)
    assert subject.consumed_input_tokens == 1200
    assert subject.consumed_output_tokens == 800
    assert subject.remaining_output_tokens == 32_000 - 800
    assert subject.closed_reason is None


@pytest.mark.parametrize(
    "usage",
    [
        None,
        UsageSummary(),
        UsageSummary(n_input_tokens=10),
        UsageSummary(n_output_tokens=10),
    ],
)
def test_an_unknown_usage_charges_the_whole_hold_and_stops_the_run(usage):
    subject = ledger()
    reservation = subject.reserve(PAYLOAD, max_output_tokens=4096)
    settlement = subject.settle(reservation, usage)
    assert settlement.measured is False
    assert settlement.input_tokens == reservation.input_tokens
    assert settlement.output_tokens == 4096
    assert subject.consumed_output_tokens == 4096
    assert subject.closed_reason == "usage-unknown"
    with pytest.raises(ValueError, match="BUDGET_RUN_CLOSED"):
        subject.reserve(PAYLOAD, max_output_tokens=1)


def test_a_reservation_settles_only_once():
    subject = ledger()
    reservation = subject.reserve(PAYLOAD, max_output_tokens=4096)
    subject.settle(reservation, UsageSummary(n_input_tokens=1, n_output_tokens=1))
    with pytest.raises(ValueError, match="BUDGET_RESERVATION_UNKNOWN"):
        subject.settle(reservation, UsageSummary(n_input_tokens=1, n_output_tokens=1))


def test_carry_over_is_required_and_bounded():
    with pytest.raises(ValueError, match="BUDGET_CONSUMED_INVALID"):
        ledger(consumed_output_tokens=-1)
    with pytest.raises(ValueError, match="BUDGET_CONSUMED_INVALID"):
        ledger(consumed_output_tokens=32_001)
    with pytest.raises(TypeError):
        BudgetLedger(BUDGET)  # type: ignore[call-arg]


@pytest.mark.parametrize("limits", [(0, 10, 1), (10, 0, 1), (10, 10, 0)])
def test_limits_must_be_usable(limits):
    with pytest.raises(ValueError, match="BUDGET_LIMITS_INVALID"):
        RunBudget(*limits)


def test_concurrent_reservations_never_exceed_the_ceiling():
    subject = BudgetLedger(
        RunBudget(
            input_tokens_limit=300_000, output_tokens_limit=32_000, deadline_seconds=900
        ),
        consumed_input_tokens=0,
        consumed_output_tokens=0,
    )
    granted: list[int] = []
    refused: list[int] = []
    barrier = threading.Barrier(8)

    def attempt() -> None:
        barrier.wait()
        try:
            reservation = subject.reserve(PAYLOAD, max_output_tokens=8_000)
        except ValueError:
            refused.append(1)
        else:
            granted.append(reservation.reservation_id)

    threads = [threading.Thread(target=attempt) for _ in range(8)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert len(granted) == 4 and len(refused) == 4
    assert subject.remaining_output_tokens == 0
