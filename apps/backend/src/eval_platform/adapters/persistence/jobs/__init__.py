"""Explicit Job schema upgrade and safe short PostgreSQL transactions."""

from collections.abc import Iterator
from contextlib import contextmanager
from importlib.resources import files

import psycopg
from psycopg.rows import DictRow

from eval_platform.adapters.persistence.connection import transaction
from eval_platform.domain.jobs.models import JobIdempotencyConflict, JobUnavailable

_PRESET_CONSTRAINT = "evaluation_jobs_batch_preset_check"
_OLD_PRESET_DEFINITION = (
    "CHECK ((batch_preset = ANY (ARRAY['demo'::text, 'quick'::text, "
    "'standard'::text])))"
)
_CONTINUOUS_PRESET_DEFINITION = (
    "CHECK ((batch_preset = ANY (ARRAY['demo'::text, 'quick'::text, "
    "'standard'::text, 'continuous'::text])))"
)


@contextmanager
def job_transaction(dsn: str) -> Iterator[psycopg.Connection[DictRow]]:
    with transaction(
        dsn,
        conflict=JobIdempotencyConflict,
        unavailable=JobUnavailable,
    ) as connection:
        yield connection


@contextmanager
def job_read_transaction(dsn: str) -> Iterator[psycopg.Connection[DictRow]]:
    """Read several tables in one snapshot so concurrent writes cannot tear.

    `read_job` runs multiple SELECTs; under READ COMMITTED each statement may
    see a different snapshot, assembling an impossible state that fails the
    stored-state validation. REPEATABLE READ pins one snapshot for the read.
    """
    with job_transaction(dsn) as connection:
        connection.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY")
        yield connection


def initialize_schema(dsn: str) -> None:
    schema = files(__package__).joinpath("schema.sql").read_text(encoding="utf-8")
    with job_transaction(dsn) as connection:
        connection.execute(schema)


def upgrade_continuous_preset(dsn: str) -> bool:
    """Upgrade the known three-value preset constraint exactly once."""
    with job_transaction(dsn) as connection:
        connection.execute("LOCK TABLE evaluation_jobs IN ACCESS EXCLUSIVE MODE")
        definition = _preset_constraint(connection)
        if definition == _CONTINUOUS_PRESET_DEFINITION:
            return False
        if definition != _OLD_PRESET_DEFINITION:
            raise JobUnavailable
        connection.execute(
            "ALTER TABLE evaluation_jobs "
            "DROP CONSTRAINT evaluation_jobs_batch_preset_check, "
            "ADD CONSTRAINT evaluation_jobs_batch_preset_check "
            "CHECK (batch_preset IN ('demo','quick','standard','continuous'))"
        )
        if _preset_constraint(connection) != _CONTINUOUS_PRESET_DEFINITION:
            raise JobUnavailable
        return True


def _preset_constraint(connection: psycopg.Connection[DictRow]) -> str | None:
    row = connection.execute(
        "SELECT pg_get_constraintdef(oid) AS definition FROM pg_constraint "
        "WHERE conrelid='evaluation_jobs'::regclass AND conname=%s",
        (_PRESET_CONSTRAINT,),
    ).fetchone()
    return None if row is None else str(row["definition"])
