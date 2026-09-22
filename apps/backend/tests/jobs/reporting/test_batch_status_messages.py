"""批次报告的状态文案必须覆盖全部 Job 状态与执行侧写过的 stage。

缺一项就会在 `_JOB_MESSAGES[job.status]` / `_RUN_MESSAGES[stage]` 抛 KeyError，
表现为报告端点 500 INTERNAL_ERROR——2026-09-22 取消态批次的实际故障即此。
执行侧 stage 的写入点：`adapters/persistence/jobs/execution/*.py`（preparing /
running_agent / collecting / verifying / completed / failed / canceled）。
"""

from typing import get_args

from eval_platform.delivery.http.routes.jobs.batch_schemas import (
    _JOB_MESSAGES,
    _RUN_MESSAGES,
)
from eval_platform.domain.jobs.models import JobStatus

EXECUTION_STAGES = {
    "pending",
    "preparing",
    "running_agent",
    "collecting",
    "verifying",
    "completed",
    "failed",
    "canceled",
}


def test_every_job_status_has_a_message():
    assert set(get_args(JobStatus)) - set(_JOB_MESSAGES) == set()


def test_every_execution_stage_has_a_message():
    assert EXECUTION_STAGES - set(_RUN_MESSAGES) == set()


def test_no_orphan_stage_message():
    assert set(_RUN_MESSAGES) - EXECUTION_STAGES == set()
