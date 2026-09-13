from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from threading import Barrier

import psycopg
import pytest
from identity.conftest import WRITE_HEADERS, Clock
from jobs.execution.support.fakes import Backend, Evaluator, MemoryArtifacts
from jobs.execution.test_postgres_execution import approved_job
from jobs.test_postgres import login, postgres_api

from eval_platform.application.execute_job import JobExecutor
from eval_platform.delivery.worker.main import WorkerShell
from eval_platform.domain.jobs.execution import JobLeaseConflict, RecoveryRequest

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

        barrier = Barrier(2, timeout=10)
        request = RecoveryRequest(created.job_id, owner.user_id, clock())

        def recover_once(_index):
            barrier.wait()
            return type(repository)(postgres_sandbox.dsn).recover(request)

        with ThreadPoolExecutor(max_workers=2) as pool:
            outcomes = tuple(pool.map(recover_once, range(2)))
        assert {outcome.status for outcome in outcomes} == {"FAILED"}
        replay = _recover(client, created.job_id)
        assert replay.status_code == 200
        assert replay.json()["failure_code"] == "INFRASTRUCTURE_INTERRUPTED"
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


def test_postgres_corrupt_result_evidence_rolls_back_recovery(postgres_sandbox):
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
            "postgres-corrupt-source-0001",
            "postgres-corrupt-approve-0001",
        )
        artifacts = MemoryArtifacts()
        executor = JobExecutor(
            repository,
            artifacts,
            Backend(artifacts, b"diff --git a/a.py b/a.py\n+x\n"),
            Evaluator(artifacts),
            jobs.tasks.source,
            clock,
        )
        assert WorkerShell(repository, executor, clock).run_once("corrupt-worker")
        with psycopg.connect(postgres_sandbox.dsn) as connection:
            connection.execute(
                "UPDATE evaluation_jobs SET status='FINALIZING',finished_at=NULL,"
                "lease_expires_at=%s,row_version=row_version+1 WHERE job_id=%s",
                (clock(), created.job_id),
            )
            connection.execute(
                "DELETE FROM job_state_events WHERE job_id=%s "
                "AND to_status='COMPLETED'",
                (created.job_id,),
            )
            connection.execute(
                "DELETE FROM deterministic_results WHERE run_id=%s",
                (created.runs[0].run_id,),
            )
        before = repository.get(created.job_id)
        event_count = len(before.state_events)

        response = _recover(client, created.job_id)

        assert response.status_code == 503
        assert response.json()["error"]["code"] == "DEPENDENCY_UNAVAILABLE"
        after = repository.get(created.job_id)
        assert after.status == "FINALIZING"
        assert after.runs[0].status == "COMPLETED"
        assert len(after.state_events) == event_count
