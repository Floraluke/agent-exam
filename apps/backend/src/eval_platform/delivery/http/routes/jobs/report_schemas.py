from dataclasses import asdict
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from eval_platform.delivery.http.routes.artifact_schemas import ArtifactItemResponse
from eval_platform.domain.jobs.execution import RunReport
from eval_platform.domain.jobs.models import RunStatus


class RunIdentityResponse(BaseModel):
    run_id: str
    job_id: str
    status: RunStatus
    stage: str | None
    task_instance_id: str
    agent_configuration_id: str
    backend_job_ref: str | None
    backend_trial_ref: str | None
    failure_code: str | None
    failure_summary: str | None
    started_at: datetime | None
    finished_at: datetime | None
    warnings: list[str]


class DeterministicResultResponse(BaseModel):
    patch_exists: bool
    patch_successfully_applied: bool
    resolved: bool
    tests_status_summary: dict[str, object]
    harness_revision: str
    duration_ms: int | None


class UsageResponse(BaseModel):
    n_input_tokens: int | None
    n_cache_tokens: int | None
    n_output_tokens: int | None
    cost_usd: float | None


class ResourceResponse(BaseModel):
    wall_time_sec: float | None
    cpu_time_sec: float | None
    peak_memory_bytes: int | None


class ProcessMetricsResponse(BaseModel):
    usage: UsageResponse
    resources: ResourceResponse


class RunReportResponse(BaseModel):
    run: RunIdentityResponse
    deterministic_result: DeterministicResultResponse | None
    process_metrics: ProcessMetricsResponse
    judge_analyses: list[object] = Field(default_factory=list)
    human_review: None = None
    quality_tiebreak: None = None
    review_status: Literal["NOT_REQUIRED"] = "NOT_REQUIRED"
    artifact_links: list[ArtifactItemResponse]

    @classmethod
    def from_record(cls, report: RunReport) -> "RunReportResponse":
        run = report.run
        result = report.deterministic_result
        return cls(
            run=RunIdentityResponse(
                run_id=run.run_id,
                job_id=run.job_id,
                status=run.status,
                stage=run.stage,
                task_instance_id=run.task.instance_id,
                agent_configuration_id=run.agent.agent_configuration_id,
                backend_job_ref=run.backend_job_ref,
                backend_trial_ref=run.backend_trial_ref,
                failure_code=run.failure_code,
                failure_summary=run.failure_summary,
                started_at=run.started_at,
                finished_at=run.finished_at,
                warnings=list(report.warnings),
            ),
            deterministic_result=(
                None
                if result is None
                else DeterministicResultResponse(
                    **{
                        key: getattr(result, key)
                        for key in DeterministicResultResponse.model_fields
                    }
                )
            ),
            process_metrics=ProcessMetricsResponse.model_validate(
                asdict(report.process_metrics)
            ),
            artifact_links=[
                ArtifactItemResponse.from_record(item) for item in report.artifacts
            ],
        )
