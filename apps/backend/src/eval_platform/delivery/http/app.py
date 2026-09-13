from collections.abc import Awaitable, Callable

from fastapi import FastAPI, Request, Response
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException

from eval_platform.adapters.identity.passwords import Argon2Passwords
from eval_platform.adapters.persistence.identity import PostgresIdentityRepository
from eval_platform.adapters.persistence.membership import PostgresMembershipRepository
from eval_platform.application.agent_registry import AgentRegistry
from eval_platform.application.identity import IdentityService
from eval_platform.application.job_lifecycle.cancellation import JobCancellation
from eval_platform.application.job_submission import JobSubmission
from eval_platform.application.membership import MembershipService
from eval_platform.application.owner_approval import OwnerApproval
from eval_platform.application.reporting import JobReporting
from eval_platform.application.task_catalog import TaskCatalog
from eval_platform.delivery.catalog_presets import create_catalog
from eval_platform.delivery.http.config import HttpConfig, database_url
from eval_platform.delivery.http.errors import (
    authentication_error,
    catalog_error,
    dependency_error,
    error_response,
    framework_http_error,
    job_error,
    membership_error,
    validation_error,
)
from eval_platform.delivery.http.routes.artifacts import artifact_router
from eval_platform.delivery.http.routes.catalog import catalog_router
from eval_platform.delivery.http.routes.identity import identity_router
from eval_platform.delivery.http.routes.jobs import jobs_router
from eval_platform.delivery.http.routes.jobs.report_routes import report_router
from eval_platform.delivery.http.routes.membership import membership_router
from eval_platform.delivery.http.security import LoginLimiter, trusted_write
from eval_platform.delivery.jobs import create_jobs
from eval_platform.domain.catalog import CatalogError
from eval_platform.domain.identity import (
    AuthenticationRequired,
    IdentityConflict,
    IdentityUnavailable,
)
from eval_platform.domain.jobs.models import JobError
from eval_platform.domain.membership import (
    InvitationUnavailable,
    MemberNotFound,
    MembershipForbidden,
)


def create_app(
    service: IdentityService,
    config: HttpConfig,
    membership: MembershipService | None = None,
    tasks: TaskCatalog | None = None,
    agents: AgentRegistry | None = None,
    jobs: JobSubmission | None = None,
    approvals: OwnerApproval | None = None,
    reporting: JobReporting | None = None,
    cancellations: JobCancellation | None = None,
) -> FastAPI:
    app = FastAPI(title="AgentExam", version="0.1.0")
    limiters = {
        "/api/v1/auth/login": LoginLimiter(),
        "/api/v1/invitations/redeem": LoginLimiter(),
    }
    app.add_exception_handler(AuthenticationRequired, authentication_error)
    app.add_exception_handler(CatalogError, catalog_error)
    app.add_exception_handler(JobError, job_error)
    app.add_exception_handler(RequestValidationError, validation_error)
    app.add_exception_handler(IdentityUnavailable, dependency_error)
    app.add_exception_handler(HTTPException, framework_http_error)
    for error in (
        MembershipForbidden,
        InvitationUnavailable,
        IdentityConflict,
        MemberNotFound,
    ):
        app.add_exception_handler(error, membership_error)

    @app.middleware("http")
    async def security(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        if request.method not in {"GET", "HEAD", "OPTIONS"}:
            if not trusted_write(request, config):
                return error_response(403, "FORBIDDEN", "请求来源不可信")
        if request.method == "POST" and request.url.path in limiters:
            if not limiters[request.url.path].allow():
                limited = error_response(429, "RATE_LIMITED", "尝试过多，请稍后重试")
                limited.headers["Retry-After"] = "60"
                return limited
        try:
            response = await call_next(request)
        except Exception:
            # Never let an unexpected driver error print secrets in a server traceback.
            return error_response(500, "INTERNAL_ERROR", "平台暂时无法完成请求")
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        return response

    app.include_router(identity_router(service, config))
    if membership is not None:
        app.include_router(membership_router(service, membership, config))
    if tasks is not None:
        app.include_router(catalog_router(service, tasks, config, agents))
    if jobs is not None:
        app.include_router(
            jobs_router(service, jobs, config, approvals, cancellations)
        )
    if reporting is not None:
        app.include_router(report_router(service, reporting, config))
        app.include_router(artifact_router(service, reporting, config))
    return app


def create_runtime_app() -> FastAPI:
    config = HttpConfig.from_environment()
    dsn = database_url()
    passwords = Argon2Passwords()
    identity = IdentityService(PostgresIdentityRepository(dsn), passwords)
    membership = MembershipService(PostgresMembershipRepository(dsn), passwords)
    tasks, agents = create_catalog(dsn)
    jobs, approvals, cancellations = create_jobs(dsn, tasks, agents)
    reporting = JobReporting(jobs.repository, tasks.artifacts)
    return create_app(
        identity,
        config,
        membership,
        tasks,
        agents,
        jobs,
        approvals,
        reporting,
        cancellations,
    )
