from uuid import uuid4

from fastapi import Request
from fastapi.responses import JSONResponse


def error_response(status: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(
        status_code=status,
        content={
            "error": {
                "code": code,
                "message": message,
                "details": {},
                "request_id": f"req_{uuid4().hex}",
            }
        },
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
