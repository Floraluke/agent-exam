from datetime import UTC, datetime
from typing import Any

from psycopg.types.json import Jsonb

from eval_platform.adapters.persistence.catalog import catalog_transaction
from eval_platform.domain.agent import AgentConfiguration
from eval_platform.domain.catalog import (
    AgentConfigurationNotFound,
    CatalogUnavailable,
    RegisteredAgent,
)


def _record(row: dict[str, Any]) -> RegisteredAgent:
    try:
        configuration = AgentConfiguration(
            str(row["agent_configuration_id"]),
            row["agent_type"],
            row["agent_version"],
            row["model_provider"],
            row["model"],
            row["authentication_type"],
            row["credential_profile_id"],
            row["public_options"],
        )
    except (TypeError, ValueError, KeyError):
        raise CatalogUnavailable from None
    if configuration.fingerprint != row["configuration_fingerprint"]:
        raise CatalogUnavailable
    return RegisteredAgent(
        configuration,
        row["display_name"],
        row["created_at"],
        row["enabled"],
        row["disabled_at"],
        str(row["limit_profile_id"]) if row["limit_profile_id"] else None,
    )


class PostgresAgentRepository:
    def __init__(self, dsn: str) -> None:
        self.dsn = dsn

    def register(self, record: RegisteredAgent) -> RegisteredAgent:
        configuration = record.configuration
        with catalog_transaction(self.dsn) as connection:
            connection.execute(
                "INSERT INTO agent_configurations "
                "(agent_configuration_id, display_name, agent_type, agent_version, "
                "model_provider, model, authentication_type, credential_profile_id, "
                "public_options, configuration_fingerprint, enabled, created_at) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,true,%s) "
                "ON CONFLICT (configuration_fingerprint) DO NOTHING",
                (
                    configuration.configuration_id,
                    record.display_name,
                    configuration.agent_name,
                    configuration.agent_version,
                    configuration.model_provider,
                    configuration.model_name,
                    configuration.authentication_type,
                    configuration.credential_configuration_id,
                    Jsonb(dict(configuration.critical_config)),
                    configuration.fingerprint,
                    record.created_at,
                ),
            )
            row = connection.execute(
                "SELECT * FROM agent_configurations WHERE configuration_fingerprint=%s",
                (configuration.fingerprint,),
            ).fetchone()
        if row is None:
            raise CatalogUnavailable
        return _record(row)

    def get(self, configuration_id: str) -> RegisteredAgent:
        with catalog_transaction(self.dsn) as connection:
            row = connection.execute(
                "SELECT * FROM agent_configurations WHERE agent_configuration_id=%s",
                (configuration_id,),
            ).fetchone()
        if row is None:
            raise AgentConfigurationNotFound
        return _record(row)

    def list(
        self,
        agent_type: str | None,
        enabled: bool | None,
        cursor: str | None,
        limit: int,
    ) -> list[RegisteredAgent]:
        if not 1 <= limit <= 101:
            raise ValueError("Invalid repository page size")
        conditions = []
        values: list[Any] = []
        if agent_type is not None:
            conditions.append("agent_type=%s")
            values.append(agent_type)
        if enabled is not None:
            conditions.append("enabled=%s")
            values.append(enabled)
        if cursor:
            conditions.append("agent_configuration_id>%s")
            values.append(cursor)
        statement = "SELECT * FROM agent_configurations"
        if conditions:
            statement += " WHERE " + " AND ".join(conditions)
        statement += " ORDER BY agent_configuration_id LIMIT %s"
        with catalog_transaction(self.dsn) as connection:
            rows = connection.execute(statement, [*values, limit]).fetchall()
        return [_record(row) for row in rows]

    def disable(self, configuration_id: str) -> None:
        with catalog_transaction(self.dsn) as connection:
            row = connection.execute(
                "UPDATE agent_configurations SET enabled=false, "
                "disabled_at=COALESCE(disabled_at,%s) "
                "WHERE agent_configuration_id=%s RETURNING agent_configuration_id",
                (datetime.now(UTC), configuration_id),
            ).fetchone()
        if row is None:
            raise AgentConfigurationNotFound
