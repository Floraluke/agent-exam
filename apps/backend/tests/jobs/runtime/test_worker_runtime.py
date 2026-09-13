from hashlib import sha256
from pathlib import Path

import pytest

from eval_platform.adapters.artifacts.config import MinioConfig
from eval_platform.adapters.artifacts.local import LocalArtifactReader
from eval_platform.delivery.worker import runtime as runtime_module
from eval_platform.delivery.worker.runtime import (
    RuntimeWorkerConfig,
    create_runtime_worker,
    main,
)
from eval_platform.domain.result import ArtifactRef


def test_runtime_worker_reads_harbor_and_fork_evidence(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    captured: dict[str, object] = {}
    shell = object()
    evidence = tmp_path / "runtime" / "acceptance" / "task13" / "evidence"
    harbor_path = evidence / "execution" / "trial" / "model.patch"
    fork_path = evidence / "evaluation" / "run" / "report.json"
    harbor_path.parent.mkdir(parents=True)
    fork_path.parent.mkdir(parents=True)
    harbor_body, fork_body = b"diff --git a/a b/a\n", b'{"resolved":true}'
    harbor_path.write_bytes(harbor_body)
    fork_path.write_bytes(fork_body)
    harbor_ref = ArtifactRef(
        str(harbor_path.resolve()),
        "model_patch",
        len(harbor_body),
        sha256(harbor_body).hexdigest(),
        "text/x-diff",
    )
    fork_ref = ArtifactRef(
        fork_path.relative_to(tmp_path).as_posix(),
        "harness_report",
        len(fork_body),
        sha256(fork_body).hexdigest(),
        "application/json",
    )

    class TaskSource:
        def __init__(self, path: Path) -> None:
            self.path = path

        def load(self, instance_id: str) -> object:
            return object()

    def executor(*args: object, **kwargs: object) -> object:
        reader = kwargs["source_artifacts"]
        assert isinstance(reader, LocalArtifactReader)
        captured["bodies"] = (
            reader.read_verified(harbor_ref),
            reader.read_bounded_verified(fork_ref, 1024).content,
        )
        return object()

    monkeypatch.setattr(runtime_module, "_verify_codex_archive", lambda path: None)
    monkeypatch.setattr(runtime_module, "validate_auth_file", lambda path: None)
    monkeypatch.setattr(
        runtime_module, "_verify_framework", lambda path, revision: None
    )
    monkeypatch.setattr(runtime_module, "SWEGymTaskSource", TaskSource)
    monkeypatch.setattr(runtime_module, "PostgresJobRepository", lambda dsn: object())
    monkeypatch.setattr(runtime_module, "create_client", lambda config: object())
    monkeypatch.setattr(
        runtime_module, "MinioArtifactStore", lambda client, bucket: object()
    )
    monkeypatch.setattr(
        runtime_module, "HarborExecutionAdapter", lambda *args, **kwargs: object()
    )
    monkeypatch.setattr(runtime_module, "SWEbenchEvaluator", lambda **kwargs: object())
    monkeypatch.setattr(runtime_module, "JobExecutor", executor)
    monkeypatch.setattr(runtime_module, "WorkerShell", lambda repository, runner: shell)
    config = RuntimeWorkerConfig(
        tmp_path,
        evidence,
        tmp_path / "task.parquet",
        tmp_path / "codex.tgz",
        tmp_path / "auth.json",
        "host=127.0.0.1",
        MinioConfig("http://127.0.0.1:9000", "bucket", "access", "secret"),
    )

    assert create_runtime_worker(config) is shell
    assert captured["bodies"] == (harbor_body, fork_body)


def test_runtime_config_keeps_private_values_out_of_diagnostics(
    monkeypatch,
) -> None:
    project = Path.cwd().resolve()
    runtime = project / "runtime" / "acceptance" / "worker-config-test"
    private = runtime / "private"
    values = {
        "AGENTEXAM_PROJECT_ROOT": str(project),
        "AGENTEXAM_DATABASE_URL": "host=127.0.0.1 password=database-secret",
        "AGENTEXAM_MINIO_ENDPOINT": "http://127.0.0.1:9000",
        "AGENTEXAM_MINIO_BUCKET": "agentexam-runtime-test",
        "AGENTEXAM_MINIO_ACCESS_KEY": "access-secret",
        "AGENTEXAM_MINIO_SECRET_KEY": "object-secret",
        "AGENTEXAM_TASK_PARQUET": str(runtime / "task.parquet"),
        "AGENTEXAM_WORKER_EVIDENCE_ROOT": str(runtime / "evidence"),
        "AGENTEXAM_CODEX_ARCHIVE": str(private / "codex.tgz"),
        "AGENTEXAM_CODEX_AUTH_PATH": str(private / "auth.json"),
    }
    for name, value in values.items():
        monkeypatch.setenv(name, value)

    config = RuntimeWorkerConfig.from_environment()

    rendered = repr(config)
    assert config.evidence_root == runtime / "evidence"
    assert "database-secret" not in rendered
    assert "access-secret" not in rendered
    assert "object-secret" not in rendered
    assert "auth.json" not in rendered


def test_runtime_worker_rejects_unverified_archive_before_claim(tmp_path: Path) -> None:
    project = Path.cwd().resolve()
    archive = tmp_path / "codex.tgz"
    archive.write_bytes(b"not the pinned archive")
    config = RuntimeWorkerConfig(
        project,
        project / "runtime" / "acceptance" / "invalid-worker",
        tmp_path / "task.parquet",
        archive,
        tmp_path / "auth.json",
        "host=127.0.0.1 password=must-not-connect",
        MinioConfig(
            "http://127.0.0.1:9000",
            "agentexam-runtime-test",
            "access-secret",
            "object-secret",
        ),
    )

    with pytest.raises(ValueError, match="CODEX_PACKAGE_SIZE_MISMATCH"):
        create_runtime_worker(config)


def test_worker_command_fails_closed_without_runtime_config(
    monkeypatch, capsys
) -> None:
    for name in (
        "AGENTEXAM_PROJECT_ROOT",
        "AGENTEXAM_DATABASE_URL",
        "AGENTEXAM_WORKER_EVIDENCE_ROOT",
        "AGENTEXAM_TASK_PARQUET",
        "AGENTEXAM_CODEX_ARCHIVE",
        "AGENTEXAM_CODEX_AUTH_PATH",
    ):
        monkeypatch.delenv(name, raising=False)

    assert main(["task13-worker"]) == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == '{"status": "worker_cycle_unavailable"}\n'
