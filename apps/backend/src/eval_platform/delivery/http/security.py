import logging
from collections import deque
from collections.abc import Awaitable, Callable
from threading import Lock
from time import monotonic
from uuid import uuid4

from fastapi import FastAPI, Request, Response

from eval_platform.delivery.http.config import HttpConfig
from eval_platform.delivery.http.errors import error_response

LOGGER = logging.getLogger("eval_platform.http")


def trusted_write(request: Request, config: HttpConfig) -> bool:
    return (
        request.headers.get("origin") == config.public_origin
        and request.headers.get("x-agentexam-request") == "1"
    )


class LoginLimiter:
    """A bounded, per-process budget; not a distributed abuse-prevention system."""

    def __init__(self) -> None:
        self._attempts: deque[float] = deque()
        self._lock = Lock()

    def allow(self) -> bool:
        with self._lock:
            now = monotonic()
            while self._attempts and self._attempts[0] <= now - 60:
                self._attempts.popleft()
            if len(self._attempts) >= 10:
                return False
            self._attempts.append(now)
            return True


def install_security(app: FastAPI, config: HttpConfig) -> None:
    limiters = {
        "/api/v1/auth/login": LoginLimiter(),
        "/api/v1/invitations/redeem": LoginLimiter(),
    }

    @app.middleware("http")
    async def security(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        denied = _preflight_response(request, config, limiters)
        if denied is not None:
            return secure_response(denied)
        try:
            response = await call_next(request)
        except Exception as error:
            return _unexpected_failure(request, error)
        return secure_response(response)


def _preflight_response(
    request: Request, config: HttpConfig, limiters: dict[str, LoginLimiter]
) -> Response | None:
    if request.method not in {"GET", "HEAD", "OPTIONS"} and not trusted_write(
        request, config
    ):
        return error_response(403, "FORBIDDEN", "请求来源不可信")
    limiter = limiters.get(request.url.path) if request.method == "POST" else None
    if limiter is None or limiter.allow():
        return None
    response = error_response(429, "RATE_LIMITED", "尝试过多，请稍后重试")
    response.headers["Retry-After"] = "60"
    return response


def _unexpected_failure(request: Request, error: Exception) -> Response:
    request_id = f"req_{uuid4().hex}"
    LOGGER.error(
        "unexpected request failure",
        extra={
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "exception_type": type(error).__name__,
        },
    )
    return secure_response(
        error_response(
            500,
            "INTERNAL_ERROR",
            "平台暂时无法完成请求",
            request_id=request_id,
        )
    )


def secure_response(response: Response) -> Response:
    response.headers["Cache-Control"] = "no-store"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    return response
