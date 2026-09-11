"""Application identities are independent of model-provider credentials."""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Literal

SESSION_LIFETIME = timedelta(hours=8)


@dataclass(frozen=True, slots=True)
class AuthenticatedActor:
    user_id: str
    username: str
    role: Literal["owner", "collaborator"]


@dataclass(frozen=True, slots=True)
class Account:
    actor: AuthenticatedActor
    password_hash: str = field(repr=False)
    auth_version: int = 1
    active: bool = True


@dataclass(frozen=True, slots=True)
class Session:
    token_hash: str = field(repr=False)
    user_id: str
    auth_version: int
    expires_at: datetime


@dataclass(frozen=True, slots=True)
class Login:
    actor: AuthenticatedActor
    token: str = field(repr=False)
    expires_at: datetime


class AuthenticationRequired(Exception):
    """Missing, invalid, expired or revoked authentication."""


class IdentityConflict(Exception):
    """Owner already exists or recovery target is not the owner."""


class IdentityUnavailable(Exception):
    """Identity persistence cannot provide a trustworthy result."""
