from dataclasses import asdict
from uuid import UUID

from fastapi import APIRouter, Query, Request, Response

from eval_platform.application.identity import IdentityService
from eval_platform.application.membership import MembershipService
from eval_platform.delivery.http.config import HttpConfig
from eval_platform.delivery.http.membership_schemas import (
    CreatedInvitation,
    InvitationPage,
    InvitationResponse,
    MemberPage,
    MemberResponse,
    RedeemRequest,
)
from eval_platform.delivery.http.schemas import (
    ActorResponse,
    EmptyRequest,
    error_responses,
)


def membership_router(
    identity: IdentityService, members: MembershipService, config: HttpConfig
) -> APIRouter:
    router = APIRouter(
        prefix="/api/v1",
        tags=["membership"],
        responses=error_responses(400, 401, 403, 404, 409, 410, 422, 429, 500, 503),
    )

    @router.post("/invitations", status_code=201, response_model=CreatedInvitation)
    def invite(request: Request, body: EmptyRequest | None = None) -> CreatedInvitation:
        actor = identity.current_actor(request.cookies.get(config.cookie_name))
        invitation, token = members.invite(actor)
        return CreatedInvitation(
            **asdict(invitation), status="pending", invitation_token=token
        )

    @router.post("/invitations/redeem", status_code=201, response_model=ActorResponse)
    def redeem(body: RedeemRequest) -> ActorResponse:
        return ActorResponse.model_validate(
            members.redeem(
                body.invitation_token.get_secret_value(),
                body.username,
                body.password.get_secret_value(),
            )
        )

    @router.get("/invitations", response_model=InvitationPage)
    def invitations(
        request: Request,
        cursor: UUID | None = None,
        limit: int = Query(20, ge=1, le=100),
    ) -> InvitationPage:
        actor = identity.current_actor(request.cookies.get(config.cookie_name))
        items, next_cursor = members.invitations(
            actor, str(cursor) if cursor else None, limit
        )
        return InvitationPage(
            items=[
                InvitationResponse(**asdict(item.invitation), status=item.status)
                for item in items
            ],
            next_cursor=next_cursor,
        )

    @router.post("/invitations/{invitation_id}/revoke", status_code=204)
    def revoke(
        invitation_id: UUID, request: Request, body: EmptyRequest | None = None
    ) -> Response:
        actor = identity.current_actor(request.cookies.get(config.cookie_name))
        members.revoke(actor, str(invitation_id))
        return Response(status_code=204)

    @router.get("/members", response_model=MemberPage)
    def member_list(
        request: Request,
        cursor: UUID | None = None,
        limit: int = Query(20, ge=1, le=100),
    ) -> MemberPage:
        actor = identity.current_actor(request.cookies.get(config.cookie_name))
        items, next_cursor = members.members(
            actor, str(cursor) if cursor else None, limit
        )
        return MemberPage(
            items=[MemberResponse.model_validate(item) for item in items],
            next_cursor=next_cursor,
        )

    @router.post("/members/{user_id}/disable", status_code=204)
    def disable(
        user_id: UUID, request: Request, body: EmptyRequest | None = None
    ) -> Response:
        actor = identity.current_actor(request.cookies.get(config.cookie_name))
        members.disable(actor, str(user_id))
        return Response(status_code=204)

    return router
