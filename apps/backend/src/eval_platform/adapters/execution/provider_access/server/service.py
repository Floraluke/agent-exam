"""The proxy pipeline: decide a request completely before anything leaves the process.

The order is the security property. Shape, token, policy, credential and hold are all
settled before an outbound request exists, so every refusal happens while nothing has
been sent and the ledger is untouched. Only the owner-private file is read and nothing
here opens a socket; the caller owns the connection, because the trial's network shape
is still the fixed-Harbor question (T2).
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
from eval_platform.adapters.execution.provider_access.failures import (
    ProviderAccessError,
)
from eval_platform.adapters.execution.provider_access.request_policy import (
    METHOD,
    PATH,
    RequestPolicy,
    check_request,
    strip_client_auth,
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
    bearer_token,
    without_connection_headers,
)
from eval_platform.adapters.execution.provider_access.transport import (
    OutboundRequest,
    build_outbound,
)


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

        headers = without_connection_headers(headers)
        body = self._shape(method, path, raw_body)
        binding = self._authenticate(headers)
        if self._ledger.closed_reason is not None:
            raise ProviderRejection("BUDGET_RUN_CLOSED")
        ceiling = self._ledger.remaining_output_tokens
        if ceiling <= 0:
            raise ProviderRejection("BUDGET_OUTPUT_EXCEEDED")
        checked, forwarded = self._apply_policy(
            binding, method, path, body, headers, ceiling=ceiling
        )
        profile = self._trusted_profile(binding)
        reservation = self._reserve(checked, ceiling)
        outbound = self._outbound(binding, checked, forwarded, profile)
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
                bearer_token(headers), run_id=self._identity.run_id
            )
        except ProviderAccessError as error:
            raise ProviderRejection(error.code) from None

    def _apply_policy(
        self,
        binding: RunBinding,
        method: str,
        path: str,
        body: Mapping[str, Any],
        headers: Mapping[str, str],
        *,
        ceiling: int,
    ) -> tuple[Mapping[str, Any], Mapping[str, str]]:
        """Step 3: the bound model, the tool list, the run's output and the headers.

        The header whitelist is evaluated here, *before* the hold, because it used to be
        caught in `build_outbound` (step 6) — after the reservation — and a hold that
        never becomes a relay is never settled, so the run silently lost that budget.
        """

        policy = RequestPolicy(
            model=binding.model,
            max_output_tokens=ceiling,
            allowed_tools=self._identity.allowed_tools,
        )
        try:
            checked = check_request(policy, method=method, path=path, body=body)
            return checked, strip_client_auth(headers)
        except ProviderAccessError as error:
            raise ProviderRejection(error.code) from None

    def _trusted_profile(self, binding: RunBinding) -> PrivateProfile:
        """Step 4: read the one profile this run may use, with its owner proof."""

        try:
            profile = load_profile(
                self._identity.profile_path,
                self._identity.profile_id,
                verify_access=self._verify_access,
            )
        except ProviderAccessError as error:
            raise ProviderRejection(error.code) from None
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
        except ProviderAccessError as error:
            raise ProviderRejection(error.code) from None

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
        except ProviderAccessError as error:
            raise ProviderRejection(error.code) from None
