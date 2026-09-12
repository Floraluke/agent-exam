from uuid import UUID

from fastapi import APIRouter, Request

from eval_platform.application.identity import IdentityService
from eval_platform.application.job_submission import JobReporting
from eval_platform.delivery.http.config import HttpConfig
from eval_platform.delivery.http.routes.jobs.report_schemas import (
    JobReportResponse,
    RunReportResponse,
)
from eval_platform.delivery.http.schemas import error_responses


def report_router(
    identity: IdentityService, reporting: JobReporting, config: HttpConfig
) -> APIRouter:
    router = APIRouter(
        prefix="/api/v1/reports",
        tags=["reports"],
        responses=error_responses(401, 404, 500, 503),
    )

    @router.get("/runs/{run_id}", response_model=RunReportResponse)
    def run_report(run_id: UUID, request: Request) -> RunReportResponse:
        actor = identity.current_actor(request.cookies.get(config.cookie_name))
        return RunReportResponse.from_record(reporting.run(actor, str(run_id)))

    @router.get("/jobs/{job_id}", response_model=JobReportResponse)
    def job_report(job_id: UUID, request: Request) -> JobReportResponse:
        actor = identity.current_actor(request.cookies.get(config.cookie_name))
        return JobReportResponse.from_record(reporting.job(actor, str(job_id)))

    return router
