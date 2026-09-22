"""The values that cross the proxy boundary: identity, refusal and admission.

`ProviderRejection` is the only place an internal code becomes the controlled user
text, so no other module judges whether a message is safe to publish. The inbound
helpers below reduce a raw HTTP request to what the client is actually asking for; they
hold no state and touch nothing, which keeps the ordered pipeline in `service.py`
readable as the security property it encodes.
"""

from __future__ import annotations

from collections.abc import Mapping
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

AUTHORIZATION = "authorization"
BEARER_PREFIX = "bearer "

# Headers that describe the client's connection *to this proxy* rather than its request
# to the upstream: `Host` names this proxy, and the rest are hop-by-hop (RFC 9110
# section 7.6.1). They are dropped before the policy runs, because a real HTTP client
# always sends `Host` and the policy refuses any client header it has not whitelisted.
# A header that tries to steer routing (`X-Forwarded-Host`, `Forwarded`) is deliberately
# absent here: it reaches the policy and is refused there.
CONNECTION_OWNED_HEADERS = frozenset(
    {
        "connection",
        "host",
        "keep-alive",
        "te",
        "trailer",
        "transfer-encoding",
        "upgrade",
    }
)


def without_connection_headers(headers: Mapping[str, str]) -> Mapping[str, str]:
    """Reduce the inbound request to what the client is actually asking for."""

    return {
        name: value
        for name, value in headers.items()
        if name.strip().lower() not in CONNECTION_OWNED_HEADERS
    }


def bearer_token(headers: Mapping[str, str]) -> str:
    """The presented token, or an empty string that resolves to 'unknown'."""

    for name, value in headers.items():
        if name.strip().lower() != AUTHORIZATION:
            continue
        if value.lower().startswith(BEARER_PREFIX):
            return value[len(BEARER_PREFIX) :].strip()
    return ""


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
