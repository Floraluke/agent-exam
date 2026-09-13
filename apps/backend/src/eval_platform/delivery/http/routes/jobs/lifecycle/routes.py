from uuid import UUID

from fastapi import APIRouter, Request

from eval_platform.application.identity import IdentityService
from eval_platform.application.job_lifecycle.recovery import JobRecovery
from eval_platform.delivery.http.config import HttpConfig
from eval_platform.delivery.http.routes.jobs.lifecycle.schemas import (
    EmptyLifecycleRequest,
)
from eval_platform.delivery.http.routes.jobs.schemas import JobSummary


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

    return router
