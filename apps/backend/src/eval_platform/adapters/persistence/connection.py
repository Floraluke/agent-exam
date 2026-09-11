"""Short identity transactions; driver details never escape the adapter."""

from collections.abc import Iterator
from contextlib import contextmanager

import psycopg
from psycopg.rows import DictRow, dict_row

from eval_platform.domain.identity import IdentityConflict, IdentityUnavailable


@contextmanager
def transaction(dsn: str) -> Iterator[psycopg.Connection[DictRow]]:
    try:
        with psycopg.connect(
            dsn,
            row_factory=dict_row,
            connect_timeout=3,
            options="-c statement_timeout=5000 -c lock_timeout=2000",
        ) as connection:
            yield connection
    except psycopg.errors.UniqueViolation:
        raise IdentityConflict from None
    except psycopg.Error:
        raise IdentityUnavailable from None
