from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime
from importlib.resources import files

import psycopg
from psycopg.rows import DictRow, dict_row

from eval_platform.domain.identity import (
    Account,
    AuthenticatedActor,
    IdentityConflict,
    IdentityUnavailable,
    Session,
)


class PostgresIdentityRepository:
    def __init__(self, dsn: str) -> None:
        self._dsn = dsn

    @contextmanager
    def _transaction(self) -> Iterator[psycopg.Connection[DictRow]]:
        try:
            with psycopg.connect(
                self._dsn,
                row_factory=dict_row,
                connect_timeout=3,
                options="-c statement_timeout=5000 -c lock_timeout=2000",
            ) as connection:
                yield connection
        except psycopg.errors.UniqueViolation:
            raise IdentityConflict from None
        except psycopg.Error:
            raise IdentityUnavailable from None

    def initialize_schema(self) -> None:
        """Explicit local maintenance only; never called during HTTP startup."""
        schema = files(__package__).joinpath("identity.sql").read_text(encoding="utf-8")
        with self._transaction() as connection:
            connection.execute(schema)

    def create_owner(self, account: Account) -> None:
        if account.actor.role != "owner":
            raise IdentityConflict
        with self._transaction() as connection:
            connection.execute(
                "INSERT INTO accounts (user_id, username, role, password_hash) "
                "VALUES (%s, %s, 'owner', %s)",
                (account.actor.user_id, account.actor.username, account.password_hash),
            )

    def find_account(self, username: str) -> Account | None:
        with self._transaction() as connection:
            row = connection.execute(
                "SELECT user_id, username, role, password_hash, auth_version, active "
                "FROM accounts WHERE username = %s",
                (username,),
            ).fetchone()
            if row is None:
                return None
            return Account(
                self._actor(row),
                str(row["password_hash"]),
                int(row["auth_version"]),
                bool(row["active"]),
            )

    def issue_session(self, session: Session) -> bool:
        with self._transaction() as connection:
            row = connection.execute(
                "SELECT auth_version, active FROM accounts "
                "WHERE user_id = %s FOR UPDATE",
                (session.user_id,),
            ).fetchone()
            if (
                not row
                or not row["active"]
                or row["auth_version"] != session.auth_version
            ):
                return False
            connection.execute(
                "INSERT INTO sessions (token_hash, user_id, auth_version, expires_at) "
                "VALUES (%s, %s, %s, %s)",
                (
                    session.token_hash,
                    session.user_id,
                    session.auth_version,
                    session.expires_at,
                ),
            )
            return True

    def session_actor(
        self, token_hash: str, now: datetime
    ) -> AuthenticatedActor | None:
        with self._transaction() as connection:
            row = connection.execute(
                "SELECT a.user_id, a.username, a.role FROM sessions s "
                "JOIN accounts a ON a.user_id = s.user_id "
                "WHERE s.token_hash = %s AND s.expires_at > %s "
                "AND s.auth_version = a.auth_version AND a.active",
                (token_hash, now),
            ).fetchone()
            return self._actor(row) if row else None

    def revoke_session(self, token_hash: str) -> None:
        with self._transaction() as connection:
            connection.execute(
                "DELETE FROM sessions WHERE token_hash = %s", (token_hash,)
            )

    def recover_owner(self, username: str, password_hash: str) -> AuthenticatedActor:
        with self._transaction() as connection:
            row = connection.execute(
                "UPDATE accounts SET password_hash = %s, "
                "auth_version = auth_version + 1 "
                "WHERE username = %s AND role = 'owner' "
                "RETURNING user_id, username, role",
                (password_hash, username),
            ).fetchone()
            if row is None:
                raise IdentityConflict
            connection.execute(
                "DELETE FROM sessions WHERE user_id = %s", (row["user_id"],)
            )
            return self._actor(row)

    @staticmethod
    def _actor(row: DictRow) -> AuthenticatedActor:
        role = row["role"]
        if role not in {"owner", "collaborator"}:
            raise IdentityUnavailable
        return AuthenticatedActor(str(row["user_id"]), str(row["username"]), role)
