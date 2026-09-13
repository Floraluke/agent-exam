from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import psycopg
import pytest
from identity.conftest import WRITE_HEADERS, Clock
from jobs.execution.support.fakes import Backend, Evaluator, MemoryArtifacts
from jobs.execution.test_postgres_execution import approved_job
from jobs.recovery.test_recovery_postgres import _CrashBeforeJobFinish, _recover
from jobs.support.postgres_api import login, postgres_api

from eval_platform.application.execute_job import JobExecutor
from eval_platform.delivery.worker.main import WorkerShell
from eval_platform.domain.jobs.execution import JobLeaseConflict, RecoveryRequest

pytestmark = pytest.mark.integration


@pytest.mark.parametrize("corruption", ["summary", "revision", "booleans"])
def test_postgres_mismatched_result_evidence_rolls_back(postgres_sandbox, corruption):
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
            f"postgres-mismatch-{corruption}-source-0001",
            f"postgres-mismatch-{corruption}-approve-0001",
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
            WorkerShell(interrupted, executor, clock).run_once("mismatch-worker")
        before = repository.get(created.job_id)
        assert before.lease_expires_at is not None
        statements = {
            "summary": (
                "UPDATE evaluation_runs SET resolved_summary=FALSE WHERE job_id=%s"
            ),
            "revision": (
                "UPDATE deterministic_results SET harness_revision=%s WHERE run_id=%s"
            ),
            "booleans": (
                "UPDATE deterministic_results SET patch_exists=FALSE,"
                "patch_successfully_applied=TRUE,resolved=TRUE WHERE run_id=%s"
            ),
        }
        with psycopg.connect(postgres_sandbox.dsn) as connection:
            if corruption == "revision":
                connection.execute(
                    statements[corruption], ("0" * 40, created.runs[0].run_id)
                )
            elif corruption == "summary":
                connection.execute(statements[corruption], (created.job_id,))
            else:
                connection.execute(statements[corruption], (created.runs[0].run_id,))
        event_count = len(before.state_events)
        clock.value = before.lease_expires_at

        response = _recover(client, created.job_id)

        assert response.status_code == 503
        assert repository.get(created.job_id).status == "FINALIZING"
        assert len(repository.get(created.job_id).state_events) == event_count


def test_postgres_finalizing_recovery_preserves_persisted_cancel_intent(
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
            "postgres-finalizing-cancel-source-0001",
            "postgres-finalizing-cancel-approve-0001",
        )
        claimed = repository.claim("cancel-finalizing-worker", clock())
        assert claimed is not None
        lease = repository.start_execution(claimed.lease, clock())
        canceled = client.post(
            f"/api/v1/jobs/{created.job_id}/cancel",
            json={"reason": "最终收束前停止"},
            headers={**WRITE_HEADERS, "Idempotency-Key": "pg-finalizing-cancel-0001"},
        )
        assert canceled.status_code == 202
        stopped = repository.start_run(lease, created.runs[0].run_id, clock())
        assert not stopped.started
        finalizing = repository.start_finalizing(stopped.lease, clock())
        clock.value = finalizing.lease_expires_at

        response = _recover(client, created.job_id)
        replay = _recover(client, created.job_id)

        assert response.status_code == 200 and replay.json() == response.json()
        assert response.json()["status"] == "CANCELED"


def test_postgres_recovery_races_the_expired_worker_transaction(postgres_sandbox):
    clock = Clock()
    with postgres_api(postgres_sandbox, recovery_clock=clock) as (
        _client,
        jobs,
        repository,
        owner,
    ):
        created = approved_job(
            jobs,
            repository,
            owner,
            "postgres-worker-race-source-0001",
            "postgres-worker-race-approve-0001",
        )
        claimed = repository.claim("racing-expired-worker", clock())
        assert claimed is not None
        clock.value = claimed.lease.lease_expires_at
        barrier = Barrier(2, timeout=10)

        def recover():
            barrier.wait()
            return type(repository)(postgres_sandbox.dsn).recover(
                RecoveryRequest(created.job_id, owner.user_id, clock())
            )

        def advance():
            barrier.wait()
            with pytest.raises(JobLeaseConflict):
                type(repository)(postgres_sandbox.dsn).start_execution(
                    claimed.lease, clock()
                )

        with ThreadPoolExecutor(max_workers=2) as pool:
            recovered, stale_worker = pool.submit(recover), pool.submit(advance)
            assert recovered.result().status == "FAILED"
            assert stale_worker.result() is None
        assert repository.get(created.job_id).status == "FAILED"
