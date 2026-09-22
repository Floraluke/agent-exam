from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Header, Query, Request

from eval_platform.application.identity import IdentityService
from eval_platform.application.job_lifecycle.cancellation import JobCancellation
from eval_platform.application.job_lifecycle.recovery import JobRecovery
from eval_platform.application.job_submission import JobSubmission
from eval_platform.application.owner_approval import OwnerApproval
from eval_platform.delivery.http.config import HttpConfig
from eval_platform.delivery.http.schemas import error_responses
from eval_platform.domain.identity import AuthenticatedActor
from eval_platform.domain.jobs.models import JobInputError, JobStatus

from .batch_schemas import JobOptionsResponse
from .cancel_schemas import CancelRequest
from .decision_schemas import OwnerDecisionRequest
from .lifecycle.routes import recovery_router
from .schemas import JobDetail, JobPage, JobRequest, JobSummary

IdempotencyKey = Annotated[
    str,
    Header(min_length=8, max_length=128, pattern=r"^[A-Za-z0-9._~-]+$"),
]
_LISTING_PARAMETERS = frozenset(
    {"cursor", "limit", "status", "created_by", "evaluation_track", "result_scope"}
)


def jobs_router(
    identity: IdentityService,
    jobs: JobSubmission,
    config: HttpConfig,
    approvals: OwnerApproval | None = None,
    cancellations: JobCancellation | None = None,
    recovery: JobRecovery | None = None,
) -> APIRouter:
    router = APIRouter(
        prefix="/api/v1",
        tags=["jobs"],
        responses=error_responses(400, 401, 403, 404, 409, 422, 500, 503),
    )
    _register_core_routes(router, identity, jobs, config)
    _register_listing_route(router, identity, jobs, config)
    if approvals is not None:
        _register_approval_routes(router, identity, approvals, config)
    if cancellations is not None:
        _register_cancellation_route(router, identity, cancellations, config)
    if recovery is not None:
        router.include_router(recovery_router(identity, recovery, config))
    return router


def _actor(
    identity: IdentityService, config: HttpConfig, request: Request
) -> AuthenticatedActor:
    return identity.current_actor(request.cookies.get(config.cookie_name))


def _register_core_routes(
    router: APIRouter,
    identity: IdentityService,
    jobs: JobSubmission,
    config: HttpConfig,
) -> None:
    @router.get("/job-options", response_model=JobOptionsResponse)
    def options(request: Request) -> JobOptionsResponse:
        _actor(identity, config, request)
        return JobOptionsResponse.from_policy(jobs.policy)

    @router.post("/jobs", status_code=202, response_model=JobSummary)
    def submit(
        request: Request,
        body: JobRequest,
        idempotency_key: IdempotencyKey,
    ) -> JobSummary:
        record = jobs.submit(
            _actor(identity, config, request),
            [str(value) for value in body.task_ids],
            [str(value) for value in body.agent_configuration_ids],
            body.evaluation_track,
            body.batch_preset,
            body.limit_profile_id,
            idempotency_key,
        )
        return JobSummary.from_record(record)

    @router.get("/jobs/{job_id}", response_model=JobDetail)
    def detail(job_id: UUID, request: Request) -> JobDetail:
        actor = _actor(identity, config, request)
        return JobDetail.from_record(jobs.get(actor, str(job_id)))


def _register_listing_route(
    router: APIRouter,
    identity: IdentityService,
    jobs: JobSubmission,
    config: HttpConfig,
) -> None:
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
        if set(parameters) - _LISTING_PARAMETERS or len(
            parameters.multi_items()
        ) != len(parameters):
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
            _actor(identity, config, request),
            filters,
            str(cursor) if cursor else None,
            limit,
        )
        return JobPage(
            items=[JobSummary.from_record(item) for item in records],
            next_cursor=next_cursor,
        )


def _register_approval_routes(
    router: APIRouter,
    identity: IdentityService,
    approvals: OwnerApproval,
    config: HttpConfig,
) -> None:
    def decide(
        job_id: UUID,
        request: Request,
        body: OwnerDecisionRequest,
        idempotency_key: str,
        kind: Literal["approve", "reject"],
    ) -> JobSummary:
        record = approvals.decide(
            _actor(identity, config, request),
            str(job_id),
            kind,
            body.reason,
            idempotency_key,
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


def _register_cancellation_route(
    router: APIRouter,
    identity: IdentityService,
    cancellations: JobCancellation,
    config: HttpConfig,
) -> None:
    @router.post("/jobs/{job_id}/cancel", status_code=202, response_model=JobSummary)
    def cancel(
        job_id: UUID,
        request: Request,
        body: CancelRequest,
        idempotency_key: IdempotencyKey,
    ) -> JobSummary:
        outcome = cancellations.cancel(
            _actor(identity, config, request),
            str(job_id),
            body.reason,
            idempotency_key,
        )
        summary = JobSummary.from_record(outcome.record)
        return summary.model_copy(update={"status": outcome.accepted_status})
