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


@dataclass(frozen=True, slots=True)
class RequestPolicy:
    """Bound model, output ceiling and the only tools this run may request."""

    model: str
    max_output_tokens: int
    allowed_tools: frozenset[str]

    def __post_init__(self) -> None:
        if not self.model.strip():
            raise ValueError("REQUEST_POLICY_MODEL_EMPTY")
        if self.max_output_tokens <= 0:
            raise ValueError("REQUEST_POLICY_CEILING_INVALID")
        if not isinstance(self.allowed_tools, frozenset):
            raise ValueError("REQUEST_POLICY_TOOLS_NOT_IMMUTABLE")


def check_request(
    policy: RequestPolicy,
    *,
    method: str,
    path: str,
    body: Any,
) -> Mapping[str, Any]:
    """Return the whitelisted body, or raise a fixed code before any egress."""

    if method != METHOD:
        raise ValueError("REQUEST_METHOD_NOT_ALLOWED")
    if path != PATH:
        raise ValueError("REQUEST_PATH_NOT_ALLOWED")
    if not isinstance(body, Mapping):
        raise ValueError("REQUEST_BODY_NOT_OBJECT")
    keys = {key for key in body if isinstance(key, str)}
    if len(keys) != len(body):
        raise ValueError("REQUEST_BODY_NOT_OBJECT")
    if keys - ALLOWED_FIELDS:
        raise ValueError("REQUEST_UNKNOWN_FIELD")
    if REQUIRED_FIELDS - keys:
        raise ValueError("REQUEST_REQUIRED_FIELD_MISSING")
    if body["model"] != policy.model:
        raise ValueError("REQUEST_MODEL_MISMATCH")
    if body.get("stream") is not True:
        raise ValueError("REQUEST_STREAM_REQUIRED")
    _check_input(body["input"])
    _check_output_ceiling(policy, body.get("max_output_tokens"))
    _check_tools(policy, body.get("tools"))
    return MappingProxyType({key: body[key] for key in sorted(keys)})


def strip_client_auth(headers: Mapping[str, str]) -> Mapping[str, str]:
    """Drop client authentication; the trusted side adds the real key."""

    return MappingProxyType(
        {
            key: value
            for key, value in headers.items()
            if key.strip().lower() not in CLIENT_AUTH_HEADERS
        }
    )


def _check_input(value: Any) -> None:
    if isinstance(value, str):
        if not value.strip():
            raise ValueError("REQUEST_INPUT_EMPTY")
        return
    if not isinstance(value, Sequence) or isinstance(value, (bytes, bytearray)):
        raise ValueError("REQUEST_INPUT_INVALID")
    if not value:
        raise ValueError("REQUEST_INPUT_EMPTY")


def _check_output_ceiling(policy: RequestPolicy, value: Any) -> None:
    if value is None:
        return
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise ValueError("REQUEST_MAX_OUTPUT_TOKENS_INVALID")
    if value > policy.max_output_tokens:
        raise ValueError("REQUEST_MAX_OUTPUT_TOKENS_EXCEEDED")


def _check_tools(policy: RequestPolicy, value: Any) -> None:
    if value is None:
        return
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        raise ValueError("REQUEST_TOOLS_INVALID")
    for entry in value:
        if not isinstance(entry, Mapping) or not isinstance(entry.get("type"), str):
            raise ValueError("REQUEST_TOOLS_INVALID")
        if entry["type"] not in policy.allowed_tools:
            raise ValueError("REQUEST_TOOL_NOT_ALLOWED")
