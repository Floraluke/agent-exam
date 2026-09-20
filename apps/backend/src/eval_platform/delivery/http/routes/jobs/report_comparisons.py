"""任务 03 对比报告 HTTP 翻译：把只读矩阵渲染为稳定 DTO。

语义与授权完全复用 `JobReporting.compare`；本文件只做 query 解析与形状翻译。
"""

from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Query, Request
from pydantic import BaseModel

from eval_platform.application.identity import IdentityService
from eval_platform.application.reporting import JobReporting
from eval_platform.application.reporting.matrix import ReportMatrix
from eval_platform.delivery.http.config import HttpConfig
from eval_platform.delivery.http.schemas import error_responses
from eval_platform.domain.jobs.models import JobInputError

ComparisonOutcome = Literal[
    "resolved",
    "unresolved",
    "infrastructure_error",
    "incomplete",
    "missing",
]


class ComparisonColumnResponse(BaseModel):
    job_id: str
    agent_configuration_id: str
    agent_display_name: str


class ComparisonCellResponse(BaseModel):
    outcome: ComparisonOutcome
    resolved: bool | None
    run_id: str | None
    failure_code: str | None
    report_path: str | None


class ComparisonRowResponse(BaseModel):
    task_instance_id: str
    repo: str
    cells: list[ComparisonCellResponse]


class ComparisonTotalsResponse(BaseModel):
    resolved: int
    unresolved: int
    infrastructure_error: int
    incomplete: int
    missing: int
    decided: int
    total: int


class ComparisonResponse(BaseModel):
    columns: list[ComparisonColumnResponse]
    rows: list[ComparisonRowResponse]
    totals: list[ComparisonTotalsResponse]

    @classmethod
    def from_matrix(cls, matrix: ReportMatrix) -> "ComparisonResponse":
        return cls(
            columns=[
                ComparisonColumnResponse(
                    job_id=column.job_id,
                    agent_configuration_id=column.agent_configuration_id,
                    agent_display_name=column.agent_display_name,
                )
                for column in matrix.columns
            ],
            rows=[
                ComparisonRowResponse(
                    task_instance_id=row.task_instance_id,
                    repo=row.repo,
                    cells=[
                        ComparisonCellResponse(
                            outcome=cell.outcome,
                            resolved=cell.resolved,
                            run_id=cell.run_id,
                            failure_code=cell.failure_code,
                            report_path=cell.report_path,
                        )
                        for cell in row.cells
                    ],
                )
                for row in matrix.rows
            ],
            totals=[
                ComparisonTotalsResponse(
                    resolved=total.resolved,
                    unresolved=total.unresolved,
                    infrastructure_error=total.infrastructure_error,
                    incomplete=total.incomplete,
                    missing=total.missing,
                    decided=(
                        total.resolved
                        + total.unresolved
                        + total.infrastructure_error
                        + total.incomplete
                    ),
                    total=(
                        total.resolved
                        + total.unresolved
                        + total.infrastructure_error
                        + total.incomplete
                        + total.missing
                    ),
                )
                for total in matrix.totals
            ],
        )


def _parse_job_ids(raw: str) -> list[str]:
    parts = [part.strip() for part in raw.split(",") if part.strip()]
    if not parts:
        raise JobInputError("EMPTY_COMPARISON_SELECTION")
    job_ids: list[str] = []
    for part in parts:
        try:
            UUID(part)
        except ValueError:
            raise JobInputError("INVALID_REQUEST") from None
        if part not in job_ids:
            job_ids.append(part)
    return job_ids


def comparison_router(
    identity: IdentityService, reporting: JobReporting, config: HttpConfig
) -> APIRouter:
    router = APIRouter(
        prefix="/api/v1/reports",
        tags=["reports"],
        responses=error_responses(401, 404, 500, 503),
    )

    @router.get(
        "/comparisons",
        response_model=ComparisonResponse,
        responses=error_responses(400, 401, 404, 503),
    )
    def comparisons(
        request: Request, job_ids: str = Query(...)
    ) -> ComparisonResponse:
        actor = identity.current_actor(request.cookies.get(config.cookie_name))
        matrix = reporting.compare(actor, _parse_job_ids(job_ids))
        return ComparisonResponse.from_matrix(matrix)

    return router
