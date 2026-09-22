from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from eval_platform.delivery import catalog as catalog_delivery
from eval_platform.domain.agent import AgentConfiguration


@pytest.mark.parametrize(
    ("provider", "authentication"),
    [
        ("openai_chatgpt", "provider_run_token"),
        ("internal_test_fake", "chatgpt_auth_json"),
        ("deepseek", "provider_run_token"),
    ],
)
def test_agent_configuration_rejects_uncontrolled_identity_pairs(
    provider: str, authentication: str
) -> None:
    with pytest.raises(ValueError, match="AGENT_IDENTITY_NOT_CONTROLLED"):
        AgentConfiguration(
            "candidate",
            "codex",
            "0.153.0",
            provider,
            "some-model",
            authentication,
            "private-reference",
            {"reasoning_effort": "medium"},
        )


@pytest.mark.integration
def test_database_rejects_crossed_controlled_identity(postgres_sandbox) -> None:
    from eval_platform.adapters.persistence.catalog import initialize_schema
    from eval_platform.adapters.persistence.catalog.agents import (
        PostgresAgentRepository,
    )
    from eval_platform.domain.catalog import CatalogUnavailable, RegisteredAgent

    initialize_schema(postgres_sandbox.dsn)
    valid = AgentConfiguration(
        str(uuid4()),
        "codex",
        "0.153.0",
        "internal_test_fake",
        "deepseek-flash",
        "provider_run_token",
        "private-reference",
        {"reasoning_effort": "medium"},
    )
    crossed = object.__new__(AgentConfiguration)
    for field, value in {
        "configuration_id": str(uuid4()),
        "agent_name": valid.agent_name,
        "agent_version": valid.agent_version,
        "model_provider": valid.model_provider,
        "model_name": valid.model_name,
        "authentication_type": "chatgpt_auth_json",
        "credential_configuration_id": valid.credential_configuration_id,
        "critical_config": valid.critical_config,
    }.items():
        object.__setattr__(crossed, field, value)
    record = RegisteredAgent(crossed, "Crossed identity", datetime.now(UTC))
    with pytest.raises(CatalogUnavailable):
        PostgresAgentRepository(postgres_sandbox.dsn).register(record)


@pytest.mark.parametrize(
    ("changed", "expected"),
    [(True, "已升级"), (False, "无需重复升级")],
)
def test_identity_constraint_upgrade_command_reports_result(
    monkeypatch, capsys, changed: bool, expected: str
) -> None:
    monkeypatch.setattr(catalog_delivery, "database_url", lambda: "test-dsn")
    monkeypatch.setattr(
        catalog_delivery, "upgrade_api_constraints", lambda dsn: changed
    )

    assert catalog_delivery.main(["upgrade-api-constraints"]) == 0
    assert expected in capsys.readouterr().out
