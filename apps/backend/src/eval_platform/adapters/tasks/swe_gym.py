from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pyarrow.parquet as pq  # type: ignore[import-untyped]

from eval_platform.adapters.execution.network import compose_profile
from eval_platform.adapters.tasks import catalog as _catalog
from eval_platform.application.ports.execution import RunLimits
from eval_platform.domain.task import EvaluationTask, EvaluatorTaskData, TaskBundle

CANDIDATE_IMAGE = _catalog.CANDIDATE_IMAGE
CANDIDATE_INSTANCE_ID = _catalog.CANDIDATE_INSTANCE_ID
FIXED_TASK_IMAGES = _catalog.FIXED_TASK_IMAGES

DATASET_ID = "SWE-Gym/SWE-Gym-Lite"
DATASET_REVISION = "61231f2c90b18985b42a1419738a240085a15107"
DATASET_SPLIT = "train"
DATASET_SIZE = 931_193
DATASET_SHA256 = "f3a7cd934e8cc523b6053298d0abb2c82fd7db2b83f9f2ccba5944545aaa4eb1"


@dataclass(frozen=True, slots=True)
class DatasetIdentity:
    dataset_id: str = DATASET_ID
    revision: str = DATASET_REVISION
    split: str = DATASET_SPLIT
    size_bytes: int = DATASET_SIZE
    sha256: str = DATASET_SHA256


class SWEGymTaskSource:
    """Read a content-verified local Parquet snapshot, never a moving HF branch."""

    def __init__(
        self,
        parquet_path: Path,
        identity: DatasetIdentity | None = None,
        images: Mapping[str, str] | None = None,
    ):
        self._path = parquet_path
        self._identity = identity or DatasetIdentity()
        # 空映射必须表示“没有任何已登记候选”，不得回落到内置白名单。
        self._images = FIXED_TASK_IMAGES if images is None else images

    def load(self, instance_id: str) -> TaskBundle:
        self._verify_dataset()
        table = pq.read_table(
            self._path,
            filters=[("instance_id", "=", instance_id)],
        )
        rows = table.to_pylist()
        if len(rows) != 1:
            raise KeyError(f"Expected one task {instance_id!r}, found {len(rows)}")
        return self._map_record(rows[0])

    def _verify_dataset(self) -> None:
        if not self._path.is_file() or self._path.is_symlink():
            raise ValueError("Dataset snapshot must be a regular local file")
        if self._path.stat().st_size != self._identity.size_bytes:
            raise ValueError("Dataset snapshot size does not match its fixed identity")
        digest = hashlib.sha256(self._path.read_bytes()).hexdigest()
        if digest != self._identity.sha256:
            raise ValueError(
                "Dataset snapshot SHA-256 does not match its fixed identity"
            )

    def _map_record(self, record: dict[str, Any]) -> TaskBundle:
        required = {
            "instance_id",
            "repo",
            "base_commit",
            "problem_statement",
            "version",
            "patch",
            "test_patch",
            "FAIL_TO_PASS",
            "PASS_TO_PASS",
        }
        missing = sorted(required - record.keys())
        if missing:
            raise ValueError(f"SWE-Gym record is missing fields: {', '.join(missing)}")
        instance_id = _string(record, "instance_id")
        image = self._images.get(instance_id)
        if image is None:
            raise ValueError(f"No fixed M0 image is registered for {instance_id!r}")
        raw = json.dumps(
            record,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        public = EvaluationTask(
            dataset_id=self._identity.dataset_id,
            dataset_revision=self._identity.revision,
            split=self._identity.split,
            instance_id=instance_id,
            repo=_string(record, "repo"),
            base_commit=_string(record, "base_commit"),
            problem_statement=_string(record, "problem_statement"),
            environment_image=image,
            raw_record_sha256=hashlib.sha256(raw).hexdigest(),
        )
        evaluator = EvaluatorTaskData(
            instance_id=instance_id,
            version=_string(record, "version"),
            gold_patch=_string(record, "patch", allow_empty=True),
            test_patch=_string(record, "test_patch", allow_empty=True),
            fail_to_pass=_string_tuple(record, "FAIL_TO_PASS"),
            pass_to_pass=_string_tuple(record, "PASS_TO_PASS"),
        )
        return TaskBundle(public=public, evaluator=evaluator, raw_record_json=raw)


def render_harbor_task(task: EvaluationTask, root: Path, limits: RunLimits) -> Path:
    """Materialize only the public task view for Harbor's Agent phase."""
    task_name = task.instance_id.lower().replace("__", "--").replace("_", "-")
    task_dir = root / task_name
    if task_dir.exists():
        raise FileExistsError(f"Refusing to overwrite Harbor task: {task_dir}")
    environment_dir = task_dir / "environment"
    environment_dir.mkdir(parents=True)
    (task_dir / "instruction.md").write_text(
        task.problem_statement.rstrip() + "\n", encoding="utf-8", newline="\n"
    )
    (task_dir / "task.toml").write_text(
        _task_toml(task, limits), encoding="utf-8", newline="\n"
    )
    (environment_dir / "Dockerfile").write_text(
        f"FROM {task.environment_image}\n"
        "COPY --chmod=0555 collect-patch.sh /opt/agent-exam/collect-patch.sh\n"
        "WORKDIR /testbed\n"
        "RUN chown -R 65534:65534 /testbed\n",
        encoding="utf-8",
        newline="\n",
    )
    (environment_dir / "collect-patch.sh").write_text(
        (Path(__file__).with_name("collect_patch.sh")).read_text(encoding="utf-8"),
        encoding="utf-8",
        newline="\n",
    )
    (environment_dir / "docker-compose.yaml").write_text(
        json.dumps(compose_profile(limits), indent=2), encoding="utf-8", newline="\n"
    )
    return task_dir


def _task_toml(task: EvaluationTask, limits: RunLimits) -> str:
    return f"""schema_version = "1.4"
artifacts = [
  {{ source = "/logs/artifacts", destination = "agentexam" }},
]

[metadata]
benchmark = "SWE-Gym"
instance_id = {json.dumps(task.instance_id)}
dataset_revision = {json.dumps(task.dataset_revision)}

[verifier]
timeout_sec = 60.0
environment_mode = "shared"

[[verifier.collect]]
command = "bash /opt/agent-exam/collect-patch.sh {task.base_commit}"
timeout_sec = 60.0
user = "65534:65534"

[agent]
timeout_sec = {float(limits.wall_timeout_sec)}
user = "65534:65534"

[environment]
network_mode = "allowlist"
allowed_hosts = []
build_timeout_sec = 1800.0
cpus = {limits.cpus}
memory_mb = {limits.memory_mb}
storage_mb = {limits.storage_mb}
"""


def _string(record: dict[str, Any], key: str, *, allow_empty: bool = False) -> str:
    value = record[key]
    if not isinstance(value, str) or (not allow_empty and not value):
        raise ValueError(f"SWE-Gym field {key} must be a string")
    return value


def _string_tuple(record: dict[str, Any], key: str) -> tuple[str, ...]:
    value = record[key]
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        raise ValueError(f"SWE-Gym field {key} must be a list of strings")
    return tuple(value)
