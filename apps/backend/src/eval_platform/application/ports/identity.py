from datetime import datetime
from typing import Protocol

from eval_platform.domain.identity import Account, AuthenticatedActor, Session
from eval_platform.domain.membership import Invitation, Member


class Passwords(Protocol):
    def hash(self, password: str) -> str: ...

    def verify(self, encoded: str, password: str) -> bool: ...


class IdentityRepository(Protocol):
    def create_owner(self, account: Account) -> None:
        """Atomically enforce a single owner; conflict cannot partially write."""
        ...

    def find_account(self, username: str) -> Account | None: ...

    def issue_session(self, session: Session) -> bool:
        """Issue only if the account is active and auth_version still matches."""
        ...

    def session_actor(
        self, token_hash: str, now: datetime
    ) -> AuthenticatedActor | None:
        """Require an unexpired session and matching active account version."""
        ...

    def revoke_session(self, token_hash: str) -> None:
        """Idempotently revoke this session, including after expiry."""
        ...

    def recover_owner(self, username: str, password_hash: str) -> AuthenticatedActor:
        """Atomically replace password/version, revoke all sessions; keep owner ID."""
        ...


class MembershipRepository(Protocol):
    def create_invitation(self, invitation: Invitation, token_hash: str) -> None: ...

    def redeem_invitation(
        self, token_hash: str, account: Account, now: datetime
    ) -> None:
        """Atomically consume one valid invitation and create one collaborator."""
        ...

    def list_invitations(self, cursor: str | None, limit: int) -> list[Invitation]: ...

    def revoke_invitation(self, invitation_id: str, now: datetime) -> None: ...

    def list_members(self, cursor: str | None, limit: int) -> list[Member]: ...

    def disable_member(self, user_id: str) -> None:
        """Only collaborators; atomically deactivate and revoke old access."""
        ...
