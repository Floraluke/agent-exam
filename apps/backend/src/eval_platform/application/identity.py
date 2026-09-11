import hashlib
import re
import secrets
from collections.abc import Callable
from datetime import UTC, datetime
from uuid import uuid4

from eval_platform.application.ports.identity import IdentityRepository, Passwords
from eval_platform.domain.identity import (
    SESSION_LIFETIME,
    Account,
    AuthenticatedActor,
    AuthenticationRequired,
    Login,
    Session,
)


class IdentityService:
    def __init__(
        self,
        repository: IdentityRepository,
        passwords: Passwords,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self._repository = repository
        self._passwords = passwords
        self._clock = clock
        self._dummy_hash = passwords.hash(secrets.token_urlsafe(32))

    def bootstrap_owner(self, username: str, password: str) -> AuthenticatedActor:
        if not re.fullmatch(r"[a-z0-9][a-z0-9_.-]{2,63}", username):
            raise ValueError("账号须为 3–64 位小写字母、数字、下划线、点或短横线")
        if not 15 <= len(password) <= 128:
            raise ValueError("密码须为 15–128 个字符")
        actor = AuthenticatedActor(str(uuid4()), username, "owner")
        self._repository.create_owner(Account(actor, self._passwords.hash(password)))
        return actor

    def login(self, username: str, password: str) -> Login:
        account = self._repository.find_account(username)
        encoded = account.password_hash if account else self._dummy_hash
        valid = self._passwords.verify(encoded, password)
        if not valid or account is None or not account.active:
            raise AuthenticationRequired
        token = secrets.token_urlsafe(32)
        expires_at = self._clock() + SESSION_LIFETIME
        session = Session(
            self._digest(token), account.actor.user_id, account.auth_version, expires_at
        )
        if not self._repository.issue_session(session):
            raise AuthenticationRequired
        return Login(account.actor, token, expires_at)

    def current_actor(self, token: str | None) -> AuthenticatedActor:
        if not token or len(token) > 128:
            raise AuthenticationRequired
        actor = self._repository.session_actor(self._digest(token), self._clock())
        if actor is None:
            raise AuthenticationRequired
        return actor

    @staticmethod
    def _digest(token: str) -> str:
        return hashlib.sha256(token.encode()).hexdigest()

    def logout(self, token: str | None) -> None:
        if token and len(token) <= 128:
            self._repository.revoke_session(self._digest(token))

    def recover_owner(self, username: str, password: str) -> AuthenticatedActor:
        if not 15 <= len(password) <= 128:
            raise ValueError("密码须为 15–128 个字符")
        return self._repository.recover_owner(username, self._passwords.hash(password))
