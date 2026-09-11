"""Synthetic external storage shared with the existing identity fake."""

from dataclasses import replace

from identity.memory import MemoryIdentityRepository

from eval_platform.domain.identity import IdentityConflict
from eval_platform.domain.membership import (
    InvitationUnavailable,
    Member,
    MemberNotFound,
    MembershipForbidden,
)


class MemoryMembershipRepository(MemoryIdentityRepository):
    def __init__(self):
        super().__init__()
        self._invitations = {}

    def create_invitation(self, invitation, token_hash):
        with self._lock:
            self._invitations[token_hash] = invitation

    def redeem_invitation(self, token_hash, account, now):
        with self._lock:
            invitation = self._invitations.get(token_hash)
            if invitation is None or invitation.status(now) != "pending":
                raise InvitationUnavailable
            if self.find_account(account.actor.username):
                raise IdentityConflict
            self._accounts[account.actor.user_id] = account
            self._invitations[token_hash] = replace(
                invitation, redeemed_at=now, redeemed_by=account.actor.user_id
            )

    def list_invitations(self, cursor, limit):
        with self._lock:
            values = sorted(
                self._invitations.values(), key=lambda item: item.invitation_id
            )
            return [
                item for item in values if cursor is None or item.invitation_id > cursor
            ][:limit]

    def revoke_invitation(self, invitation_id, now):
        with self._lock:
            for token_hash, invitation in self._invitations.items():
                if invitation.invitation_id == invitation_id:
                    if invitation.redeemed_at:
                        raise IdentityConflict
                    self._invitations[token_hash] = replace(
                        invitation, revoked_at=invitation.revoked_at or now
                    )
                    return
            raise InvitationUnavailable

    def list_members(self, cursor, limit):
        with self._lock:
            values = sorted(
                self._accounts.values(), key=lambda item: item.actor.user_id
            )
            return [
                Member(item.actor.user_id, item.actor.username, item.active)
                for item in values
                if item.actor.role == "collaborator"
                and (cursor is None or item.actor.user_id > cursor)
            ][:limit]

    def disable_member(self, user_id):
        with self._lock:
            account = self._accounts.get(user_id)
            if account is None:
                raise MemberNotFound
            if account.actor.role != "collaborator":
                raise MembershipForbidden
            if account.active:
                self._accounts[user_id] = replace(
                    account, active=False, auth_version=account.auth_version + 1
                )
                self._sessions = {
                    key: value
                    for key, value in self._sessions.items()
                    if value.user_id != user_id
                }
