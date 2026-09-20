"""03 报告语义：跨批次对比读取服务的权限、边界与聚合。"""

from dataclasses import replace
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from catalog.conftest import task_bundle
from catalog.memory import FixedSource
from jobs.execution.support.fakes import Backend, Evaluator, MemoryArtifacts
from jobs.execution.support.fixtures import queued_batch, queued_job
from jobs.execution.support.memory import ExecutableMemoryJobs

from eval_platform.application.execute_job import JobExecutor
from eval_platform.application.reporting import JobReporting
from eval_platform.delivery.worker.main import WorkerShell
from eval_platform.domain.agent import AgentConfiguration
from eval_platform.domain.identity import AuthenticatedActor
from eval_platform.domain.jobs.models import (
    AgentSnapshot,
    JobInputError,
    JobNotFound,
)

NOW = datetime(2026, 9, 20, 12, 0, tzinfo=UTC)
PATCH = b"diff --git a/a.py b/a.py\n--- a/a.py\n+++ b/a.py\n@@ -1 +1 @@\n-bug\n+fix\n"


def _second_agent():
    config = AgentConfiguration(
        str(uuid4()),
        "codex",
        "test-version",
        "openai_chatgpt",
        "test-model-b",
        "chatgpt_auth_json",
        "test-profile-b",
        {"reasoning_effort": "medium"},
    )
    return AgentSnapshot(
        config.configuration_id,
        "Synthetic B",
        config.agent_name,
        config.agent_version,
        config.model_provider,
        config.model_name,
        config.authentication_type,
        config.credential_configuration_id,
        "medium",
        config.fingerprint,
    )


def _source():
    source = FixedSource(task_bundle())
    source.bundles["example__repo-2"] = task_bundle("example__repo-2", "example/repo-2")
    return source


def _executed():
    job_a, _ = queued_batch(NOW, size=2)
    job_b, _ = queued_job(NOW)
    job_b = replace(
        job_b,
        job_id=str(uuid4()),
        runs=(replace(job_b.runs[0], agent=_second_agent()),),
    )
    repository = ExecutableMemoryJobs(job_a, job_b)
    artifacts = MemoryArtifacts()
    executor = JobExecutor(
        repository,
        artifacts,
        Backend(artifacts, PATCH),
        Evaluator(artifacts),
        _source(),
        lambda: NOW,
    )
    assert WorkerShell(repository, executor, lambda: NOW).run_once("worker-a")
    assert WorkerShell(repository, executor, lambda: NOW).run_once("worker-b")
    reporting = JobReporting(
        repository, artifacts, lambda scope: scope == "internal_test"
    )
    return job_a, job_b, reporting


def test_compare_aggregates_two_batches_with_missing_semantics():
    job_a, job_b, reporting = _executed()
    owner = AuthenticatedActor("owner-id", "owner", "owner")

    matrix = reporting.compare(owner, [job_a.job_id, job_b.job_id])
    assert [column.agent_display_name for column in matrix.columns] == [
        "Synthetic Codex",
        "Synthetic B",
    ]
    assert len(matrix.rows) == 2
    assert matrix.totals[0].resolved == 2 and matrix.totals[0].missing == 0
    assert matrix.totals[1].resolved == 1 and matrix.totals[1].missing == 1


def test_compare_deduplicates_job_ids():
    job_a, job_b, reporting = _executed()
    owner = AuthenticatedActor("owner-id", "owner", "owner")

    matrix = reporting.compare(owner, [job_a.job_id, job_b.job_id, job_a.job_id])
    assert len(matrix.columns) == 2


def test_compare_rejects_empty_and_oversized_selections():
    _, _, reporting = _executed()
    owner = AuthenticatedActor("owner-id", "owner", "owner")

    with pytest.raises(JobInputError) as empty:
        reporting.compare(owner, [])
    assert empty.value.code == "EMPTY_COMPARISON_SELECTION"
    with pytest.raises(JobInputError) as oversized:
        reporting.compare(owner, [f"job-{index}" for index in range(21)])
    assert oversized.value.code == "COMPARISON_LIMIT_EXCEEDED"


def test_compare_hides_other_members_jobs_from_collaborators():
    job_a, job_b, reporting = _executed()
    collaborator = AuthenticatedActor("other-user", "collab", "collaborator")

    with pytest.raises(JobNotFound):
        reporting.compare(collaborator, [job_a.job_id, job_b.job_id])
