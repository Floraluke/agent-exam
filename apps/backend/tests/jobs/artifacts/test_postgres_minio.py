from datetime import UTC, datetime, timedelta

import pytest
from botocore.exceptions import ClientError

from eval_platform.application.execute_job import JobExecutor
from eval_platform.application.job_lifecycle.retention import ArtifactRetention
from eval_platform.application.owner_approval import OwnerApproval
from eval_platform.delivery.worker.main import WorkerShell
from eval_platform.domain.catalog import ArtifactUnavailable
from eval_platform.domain.jobs.models import JobUnavailable
from jobs.execution.support.fakes import Backend, Evaluator, MemoryArtifacts
from jobs.support.postgres_api import login, postgres_api, register


class DeleteFailure:
    def __init__(self, store):
        self.store = store

    def read_bounded_verified(self, reference, maximum):
        return self.store.read_bounded_verified(reference, maximum)

    def delete_verified(self, reference):
        raise ArtifactUnavailable


class AuditFailure:
    def __init__(self, repository):
        self.repository = repository

    def expired_artifacts(self, now, limit):
        return self.repository.expired_artifacts(now, limit)

    def begin_artifact_deletion(self, *args):
        return self.repository.begin_artifact_deletion(*args)

    def confirm_artifact_deletion(self, *args):
        return self.repository.confirm_artifact_deletion(*args)

    def mark_artifact_deleted(self, intent, occurred_at):
        raise JobUnavailable


@pytest.mark.integration
def test_real_postgres_and_minio_cleanup_preserves_results_and_audit(
    postgres_sandbox,
    job_minio_sandbox,
):
    store, client, bucket = job_minio_sandbox
    now = datetime(2026, 9, 13, 8, 0, tzinfo=UTC)
    with postgres_api(postgres_sandbox, report_store=store) as (
        http,
        jobs,
        repository,
        owner,
    ):
        assert login(http).status_code == 200
        task = register(http, "/api/v1/tasks/register", "verified-task")
        agent = register(http, "/api/v1/agent-configurations", "verified-codex")
        created = jobs.submit(
            owner,
            [task["task_id"]],
            [agent["agent_configuration_id"]],
            "closed_book",
            "demo",
            "default-single-host-v1",
            "real-retention-source-0001",
        )
        OwnerApproval(repository).decide(
            owner,
            created.job_id,
            "approve",
            None,
            "real-retention-approve-0001",
        )
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
        assert WorkerShell(repository, executor, lambda: now).run_once(
            "real-retention-worker"
        )
        run_id = created.runs[0].run_id
        before = http.get(f"/api/v1/reports/runs/{run_id}").json()
        raw = [
            item
            for item in before["artifact_links"]
            if item["retention_class"] == "raw_30d"
        ]
        assert len(raw) == 3
        assert (
            repository.expired_artifacts(
                now + timedelta(days=30) - timedelta(microseconds=1), 100
            )
            == ()
        )
        assert len(repository.expired_artifacts(now + timedelta(days=30), 100)) == 3

        expired_at = now + timedelta(days=31)
        target = repository.expired_artifacts(expired_at, 1)[0]
        with pytest.raises(ArtifactUnavailable):
            ArtifactRetention(repository, DeleteFailure(store)).cleanup(
                owner, expired_at, 1
            )
        assert len(repository.expired_artifacts(expired_at, 100)) == 3
        client.head_object(Bucket=bucket, Key=target.reference.object_key)

        with pytest.raises(JobUnavailable):
            ArtifactRetention(AuditFailure(repository), store).cleanup(
                owner, expired_at, 1
            )
        assert len(repository.expired_artifacts(expired_at, 100)) == 3
        with pytest.raises(ClientError) as missing:
            client.head_object(Bucket=bucket, Key=target.reference.object_key)
        assert missing.value.response["ResponseMetadata"]["HTTPStatusCode"] == 404

        recovered = ArtifactRetention(repository, store).cleanup(owner, expired_at, 1)
        result = ArtifactRetention(repository, store).cleanup(owner, expired_at)

        assert (recovered.scanned, recovered.deleted, recovered.recovered) == (1, 0, 1)
        assert (result.scanned, result.deleted, result.recovered) == (2, 2, 0)
        assert (
            ArtifactRetention(repository, store).cleanup(owner, expired_at).scanned == 0
        )
        after = http.get(f"/api/v1/reports/runs/{run_id}")
        assert after.status_code == 200
        deleted = [
            item
            for item in after.json()["artifact_links"]
            if item["retention_class"] == "raw_30d"
        ]
        assert all(item["content_status"] == "deleted" for item in deleted)
        assert all(item["deleted_by"] == owner.user_id for item in deleted)
        assert all(
            item["deletion_reason"] == "raw_retention_expired" for item in deleted
        )
        assert all(
            item["size_bytes"] > 0 and len(item["sha256"]) == 64 for item in deleted
        )
        assert all(item["created_at"] is not None for item in deleted)
        assert (
            http.get(
                f"/api/v1/artifacts/{deleted[0]['artifact_id']}/content"
            ).status_code
            == 410
        )
        remaining = client.list_objects_v2(Bucket=bucket).get("Contents", [])
        assert len(remaining) == 5
