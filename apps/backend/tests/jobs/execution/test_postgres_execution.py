from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import UTC, datetime
from threading import Barrier

import psycopg
import pytest

from eval_platform.application.execute_job import JobExecutor
from eval_platform.application.owner_approval import OwnerApproval
from eval_platform.delivery.worker.main import WorkerShell
from eval_platform.domain.jobs.execution import JobLeaseConflict
from jobs.execution.support.fakes import Backend, Evaluator, MemoryArtifacts
from jobs.test_postgres import postgres_api

pytestmark = pytest.mark.integration


def test_postgres_claim_is_exclusive_versioned_and_restart_safe(postgres_sandbox):
    with postgres_api(postgres_sandbox) as (_client, jobs, repository, owner):
        task = jobs.tasks.register(owner, "verified-task")
        agent = jobs.agents.register(owner, "verified-codex")
        created = jobs.submit(
            owner,
            [task.task_id],
            [agent.configuration.configuration_id],
            "closed_book",
            "demo",
            "default-single-host-v1",
            "postgres-worker-source-0001",
        )
        OwnerApproval(repository).decide(
            owner, created.job_id, "approve", None, "postgres-worker-approve-0001"
        )
        now = datetime(2026, 9, 12, 10, 0, tzinfo=UTC)
        barrier = Barrier(2, timeout=10)

        def claim(worker):
            barrier.wait()
            return repository.claim(worker, now)

        with ThreadPoolExecutor(max_workers=2) as pool:
            outcomes = tuple(pool.map(claim, ("worker-one", "worker-two")))
        claimed = [item for item in outcomes if item is not None]
        assert len(claimed) == 1
        restored = repository.get(created.job_id)
        assert restored.status == "PREPARING"
        assert restored.runs[0].status == "PREPARING"
        assert restored.claimed_by == claimed[0].lease.worker_id
        assert restored.lease_expires_at == claimed[0].lease.lease_expires_at
        assert repository.claim("worker-three", now) is None

        invalid = replace(claimed[0].lease, worker_id="wrong-worker")
        with pytest.raises(JobLeaseConflict):
            repository.start_execution(invalid, now)
        assert repository.get(created.job_id).status == "PREPARING"


def test_postgres_result_transaction_restores_complete_report(postgres_sandbox):
    with postgres_api(postgres_sandbox) as (_client, jobs, repository, owner):
        task = jobs.tasks.register(owner, "verified-task")
        agent = jobs.agents.register(owner, "verified-codex")
        created = jobs.submit(
            owner,
            [task.task_id],
            [agent.configuration.configuration_id],
            "closed_book",
            "demo",
            "default-single-host-v1",
            "postgres-result-source-0001",
        )
        OwnerApproval(repository).decide(
            owner, created.job_id, "approve", None, "postgres-result-approve-0001"
        )
        now = datetime(2026, 9, 12, 11, 0, tzinfo=UTC)
        artifacts = MemoryArtifacts()
        patch = b"diff --git a/a.py b/a.py\n" + b"+" * (256 * 1024)
        backend = Backend(artifacts, patch)
        evaluator = Evaluator(artifacts)
        executor = JobExecutor(
            repository, artifacts, backend, evaluator, jobs.tasks.source, lambda: now
        )

        assert WorkerShell(repository, executor, lambda: now).run_once("worker-result")

        restarted = type(repository)(postgres_sandbox.dsn)
        stored = restarted.get(created.job_id)
        report = restarted.get_run_report(created.runs[0].run_id)
        assert stored.status == "COMPLETED"
        assert stored.runs[0].resolved_summary is True
        assert report.deterministic_result is not None
        assert report.deterministic_result.resolved is True
        assert report.process_metrics.resources.peak_memory_bytes == 4096
        assert len(report.artifacts) == 3
        patch_artifact = next(
            item
            for item in report.artifacts
            if item.reference.artifact_type == "agent_patch"
        )
        assert patch_artifact.reference.size_bytes == len(patch)
        assert patch_artifact.reference.warnings == ("PATCH_SIZE_WARNING",)


def test_real_pg_minio_database_failure_never_publishes_partial_result(
    postgres_sandbox, job_minio_sandbox
):
    store, service, bucket = job_minio_sandbox
    with postgres_api(postgres_sandbox) as (_client, jobs, repository, owner):
        task = jobs.tasks.register(owner, "verified-task")
        agent = jobs.agents.register(owner, "verified-codex")
        created = jobs.submit(
            owner,
            [task.task_id],
            [agent.configuration.configuration_id],
            "closed_book",
            "demo",
            "default-single-host-v1",
            "postgres-minio-failure-source-0001",
        )
        OwnerApproval(repository).decide(
            owner,
            created.job_id,
            "approve",
            None,
            "postgres-minio-failure-approve-0001",
        )
        with psycopg.connect(postgres_sandbox.dsn) as connection:
            connection.execute(
                "CREATE FUNCTION fail_result() RETURNS trigger LANGUAGE plpgsql "
                "AS $$ BEGIN RAISE EXCEPTION 'synthetic'; END $$"
            )
            connection.execute(
                "CREATE TRIGGER fail_result BEFORE INSERT ON deterministic_results "
                "FOR EACH ROW EXECUTE FUNCTION fail_result()"
            )
        now = datetime(2026, 9, 12, 12, 0, tzinfo=UTC)
        executor = JobExecutor(
            repository,
            store,
            Backend(store, b"diff --git a/a b/a\n"),
            Evaluator(store),
            jobs.tasks.source,
            lambda: now,
        )
        assert WorkerShell(repository, executor, lambda: now).run_once("worker-failure")

        stored = repository.get(created.job_id)
        report = repository.get_run_report(created.runs[0].run_id)
        objects = service.list_objects_v2(Bucket=bucket).get("Contents", [])
        assert stored.status == "FAILED"
        assert report.deterministic_result is None and report.artifacts == ()
        assert len(objects) == 3
