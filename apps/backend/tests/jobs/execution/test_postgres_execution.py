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
from jobs.test_postgres import login, postgres_api

pytestmark = pytest.mark.integration


def approved_job(jobs, repository, owner, submit_key, approval_key):
    task = jobs.tasks.register(owner, "verified-task")
    agent = jobs.agents.register(owner, "verified-codex")
    created = jobs.submit(
        owner,
        [task.task_id],
        [agent.configuration.configuration_id],
        "closed_book",
        "demo",
        "default-single-host-v1",
        submit_key,
    )
    OwnerApproval(repository).decide(
        owner, created.job_id, "approve", None, approval_key
    )
    return created


def test_postgres_claim_is_exclusive_versioned_and_restart_safe(postgres_sandbox):
    with postgres_api(postgres_sandbox) as (_client, jobs, repository, owner):
        created = approved_job(
            jobs,
            repository,
            owner,
            "postgres-worker-source-0001",
            "postgres-worker-approve-0001",
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
        created = approved_job(
            jobs,
            repository,
            owner,
            "postgres-result-source-0001",
            "postgres-result-approve-0001",
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
        assert len(report.artifacts) == 5
        patch_artifact = next(
            item
            for item in report.artifacts
            if item.reference.artifact_type == "agent_patch"
        )
        assert patch_artifact.reference.size_bytes == len(patch)
        assert patch_artifact.reference.warnings == ("PATCH_SIZE_WARNING",)
        assert all(
            item.reference.warnings == ()
            for item in report.artifacts
            if item is not patch_artifact
        )


def test_real_pg_minio_database_failure_never_publishes_partial_result(
    postgres_sandbox, job_minio_sandbox
):
    store, service, bucket = job_minio_sandbox
    with postgres_api(postgres_sandbox) as (_client, jobs, repository, owner):
        created = approved_job(
            jobs,
            repository,
            owner,
            "postgres-minio-failure-source-0001",
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
        source = MemoryArtifacts()
        executor = JobExecutor(
            repository,
            store,
            Backend(source, b"diff --git a/a b/a\n"),
            Evaluator(source),
            jobs.tasks.source,
            lambda: now,
            source,
        )
        assert WorkerShell(repository, executor, lambda: now).run_once("worker-failure")

        stored = repository.get(created.job_id)
        report = repository.get_run_report(created.runs[0].run_id)
        objects = service.list_objects_v2(Bucket=bucket).get("Contents", [])
        assert stored.status == "FAILED"
        assert report.deterministic_result is None and report.artifacts == ()
        assert sorted(item["Key"].split("/")[2] for item in objects) == [
            "agent_patch",
            "harness_report",
            "harness_test_output",
            "public_test_summary",
            "public_trajectory",
        ]


def test_real_pg_minio_http_report_fails_closed_after_object_loss(
    postgres_sandbox, job_minio_sandbox
):
    store, service, bucket = job_minio_sandbox
    with postgres_api(postgres_sandbox, report_store=store) as (
        client,
        jobs,
        repository,
        owner,
    ):
        created = approved_job(
            jobs,
            repository,
            owner,
            "postgres-minio-report-source-0001",
            "postgres-minio-report-approve-0001",
        )
        now = datetime(2026, 9, 12, 13, 0, tzinfo=UTC)
        source = MemoryArtifacts()
        executor = JobExecutor(
            repository,
            store,
            Backend(source, b"diff --git a/a b/a\n"),
            Evaluator(source),
            jobs.tasks.source,
            lambda: now,
            source,
        )
        assert WorkerShell(repository, executor, lambda: now).run_once("worker-report")
        assert login(client).status_code == 200
        path = f"/api/v1/reports/runs/{created.runs[0].run_id}"
        assert client.get(path).status_code == 200
        reference = repository.get_run_report(created.runs[0].run_id).artifacts[0]
        service.delete_object(Bucket=bucket, Key=reference.reference.object_key)
        unavailable = client.get(path)
        assert unavailable.status_code == 503
        assert unavailable.json()["error"]["code"] == "DEPENDENCY_UNAVAILABLE"
