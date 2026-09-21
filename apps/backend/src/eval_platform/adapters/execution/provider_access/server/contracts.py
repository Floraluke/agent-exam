"""The values that cross the proxy boundary: identity, refusal and admission.

`ProviderRejection` is the only place an internal code becomes the controlled user
text, so no other module judges whether a message is safe to publish. These shapes
carry no behaviour, which keeps the ordered pipeline in `service.py` readable as the
security property it encodes.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from eval_platform.adapters.execution.provider_access.binding import RunBinding
from eval_platform.adapters.execution.provider_access.budget import Reservation
from eval_platform.adapters.execution.provider_access.failures import controlled_failure
from eval_platform.adapters.execution.provider_access.transport import OutboundRequest

# Above the byte count the ledger can admit under the conservative input count, so this
# never refuses a request the budget would allow, while still bounding what one client
# can make the proxy buffer.
MAX_BODY_BYTES = 1024 * 1024


@dataclass(frozen=True, slots=True)
class ProxyIdentity:
    """The one Run this proxy serves; the token carries no identity of its own."""

    run_id: str
    allowed_tools: frozenset[str]
    profile_path: Path
    profile_id: str


class ProviderRejection(Exception):
    """A refusal reduced to an internal code and the text a user may see."""

    def __init__(self, internal_code: str) -> None:
        self.internal_code = internal_code
        self.failure_code, self.failure_summary = controlled_failure(internal_code)
        super().__init__(internal_code)


@dataclass(frozen=True, slots=True)
class Admission:
    """What may be sent for an admitted request: identity, hold and the single call."""

    binding: RunBinding
    reservation: Reservation
    outbound: OutboundRequest
