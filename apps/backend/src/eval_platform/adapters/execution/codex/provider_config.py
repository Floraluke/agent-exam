"""Render the fixed provider entry the task container's Codex CLI reads.

The container may reach only the proxy, so the rendered file points the CLI at the
proxy entry and names the environment variable that will hold this Run's token. It
never holds a credential: the function takes the variable's *name*, and only the name
is written.

RETRY CAPS ARE WRITTEN IN BOTH PLACEMENTS ON PURPOSE. The design freeze requires
`request_max_retries = 0` and `stream_max_retries = 0` to be explicit, because the
CLI's defaults are not zero, but the repository has no verified statement of which
table the fixed 0.153.0 reads them from (research section 1 records the options, not
their nesting). Writing both cannot silently lose the cap: whichever placement the CLI
honours is zero, and a strict parser that rejects the extra key fails loudly in the
contract probe rather than quietly retrying. Reconciling this against the fixed CLI is
part of the S2 verification and is why the layout below stays in one function with a
pinned digest.

The enforcing invariant for "no retries" is not this file: `transport.py` refuses any
outbound request whose `max_attempts` is not 1, so a config the CLI ignored cannot
produce a re-send."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass

from eval_platform.adapters.execution.provider_access.secrets import (
    REGISTERED_UPSTREAMS,
)

_LOGICAL_ID = re.compile(r"[a-z][a-z0-9_]{1,31}")
_ENV_NAME = re.compile(r"[A-Z][A-Z0-9_]{2,63}")
_BASE_URL = re.compile(
    r"^(?P<scheme>https?)://(?P<host>[a-z0-9.-]+)(?::(?P<port>[0-9]{1,5}))?$"
)
WIRE_API = "responses"
RETRY_KEYS = ("request_max_retries", "stream_max_retries")
RETRY_VALUE = 0
# The container may reach only the proxy, so its CLI entry must never be a
# provider-side endpoint. `REGISTERED_UPSTREAMS` holds the proxy's own
# destinations, but it is narrowed to the controlled fake provider, so it can
# no longer answer "is this a real vendor?"; the real hosts are named here until
# tasks 06/07 register them.
REAL_PROVIDER_HOSTS = frozenset({"api.deepseek.com", "api.moonshot.cn"})


@dataclass(frozen=True, slots=True)
class ProviderConfig:
    text: str
    digest: str
    provider: str
    base_url: str
    env_key: str

    def __repr__(self) -> str:
        return (
            f"ProviderConfig(provider={self.provider!r}, base_url={self.base_url!r}, "
            f"env_key={self.env_key!r}, digest={self.digest!r})"
        )


def render_provider_config(
    *, provider: str, base_url: str, env_key: str
) -> ProviderConfig:
    """Return the fixed config text plus its digest, or raise a fixed code."""
    if not _LOGICAL_ID.fullmatch(provider) or provider not in REGISTERED_UPSTREAMS:
        raise ValueError("PROVIDER_CONFIG_PROVIDER_NOT_REGISTERED")
    if not _ENV_NAME.fullmatch(env_key):
        raise ValueError("PROVIDER_CONFIG_ENV_KEY_INVALID")
    match = _BASE_URL.fullmatch(base_url)
    if match is None or match.group("host") in {"localhost", "127.0.0.1", "::1"}:
        # The entry must be a host the isolated trial network resolves, never loopback:
        # loopback inside the task container would mean the CLI talking to itself.
        raise ValueError("PROVIDER_CONFIG_ENTRY_INVALID")
    if base_url in set(REGISTERED_UPSTREAMS.values()) or (
        match.group("host") in REAL_PROVIDER_HOSTS
    ):
        # A provider-side endpoint belongs on the trusted proxy side only.
        raise ValueError("PROVIDER_CONFIG_ENTRY_IS_UPSTREAM")
    lines = [
        "# Rendered for this Run. The token value is never written here.",
        f'model_provider = "{provider}"',
        *[f"{key} = {RETRY_VALUE}" for key in RETRY_KEYS],
        "",
        f"[model_providers.{provider}]",
        f'name = "{provider}"',
        f'base_url = "{base_url}"',
        f'env_key = "{env_key}"',
        f'wire_api = "{WIRE_API}"',
        *[f"{key} = {RETRY_VALUE}" for key in RETRY_KEYS],
    ]
    text = "\n".join(lines) + "\n"
    return ProviderConfig(
        text,
        hashlib.sha256(text.encode("utf-8")).hexdigest(),
        provider,
        base_url,
        env_key,
    )
