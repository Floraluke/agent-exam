from typing import Literal

from pydantic import BaseModel

from eval_platform.domain.jobs.execution import JobReport
from eval_platform.domain.jobs.models import (
    EvaluationRun,
    JobStatus,
    RunStatus,
    run_order_key,
)

BatchOutcome = Literal["resolved", "unresolved", "infrastructure_error", "incomplete"]

_JOB_MESSAGES = {
    "AWAITING_OWNER_APPROVAL": "等待所有者批准，不会启动执行。",
    "QUEUED": "已批准，正在等待单机 Worker。",
    "PREPARING": "正在准备一个 Harbor Job 的冻结输入。",
    "EXECUTING": "Harbor 正按顺序执行，或平台正在核验已返回的 Run。",
    "FINALIZING": "所有 Run 已收束，正在保存批次终态。",
    "COMPLETED": "全部组合已形成可信确定性结果。",
    "COMPLETED_WITH_ERRORS": "批次含部分错误；已完成结果仍然保留。",
    "FAILED": "批次无法形成可汇总结果。",
    "REJECTED": "所有者已拒绝，未启动执行。",
}

_RUN_MESSAGES = {
    "pending": "等待轮到此任务与配置组合。",
    "preparing": "正在准备此组合。",
    "running_agent": "Agent 正在执行此组合。",
    "collecting": "Trial 已结束，等待映射受控结果。",
    "verifying": "固定判卷器正在核验补丁。",
    "completed": "可信结果与证据已经关联。",
    "failed": "此组合未形成可信结果。",
    "canceled": "此组合未执行完成。",
}


class JobRunReportResponse(BaseModel):
    run_id: str
    status: RunStatus
    stage: str | None
    stage_message: str
    task_instance_id: str
    agent_configuration_id: str
    agent_display_name: str
    outcome: BatchOutcome
    resolved: bool | None
    failure_code: str | None
    report_path: str


class JobReportResponse(BaseModel):
    job_id: str
    status: JobStatus
    stage_message: str
    failure_code: str | None
    trial_count: int
    completed_runs: int
    failed_runs: int
    pending_runs: int
    resolved_runs: int
    unresolved_runs: int
    runs: list[JobRunReportResponse]

    @classmethod
    def from_record(cls, report: JobReport) -> "JobReportResponse":
        job = report.job
        runs = sorted(job.runs, key=run_order_key)
        return cls(
            job_id=job.job_id,
            status=job.status,
            stage_message=_JOB_MESSAGES[job.status],
            failure_code=job.failure_code,
            trial_count=job.trial_count,
            completed_runs=sum(run.status == "COMPLETED" for run in runs),
            failed_runs=sum(run.status == "FAILED" for run in runs),
            pending_runs=sum(run.status not in {"COMPLETED", "FAILED"} for run in runs),
            resolved_runs=sum(run.resolved_summary is True for run in runs),
            unresolved_runs=sum(run.resolved_summary is False for run in runs),
            runs=[_run(run) for run in runs],
        )


def _run(run: EvaluationRun) -> JobRunReportResponse:
    stage = run.stage or ("canceled" if run.status == "CANCELED" else "pending")
    if run.status == "COMPLETED":
        outcome: BatchOutcome = "resolved" if run.resolved_summary else "unresolved"
    elif run.status == "FAILED":
        outcome = "infrastructure_error"
    else:
        outcome = "incomplete"
    return JobRunReportResponse(
        run_id=run.run_id,
        status=run.status,
        stage=run.stage,
        stage_message=_RUN_MESSAGES[stage],
        task_instance_id=run.task.instance_id,
        agent_configuration_id=run.agent.agent_configuration_id,
        agent_display_name=run.agent.display_name,
        outcome=outcome,
        resolved=run.resolved_summary,
        failure_code=run.failure_code,
        report_path=f"/api/v1/reports/runs/{run.run_id}",
    )
