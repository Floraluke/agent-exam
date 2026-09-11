from uuid import uuid4

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.datastructures import Headers
from starlette.exceptions import HTTPException

from eval_platform.delivery.http.schemas import ApiError, ErrorDetails


def error_response(status: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(
        status_code=status,
        content=ApiError(
            error=ErrorDetails(
                code=code, message=message, details={}, request_id=f"req_{uuid4().hex}"
            )
        ).model_dump(),
        headers={"Cache-Control": "no-store"},
    )


async def authentication_error(request: Request, exc: Exception) -> JSONResponse:
    return error_response(
        401, "AUTHENTICATION_REQUIRED", "登录无效或已失效，请重新登录"
    )


async def validation_error(request: Request, exc: Exception) -> JSONResponse:
    return error_response(422, "VALIDATION_ERROR", "请求字段或格式不符合要求")


async def dependency_error(request: Request, exc: Exception) -> JSONResponse:
    return error_response(503, "DEPENDENCY_UNAVAILABLE", "身份存储暂不可用，请稍后重试")


async def framework_http_error(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, HTTPException)
    code, message = {
        404: ("RESOURCE_NOT_FOUND", "请求的资源不存在"),
        405: ("METHOD_NOT_ALLOWED", "该资源不支持此请求方法"),
    }.get(exc.status_code, ("HTTP_ERROR", "HTTP 请求未能完成"))
    response = error_response(exc.status_code, code, message)
    headers = Headers(exc.headers or {})
    for name in ("Allow", "WWW-Authenticate", "Retry-After"):
        if name in headers:
            response.headers[name] = headers[name]
    return response
