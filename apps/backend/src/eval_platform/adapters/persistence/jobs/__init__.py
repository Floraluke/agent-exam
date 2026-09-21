"""Explicit Job schema upgrade and safe short PostgreSQL transactions."""

from collections.abc import Iterator
from contextlib import contextmanager
from importlib.resources import files

import psycopg
from psycopg.rows import DictRow

from eval_platform.adapters.persistence.connection import transaction
from eval_platform.domain.jobs.models import JobIdempotencyConflict, JobUnavailable


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
        connection.execute(
            "SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY"
        )
        yield connection


def initialize_schema(dsn: str) -> None:
    schema = files(__package__).joinpath("schema.sql").read_text(encoding="utf-8")
    with job_transaction(dsn) as connection:
        connection.execute(schema)
