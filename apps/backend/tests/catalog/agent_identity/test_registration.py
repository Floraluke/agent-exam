"""受控 Agent 身份的登记：Codex 登录身份与受控假提供方身份。

任务 05 只放开一个受控的 API 身份（用户确认的方案 A），真实提供方身份留给 06/07。
本文件同时是响应枚举与域常量的对账门禁：两者若漂移，这里会失败。
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import get_args
from uuid import uuid4

import pytest
from identity.conftest import WRITE_HEADERS

from catalog.conftest import catalog_api
from catalog.memory import MemoryAgents
from eval_platform.application.agent_registry import AgentRegistry
from eval_platform.delivery.catalog_presets import (
    AGENT_PRESETS,
    INTERNAL_TEST_AGENT_PRESETS,
)
from eval_platform.delivery.http.catalog_schemas import AgentSummary
from eval_platform.domain.agent import (
    CONTROLLED_AGENT_TYPES,
    CONTROLLED_AUTHENTICATION_TYPES,
    CONTROLLED_PROVIDERS,
    INTERNAL_TEST_AUTHENTICATION,
    INTERNAL_TEST_PROVIDER,
    AgentConfiguration,
)
from eval_platform.domain.catalog import CatalogInvalid
from eval_platform.domain.identity import AuthenticatedActor

PRESET_ID = "internal-test-provider-proxy"
OWNER = AuthenticatedActor("owner-id", "owner", "owner")


def _preset(provider: str, authentication: str):
    return {
        "uncontrolled": (
            "Uncontrolled",
            AgentConfiguration(
                "uncontrolled",
                "codex",
                "0.153.0",
                provider,
                "some-model",
                authentication,
                "private-reference",
                {"reasoning_effort": "medium"},
            ),
        )
    }


def test_public_provider_enum_matches_the_controlled_sets():
    """Pin the contract enum to the domain constants so the two cannot drift."""
    declared = sorted(get_args(AgentSummary.model_fields["model_provider"].annotation))
    assert declared == sorted(CONTROLLED_PROVIDERS)
    assert (
        get_args(AgentSummary.model_fields["agent_type"].annotation)
        == CONTROLLED_AGENT_TYPES
    )
    assert sorted(CONTROLLED_AUTHENTICATION_TYPES) == [
        "chatgpt_auth_json",
        "provider_run_token",
    ]


def test_controlled_api_preset_is_registered_and_reported_honestly(identity_api):
    """The controlled preset registers, and the response reports its own identity.

    Before the fix the response repeated a hardcoded provider, so a record whose
    provider is not openai_chatgpt was still answered as openai_chatgpt: the provider
    assertion is what separates reporting the record from reporting a constant.
    """
    assert identity_api.login().status_code == 200
    with catalog_api(agent_presets=INTERNAL_TEST_AGENT_PRESETS) as api:
        assert api.login().status_code == 200
        endpoint = "/api/v1/agent-configurations"
        created = api.client.post(
            endpoint, json={"preset_id": PRESET_ID}, headers=WRITE_HEADERS
        )
        assert created.status_code == 201
        body = created.json()
        assert body["agent_type"] == "codex"
        assert body["model_provider"] == INTERNAL_TEST_PROVIDER
        assert body["display_name"] == "Internal test / provider proxy"

        page = api.client.get(endpoint).json()
        assert [item["model_provider"] for item in page["items"]] == [
            INTERNAL_TEST_PROVIDER
        ]
        detail = api.client.get(endpoint + "/" + body["agent_configuration_id"]).json()
        assert detail == body


def test_production_presets_carry_no_fake_provider():
    """Task 05 acceptance: the production catalog must not register a fake service."""
    assert PRESET_ID not in AGENT_PRESETS
    assert all(
        configuration.model_provider != INTERNAL_TEST_PROVIDER
        for _, configuration in AGENT_PRESETS.values()
    )


def test_uncontrolled_identity_is_rejected_before_storage():
    """A pair outside the controlled set never reaches a repository."""
    for provider, authentication in (
        ("deepseek", "chatgpt_auth_json"),
        ("openai_chatgpt", "provider_run_token"),
        ("internal_test_fake", "chatgpt_auth_json"),
    ):
        presets = _preset(provider, authentication)
        with pytest.raises(CatalogInvalid):
            AgentRegistry(MemoryAgents(), presets).register(OWNER, "uncontrolled")


@pytest.mark.integration
def test_controlled_identity_round_trips_and_upgrades_explicitly(postgres_sandbox):
    """Real PostgreSQL: a legacy install rejects the controlled identity until
    upgraded."""
    from eval_platform.adapters.persistence.catalog import (
        initialize_schema,
        upgrade_api_constraints,
    )
    from eval_platform.adapters.persistence.catalog.agents import (
        PostgresAgentRepository,
    )
    from eval_platform.domain.catalog import CatalogUnavailable, RegisteredAgent

    initialize_schema(postgres_sandbox.dsn)
    repository = PostgresAgentRepository(postgres_sandbox.dsn)
    record = RegisteredAgent(
        AgentConfiguration(
            str(uuid4()),
            "codex",
            "0.153.0",
            INTERNAL_TEST_PROVIDER,
            "deepseek-flash",
            INTERNAL_TEST_AUTHENTICATION,
            "t05-fake-provider",
            {"reasoning_effort": "medium"},
        ),
        "Internal test",
        datetime.now(UTC),
    )

    # A fresh install is already current, so there is nothing to migrate.
    assert upgrade_api_constraints(postgres_sandbox.dsn) is False

    # An install created before the controlled identity carries single-value
    # constraints: it refuses the controlled record, and the upgrade is what fixes it.
    _set_identity_constraints(
        postgres_sandbox.dsn,
        "CHECK (model_provider = 'openai_chatgpt')",
        "CHECK (authentication_type = 'chatgpt_auth_json')",
    )
    with pytest.raises(CatalogUnavailable):
        repository.register(record)
    assert upgrade_api_constraints(postgres_sandbox.dsn) is True
    registered = repository.register(record)
    assert repository.get(registered.configuration.configuration_id) == registered
    assert upgrade_api_constraints(postgres_sandbox.dsn) is False

    # An unknown shape is refused rather than overwritten.
    _set_identity_constraints(
        postgres_sandbox.dsn, "CHECK (model_provider LIKE '%')", None
    )
    with pytest.raises(CatalogUnavailable):
        upgrade_api_constraints(postgres_sandbox.dsn)


def _set_identity_constraints(dsn: str, provider: str, authentication: str | None):
    from eval_platform.adapters.persistence.catalog import catalog_transaction

    with catalog_transaction(dsn) as connection:
        connection.execute(
            "ALTER TABLE agent_configurations "
            "DROP CONSTRAINT IF EXISTS agent_configurations_model_provider_check, "
            "DROP CONSTRAINT IF EXISTS agent_configurations_authentication_type_check"
        )
        connection.execute(
            "ALTER TABLE agent_configurations ADD CONSTRAINT "
            f"agent_configurations_model_provider_check {provider}"
        )
        if authentication is not None:
            connection.execute(
                "ALTER TABLE agent_configurations ADD CONSTRAINT "
                f"agent_configurations_authentication_type_check {authentication}"
            )
