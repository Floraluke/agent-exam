"""08 演练：真实 PostgreSQL 上跑"两批 Job → 批次报告 → 对比矩阵"。

形态对齐任务 08：配置 A 跑满 6 题；配置 B 只跑 5 题且其中 1 题判卷失败。
矩阵预期：A 列 6/6 有结论；B 列 5 格有结论（4 已解决 + 1 基础设施错误）+ 1 格"缺失"。
"""

from datetime import UTC, datetime

import pytest
from catalog.conftest import task_bundle
from catalog.memory import FixedSource
from catalog.memory import MemoryArtifacts as CatalogArtifacts
from jobs.execution.support.fakes import (
    Backend,
    Evaluator,
    FailingEvaluator,
    MemoryArtifacts,
)
from jobs.support.postgres_api import postgres_api

from eval_platform.adapters.persistence.catalog.agents import PostgresAgentRepository
from eval_platform.adapters.persistence.catalog.tasks import PostgresTaskRepository
from eval_platform.adapters.persistence.jobs.repository import PostgresJobRepository
from eval_platform.application.agent_registry import AgentRegistry
from eval_platform.application.execute_job import JobExecutor
from eval_platform.application.job_submission import JobSubmission
from eval_platform.application.owner_approval import OwnerApproval
from eval_platform.application.reporting.matrix import build_matrix
from eval_platform.application.reporting.matrix_markdown import render_matrix_markdown
from eval_platform.application.task_catalog import TaskCatalog
from eval_platform.delivery.job_presets import submission_policy
from eval_platform.delivery.worker.main import WorkerShell
from eval_platform.domain.agent import AgentConfiguration

pytestmark = pytest.mark.integration

NOW = datetime(2026, 9, 20, 9, 0, tzinfo=UTC)
PATCH = b"diff --git a/a.py b/a.py\n--- a/a.py\n+++ b/a.py\n@@ -1 +1 @@\n-bug\n+fix\n"
TASK_COUNT = 6
SECOND_BATCH_TASKS = 5


def _source():
    source = FixedSource(task_bundle())
    for index in range(2, TASK_COUNT + 1):
        instance = f"example__repo-{index}"
        source.bundles[instance] = task_bundle(instance, f"example/repo-{index}")
    return source


def _configuration(model: str) -> AgentConfiguration:
    return AgentConfiguration(
        "preset",
        "codex",
        "test-version",
        "openai_chatgpt",
        model,
        "chatgpt_auth_json",
        "test-private-reference",
        {"reasoning_effort": "medium"},
    )


def _preset_names(count: int = TASK_COUNT) -> list[str]:
    return ["verified-task"] + [
        f"verified-task-{index}" for index in range(2, count + 1)
    ]


def _job_seams(sandbox):
    tasks = TaskCatalog(
        PostgresTaskRepository(sandbox.dsn),
        CatalogArtifacts(),
        _source(),
        {
            name: f"example__repo-{position}"
            for position, name in enumerate(_preset_names(), start=1)
        },
    )
    agents = AgentRegistry(
        PostgresAgentRepository(sandbox.dsn),
        {
            "verified-codex": ("Synthetic A", _configuration("test-model-a")),
            "verified-codex-2": ("Synthetic B", _configuration("test-model-b")),
        },
    )
    repository = PostgresJobRepository(sandbox.dsn)
    jobs = JobSubmission(tasks, agents, repository, submission_policy("internal_test"))
    return jobs, repository


def _submit(jobs, owner, task_ids, agent, key):
    return jobs.submit(
        owner,
        task_ids,
        [agent.configuration.configuration_id],
        "closed_book",
        "continuous",
        "default-single-host-v1",
        key,
    )


def test_two_batch_matrix_rehearsal_on_real_postgres(postgres_sandbox):
    with postgres_api(postgres_sandbox) as (_client, _jobs, _repository, owner):
        jobs, repository = _job_seams(postgres_sandbox)
        tasks = [jobs.tasks.register(owner, name) for name in _preset_names()]
        agent_a = jobs.agents.register(owner, "verified-codex")
        agent_b = jobs.agents.register(owner, "verified-codex-2")
        job_a = _submit(
            jobs,
            owner,
            [item.task_id for item in tasks],
            agent_a,
            "rehearsal-batch-a-0001",
        )
        job_b = _submit(
            jobs,
            owner,
            [item.task_id for item in tasks[:SECOND_BATCH_TASKS]],
            agent_b,
            "rehearsal-batch-b-0001",
        )
        assert job_a.trial_count == TASK_COUNT
        assert job_b.trial_count == SECOND_BATCH_TASKS

        approvals = OwnerApproval(repository)
        artifacts = MemoryArtifacts()

        approvals.decide(owner, job_a.job_id, "approve", None, "rehearsal-approve-a")
        executor_a = JobExecutor(
            repository,
            artifacts,
            Backend(artifacts, PATCH),
            Evaluator(artifacts),
            jobs.tasks.source,
            lambda: NOW,
        )
        assert WorkerShell(repository, executor_a, lambda: NOW).run_once("worker-a")

        approvals.decide(owner, job_b.job_id, "approve", None, "rehearsal-approve-b")
        executor_b = JobExecutor(
            repository,
            artifacts,
            Backend(artifacts, PATCH),
            FailingEvaluator(artifacts, {job_b.runs[0].run_id}),
            jobs.tasks.source,
            lambda: NOW,
        )
        assert WorkerShell(repository, executor_b, lambda: NOW).run_once("worker-b")

        assert repository.get(job_a.job_id).status == "COMPLETED"
        assert repository.get(job_b.job_id).status == "COMPLETED_WITH_ERRORS"

        matrix = build_matrix(
            [
                repository.get_job_report(job_a.job_id),
                repository.get_job_report(job_b.job_id),
            ]
        )
        assert [column.agent_display_name for column in matrix.columns] == [
            "Synthetic A",
            "Synthetic B",
        ]
        assert len(matrix.rows) == TASK_COUNT
        assert matrix.totals[0].resolved == TASK_COUNT
        assert matrix.totals[0].missing == 0
        assert matrix.totals[1].resolved == SECOND_BATCH_TASKS - 1
        assert matrix.totals[1].infrastructure_error == 1
        assert matrix.totals[1].missing == 1

        text = render_matrix_markdown(matrix)
        assert "| 6/6 |" in text
        assert "| 5/6 |" in text
