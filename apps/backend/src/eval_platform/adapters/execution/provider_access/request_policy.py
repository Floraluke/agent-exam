"""Request whitelist for the isolated proxy entry: reject before any egress.

The proxy is the only reachable peer for the workload, so every request body is
decided here rather than forwarded and filtered later. Only fields the fixed CLI
was observed to send are admitted; anything else is a hard rejection, not an
ignored key. Nothing in this module reads a credential or performs IO.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any

from eval_platform.adapters.execution.provider_access.failures import (
    ProviderAccessError,
)

PATH = "/responses"
METHOD = "POST"
ALLOWED_FIELDS = frozenset(
    {
        "model",
        "stream",
        "input",
        "tools",
        "max_output_tokens",
        "instructions",
        "reasoning",
    }
)
REQUIRED_FIELDS = frozenset({"model", "input"})
CLIENT_AUTH_HEADERS = frozenset(
    {"authorization", "proxy-authorization", "x-api-key", "api-key"}
)
IGNORED_CLIENT_HEADERS = frozenset({"content-length", "content-type"})
FORWARDED_CLIENT_HEADERS = frozenset({"accept", "accept-encoding", "user-agent"})


@dataclass(frozen=True, slots=True)
class RequestPolicy:
    """Bound model, output ceiling and the only tools this run may request."""

    model: str
    max_output_tokens: int
    allowed_tools: frozenset[str]

    def __post_init__(self) -> None:
        if not self.model.strip():
            raise ProviderAccessError("REQUEST_POLICY_MODEL_EMPTY")
        if self.max_output_tokens <= 0:
            raise ProviderAccessError("REQUEST_POLICY_CEILING_INVALID")
        if not isinstance(self.allowed_tools, frozenset):
            raise ProviderAccessError("REQUEST_POLICY_TOOLS_NOT_IMMUTABLE")


def check_request(
    policy: RequestPolicy,
    *,
    method: str,
    path: str,
    body: Any,
) -> Mapping[str, Any]:
    """Return the whitelisted body, or raise a fixed code before any egress."""

    if method != METHOD:
        raise ProviderAccessError("REQUEST_METHOD_NOT_ALLOWED")
    if path != PATH:
        raise ProviderAccessError("REQUEST_PATH_NOT_ALLOWED")
    if not isinstance(body, Mapping):
        raise ProviderAccessError("REQUEST_BODY_NOT_OBJECT")
    keys = {key for key in body if isinstance(key, str)}
    if len(keys) != len(body):
        raise ProviderAccessError("REQUEST_BODY_NOT_OBJECT")
    if keys - ALLOWED_FIELDS:
        raise ProviderAccessError("REQUEST_UNKNOWN_FIELD")
    if REQUIRED_FIELDS - keys:
        raise ProviderAccessError("REQUEST_REQUIRED_FIELD_MISSING")
    if body["model"] != policy.model:
        raise ProviderAccessError("REQUEST_MODEL_MISMATCH")
    if body.get("stream") is not True:
        raise ProviderAccessError("REQUEST_STREAM_REQUIRED")
    _check_input(body["input"])
    _check_output_ceiling(policy, body.get("max_output_tokens"))
    _check_tools(policy, body.get("tools"))
    return MappingProxyType({key: body[key] for key in sorted(keys)})


def strip_client_auth(headers: Mapping[str, str]) -> Mapping[str, str]:
    """Strip credentials and reject every non-approved client header."""

    forwarded: dict[str, str] = {}
    for key, value in headers.items():
        normalized = key.strip().lower()
        if normalized in CLIENT_AUTH_HEADERS | IGNORED_CLIENT_HEADERS:
            continue
        if normalized not in FORWARDED_CLIENT_HEADERS:
            raise ProviderAccessError("REQUEST_HEADER_NOT_ALLOWED")
        forwarded[key] = value
    return MappingProxyType(forwarded)


def _check_input(value: Any) -> None:
    if isinstance(value, str):
        if not value.strip():
            raise ProviderAccessError("REQUEST_INPUT_EMPTY")
        return
    if not isinstance(value, Sequence) or isinstance(value, (bytes, bytearray)):
        raise ProviderAccessError("REQUEST_INPUT_INVALID")
    if not value:
        raise ProviderAccessError("REQUEST_INPUT_EMPTY")


def _check_output_ceiling(policy: RequestPolicy, value: Any) -> None:
    if value is None:
        return
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise ProviderAccessError("REQUEST_MAX_OUTPUT_TOKENS_INVALID")
    if value > policy.max_output_tokens:
        raise ProviderAccessError("REQUEST_MAX_OUTPUT_TOKENS_EXCEEDED")


def _check_tools(policy: RequestPolicy, value: Any) -> None:
    if value is None:
        return
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        raise ProviderAccessError("REQUEST_TOOLS_INVALID")
    for entry in value:
        if not isinstance(entry, Mapping) or not isinstance(entry.get("type"), str):
            raise ProviderAccessError("REQUEST_TOOLS_INVALID")
        if entry["type"] not in policy.allowed_tools:
            raise ProviderAccessError("REQUEST_TOOL_NOT_ALLOWED")
