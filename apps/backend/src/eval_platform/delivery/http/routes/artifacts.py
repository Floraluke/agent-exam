"""Authorized public-evidence delivery; MinIO identities never cross this boundary."""

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Query, Request, Response
from pydantic import BaseModel

from eval_platform.application.identity import IdentityService
from eval_platform.application.reporting import JobReporting
from eval_platform.application.reporting.evidence import TrajectoryPage
from eval_platform.delivery.http.config import HttpConfig
from eval_platform.delivery.http.routes.artifact_schemas import (
    ArtifactPageResponse,
)
from eval_platform.delivery.http.schemas import error_responses
from eval_platform.domain.artifacts import ArtifactType


class TrajectoryEventResponse(BaseModel):
    sequence: int
    occurred_at: datetime
    source: str
    type: str
    summary: str
    payload: dict[str, object]


class TrajectoryPageResponse(BaseModel):
    items: list[TrajectoryEventResponse]
    next_after_sequence: int
    complete: bool

    @classmethod
    def from_record(cls, page: TrajectoryPage) -> "TrajectoryPageResponse":
        return cls(
            items=[
                TrajectoryEventResponse.model_validate(event, from_attributes=True)
                for event in page.items
            ],
            next_after_sequence=page.next_after_sequence,
            complete=page.complete,
        )


def artifact_router(
    identity: IdentityService, reporting: JobReporting, config: HttpConfig
) -> APIRouter:
    router = APIRouter(
        prefix="/api/v1",
        tags=["evidence"],
        responses=error_responses(401, 404, 409, 410, 422, 500, 503),
    )

    @router.get("/runs/{run_id}/artifacts", response_model=ArtifactPageResponse)
    def artifacts(
        run_id: UUID,
        request: Request,
        artifact_type: ArtifactType | None = None,
        cursor: UUID | None = None,
        limit: int = Query(100, ge=1, le=100),
    ) -> ArtifactPageResponse:
        actor = identity.current_actor(request.cookies.get(config.cookie_name))
        page = reporting.artifacts(
            actor,
            str(run_id),
            artifact_type,
            None if cursor is None else str(cursor),
            limit,
        )
        return ArtifactPageResponse.from_record(page)

    @router.get("/runs/{run_id}/trajectory", response_model=TrajectoryPageResponse)
    def trajectory(
        run_id: UUID,
        request: Request,
        after_sequence: int = Query(0, ge=0),
        limit: int = Query(100, ge=1, le=500),
        event_type: str | None = Query(None, alias="type", max_length=64),
    ) -> TrajectoryPageResponse:
        actor = identity.current_actor(request.cookies.get(config.cookie_name))
        return TrajectoryPageResponse.from_record(
            reporting.trajectory(actor, str(run_id), after_sequence, limit, event_type)
        )

    @router.get("/artifacts/{artifact_id}/content", response_class=Response)
    def artifact_content(artifact_id: UUID, request: Request) -> Response:
        actor = identity.current_actor(request.cookies.get(config.cookie_name))
        evidence = reporting.content(actor, str(artifact_id))
        return Response(
            evidence.body,
            media_type=evidence.content_type,
            headers={
                "Content-Disposition": f'attachment; filename="{evidence.filename}"'
            },
        )

    return router
