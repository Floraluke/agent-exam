from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Header, Query, Request

from eval_platform.application.identity import IdentityService
from eval_platform.application.job_submission import JobSubmission
from eval_platform.delivery.http.config import HttpConfig
from eval_platform.delivery.http.routes.jobs.schemas import (
    JobDetail,
    JobOptionsResponse,
    JobPage,
    JobRequest,
    JobSummary,
)
from eval_platform.delivery.http.schemas import error_responses
from eval_platform.domain.identity import AuthenticatedActor
from eval_platform.domain.jobs.models import JobInputError


def jobs_router(
    identity: IdentityService, jobs: JobSubmission, config: HttpConfig
) -> APIRouter:
    router = APIRouter(
        prefix="/api/v1",
        tags=["jobs"],
        responses=error_responses(400, 401, 404, 409, 422, 500, 503),
    )

    def actor(request: Request) -> AuthenticatedActor:
        return identity.current_actor(request.cookies.get(config.cookie_name))

    @router.get("/job-options", response_model=JobOptionsResponse)
    def options(request: Request) -> JobOptionsResponse:
        actor(request)
        return JobOptionsResponse.from_policy(jobs.policy)

    @router.post("/jobs", status_code=202, response_model=JobSummary)
    def submit(
        request: Request,
        body: JobRequest,
        idempotency_key: str = Header(
            min_length=8,
            max_length=128,
            pattern=r"^[A-Za-z0-9._~-]+$",
        ),
    ) -> JobSummary:
        record = jobs.submit(
            actor(request),
            [str(value) for value in body.task_ids],
            [str(value) for value in body.agent_configuration_ids],
            body.evaluation_track,
            body.batch_preset,
            body.limit_profile_id,
            idempotency_key,
        )
        return JobSummary.from_record(record)

    @router.get("/jobs", response_model=JobPage)
    def page(
        request: Request,
        cursor: UUID | None = None,
        limit: int = Query(20, ge=1, le=100),
        status: Literal["AWAITING_OWNER_APPROVAL"] | None = None,
        created_by: UUID | None = None,
        evaluation_track: Literal["closed_book"] | None = None,
        result_scope: Literal["official", "internal_test"] | None = None,
    ) -> JobPage:
        parameters = request.query_params
        allowed = {
            "cursor",
            "limit",
            "status",
            "created_by",
            "evaluation_track",
            "result_scope",
        }
        if set(parameters) - allowed or len(parameters.multi_items()) != len(
            parameters
        ):
            raise JobInputError("INVALID_REQUEST")
        filters = {
            key: value
            for key, value in (
                ("status", status),
                ("created_by", str(created_by) if created_by else None),
                ("evaluation_track", evaluation_track),
                ("result_scope", result_scope),
            )
            if value is not None
        }
        records, next_cursor = jobs.list(
            actor(request), filters, str(cursor) if cursor else None, limit
        )
        return JobPage(
            items=[JobSummary.from_record(item) for item in records],
            next_cursor=next_cursor,
        )

    @router.get("/jobs/{job_id}", response_model=JobDetail)
    def detail(job_id: UUID, request: Request) -> JobDetail:
        return JobDetail.from_record(jobs.get(actor(request), str(job_id)))

    return router
