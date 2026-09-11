from datetime import datetime
from typing import Protocol

from eval_platform.domain.identity import Account, AuthenticatedActor, Session


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
