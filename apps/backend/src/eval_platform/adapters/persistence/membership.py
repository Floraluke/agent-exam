from datetime import datetime
from importlib.resources import files

from psycopg.rows import DictRow

from eval_platform.adapters.persistence.connection import transaction
from eval_platform.domain.identity import Account, IdentityConflict
from eval_platform.domain.membership import (
    Invitation,
    InvitationUnavailable,
    Member,
    MemberNotFound,
    MembershipForbidden,
)


class PostgresMembershipRepository:
    def __init__(self, dsn: str) -> None:
        self._dsn = dsn

    def initialize_schema(self) -> None:
        schema = (
            files(__package__).joinpath("membership.sql").read_text(encoding="utf-8")
        )
        with transaction(self._dsn) as connection:
            connection.execute(schema)

    def create_invitation(self, invitation: Invitation, token_hash: str) -> None:
        with transaction(self._dsn) as connection:
            result = connection.execute(
                "INSERT INTO invitations "
                "(invitation_id, token_hash, created_by, created_at, expires_at) "
                "SELECT %s, %s, user_id, %s, %s FROM accounts "
                "WHERE user_id = %s AND role = 'owner' AND active",
                (
                    invitation.invitation_id,
                    token_hash,
                    invitation.created_at,
                    invitation.expires_at,
                    invitation.created_by,
                ),
            )
            if result.rowcount != 1:
                raise MembershipForbidden

    def redeem_invitation(
        self, token_hash: str, account: Account, now: datetime
    ) -> None:
        if account.actor.role != "collaborator":
            raise MembershipForbidden
        with transaction(self._dsn) as connection:
            row = connection.execute(
                "SELECT invitation_id, created_by, created_at, expires_at, "
                "revoked_at, redeemed_at, redeemed_by FROM invitations "
                "WHERE token_hash = %s FOR UPDATE",
                (token_hash,),
            ).fetchone()
            # Observe expiry after acquiring the lock, including time spent waiting.
            clock = connection.execute("SELECT clock_timestamp() AS now").fetchone()
            assert clock is not None
            observed = max(now, clock["now"])
            if row is None or self._invitation(row).status(observed) != "pending":
                raise InvitationUnavailable
            connection.execute(
                "INSERT INTO accounts (user_id, username, role, password_hash) "
                "VALUES (%s, %s, 'collaborator', %s)",
                (account.actor.user_id, account.actor.username, account.password_hash),
            )
            connection.execute(
                "UPDATE invitations SET redeemed_at = %s, redeemed_by = %s "
                "WHERE invitation_id = %s",
                (observed, account.actor.user_id, row["invitation_id"]),
            )

    def list_invitations(self, cursor: str | None, limit: int) -> list[Invitation]:
        with transaction(self._dsn) as connection:
            rows = connection.execute(
                "SELECT invitation_id, created_by, created_at, expires_at, "
                "revoked_at, redeemed_at, redeemed_by FROM invitations "
                "WHERE (%s::uuid IS NULL OR invitation_id > %s::uuid) "
                "ORDER BY invitation_id LIMIT %s",
                (cursor, cursor, limit),
            ).fetchall()
            return [self._invitation(row) for row in rows]

    def revoke_invitation(self, invitation_id: str, now: datetime) -> None:
        with transaction(self._dsn) as connection:
            row = connection.execute(
                "SELECT redeemed_at FROM invitations "
                "WHERE invitation_id = %s FOR UPDATE",
                (invitation_id,),
            ).fetchone()
            if row is None:
                raise InvitationUnavailable
            if row["redeemed_at"] is not None:
                raise IdentityConflict
            connection.execute(
                "UPDATE invitations SET revoked_at = COALESCE(revoked_at, %s) "
                "WHERE invitation_id = %s",
                (now, invitation_id),
            )

    def list_members(self, cursor: str | None, limit: int) -> list[Member]:
        with transaction(self._dsn) as connection:
            rows = connection.execute(
                "SELECT user_id, username, active FROM accounts "
                "WHERE role = 'collaborator' AND "
                "(%s::uuid IS NULL OR user_id > %s::uuid) ORDER BY user_id LIMIT %s",
                (cursor, cursor, limit),
            ).fetchall()
            return [
                Member(str(row["user_id"]), row["username"], row["active"])
                for row in rows
            ]

    def disable_member(self, user_id: str) -> None:
        with transaction(self._dsn) as connection:
            row = connection.execute(
                "SELECT role, active FROM accounts WHERE user_id = %s FOR UPDATE",
                (user_id,),
            ).fetchone()
            if row is None:
                raise MemberNotFound
            if row["role"] != "collaborator":
                raise MembershipForbidden
            if row["active"]:
                connection.execute(
                    "UPDATE accounts SET active = false, "
                    "auth_version = auth_version + 1 "
                    "WHERE user_id = %s",
                    (user_id,),
                )
                connection.execute(
                    "DELETE FROM sessions WHERE user_id = %s", (user_id,)
                )

    @staticmethod
    def _invitation(row: DictRow) -> Invitation:
        return Invitation(
            str(row["invitation_id"]),
            str(row["created_by"]),
            row["created_at"],
            row["expires_at"],
            row["revoked_at"],
            row["redeemed_at"],
            str(row["redeemed_by"]) if row["redeemed_by"] else None,
        )
