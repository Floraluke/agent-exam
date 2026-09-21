"""Execute one admitted request against the injected sender and settle its hold.

The sender is injected because the trial's network shape is still the fixed-Harbor
question (T2); what matters here is that the hold is settled exactly once and in the
fail-closed direction. A stream that reports no usage, ends without the terminal event,
is cut, times out, or that the client walks away from is never billed as zero: the whole
hold is charged and the run stops accepting further requests.

The relay is a plain iterator, so the caller decides how fast bytes move and can stop
early. Stopping early is not a way to get out of paying: `close()` settles too.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator
from dataclasses import dataclass

from eval_platform.adapters.execution.provider_access.budget import (
    BudgetLedger,
    Settlement,
)
from eval_platform.adapters.execution.provider_access.server.contracts import Admission
from eval_platform.adapters.execution.provider_access.server.stream import (
    TerminalScanner,
)
from eval_platform.adapters.execution.provider_access.transport import OutboundRequest
from eval_platform.domain.result import UsageSummary

Sender = Callable[[OutboundRequest], Iterator[bytes]]


@dataclass(frozen=True, slots=True)
class RunOutcome:
    """What may be recorded for one request: the charge and whether the answer ended."""

    settlement: Settlement
    ended: bool
    usage: UsageSummary | None


class Relay:
    """One request in flight: yields upstream bytes, settles once, however it ends."""

    def __init__(
        self, *, sender: Sender, admission: Admission, ledger: BudgetLedger
    ) -> None:
        self._ledger = ledger
        self._admission = admission
        self._scanner = TerminalScanner()
        self._frames = iter(sender(admission.outbound))
        self._outcome: RunOutcome | None = None

    def __iter__(self) -> Relay:
        return self

    def __next__(self) -> bytes:
        if self._outcome is not None:
            raise StopIteration
        try:
            chunk = next(self._frames)
        except StopIteration:
            self.close()
            raise
        except BaseException:
            self.close()
            raise
        self._scanner.feed(chunk)
        return chunk

    @property
    def outcome(self) -> RunOutcome | None:
        """The settlement, available once the stream ended or was closed."""

        return self._outcome

    def close(self) -> None:
        """Stop relaying and settle; safe to call repeatedly and after the end."""

        if self._outcome is not None:
            return
        shut = getattr(self._frames, "close", None)
        if shut is not None:
            try:
                shut()
            except Exception:
                # Settling below must happen even when the sender's own cleanup fails.
                pass
        terminal = self._scanner.terminal
        if terminal is None or self._scanner.overflowed:
            ended, usage = False, None
        else:
            ended, usage = True, terminal.usage
        settlement = self._ledger.settle(self._admission.reservation, usage)
        self._outcome = RunOutcome(settlement, ended=ended, usage=usage)


class RunRunner:
    """Opens relays against the injected sender; holds no state beyond the ledger."""

    def __init__(self, ledger: BudgetLedger, *, sender: Sender) -> None:
        self._ledger = ledger
        self._sender = sender

    def relay(self, admission: Admission) -> Relay:
        return Relay(sender=self._sender, admission=admission, ledger=self._ledger)
