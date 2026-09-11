"""Invitation metadata is public to the owner; its bearer token is not."""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Literal

INVITATION_LIFETIME = timedelta(hours=24)
type InvitationStatus = Literal["pending", "expired", "revoked", "redeemed"]


@dataclass(frozen=True, slots=True)
class Invitation:
    invitation_id: str
    created_by: str
    created_at: datetime
    expires_at: datetime
    revoked_at: datetime | None = None
    redeemed_at: datetime | None = None
    redeemed_by: str | None = None

    def status(self, now: datetime) -> InvitationStatus:
        if self.redeemed_at is not None:
            return "redeemed"
        if self.revoked_at is not None:
            return "revoked"
        return "expired" if self.expires_at <= now else "pending"


class MembershipForbidden(Exception):
    """Only the authenticated owner can administer collaborators."""


class InvitationUnavailable(Exception):
    """Unknown, expired, revoked or already redeemed invitation."""


@dataclass(frozen=True, slots=True)
class InvitationSummary:
    invitation: Invitation
    status: InvitationStatus


@dataclass(frozen=True, slots=True)
class Member:
    user_id: str
    username: str
    active: bool


class MemberNotFound(Exception):
    """The collaborator does not exist."""
