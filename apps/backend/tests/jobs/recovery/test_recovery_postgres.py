from datetime import timedelta

import pytest
from identity.conftest import WRITE_HEADERS, Clock
from jobs.execution.support.fakes import Backend, Evaluator, MemoryArtifacts
from jobs.execution.test_postgres_execution import approved_job
from jobs.test_postgres import login, postgres_api

from eval_platform.application.execute_job import JobExecutor
from eval_platform.delivery.worker.main import WorkerShell
from eval_platform.domain.jobs.execution import JobLeaseConflict

pytestmark = pytest.mark.integration


def _recover(client, job_id):
    return client.post(f"/api/v1/jobs/{job_id}/recover", json={}, headers=WRITE_HEADERS)


def test_postgres_expired_recovery_is_atomic_and_rejects_the_old_worker(
    postgres_sandbox,
):
    clock = Clock()
    with postgres_api(postgres_sandbox, recovery_clock=clock) as (
        client,
        jobs,
        repository,
        owner,
    ):
        login(client)
        created = approved_job(
            jobs,
            repository,
            owner,
            "postgres-recovery-source-0001",
            "postgres-recovery-approve-0001",
        )
        claimed = repository.claim("expired-postgres-worker", clock())
        assert claimed is not None
        clock.value = claimed.lease.lease_expires_at

        response = _recover(client, created.job_id)
        assert response.status_code == 200
        assert response.json()["failure_code"] == "INFRASTRUCTURE_INTERRUPTED"
        replay = _recover(client, created.job_id)
        assert replay.json() == response.json()
        stored = type(repository)(postgres_sandbox.dsn).get(created.job_id)
        assert stored.status == "FAILED"
        assert stored.runs[0].failure_code == "INFRASTRUCTURE_INTERRUPTED"
        assert (
            sum(
                event.reason_code == "INTERRUPTION_RECOVERED"
                for event in stored.state_events
            )
            == 1
        )
        with pytest.raises(JobLeaseConflict):
            repository.start_execution(
                claimed.lease,
                claimed.lease.lease_expires_at - timedelta(seconds=1),
            )


class _CrashBeforeJobFinish:
    def __init__(self, repository):
        self.repository = repository

    def __getattr__(self, name):
        return getattr(self.repository, name)

    def finish(self, lease, now, failure_code=None):
        raise RuntimeError("synthetic interruption before final Job commit")


def test_postgres_recovery_finishes_from_complete_persisted_run_without_reexecution(
    postgres_sandbox,
):
    clock = Clock()
    with postgres_api(postgres_sandbox, recovery_clock=clock) as (
        client,
        jobs,
        repository,
        owner,
    ):
        login(client)
        created = approved_job(
            jobs,
            repository,
            owner,
            "postgres-evidence-source-0001",
            "postgres-evidence-approve-0001",
        )
        artifacts = MemoryArtifacts()
        interrupted = _CrashBeforeJobFinish(repository)
        executor = JobExecutor(
            interrupted,
            artifacts,
            Backend(artifacts, b"diff --git a/a.py b/a.py\n+x\n"),
            Evaluator(artifacts),
            jobs.tasks.source,
            clock,
        )
        with pytest.raises(RuntimeError, match="synthetic interruption"):
            WorkerShell(interrupted, executor, clock).run_once("finalizing-worker")
        before = repository.get(created.job_id)
        assert before.status == "FINALIZING"
        assert before.runs[0].status == "COMPLETED"
        result = repository.get_run_report(before.runs[0].run_id).deterministic_result
        assert result is not None
        assert before.lease_expires_at is not None
        clock.value = before.lease_expires_at

        recovered = _recover(client, created.job_id)

        assert recovered.status_code == 200
        assert recovered.json()["status"] == "COMPLETED"
        assert recovered.json()["failure_code"] is None
        after = repository.get_run_report(before.runs[0].run_id)
        assert after.deterministic_result == result
