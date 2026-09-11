"""External persistence fake. Never imported by production code."""

from dataclasses import replace
from datetime import datetime
from threading import RLock

from eval_platform.domain.identity import (
    Account,
    AuthenticatedActor,
    IdentityConflict,
    Session,
)


class MemoryIdentityRepository:
    def __init__(self) -> None:
        self._accounts: dict[str, Account] = {}
        self._sessions: dict[str, Session] = {}
        self._lock = RLock()

    def create_owner(self, account: Account) -> None:
        with self._lock:
            if any(a.actor.role == "owner" for a in self._accounts.values()):
                raise IdentityConflict
            self._accounts[account.actor.user_id] = account

    def find_account(self, username: str) -> Account | None:
        with self._lock:
            return next(
                (a for a in self._accounts.values() if a.actor.username == username),
                None,
            )

    def issue_session(self, session: Session) -> bool:
        with self._lock:
            account = self._accounts.get(session.user_id)
            if not account or not account.active:
                return False
            if account.auth_version != session.auth_version:
                return False
            self._sessions[session.token_hash] = session
            return True

    def session_actor(
        self, token_hash: str, now: datetime
    ) -> AuthenticatedActor | None:
        with self._lock:
            session = self._sessions.get(token_hash)
            if not session or session.expires_at <= now:
                return None
            account = self._accounts.get(session.user_id)
            if (
                account
                and account.active
                and account.auth_version == session.auth_version
            ):
                return account.actor
            return None

    def revoke_session(self, token_hash: str) -> None:
        with self._lock:
            self._sessions.pop(token_hash, None)

    def recover_owner(self, username: str, password_hash: str) -> AuthenticatedActor:
        with self._lock:
            account = self.find_account(username)
            if not account or account.actor.role != "owner":
                raise IdentityConflict
            user_id = account.actor.user_id
            self._accounts[user_id] = replace(
                account,
                password_hash=password_hash,
                auth_version=account.auth_version + 1,
            )
            self._sessions = {
                key: value
                for key, value in self._sessions.items()
                if value.user_id != user_id
            }
            return account.actor
