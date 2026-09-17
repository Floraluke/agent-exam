"""Owner-local production Worker composition; command control is kept separate."""

import hashlib
import os
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from eval_platform.adapters.artifacts.config import MinioConfig, create_client
from eval_platform.adapters.artifacts.local import LocalArtifactReader
from eval_platform.adapters.artifacts.minio import MinioArtifactStore
from eval_platform.adapters.evaluation.swe_bench import FORK_REVISION, SWEbenchEvaluator
from eval_platform.adapters.execution.codex.install import ARCHIVE_BYTES, ARCHIVE_SHA512
from eval_platform.adapters.execution.codex.uploads import validate_auth_file
from eval_platform.adapters.execution.harbor.adapter import HarborExecutionAdapter
from eval_platform.adapters.execution.harbor.config_mapper import HARBOR_REVISION
from eval_platform.adapters.persistence.jobs.repository import PostgresJobRepository
from eval_platform.adapters.tasks.swe_gym import CANDIDATE_INSTANCE_ID, SWEGymTaskSource
from eval_platform.application.execute_job import JobExecutor
from eval_platform.application.ports.execution import RunLimits
from eval_platform.delivery.http.config import database_url
from eval_platform.delivery.job_presets import submission_policy
from eval_platform.delivery.worker.command import run_command
from eval_platform.delivery.worker.main import WorkerShell

MODEL_HOSTS = ("auth.openai.com", "chatgpt.com")


@dataclass(frozen=True, slots=True)
class RuntimeWorkerConfig:
    project_root: Path
    evidence_root: Path
    task_parquet: Path
    codex_archive: Path = field(repr=False)
    codex_auth_path: Path = field(repr=False)
    dsn: str = field(repr=False)
    minio: MinioConfig = field(repr=False)

    @classmethod
    def from_environment(cls) -> "RuntimeWorkerConfig":
        project = _required_path("AGENTEXAM_PROJECT_ROOT")
        evidence = _required_path("AGENTEXAM_WORKER_EVIDENCE_ROOT")
        runtime = (project / "runtime").resolve()
        try:
            relative = evidence.relative_to(runtime)
        except ValueError:
            raise ValueError(
                "Worker evidence must stay under project runtime"
            ) from None
        if not relative.parts:
            raise ValueError("Worker evidence requires a dedicated runtime directory")
        return cls(
            project,
            evidence,
            _required_path("AGENTEXAM_TASK_PARQUET"),
            _required_path("AGENTEXAM_CODEX_ARCHIVE"),
            _required_path("AGENTEXAM_CODEX_AUTH_PATH"),
            database_url(),
            MinioConfig.from_environment(),
        )


def create_runtime_worker(config: RuntimeWorkerConfig) -> WorkerShell:
    """Validate fixed local inputs, then compose the existing Worker seam."""
    _verify_codex_archive(config.codex_archive)
    validate_auth_file(config.codex_auth_path)
    _verify_framework(config.project_root / "framework/harbor", HARBOR_REVISION)
    _verify_framework(config.project_root / "framework/swe-bench-fork", FORK_REVISION)
    source = SWEGymTaskSource(config.task_parquet)
    source.load(CANDIDATE_INSTANCE_ID)
    if config.evidence_root.is_symlink() or (
        config.evidence_root.exists() and not config.evidence_root.is_dir()
    ):
        raise ValueError("Worker evidence root must be a regular directory")
    profile = submission_policy().limits("default-single-host-v1")
    if profile is None:
        raise ValueError("Fixed Worker limit profile is unavailable")
    repository = PostgresJobRepository(config.dsn)
    artifacts = MinioArtifactStore(create_client(config.minio), config.minio.bucket)
    backend = HarborExecutionAdapter(
        config.project_root / "framework/harbor/.venv/Scripts/harbor.exe",
        config.evidence_root / "execution",
        config.project_root,
        network_hosts=MODEL_HOSTS,
        codex_archive=config.codex_archive,
        codex_auth_path=config.codex_auth_path,
    )
    evaluator = SWEbenchEvaluator(
        repo_root=config.project_root,
        task_source=source,
        evidence_root=config.evidence_root / "evaluation",
        limits=RunLimits(
            profile.evaluator_wall_timeout_sec,
            profile.evaluator_cpus,
            profile.evaluator_memory_mb,
            profile.agent_storage_mb,
        ),
    )
    return WorkerShell(
        repository,
        JobExecutor(
            repository,
            artifacts,
            backend,
            evaluator,
            source,
            source_artifacts=LocalArtifactReader(
                config.evidence_root, reference_root=config.project_root
            ),
        ),
    )


def main(argv: list[str] | None = None) -> int:
    return run_command(
        argv, lambda: create_runtime_worker(RuntimeWorkerConfig.from_environment())
    )


def _verify_codex_archive(path: Path) -> None:
    if path.is_symlink() or not path.is_file():
        raise ValueError("CODEX_PACKAGE_INVALID")
    if path.stat().st_size != ARCHIVE_BYTES:
        raise ValueError("CODEX_PACKAGE_SIZE_MISMATCH")
    with path.open("rb") as stream:
        if hashlib.file_digest(stream, "sha512").hexdigest() != ARCHIVE_SHA512:
            raise ValueError("CODEX_PACKAGE_HASH_MISMATCH")


def _verify_framework(path: Path, revision: str) -> None:
    try:
        head = subprocess.run(
            ["git", "-C", str(path), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
            timeout=10,
        ).stdout.strip()
        status = subprocess.run(
            ["git", "-C", str(path), "status", "--porcelain", "--untracked-files=no"],
            check=True,
            capture_output=True,
            text=True,
            timeout=10,
        ).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        raise ValueError("FIXED_FRAMEWORK_UNAVAILABLE") from None
    if head != revision or status:
        raise ValueError("FIXED_FRAMEWORK_IDENTITY_MISMATCH")


def _required_path(name: str) -> Path:
    value = os.environ.get(name, "")
    path = Path(value)
    if not value or not path.is_absolute():
        raise ValueError(f"{name} must be an explicit absolute path")
    return path.resolve()


if __name__ == "__main__":
    raise SystemExit(main())
