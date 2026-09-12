from collections.abc import Mapping
from dataclasses import replace
from datetime import UTC, datetime
from uuid import uuid4

from eval_platform.application.ports.repositories import AgentConfigurationRepository
from eval_platform.domain.agent import AgentConfiguration
from eval_platform.domain.catalog import (
    CatalogForbidden,
    CatalogInvalid,
    RegisteredAgent,
)
from eval_platform.domain.identity import AuthenticatedActor


class AgentRegistry:
    def __init__(
        self,
        repository: AgentConfigurationRepository,
        presets: Mapping[str, tuple[str, AgentConfiguration]],
    ) -> None:
        self.repository = repository
        self.presets = dict(presets)

    def register(self, actor: AuthenticatedActor, preset_id: str) -> RegisteredAgent:
        if actor.role != "owner":
            raise CatalogForbidden
        preset = self.presets.get(preset_id)
        if preset is None:
            raise CatalogInvalid
        display_name, configuration = preset
        options = configuration.critical_config
        if (
            configuration.agent_name != "codex"
            or configuration.model_provider != "openai_chatgpt"
            or configuration.authentication_type != "chatgpt_auth_json"
            or set(options) != {"reasoning_effort"}
            or options["reasoning_effort"] not in ("low", "medium", "high", "xhigh")
        ):
            raise CatalogInvalid
        return self.repository.register(
            RegisteredAgent(
                replace(configuration, configuration_id=str(uuid4())),
                display_name,
                datetime.now(UTC),
            )
        )

    def get(self, actor: AuthenticatedActor, configuration_id: str) -> RegisteredAgent:
        return self.repository.get(configuration_id)

    def list(
        self,
        actor: AuthenticatedActor,
        enabled: bool | None,
        cursor: str | None,
        limit: int,
    ) -> tuple[list[RegisteredAgent], str | None]:
        if not 1 <= limit <= 100:
            raise CatalogInvalid
        records = self.repository.list(enabled, cursor, limit + 1)
        page = records[:limit]
        cursor = (
            page[-1].configuration.configuration_id if len(records) > limit else None
        )
        return page, cursor

    def disable(self, actor: AuthenticatedActor, configuration_id: str) -> None:
        if actor.role != "owner":
            raise CatalogForbidden
        self.repository.disable(configuration_id)
