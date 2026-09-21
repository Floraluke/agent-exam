"""The proxy pipeline: decide a request completely before anything leaves the process.

The order is the security property. Shape, token, policy, credential and hold are all
settled before an outbound request exists, so every refusal happens while nothing has
been sent and the ledger is untouched.

Only the owner-private file is read; nothing here opens a socket. The sender is
deliberately absent: the trial's network shape is still the fixed-Harbor question (T2),
so this returns a ready-to-send description and the caller owns the connection.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

from eval_platform.adapters.execution.provider_access.binding import (
    RunBinding,
    TokenRegistry,
)
from eval_platform.adapters.execution.provider_access.budget import (
    BudgetLedger,
    Reservation,
)
from eval_platform.adapters.execution.provider_access.request_policy import (
    METHOD,
    PATH,
    RequestPolicy,
    check_request,
)
from eval_platform.adapters.execution.provider_access.secrets import (
    PrivateProfile,
    load_profile,
)
from eval_platform.adapters.execution.provider_access.server.contracts import (
    MAX_BODY_BYTES,
    Admission,
    ProviderRejection,
    ProxyIdentity,
)
from eval_platform.adapters.execution.provider_access.transport import (
    OutboundRequest,
    build_outbound,
)

AUTHORIZATION = "authorization"
BEARER_PREFIX = "bearer "


class ProviderProxyService:
    """Wires the reviewed pieces into the ordered pipeline; performs no egress."""

    def __init__(
        self,
        identity: ProxyIdentity,
        *,
        registry: TokenRegistry,
        ledger: BudgetLedger,
        verify_access: Callable[[Path], None],
        max_body_bytes: int = MAX_BODY_BYTES,
    ) -> None:
        self._identity = identity
        self._registry = registry
        self._ledger = ledger
        self._verify_access = verify_access
        self._max_body_bytes = max_body_bytes

    def decide(
        self,
        *,
        method: str,
        path: str,
        raw_body: bytes,
        headers: Mapping[str, str],
    ) -> Admission:
        """Decide one request; return what may be sent, or raise ProviderRejection."""

        body = self._shape(method, path, raw_body)
        binding = self._authenticate(headers)
        if self._ledger.closed_reason is not None:
            raise ProviderRejection("BUDGET_RUN_CLOSED")
        ceiling = self._ledger.remaining_output_tokens
        if ceiling <= 0:
            raise ProviderRejection("BUDGET_OUTPUT_EXCEEDED")
        checked = self._apply_policy(binding, method, path, body, ceiling=ceiling)
        profile = self._trusted_profile(binding)
        reservation = self._reserve(checked, ceiling)
        outbound = self._outbound(binding, checked, headers, profile)
        return Admission(binding, reservation, outbound)

    def _shape(self, method: str, path: str, raw_body: bytes) -> Mapping[str, Any]:
        """Step 1: the only accepted request is POST /responses, size-capped."""

        if method != METHOD:
            raise ProviderRejection("REQUEST_METHOD_NOT_ALLOWED")
        if path != PATH:
            raise ProviderRejection("REQUEST_PATH_NOT_ALLOWED")
        if len(raw_body) > self._max_body_bytes:
            raise ProviderRejection("REQUEST_BODY_TOO_LARGE")
        try:
            body = json.loads(raw_body)
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise ProviderRejection("REQUEST_BODY_MALFORMED") from None
        if not isinstance(body, dict):
            raise ProviderRejection("REQUEST_BODY_NOT_OBJECT")
        return body

    def _authenticate(self, headers: Mapping[str, str]) -> RunBinding:
        """Step 2: the token resolves against *this* run, or nothing proceeds."""

        try:
            return self._registry.resolve(
                _bearer_token(headers), run_id=self._identity.run_id
            )
        except ValueError as error:
            raise ProviderRejection(str(error)) from None

    def _apply_policy(
        self,
        binding: RunBinding,
        method: str,
        path: str,
        body: Mapping[str, Any],
        *,
        ceiling: int,
    ) -> Mapping[str, Any]:
        """Step 3: the bound model, the tool list and the run's remaining output."""

        policy = RequestPolicy(
            model=binding.model,
            max_output_tokens=ceiling,
            allowed_tools=self._identity.allowed_tools,
        )
        try:
            return check_request(policy, method=method, path=path, body=body)
        except ValueError as error:
            raise ProviderRejection(str(error)) from None

    def _trusted_profile(self, binding: RunBinding) -> PrivateProfile:
        """Step 4: read the one profile this run may use, with its owner proof."""

        try:
            profile = load_profile(
                self._identity.profile_path,
                self._identity.profile_id,
                verify_access=self._verify_access,
            )
        except ValueError as error:
            raise ProviderRejection(str(error)) from None
        if profile.provider != binding.provider or profile.model != binding.model:
            # A profile's secret may only ever reach its own provider: a mismatched
            # selection would hand one vendor's key to another vendor's endpoint.
            raise ProviderRejection("PRIVATE_PROFILE_RUN_MISMATCH")
        return profile

    def _reserve(self, checked: Mapping[str, Any], ceiling: int) -> Reservation:
        """Step 5: hold the input bound plus the requested output, atomically."""

        requested = checked.get("max_output_tokens")
        # json serializes only real dicts, and the hold must bound exactly the bytes the
        # outbound serializer will produce.
        try:
            return self._ledger.reserve(
                dict(checked),
                max_output_tokens=ceiling if requested is None else requested,
            )
        except ValueError as error:
            raise ProviderRejection(str(error)) from None

    def _outbound(
        self,
        binding: RunBinding,
        checked: Mapping[str, Any],
        headers: Mapping[str, str],
        profile: PrivateProfile,
    ) -> OutboundRequest:
        """Step 6: compose the single permitted call; client credentials are dropped."""

        try:
            return build_outbound(
                provider=binding.provider,
                body=dict(checked),
                client_headers=headers,
                secret=profile.secret,
            )
        except ValueError as error:
            raise ProviderRejection(str(error)) from None


def _bearer_token(headers: Mapping[str, str]) -> str:
    """The presented token, or an empty string that resolves to 'unknown'."""

    for name, value in headers.items():
        if name.strip().lower() != AUTHORIZATION:
            continue
        if value.lower().startswith(BEARER_PREFIX):
            return value[len(BEARER_PREFIX) :].strip()
    return ""
