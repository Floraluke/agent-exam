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
