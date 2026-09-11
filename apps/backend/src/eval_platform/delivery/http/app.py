from collections.abc import Awaitable, Callable

from fastapi import FastAPI, Request, Response
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException

from eval_platform.adapters.identity.passwords import Argon2Passwords
from eval_platform.adapters.persistence.identity import PostgresIdentityRepository
from eval_platform.adapters.persistence.membership import PostgresMembershipRepository
from eval_platform.application.identity import IdentityService
from eval_platform.application.membership import MembershipService
from eval_platform.delivery.http.config import HttpConfig, database_url
from eval_platform.delivery.http.errors import (
    authentication_error,
    dependency_error,
    error_response,
    framework_http_error,
    membership_error,
    validation_error,
)
from eval_platform.delivery.http.routes.identity import identity_router
from eval_platform.delivery.http.routes.membership import membership_router
from eval_platform.delivery.http.security import LoginLimiter, trusted_write
from eval_platform.domain.identity import (
    AuthenticationRequired,
    IdentityConflict,
    IdentityUnavailable,
)
from eval_platform.domain.membership import (
    InvitationUnavailable,
    MemberNotFound,
    MembershipForbidden,
)


def create_app(
    service: IdentityService,
    config: HttpConfig,
    membership: MembershipService | None = None,
) -> FastAPI:
    app = FastAPI(title="AgentExam", version="0.1.0")
    limiters = {
        "/api/v1/auth/login": LoginLimiter(),
        "/api/v1/invitations/redeem": LoginLimiter(),
    }
    app.add_exception_handler(AuthenticationRequired, authentication_error)
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
    return app


def create_runtime_app() -> FastAPI:
    config = HttpConfig.from_environment()
    dsn = database_url()
    passwords = Argon2Passwords()
    identity = IdentityService(PostgresIdentityRepository(dsn), passwords)
    membership = MembershipService(PostgresMembershipRepository(dsn), passwords)
    return create_app(identity, config, membership)
