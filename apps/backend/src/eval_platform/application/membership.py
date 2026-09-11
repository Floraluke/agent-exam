import hashlib
import re
import secrets
from collections.abc import Callable
from datetime import UTC, datetime
from uuid import uuid4

from eval_platform.application.ports.identity import MembershipRepository, Passwords
from eval_platform.domain.identity import Account, AuthenticatedActor
from eval_platform.domain.membership import (
    INVITATION_LIFETIME,
    Invitation,
    InvitationSummary,
    Member,
    MembershipForbidden,
)


class MembershipService:
    def __init__(
        self,
        repository: MembershipRepository,
        passwords: Passwords,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self._repository = repository
        self._passwords = passwords
        self._clock = clock

    @staticmethod
    def require_owner(actor: AuthenticatedActor) -> None:
        if actor.role != "owner":
            raise MembershipForbidden

    def invite(self, actor: AuthenticatedActor) -> tuple[Invitation, str]:
        self.require_owner(actor)
        token = secrets.token_urlsafe(32)
        now = self._clock()
        invitation = Invitation(
            str(uuid4()), actor.user_id, now, now + INVITATION_LIFETIME
        )
        self._repository.create_invitation(invitation, self._digest(token))
        return invitation, token

    def redeem(self, token: str, username: str, password: str) -> AuthenticatedActor:
        if not re.fullmatch(r"[a-z0-9][a-z0-9_.-]{2,63}", username):
            raise ValueError("Invalid username")
        if not 15 <= len(password) <= 128 or not 1 <= len(token) <= 128:
            raise ValueError("Invalid invitation input")
        actor = AuthenticatedActor(str(uuid4()), username, "collaborator")
        account = Account(actor, self._passwords.hash(password))
        self._repository.redeem_invitation(self._digest(token), account, self._clock())
        return actor

    @staticmethod
    def _digest(token: str) -> str:
        return hashlib.sha256(token.encode()).hexdigest()

    def invitations(
        self, actor: AuthenticatedActor, cursor: str | None, limit: int
    ) -> tuple[list[InvitationSummary], str | None]:
        self.require_owner(actor)
        items = self._repository.list_invitations(cursor, limit + 1)
        next_cursor = items[limit - 1].invitation_id if len(items) > limit else None
        now = self._clock()
        return [
            InvitationSummary(item, item.status(now)) for item in items[:limit]
        ], next_cursor

    def revoke(self, actor: AuthenticatedActor, invitation_id: str) -> None:
        self.require_owner(actor)
        self._repository.revoke_invitation(invitation_id, self._clock())

    def members(
        self, actor: AuthenticatedActor, cursor: str | None, limit: int
    ) -> tuple[list[Member], str | None]:
        self.require_owner(actor)
        items = self._repository.list_members(cursor, limit + 1)
        next_cursor = items[limit - 1].user_id if len(items) > limit else None
        return items[:limit], next_cursor

    def disable(self, actor: AuthenticatedActor, user_id: str) -> None:
        self.require_owner(actor)
        if actor.user_id == user_id:
            raise MembershipForbidden
        self._repository.disable_member(user_id)
