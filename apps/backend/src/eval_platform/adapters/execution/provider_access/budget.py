"""Per-run token ledger for the isolated proxy. Upper bounds, never billing.

Two rules drive every decision here. First, the input count is a deliberate
upper bound, because the owner selected the conservative option and no
tokenizer is aligned with the provider yet: a byte-level tokenizer can emit one
token per byte, so the UTF-8 byte length of the request is a safe ceiling, and
a fixed framing allowance is added on top. Second, a missing or partial usage
report is not zero and not refunded: the full reservation is charged and the
run stops accepting further requests.

The consumed totals are constructor arguments with no defaults on purpose. A
caller that cannot say what this run already spent must not be able to start a
fresh ledger at zero after a proxy restart.
"""

from __future__ import annotations

import json
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from eval_platform.domain.result import UsageSummary

FRAMING_ALLOWANCE_TOKENS = 256
UNKNOWN_USAGE_REASON = "usage-unknown"


@dataclass(frozen=True, slots=True)
class RunBudget:
    """Owner-confirmed per-run ceilings; the deadline is separate from build time."""

    input_tokens_limit: int
    output_tokens_limit: int
    deadline_seconds: float

    def __post_init__(self) -> None:
        if self.input_tokens_limit <= 0 or self.output_tokens_limit <= 0:
            raise ValueError("BUDGET_LIMITS_INVALID")
        if self.deadline_seconds <= 0:
            raise ValueError("BUDGET_LIMITS_INVALID")


@dataclass(frozen=True, slots=True)
class Reservation:
    reservation_id: int
    input_tokens: int
    max_output_tokens: int


@dataclass(frozen=True, slots=True)
class Settlement:
    """What was actually charged; ``measured`` is False for a conservative charge."""

    input_tokens: int
    output_tokens: int
    measured: bool


def conservative_input_tokens(payload: Any) -> int:
    """Upper bound on request tokens: UTF-8 bytes plus a framing allowance."""

    try:
        encoded = json.dumps(
            payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False
        ).encode("utf-8")
    except (TypeError, ValueError):
        raise ValueError("BUDGET_PAYLOAD_NOT_SERIALIZABLE") from None
    return len(encoded) + FRAMING_ALLOWANCE_TOKENS


class BudgetLedger:
    """Mutable per-run state; every mutation happens under one lock."""

    def __init__(
        self,
        budget: RunBudget,
        *,
        consumed_input_tokens: int,
        consumed_output_tokens: int,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        if consumed_input_tokens < 0 or consumed_output_tokens < 0:
            raise ValueError("BUDGET_CONSUMED_INVALID")
        if consumed_input_tokens > budget.input_tokens_limit:
            raise ValueError("BUDGET_CONSUMED_INVALID")
        if consumed_output_tokens > budget.output_tokens_limit:
            raise ValueError("BUDGET_CONSUMED_INVALID")
        self._budget = budget
        self._clock = clock
        self._started_at = clock()
        self._lock = threading.Lock()
        self._input_used = consumed_input_tokens
        self._output_used = consumed_output_tokens
        self._reserved_input = 0
        self._reserved_output = 0
        self._open: dict[int, Reservation] = {}
        self._next_id = 1
        self._closed_reason: str | None = None

    @property
    def closed_reason(self) -> str | None:
        with self._lock:
            return self._closed_reason

    @property
    def consumed_input_tokens(self) -> int:
        with self._lock:
            return self._input_used

    @property
    def consumed_output_tokens(self) -> int:
        with self._lock:
            return self._output_used

    @property
    def remaining_output_tokens(self) -> int:
        with self._lock:
            return (
                self._budget.output_tokens_limit
                - self._output_used
                - self._reserved_output
            )

    def close(self, reason: str) -> None:
        with self._lock:
            self._closed_reason = self._closed_reason or reason

    def reserve(self, payload: Any, *, max_output_tokens: int) -> Reservation:
        """Reserve the input bound plus the requested output, atomically."""

        input_bound = conservative_input_tokens(payload)
        if max_output_tokens <= 0:
            raise ValueError("BUDGET_OUTPUT_REQUEST_INVALID")
        with self._lock:
            if self._closed_reason is not None:
                raise ValueError("BUDGET_RUN_CLOSED")
            if self._clock() - self._started_at > self._budget.deadline_seconds:
                raise ValueError("BUDGET_DEADLINE_EXCEEDED")
            if (
                self._input_used + self._reserved_input + input_bound
                > self._budget.input_tokens_limit
            ):
                raise ValueError("BUDGET_INPUT_EXCEEDED")
            if (
                self._output_used + self._reserved_output + max_output_tokens
                > self._budget.output_tokens_limit
            ):
                raise ValueError("BUDGET_OUTPUT_EXCEEDED")
            reservation = Reservation(self._next_id, input_bound, max_output_tokens)
            self._next_id += 1
            self._open[reservation.reservation_id] = reservation
            self._reserved_input += input_bound
            self._reserved_output += max_output_tokens
            return reservation

    def settle(
        self, reservation: Reservation, usage: UsageSummary | None
    ) -> Settlement:
        """Release a reservation; charge the measured usage or the whole hold."""

        with self._lock:
            held = self._open.pop(reservation.reservation_id, None)
            if held is None:
                raise ValueError("BUDGET_RESERVATION_UNKNOWN")
            self._reserved_input -= held.input_tokens
            self._reserved_output -= held.max_output_tokens
            measured = _measured_tokens(usage)
            if measured is None:
                self._input_used += held.input_tokens
                self._output_used += held.max_output_tokens
                self._closed_reason = self._closed_reason or UNKNOWN_USAGE_REASON
                return Settlement(held.input_tokens, held.max_output_tokens, False)
            self._input_used += measured[0]
            self._output_used += measured[1]
            return Settlement(measured[0], measured[1], True)


def _measured_tokens(usage: UsageSummary | None) -> tuple[int, int] | None:
    if usage is None:
        return None
    if usage.n_input_tokens is None or usage.n_output_tokens is None:
        return None
    return usage.n_input_tokens, usage.n_output_tokens
