import os
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

from eval_platform.delivery import jobs as jobs_cli
from jobs.artifacts.cleanup_support import NOW, OWNER, RetentionRecords, expired
from jobs.execution.support.fakes import MemoryArtifacts


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
