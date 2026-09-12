from uuid import uuid4

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.datastructures import Headers
from starlette.exceptions import HTTPException

from eval_platform.delivery.http.schemas import ApiError, ErrorDetails
from eval_platform.domain.catalog import (
    AgentConfigurationNotFound,
    CatalogConflict,
    CatalogError,
    CatalogForbidden,
    CatalogInvalid,
    CatalogUnavailable,
    TaskNotFound,
)
from eval_platform.domain.identity import IdentityConflict
from eval_platform.domain.jobs.decisions import JobStateConflict, OwnerApprovalRequired
from eval_platform.domain.jobs.models import (
    EvidenceNotFound,
    EvidenceNotReady,
    JobConfigurationDisabled,
    JobError,
    JobIdempotencyConflict,
    JobInputError,
    JobNotFound,
    JobUnavailable,
)
from eval_platform.domain.membership import (
    InvitationUnavailable,
    MemberNotFound,
    MembershipForbidden,
)


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


async def catalog_error(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, CatalogError)
    if isinstance(exc, CatalogUnavailable):
        return error_response(503, "DEPENDENCY_UNAVAILABLE", "目录或快照暂不可用")
    status, code, message = {
        CatalogForbidden: (403, "FORBIDDEN", "只有所有者可以管理目录"),
        CatalogInvalid: (400, "INVALID_REQUEST", "目录选择无效"),
        CatalogConflict: (409, "CATALOG_CONFLICT", "固定身份内容冲突，不能覆盖"),
        TaskNotFound: (404, "TASK_NOT_FOUND", "任务不存在"),
        AgentConfigurationNotFound: (
            404,
            "AGENT_CONFIGURATION_NOT_FOUND",
            "配置不存在",
        ),
    }[type(exc)]
    return error_response(status, code, message)


async def job_error(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, JobError)
    if isinstance(exc, JobInputError):
        return error_response(400, exc.code, "评测批次选择无效")
    status, code, message = {
        OwnerApprovalRequired: (
            403,
            "OWNER_APPROVAL_REQUIRED",
            "只有所有者可以决定评测",
        ),
        JobStateConflict: (409, "JOB_STATE_CONFLICT", "评测批次状态已经改变"),
        JobConfigurationDisabled: (409, "AGENT_CONFIGURATION_DISABLED", "配置已禁用"),
        JobIdempotencyConflict: (409, "IDEMPOTENCY_CONFLICT", "幂等键正文冲突"),
        JobNotFound: (404, "JOB_NOT_FOUND", "评测批次不存在"),
        JobUnavailable: (503, "DEPENDENCY_UNAVAILABLE", "评测批次存储暂不可用"),
        EvidenceNotFound: (404, "ARTIFACT_NOT_FOUND", "证据不存在或无权查看"),
        EvidenceNotReady: (409, "ARTIFACT_NOT_READY", "证据正文尚不可安全发布"),
    }[type(exc)]
    return error_response(status, code, message)


async def membership_error(request: Request, exc: Exception) -> JSONResponse:
    status, code, message = {
        MembershipForbidden: (403, "FORBIDDEN", "只有所有者可以管理协作者"),
        InvitationUnavailable: (
            410,
            "INVITATION_UNAVAILABLE",
            "邀请无效、过期或已被使用",
        ),
        IdentityConflict: (
            409,
            "IDENTITY_CONFLICT",
            "账号或邀请状态冲突，请检查后重试",
        ),
        MemberNotFound: (404, "MEMBER_NOT_FOUND", "成员不存在"),
    }[type(exc)]
    return error_response(status, code, message)


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
