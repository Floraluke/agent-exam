from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, SecretStr

from eval_platform.delivery.http.schemas import LoginRequest
from eval_platform.domain.membership import InvitationStatus


class InvitationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    invitation_id: str
    created_by: str
    created_at: datetime
    expires_at: datetime
    revoked_at: datetime | None
    redeemed_at: datetime | None
    redeemed_by: str | None
    status: InvitationStatus


class CreatedInvitation(InvitationResponse):
    invitation_token: str


class RedeemRequest(LoginRequest):
    invitation_token: SecretStr = Field(min_length=1, max_length=128)
    password: SecretStr = Field(min_length=15, max_length=128)


class InvitationPage(BaseModel):
    items: list[InvitationResponse]
    next_cursor: str | None


class MemberResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    user_id: str
    username: str
    active: bool


class MemberPage(BaseModel):
    items: list[MemberResponse]
    next_cursor: str | None
