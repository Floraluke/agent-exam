from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Header, Query, Request

from eval_platform.application.identity import IdentityService
from eval_platform.application.job_lifecycle.cancellation import JobCancellation
from eval_platform.application.job_submission import JobSubmission
from eval_platform.application.owner_approval import OwnerApproval
from eval_platform.delivery.http.config import HttpConfig
from eval_platform.delivery.http.routes.jobs.cancel_schemas import CancelRequest
from eval_platform.delivery.http.routes.jobs.decision_schemas import (
    OwnerDecisionRequest,
)
from eval_platform.delivery.http.routes.jobs.schemas import (
    JobDetail,
    JobOptionsResponse,
    JobPage,
    JobRequest,
    JobSummary,
)
from eval_platform.delivery.http.schemas import error_responses
from eval_platform.domain.identity import AuthenticatedActor
from eval_platform.domain.jobs.models import JobInputError, JobStatus

IdempotencyKey = Annotated[
    str,
    Header(min_length=8, max_length=128, pattern=r"^[A-Za-z0-9._~-]+$"),
]


def jobs_router(
    identity: IdentityService,
    jobs: JobSubmission,
    config: HttpConfig,
    approvals: OwnerApproval | None = None,
    cancellations: JobCancellation | None = None,
) -> APIRouter:
    router = APIRouter(
        prefix="/api/v1",
        tags=["jobs"],
        responses=error_responses(400, 401, 403, 404, 409, 422, 500, 503),
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
        idempotency_key: IdempotencyKey,
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
        status: JobStatus | None = None,
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

    if approvals is not None:

        def decide(
            job_id: UUID,
            request: Request,
            body: OwnerDecisionRequest,
            idempotency_key: str,
            kind: Literal["approve", "reject"],
        ) -> JobSummary:
            record = approvals.decide(
                actor(request), str(job_id), kind, body.reason, idempotency_key
            )
            return JobSummary.from_record(record)

        @router.post("/jobs/{job_id}/approve", response_model=JobSummary)
        def approve(
            job_id: UUID,
            request: Request,
            body: OwnerDecisionRequest,
            idempotency_key: IdempotencyKey,
        ) -> JobSummary:
            return decide(job_id, request, body, idempotency_key, "approve")

        @router.post("/jobs/{job_id}/reject", response_model=JobSummary)
        def reject(
            job_id: UUID,
            request: Request,
            body: OwnerDecisionRequest,
            idempotency_key: IdempotencyKey,
        ) -> JobSummary:
            return decide(job_id, request, body, idempotency_key, "reject")

    if cancellations is not None:

        @router.post(
            "/jobs/{job_id}/cancel", status_code=202, response_model=JobSummary
        )
        def cancel(
            job_id: UUID,
            request: Request,
            body: CancelRequest,
            idempotency_key: IdempotencyKey,
        ) -> JobSummary:
            outcome = cancellations.cancel(
                actor(request), str(job_id), body.reason, idempotency_key
            )
            summary = JobSummary.from_record(outcome.record)
            return summary.model_copy(update={"status": outcome.accepted_status})

    return router
