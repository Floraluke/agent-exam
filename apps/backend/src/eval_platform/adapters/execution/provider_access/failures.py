"""Proxy failures mapped to the user-facing controlled text (HTTP_API §10.2).

The HTTP contract requires `failure_code` to be a controlled enum and
`failure_summary` to be a short controlled sentence naming only the failure
class and stage: no upstream host or URL, no filesystem path, no credential
profile name, no token or key fragment, no container or network topology. This
module is the only place that turns a proxy-internal code into that text, so no
caller has to judge whether a message is safe.

An unmapped internal code becomes the generic controlled value; it is never
echoed, because an internal code has not been reviewed for publication and some
are raised next to paths and profile identities.

The codes below are candidates until the HTTP contract lists them. The
vocabulary guard in tests/providers/policy/test_controlled_failures.py fails
when a new internal code appears without a decision here.
"""

from __future__ import annotations

# Internal codes a Run can raise, grouped by what the user may be told.
_CREDENTIAL_UNAVAILABLE = (
    "PRIVATE_ACCESS_UNVERIFIABLE",
    "PRIVATE_FILE_IN_SYNC_LOCATION",
    "PRIVATE_FILE_CHANGED",
    "PRIVATE_FILE_MALFORMED",
    "PRIVATE_FILE_NOT_REGULAR",
    "PRIVATE_FILE_OWNER_MISMATCH",
    "PRIVATE_FILE_PERMISSIONS_TOO_WIDE",
    "PRIVATE_FILE_STRUCTURE_INVALID",
    "PRIVATE_FILE_SYMLINK_COMPONENT",
    "PRIVATE_FILE_TOO_LARGE",
    "PRIVATE_FILE_UNREADABLE",
    "PRIVATE_PROFILE_IDENTITY_EMPTY",
    "PRIVATE_PROFILE_ID_INVALID",
    "PRIVATE_PROFILE_NOT_FOUND",
    "PRIVATE_SECRET_EMPTY",
    "PRIVATE_UPSTREAM_NOT_REGISTERED",
    "TRANSPORT_CREDENTIAL_EMPTY",
)
_ACCESS_DENIED = (
    "PROVIDER_BINDING_ALREADY_ISSUED",
    "PROVIDER_BINDING_IDENTITY_EMPTY",
    "PROVIDER_BINDING_TTL_INVALID",
    "PROVIDER_TOKEN_CROSS_RUN",
    "PROVIDER_TOKEN_EXPIRED",
    "PROVIDER_TOKEN_NOT_UNIQUE",
    "PROVIDER_TOKEN_UNKNOWN",
    "PROVIDER_UNREGISTERED",
    "TRANSPORT_PROVIDER_UNREGISTERED",
)
_REQUEST_REJECTED = (
    "REQUEST_BODY_NOT_OBJECT",
    "REQUEST_HEADER_NOT_ALLOWED",
    "REQUEST_INPUT_EMPTY",
    "REQUEST_INPUT_INVALID",
    "REQUEST_MAX_OUTPUT_TOKENS_EXCEEDED",
    "REQUEST_MAX_OUTPUT_TOKENS_INVALID",
    "REQUEST_METHOD_NOT_ALLOWED",
    "REQUEST_MODEL_MISMATCH",
    "REQUEST_PATH_NOT_ALLOWED",
    "REQUEST_REQUIRED_FIELD_MISSING",
    "REQUEST_STREAM_REQUIRED",
    "REQUEST_TOOLS_INVALID",
    "REQUEST_TOOL_NOT_ALLOWED",
    "REQUEST_UNKNOWN_FIELD",
    "TRANSPORT_PAYLOAD_NOT_SERIALIZABLE",
    "TRANSPORT_REDIRECT_NOT_PERMITTED",
    "TRANSPORT_RETRY_NOT_PERMITTED",
    "TRANSPORT_UPSTREAM_NOT_ENCRYPTED",
)
_BUDGET_EXHAUSTED = (
    "BUDGET_CONSUMED_INVALID",
    "BUDGET_DEADLINE_EXCEEDED",
    "BUDGET_INPUT_EXCEEDED",
    "BUDGET_OUTPUT_EXCEEDED",
    "BUDGET_OUTPUT_REQUEST_INVALID",
    "BUDGET_PAYLOAD_NOT_SERIALIZABLE",
    "BUDGET_RESERVATION_UNKNOWN",
    "BUDGET_RUN_CLOSED",
)
# Raised only while configuring the proxy itself: a Run cannot trigger them, so they are
# deliberately absent from the published mapping.
CONFIGURATION_ONLY = frozenset(
    {
        "BUDGET_LIMITS_INVALID",
        "REQUEST_POLICY_CEILING_INVALID",
        "REQUEST_POLICY_MODEL_EMPTY",
        "REQUEST_POLICY_TOOLS_NOT_IMMUTABLE",
    }
)

_GROUPS = (
    (
        _CREDENTIAL_UNAVAILABLE,
        "PROVIDER_CREDENTIAL_UNAVAILABLE",
        "模型凭据不可用，运行未开始。",
    ),
    (_ACCESS_DENIED, "PROVIDER_ACCESS_DENIED", "模型访问未获授权。"),
    (_REQUEST_REJECTED, "PROVIDER_REQUEST_REJECTED", "模型请求不符合受限策略。"),
    (_BUDGET_EXHAUSTED, "PROVIDER_BUDGET_EXHAUSTED", "运行额度或期限已用尽。"),
)
MAPPED_CODES = {
    code: (failure, summary) for group, failure, summary in _GROUPS for code in group
}
GENERIC_FAILURE = ("PROVIDER_ACCESS_FAILED", "模型访问未完成。")
ALL_INTERNAL_CODES = frozenset(MAPPED_CODES) | CONFIGURATION_ONLY


class ProviderAccessError(ValueError):
    """A validated internal code; unknown strings cannot silently become generic."""

    def __init__(self, code: str) -> None:
        if code not in ALL_INTERNAL_CODES:
            raise ValueError("PROVIDER_INTERNAL_CODE_UNKNOWN")
        self.code = code
        super().__init__(code)


def controlled_failure(internal_code: str) -> tuple[str, str]:
    """Return the (failure_code, failure_summary) pair a user may see."""
    return MAPPED_CODES.get(internal_code, GENERIC_FAILURE)
