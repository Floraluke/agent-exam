"""End of a run: revoke the token and stop the ledger, without pretending to persist.

Neither the proxy nor this module decides whether a run may resume. That judgement needs
the persisted Job record and belongs to the worker (S9). What must hold here is narrower
and provable: ending a run leaves no usable credential behind, a closed run stays closed
even if its first close was for another reason, and a fresh proxy over the same ledger
inherits what was already spent instead of starting from zero.
"""

from __future__ import annotations

from dataclasses import dataclass

from eval_platform.adapters.execution.provider_access.binding import TokenRegistry
from eval_platform.adapters.execution.provider_access.budget import BudgetLedger

RUN_FINISHED = "run-finished"


@dataclass(frozen=True, slots=True)
class RunClosing:
    """What ending a run did: was a credential still held, and what was spent."""

    revoked: bool
    reason: str
    consumed_input_tokens: int
    consumed_output_tokens: int


class RunClosure:
    """The single place a run is ended; safe to call more than once."""

    def __init__(
        self, registry: TokenRegistry, ledger: BudgetLedger, *, run_id: str
    ) -> None:
        self._registry = registry
        self._ledger = ledger
        self._run_id = run_id

    @property
    def closed(self) -> bool:
        return self._ledger.closed_reason is not None

    def close(self, reason: str = RUN_FINISHED) -> RunClosing:
        """Revoke this run's token and stop its ledger; the first reason is kept."""

        self._ledger.close(reason)
        revoked = self._registry.revoke_run(self._run_id)
        return RunClosing(
            revoked=revoked,
            reason=self._ledger.closed_reason or reason,
            consumed_input_tokens=self._ledger.consumed_input_tokens,
            consumed_output_tokens=self._ledger.consumed_output_tokens,
        )
