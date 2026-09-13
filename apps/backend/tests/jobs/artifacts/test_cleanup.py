import os
import subprocess
import sys
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from pathlib import Path
from types import SimpleNamespace

import pytest

from eval_platform.application.job_lifecycle.retention import ArtifactRetention
from eval_platform.delivery import jobs as jobs_cli
from eval_platform.domain.catalog import ArtifactUnavailable
from eval_platform.domain.identity import AuthenticatedActor
from eval_platform.domain.jobs.execution import RunArtifact
from eval_platform.domain.jobs.models import JobUnavailable
from eval_platform.domain.result import ArtifactRef
from jobs.execution.support.fakes import MemoryArtifacts

NOW = datetime(2026, 10, 14, 8, 0, tzinfo=UTC)
RUN_ID = "5e87af1c-a652-4c64-a1a3-e454e4638ebd"
OWNER = AuthenticatedActor("00000000-0000-4000-8000-000000000001", "owner", "owner")
MEMBER = AuthenticatedActor(
    "00000000-0000-4000-8000-000000000002", "member", "collaborator"
)


def expired(store: MemoryArtifacts) -> RunArtifact:
    body = b"synthetic raw evidence"
    digest = sha256(body).hexdigest()
    reference = ArtifactRef(
        f"runs/{RUN_ID}/agent_trajectory/{digest}",
        "agent_trajectory",
        len(body),
        digest,
        "application/json",
        "raw_30d",
        created_at=NOW - timedelta(days=31),
        original_filename="trajectory.json",
        original_size_bytes=len(body),
        expires_at=NOW - timedelta(days=1),
    )
    store.content[reference.object_key] = body
    return RunArtifact(
        "00000000-0000-4000-8000-000000000003", RUN_ID, reference, "blocked"
    )


class RetentionRecords:
    def __init__(self, item: RunArtifact, *, fail_once: bool = False):
        self.item = item
        self.fail_once = fail_once
        self.marks = 0

    def expired_artifacts(self, now, limit):
        reference = self.item.reference
        if reference.deleted_at is not None or reference.expires_at > now:
            return ()
        return (self.item,)

    def mark_artifact_deleted(self, item, actor_user_id, occurred_at, reason):
        self.marks += 1
        if self.fail_once:
            self.fail_once = False
            raise JobUnavailable
        assert item == self.item
        reference = replace(
            item.reference,
            deleted_at=occurred_at,
            deleted_by=actor_user_id,
            deletion_reason=reason,
        )
        self.item = replace(item, reference=reference)


class FailingDelete(MemoryArtifacts):
    def delete_verified(self, reference):
        raise ArtifactUnavailable


def test_owner_cleanup_is_exact_audited_and_idempotent():
    store = MemoryArtifacts()
    records = RetentionRecords(expired(store))
    retention = ArtifactRetention(records, store)

    first = retention.cleanup(OWNER, NOW)
    second = retention.cleanup(OWNER, NOW)

    assert (first.scanned, first.deleted, first.recovered) == (1, 1, 0)
    assert (second.scanned, second.deleted, second.recovered) == (0, 0, 0)
    assert records.item.reference.deleted_by == OWNER.user_id
    assert records.item.reference.deletion_reason == "raw_retention_expired"
    assert records.item.reference.object_key not in store.content


def test_database_failure_after_object_delete_is_recovered_on_retry():
    store = MemoryArtifacts()
    records = RetentionRecords(expired(store), fail_once=True)
    retention = ArtifactRetention(records, store)

    with pytest.raises(JobUnavailable):
        retention.cleanup(OWNER, NOW)
    assert records.item.reference.deleted_at is None
    assert records.item.reference.object_key not in store.content

    result = retention.cleanup(OWNER, NOW)
    assert (result.deleted, result.recovered) == (0, 1)
    assert records.item.reference.deleted_at == NOW


def test_object_failure_and_non_owner_never_write_deletion_audit():
    healthy = MemoryArtifacts()
    item = expired(healthy)
    failed = FailingDelete()
    failed.content.update(healthy.content)
    records = RetentionRecords(item)

    with pytest.raises(PermissionError):
        ArtifactRetention(records, healthy).cleanup(MEMBER, NOW)
    with pytest.raises(ArtifactUnavailable):
        ArtifactRetention(records, failed).cleanup(OWNER, NOW)

    assert records.marks == 0
    assert records.item.reference.deleted_at is None


def test_cleanup_cli_refuses_password_pipes_before_loading_storage():
    environment = dict(os.environ)
    environment.pop("AGENTEXAM_DATABASE_URL", None)
    environment["PYTHONPATH"] = str(Path(__file__).parents[3] / "src")
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "eval_platform.delivery.jobs",
            "cleanup-artifacts",
            "owner",
        ],
        input="synthetic piped password\n",
        text=True,
        capture_output=True,
        env=environment,
        timeout=10,
    )
    assert result.returncode == 2
    assert "本机交互终端" in result.stderr
    assert "synthetic piped password" not in result.stdout + result.stderr


def test_cleanup_cli_authenticates_owner_and_revokes_transient_session(
    monkeypatch, capsys
):
    store = MemoryArtifacts()
    records = RetentionRecords(expired(store))
    sessions: list[str] = []

    class FakeIdentity:
        def __init__(self, repository, passwords):
            pass

        def login(self, username, password):
            assert (username, password) == ("owner", "synthetic password")
            return SimpleNamespace(actor=OWNER, token="transient-session")

        def logout(self, token):
            sessions.append(token)

    monkeypatch.setattr(jobs_cli.sys, "stdin", SimpleNamespace(isatty=lambda: True))
    monkeypatch.setattr(
        jobs_cli.getpass, "getpass", lambda _prompt: "synthetic password"
    )
    monkeypatch.setattr(jobs_cli, "database_url", lambda: "synthetic-dsn")
    monkeypatch.setattr(jobs_cli, "PostgresIdentityRepository", lambda _dsn: object())
    monkeypatch.setattr(jobs_cli, "PostgresJobRepository", lambda _dsn: records)
    monkeypatch.setattr(jobs_cli, "MinioArtifactStore", lambda *_args: store)
    monkeypatch.setattr(jobs_cli, "IdentityService", FakeIdentity)
    monkeypatch.setattr(
        jobs_cli, "datetime", SimpleNamespace(now=lambda _timezone: NOW)
    )

    assert jobs_cli.main(["cleanup-artifacts", "owner"]) == 0
    assert sessions == ["transient-session"]
    assert records.item.reference.deleted_at == NOW
    assert "删除 1 个" in capsys.readouterr().out
