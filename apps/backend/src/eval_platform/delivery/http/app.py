from collections.abc import Awaitable, Callable

from fastapi import FastAPI, Request, Response
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException

from eval_platform.adapters.identity.passwords import Argon2Passwords
from eval_platform.adapters.persistence.identity import PostgresIdentityRepository
from eval_platform.application.identity import IdentityService
from eval_platform.delivery.http.config import HttpConfig, database_url
from eval_platform.delivery.http.errors import (
    authentication_error,
    dependency_error,
    error_response,
    framework_http_error,
    validation_error,
)
from eval_platform.delivery.http.routes.identity import identity_router
from eval_platform.delivery.http.security import LoginLimiter, trusted_write
from eval_platform.domain.identity import AuthenticationRequired, IdentityUnavailable


def create_app(service: IdentityService, config: HttpConfig) -> FastAPI:
    app = FastAPI(title="AgentExam", version="0.1.0")
    limiter = LoginLimiter()
    app.add_exception_handler(AuthenticationRequired, authentication_error)
    app.add_exception_handler(RequestValidationError, validation_error)
    app.add_exception_handler(IdentityUnavailable, dependency_error)
    app.add_exception_handler(HTTPException, framework_http_error)

    @app.middleware("http")
    async def security(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        if request.method not in {"GET", "HEAD", "OPTIONS"}:
            if not trusted_write(request, config):
                return error_response(403, "FORBIDDEN", "请求来源不可信")
        if request.method == "POST" and request.url.path == "/api/v1/auth/login":
            if not limiter.allow():
                limited = error_response(
                    429, "RATE_LIMITED", "登录尝试过多，请稍后重试"
                )
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
    return app


def create_runtime_app() -> FastAPI:
    config = HttpConfig.from_environment()
    repository = PostgresIdentityRepository(database_url())
    return create_app(IdentityService(repository, Argon2Passwords()), config)
