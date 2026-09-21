"""Outbound request construction for the isolated proxy: fixed upstream, no retry.

The destination is never taken from the request. It is resolved from the
registered upstream of the bound provider, so a client-supplied URL or Host
header cannot redirect the call. Redirect following and retrying are rejected
by construction rather than by convention, because the fixed CLI was shown to
retry by default and the platform's zero-retry rule is not a preference.

Composing a request performs no IO. The body is kept out of every
representation and the safe summary reports shapes and sizes only, never a
header value, so nothing here can leak into a log.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType

from eval_platform.adapters.execution.provider_access.failures import (
    ProviderAccessError,
)
from eval_platform.adapters.execution.provider_access.request_policy import (
    PATH,
    strip_client_auth,
)
from eval_platform.adapters.execution.provider_access.secrets import (
    REGISTERED_UPSTREAMS,
)

METHOD = "POST"
AUTHORIZATION = "Authorization"
CONTENT_TYPE = "application/json"


@dataclass(frozen=True, slots=True)
class OutboundRequest:
    """A ready-to-send description; payload, headers and credential stay out of repr.

    The credential is held apart from ``headers`` on purpose. Merging it in at
    construction time would put it into ``repr(headers)``, and a single stray
    log line of that mapping would then leak it.
    """

    url: str
    headers: Mapping[str, str] = field(repr=False)
    payload: bytes = field(repr=False)
    authorization: str = field(repr=False, compare=False)
    max_attempts: int = 1
    follow_redirects: bool = False

    def __post_init__(self) -> None:
        if self.max_attempts != 1:
            raise ProviderAccessError("TRANSPORT_RETRY_NOT_PERMITTED")
        if self.follow_redirects:
            raise ProviderAccessError("TRANSPORT_REDIRECT_NOT_PERMITTED")
        if not self.url.startswith("https://"):
            raise ProviderAccessError("TRANSPORT_UPSTREAM_NOT_ENCRYPTED")
        if not self.authorization.strip():
            raise ProviderAccessError("TRANSPORT_CREDENTIAL_EMPTY")

    def send_headers(self) -> Mapping[str, str]:
        """The only supported way to obtain the outbound header set.

        The result carries the credential, so it must never be logged or
        persisted; ``safe_summary`` is the loggable view.
        """

        return MappingProxyType({**self.headers, AUTHORIZATION: self.authorization})

    def safe_summary(self) -> Mapping[str, object]:
        """Loggable description: shapes and sizes only, never a value."""

        return MappingProxyType(
            {
                "method": METHOD,
                "url": self.url,
                "header_names": tuple(sorted(self.send_headers())),
                "payload_bytes": len(self.payload),
            }
        )


def build_outbound(
    *,
    provider: str,
    body: Mapping[str, object],
    client_headers: Mapping[str, str],
    secret: str,
) -> OutboundRequest:
    """Compose the single permitted outbound call for this provider."""

    origin = REGISTERED_UPSTREAMS.get(provider)
    if origin is None:
        raise ProviderAccessError("TRANSPORT_PROVIDER_UNREGISTERED")
    if not secret.strip():
        raise ProviderAccessError("TRANSPORT_CREDENTIAL_EMPTY")
    headers = dict(strip_client_auth(client_headers))
    headers["Content-Type"] = CONTENT_TYPE
    try:
        payload = json.dumps(
            body, sort_keys=True, separators=(",", ":"), ensure_ascii=False
        ).encode("utf-8")
    except (TypeError, ValueError):
        raise ProviderAccessError("TRANSPORT_PAYLOAD_NOT_SERIALIZABLE") from None
    return OutboundRequest(
        url=f"{origin}{PATH}",
        headers=MappingProxyType(headers),
        payload=payload,
        authorization=f"Bearer {secret}",
    )
