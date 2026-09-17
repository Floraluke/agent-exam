"""Atomic first-time schema initialization for an empty dedicated database."""

from importlib.resources import files

from eval_platform.adapters.persistence.connection import transaction

_SCHEMAS = (
    ("eval_platform.adapters.persistence", "identity.sql"),
    ("eval_platform.adapters.persistence", "membership.sql"),
    ("eval_platform.adapters.persistence.catalog", "schema.sql"),
    ("eval_platform.adapters.persistence.jobs", "schema.sql"),
)

_HAS_USER_OBJECTS = """
SELECT (
    EXISTS (
        SELECT 1 FROM pg_catalog.pg_namespace
        WHERE nspname NOT IN ('pg_catalog', 'information_schema', 'public')
          AND nspname !~ '^pg_(toast|temp)'
    )
    OR EXISTS (
        SELECT 1 FROM pg_catalog.pg_class c
        JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace
        WHERE n.nspname = 'public'
    )
    OR EXISTS (
        SELECT 1 FROM pg_catalog.pg_proc p
        JOIN pg_catalog.pg_namespace n ON n.oid = p.pronamespace
        WHERE n.nspname = 'public'
    )
    OR EXISTS (
        SELECT 1 FROM pg_catalog.pg_type t
        JOIN pg_catalog.pg_namespace n ON n.oid = t.typnamespace
        WHERE n.nspname = 'public'
    )
) AS has_user_objects
"""


def initialize_empty_database(dsn: str) -> None:
    """Install the complete schema once, refusing every non-empty database."""
    schemas = [
        files(package).joinpath(name).read_text(encoding="utf-8")
        for package, name in _SCHEMAS
    ]
    with transaction(dsn) as connection:
        connection.execute(
            "SELECT pg_advisory_xact_lock("
            "hashtextextended('agentexam-platform-init-v1', 0))"
        )
        row = connection.execute(_HAS_USER_OBJECTS).fetchone()
        if row is None or row["has_user_objects"]:
            raise ValueError("platform initialization requires an empty database")
        connection.execute("SET LOCAL search_path = public, pg_catalog")
        for schema in schemas:
            connection.execute(schema)
