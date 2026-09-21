"""08 预演：单 Job 6 题 × 2 配置 = 12 Run 的冻结矩阵（真实 PostgreSQL）。

这是任务 08"12 Run 矩阵"的形状预演：一次提交覆盖笛卡尔积、每组合恰好一个 Run、
零自动重试，两列各自 6/6 有结论。真实 provider 到位后只需替换执行上游。
"""

import pytest
from jobs.execution.support.fakes import Backend, Evaluator, MemoryArtifacts
from jobs.reporting.test_matrix_rehearsal import (
    NOW,
    PATCH,
    TASK_COUNT,
    _job_seams,
    _preset_names,
)
from jobs.support.postgres_api import postgres_api

from eval_platform.application.execute_job import JobExecutor
from eval_platform.application.owner_approval import OwnerApproval
from eval_platform.application.reporting.matrix import build_matrix
from eval_platform.application.reporting.matrix_markdown import render_matrix_markdown
from eval_platform.delivery.worker.main import WorkerShell

pytestmark = pytest.mark.integration

CONFIGURATION_NAMES = ("verified-codex", "verified-codex-2")
TOTAL_RUNS = TASK_COUNT * len(CONFIGURATION_NAMES)


def test_single_job_twelve_run_matrix_rehearsal_on_real_postgres(postgres_sandbox):
    with postgres_api(postgres_sandbox) as (_client, _jobs, _repository, owner):
        jobs, repository = _job_seams(postgres_sandbox)
        tasks = [jobs.tasks.register(owner, name) for name in _preset_names()]
        agents = [jobs.agents.register(owner, name) for name in CONFIGURATION_NAMES]
        job = jobs.submit(
            owner,
            [item.task_id for item in tasks],
            [agent.configuration.configuration_id for agent in agents],
            "closed_book",
            "continuous",
            "default-single-host-v1",
            "rehearsal-twelve-0001",
        )
        # 笛卡尔积一次成型：12 个组合恰好 12 个 Run，没有第二个尝试。
        assert job.trial_count == TOTAL_RUNS
        assert len(job.runs) == TOTAL_RUNS

        OwnerApproval(repository).decide(
            owner, job.job_id, "approve", None, "rehearsal-twelve-approve"
        )
        artifacts = MemoryArtifacts()
        executor = JobExecutor(
            repository,
            artifacts,
            Backend(artifacts, PATCH),
            Evaluator(artifacts),
            jobs.tasks.source,
            lambda: NOW,
        )
        assert WorkerShell(repository, executor, lambda: NOW).run_once("worker-twelve")

        stored = repository.get(job.job_id)
        assert stored.status == "COMPLETED"
        assert len(stored.runs) == TOTAL_RUNS
        assert {run.status for run in stored.runs} == {"COMPLETED"}
        assert all(run.resolved_summary is True for run in stored.runs)

        matrix = build_matrix([repository.get_job_report(job.job_id)])
        assert [column.agent_display_name for column in matrix.columns] == [
            "Synthetic A",
            "Synthetic B",
        ]
        assert len(matrix.rows) == TASK_COUNT
        for totals in matrix.totals:
            assert totals.resolved == TASK_COUNT
            assert totals.missing == 0
            assert totals.decided == totals.total == TASK_COUNT

        text = render_matrix_markdown(matrix)
        rows = [line for line in text.splitlines() if line.startswith("| example__")]
        assert len(rows) == TASK_COUNT
        assert all(row.count("已解决") == len(CONFIGURATION_NAMES) for row in rows)
        assert text.count("| 6/6 |") == len(CONFIGURATION_NAMES)
