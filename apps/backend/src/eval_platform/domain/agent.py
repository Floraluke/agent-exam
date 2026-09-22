from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any

# Agent identities the catalog may register, as
# (model_provider, authentication_type) pairs. Anything else is rejected before storage.
#
# The controlled API identity exists only so internal_test runs can exercise the
# provider proxy chain: its fixed upstream lives in the reserved `.invalid` domain,
# resolve outside the isolated trial network and a production binding fails closed. Real
# provider identities (DeepSeek/Kimi) stay with tasks 06/07.
CHATGPT_IDENTITY = ("openai_chatgpt", "chatgpt_auth_json")
INTERNAL_TEST_PROVIDER = "internal_test_fake"
INTERNAL_TEST_AUTHENTICATION = "provider_run_token"
INTERNAL_TEST_UPSTREAM = "https://fake-upstream.t05.invalid"
INTERNAL_TEST_IDENTITY = (INTERNAL_TEST_PROVIDER, INTERNAL_TEST_AUTHENTICATION)
CONTROLLED_IDENTITIES = frozenset({CHATGPT_IDENTITY, INTERNAL_TEST_IDENTITY})
CONTROLLED_AGENT_TYPES = ("codex",)
CONTROLLED_PROVIDERS = tuple(sorted({pair[0] for pair in CONTROLLED_IDENTITIES}))
CONTROLLED_AUTHENTICATION_TYPES = tuple(
    sorted({pair[1] for pair in CONTROLLED_IDENTITIES})
)


@dataclass(frozen=True, slots=True)
class AgentConfiguration:
    configuration_id: str
    agent_name: str
    agent_version: str
    model_provider: str
    model_name: str
    authentication_type: str
    credential_configuration_id: str
    critical_config: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        values = (
            self.configuration_id,
            self.agent_name,
            self.agent_version,
            self.model_provider,
            self.model_name,
            self.authentication_type,
            self.credential_configuration_id,
        )
        if any(not value.strip() for value in values):
            raise ValueError("Agent identity fields must not be empty")
        if (
            self.agent_name not in CONTROLLED_AGENT_TYPES
            or (self.model_provider, self.authentication_type)
            not in CONTROLLED_IDENTITIES
        ):
            raise ValueError("AGENT_IDENTITY_NOT_CONTROLLED")
        safe_config = json.loads(
            json.dumps(dict(self.critical_config), allow_nan=False)
        )
        object.__setattr__(self, "critical_config", _freeze(safe_config))

    @property
    def fingerprint(self) -> str:
        identity = {
            "agent_name": self.agent_name,
            "agent_version": self.agent_version,
            "authentication_type": self.authentication_type,
            "critical_config": _thaw(self.critical_config),
            "model_name": self.model_name,
            "model_provider": self.model_provider,
        }
        encoded = json.dumps(identity, sort_keys=True, separators=(",", ":")).encode()
        return hashlib.sha256(encoded).hexdigest()


def _freeze(value: Any) -> Any:
    if isinstance(value, dict):
        return MappingProxyType({key: _freeze(item) for key, item in value.items()})
    if isinstance(value, list):
        return tuple(_freeze(item) for item in value)
    return value


def _thaw(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {key: _thaw(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_thaw(item) for item in value]
    return value
