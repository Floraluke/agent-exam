"""Explicit catalog upgrade; importing or starting HTTP never creates tables."""

from collections.abc import Iterator
from contextlib import contextmanager
from importlib.resources import files

import psycopg
from psycopg.rows import DictRow

from eval_platform.adapters.persistence.connection import transaction
from eval_platform.domain.catalog import CatalogConflict, CatalogUnavailable


@contextmanager
def catalog_transaction(dsn: str) -> Iterator[psycopg.Connection[DictRow]]:
    with transaction(
        dsn,
        conflict=CatalogConflict,
        unavailable=CatalogUnavailable,
    ) as connection:
        yield connection


def initialize_schema(dsn: str) -> None:
    schema = files(__package__).joinpath("schema.sql").read_text(encoding="utf-8")
    with catalog_transaction(dsn) as connection:
        connection.execute(schema)


# The two identity constraints an install created before the controlled API identity
# existed still carries. Mirrors upgrade_continuous_preset in the Job package:
# verify the known old shape, upgrade, verify, refuse anything else rather than guess.
_PROVIDER_CONSTRAINT = "agent_configurations_model_provider_check"
_AUTHENTICATION_CONSTRAINT = "agent_configurations_authentication_type_check"
_PAIR_CONSTRAINT = "agent_configurations_identity_pair_check"
_LEGACY_DEFINITIONS = {
    _PROVIDER_CONSTRAINT: "CHECK ((model_provider = 'openai_chatgpt'::text))",
    _AUTHENTICATION_CONSTRAINT: (
        "CHECK ((authentication_type = 'chatgpt_auth_json'::text))"
    ),
}
_CONTROLLED_DEFINITIONS = {
    _PROVIDER_CONSTRAINT: (
        "CHECK ((model_provider = ANY (ARRAY['openai_chatgpt'::text, "
        "'internal_test_fake'::text])))"
    ),
    _AUTHENTICATION_CONSTRAINT: (
        "CHECK ((authentication_type = ANY (ARRAY['chatgpt_auth_json'::text, "
        "'provider_run_token'::text])))"
    ),
}
_PAIR_DEFINITION = (
    "CHECK ((((model_provider = 'openai_chatgpt'::text) AND "
    "(authentication_type = 'chatgpt_auth_json'::text)) OR "
    "((model_provider = 'internal_test_fake'::text) AND "
    "(authentication_type = 'provider_run_token'::text))))"
)
_CURRENT_DEFINITIONS = {**_CONTROLLED_DEFINITIONS, _PAIR_CONSTRAINT: _PAIR_DEFINITION}


def upgrade_api_constraints(dsn: str) -> bool:
    """Widen the identity constraints to the controlled sets, exactly once.

    Returns False when the install is already current and True when it changed. A
    definition that is neither the known legacy one nor the current one raises
    instead of being overwritten, so an unknown schema is never silently rewritten.
    """
    with catalog_transaction(dsn) as connection:
        connection.execute("LOCK TABLE agent_configurations IN ACCESS EXCLUSIVE MODE")
        definitions = _identity_definitions(connection)
        if definitions == _CURRENT_DEFINITIONS:
            return False
        if definitions not in (_LEGACY_DEFINITIONS, _CONTROLLED_DEFINITIONS):
            raise CatalogUnavailable
        if definitions == _LEGACY_DEFINITIONS:
            connection.execute(
                "ALTER TABLE agent_configurations "
                f"DROP CONSTRAINT {_PROVIDER_CONSTRAINT}, "
                f"DROP CONSTRAINT {_AUTHENTICATION_CONSTRAINT}, "
                f"ADD CONSTRAINT {_PROVIDER_CONSTRAINT} "
                "CHECK (model_provider IN ('openai_chatgpt','internal_test_fake')), "
                f"ADD CONSTRAINT {_AUTHENTICATION_CONSTRAINT} "
                "CHECK (authentication_type IN "
                "('chatgpt_auth_json','provider_run_token'))"
            )
        connection.execute(
            "ALTER TABLE agent_configurations "
            f"ADD CONSTRAINT {_PAIR_CONSTRAINT} CHECK ("
            "(model_provider = 'openai_chatgpt' AND "
            "authentication_type = 'chatgpt_auth_json') OR "
            "(model_provider = 'internal_test_fake' AND "
            "authentication_type = 'provider_run_token'))"
        )
        if _identity_definitions(connection) != _CURRENT_DEFINITIONS:
            raise CatalogUnavailable
        return True


def _identity_definitions(connection: psycopg.Connection[DictRow]) -> dict[str, str]:
    rows = connection.execute(
        "SELECT conname, pg_get_constraintdef(oid) AS definition FROM pg_constraint "
        "WHERE conrelid = 'agent_configurations'::regclass AND conname = ANY(%s)",
        (list(_CURRENT_DEFINITIONS),),
    ).fetchall()
    return {row["conname"]: row["definition"] for row in rows}
