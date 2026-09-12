from dataclasses import replace
from datetime import UTC, datetime, timedelta

import pytest
from jobs.execution.support.fakes import (
    Backend,
    FailingEvaluator,
    MemoryArtifacts,
)
from jobs.test_postgres import postgres_api

from eval_platform.application.execute_job import JobExecutor
from eval_platform.application.owner_approval import OwnerApproval
from eval_platform.delivery.worker.main import WorkerShell
from eval_platform.domain.jobs.execution import JobLeaseConflict
from eval_platform.domain.jobs.models import run_order_key

pytestmark = pytest.mark.integration


def _approved_batch(jobs, repository, owner, source_key):
    first = jobs.tasks.register(owner, "verified-task")
    second = jobs.tasks.register(owner, "verified-task-2")
    agent = jobs.agents.register(owner, "verified-codex")
    created = jobs.submit(
        owner,
        [first.task_id, second.task_id],
        [agent.configuration.configuration_id],
        "closed_book",
        "demo",
        "default-single-host-v1",
        source_key,
    )
    OwnerApproval(repository).decide(
        owner, created.job_id, "approve", None, source_key + "-approve"
    )
    return created


def test_batch_partial_result_and_events_survive_repository_restart(
    postgres_sandbox,
):
    with postgres_api(postgres_sandbox) as (_client, jobs, repository, owner):
        created = _approved_batch(jobs, repository, owner, "pg-batch-result-0001")
        ordered = sorted(created.runs, key=run_order_key)
        now = datetime(2026, 9, 12, 16, 0, tzinfo=UTC)
        artifacts = MemoryArtifacts()
        executor = JobExecutor(
            repository,
            artifacts,
            Backend(artifacts, b"diff --git a/a b/a\n"),
            FailingEvaluator(artifacts, {ordered[0].run_id}),
            jobs.tasks.source,
            lambda: now,
        )

        assert WorkerShell(repository, executor, lambda: now).run_once(
            "pg-batch-worker"
        )

        restarted = type(repository)(postgres_sandbox.dsn)
        stored = restarted.get(created.job_id)
        first = restarted.get_run_report(ordered[0].run_id)
        second = restarted.get_run_report(ordered[1].run_id)
        assert stored.status == "COMPLETED_WITH_ERRORS"
        assert stored.failure_code == "BATCH_PARTIAL_FAILURE"
        assert first.run.failure_code == "HARNESS_FAILED"
        assert first.deterministic_result is None
        assert second.run.status == "COMPLETED"
        assert second.deterministic_result is not None
        assert [event.to_status for event in stored.state_events][-3:] == [
            "EXECUTING",
            "FINALIZING",
            "COMPLETED_WITH_ERRORS",
        ]
        for run in stored.runs:
            assert [event.sequence for event in run.state_events] == list(
                range(1, len(run.state_events) + 1)
            )


def test_batch_progress_rejects_stale_wrong_and_duplicate_worker_updates(
    postgres_sandbox,
):
    with postgres_api(postgres_sandbox) as (_client, jobs, repository, owner):
        created = _approved_batch(jobs, repository, owner, "pg-batch-lease-0001")
        now = datetime(2026, 9, 12, 16, 30, tzinfo=UTC)
        claimed = repository.claim("pg-batch-worker", now)
        assert claimed is not None
        assert claimed.lease.lease_expires_at == now + timedelta(seconds=7_380)
        lease = repository.start_execution(claimed.lease, now)
        run_id = min(created.runs, key=run_order_key).run_id
        running = repository.start_run(lease, run_id, now)
        collecting = repository.finish_run_execution(running, run_id, now)

        invalid = (
            replace(running, worker_id="wrong-worker"),
            replace(running, job_version=running.job_version - 1),
            running,
            replace(collecting, lease_expires_at=now),
        )
        for stale in invalid:
            with pytest.raises(JobLeaseConflict):
                repository.finish_run_execution(stale, run_id, now)

        restored = type(repository)(postgres_sandbox.dsn).get(created.job_id)
        run = next(item for item in restored.runs if item.run_id == run_id)
        assert run.status == "RUNNING_AGENT" and run.stage == "collecting"
        assert [event.reason_code for event in run.state_events].count(
            "TRIAL_FINISHED"
        ) == 1
