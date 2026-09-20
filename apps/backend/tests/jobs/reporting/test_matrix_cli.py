"""08 工具：render-matrix 本机命令的端到端验证（真实 PostgreSQL）。"""

from datetime import UTC, datetime

import pytest
from jobs.execution.support.fakes import Backend, Evaluator, MemoryArtifacts
from jobs.reporting.test_matrix_rehearsal import _job_seams, _preset_names, _submit
from jobs.support.postgres_api import postgres_api

from eval_platform.application.execute_job import JobExecutor
from eval_platform.application.owner_approval import OwnerApproval
from eval_platform.delivery.jobs import main
from eval_platform.delivery.worker.main import WorkerShell

pytestmark = pytest.mark.integration

NOW = datetime(2026, 9, 20, 10, 0, tzinfo=UTC)
PATCH = b"diff --git a/a.py b/a.py\n--- a/a.py\n+++ b/a.py\n@@ -1 +1 @@\n-bug\n+fix\n"


def _run_batch(
    repository, artifacts, executor_factory, owner, job, approve_key, worker
):
    OwnerApproval(repository).decide(owner, job.job_id, "approve", None, approve_key)
    executor = executor_factory(artifacts)
    assert WorkerShell(repository, executor, lambda: NOW).run_once(worker)


def test_render_matrix_command_prints_comparison_table(
    postgres_sandbox, monkeypatch, capsys
):
    with postgres_api(postgres_sandbox) as (_client, _jobs, _repository, owner):
        jobs, repository = _job_seams(postgres_sandbox)
        tasks = [jobs.tasks.register(owner, name) for name in _preset_names()[:2]]
        agent_a = jobs.agents.register(owner, "verified-codex")
        agent_b = jobs.agents.register(owner, "verified-codex-2")
        job_a = _submit(
            jobs, owner, [item.task_id for item in tasks], agent_a, "cli-a-0001"
        )
        job_b = _submit(jobs, owner, [tasks[0].task_id], agent_b, "cli-b-0001")

        artifacts = MemoryArtifacts()

        def executor_factory(store):
            return JobExecutor(
                repository,
                store,
                Backend(store, PATCH),
                Evaluator(store),
                jobs.tasks.source,
                lambda: NOW,
            )

        _run_batch(
            repository,
            artifacts,
            executor_factory,
            owner,
            job_a,
            "cli-approve-a",
            "worker-cli-a",
        )
        _run_batch(
            repository,
            artifacts,
            executor_factory,
            owner,
            job_b,
            "cli-approve-b",
            "worker-cli-b",
        )

        monkeypatch.setenv("AGENTEXAM_DATABASE_URL", postgres_sandbox.dsn)
        assert main(["render-matrix", job_a.job_id, job_b.job_id]) == 0
        output = capsys.readouterr().out
        assert "| 题目 |" in output
        assert "| 2/2 |" in output
        assert "| 1/2 |" in output
        assert "缺失" in output


def test_render_matrix_fails_closed_without_database_config(monkeypatch, capsys):
    monkeypatch.delenv("AGENTEXAM_DATABASE_URL", raising=False)
    assert main(["render-matrix", "00000000-0000-0000-0000-000000000000"]) == 2
    assert "未确认成功" in capsys.readouterr().err
