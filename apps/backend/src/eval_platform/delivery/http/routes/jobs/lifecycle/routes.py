from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Header, Request

from eval_platform.application.identity import IdentityService
from eval_platform.application.job_lifecycle.recovery import JobRecovery
from eval_platform.delivery.http.config import HttpConfig
from eval_platform.delivery.http.routes.jobs.lifecycle.schemas import (
    EmptyLifecycleRequest,
)
from eval_platform.delivery.http.routes.jobs.schemas import JobSummary

RetryKey = Annotated[
    str,
    Header(min_length=8, max_length=128, pattern=r"^[A-Za-z0-9._~-]+$"),
]


def recovery_router(
    identity: IdentityService, recovery: JobRecovery, config: HttpConfig
) -> APIRouter:
    router = APIRouter()

    @router.post("/jobs/{job_id}/recover", response_model=JobSummary)
    def recover(
        job_id: UUID, request: Request, body: EmptyLifecycleRequest
    ) -> JobSummary:
        actor = identity.current_actor(request.cookies.get(config.cookie_name))
        return JobSummary.from_record(recovery.recover(actor, str(job_id)))

    @router.post("/jobs/{job_id}/retry", status_code=202, response_model=JobSummary)
    def retry(
        job_id: UUID,
        request: Request,
        body: EmptyLifecycleRequest,
        idempotency_key: RetryKey,
    ) -> JobSummary:
        actor = identity.current_actor(request.cookies.get(config.cookie_name))
        record = recovery.retry(actor, str(job_id), idempotency_key)
        return JobSummary.from_record(record)

    return router
