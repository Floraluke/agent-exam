from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from eval_platform.adapters.execution.harbor.artifacts import (
    RAW_ARTIFACT_MAX_BYTES,
    PatchArtifactError,
    validate_patch_artifact,
)
from eval_platform.application.ports.execution import ExecutionJobRequest
from eval_platform.domain.result import (
    ArtifactRef,
    ExecutionTrialResult,
    ResourceSummary,
    TerminationReason,
    UsageSummary,
)


def process_start_failure(
    request: ExecutionJobRequest,
    error: OSError,
    warnings: tuple[str, ...],
) -> tuple[ExecutionTrialResult, ...]:
    reason = (
        TerminationReason.AGENT_UNAVAILABLE
        if isinstance(error, FileNotFoundError)
        else TerminationReason.INFRASTRUCTURE_INTERRUPTED
    )
    return tuple(
        ExecutionTrialResult(
            run_id=run.run_id,
            backend_job_ref=request.job_id,
            backend_trial_ref="",
            termination_reason=reason,
            patch_ref=None,
            trajectory_ref=None,
            warnings=warnings,
        )
        for run in request.runs
    )


def patch_ref(trial_dir: Path) -> ArtifactRef:
    artifact_dir = trial_dir / "artifacts/agentexam"
    patch = validate_patch_artifact(artifact_dir)
    path = artifact_dir / "model.patch"
    return ArtifactRef(
        object_key=str(path.resolve()),
        artifact_type="model_patch",
        size_bytes=patch.size_bytes,
        sha256=patch.sha256,
        content_type="text/x-diff",
        created_at=modified_at(path),
        warnings=patch.warnings,
    )


def file_ref(path: Path, artifact_type: str, content_type: str) -> ArtifactRef:
    if not path.is_file() or path.is_symlink():
        raise ValueError(f"Required Harbor artifact is missing: {path.name}")
    content = path.read_bytes()
    return ArtifactRef(
        object_key=str(path.resolve()),
        artifact_type=artifact_type,
        size_bytes=len(content),
        sha256=hashlib.sha256(content).hexdigest(),
        content_type=content_type,
        created_at=modified_at(path),
    )


def trajectory_ref(trial_dir: Path) -> tuple[ArtifactRef | None, str | None]:
    path = trial_dir / "agent/trajectory.json"
    if not path.is_file() or path.is_symlink():
        return None, "TRAJECTORY_UNAVAILABLE"
    if path.stat().st_size > RAW_ARTIFACT_MAX_BYTES:
        return None, "TRAJECTORY_TOO_LARGE"
    return file_ref(path, "agent_trajectory", "application/json"), None


def usage_summary(value: Any) -> tuple[UsageSummary | None, str | None]:
    if not isinstance(value, dict):
        return None, None
    raw = (
        value.get("n_input_tokens"),
        value.get("n_cache_tokens"),
        value.get("n_output_tokens"),
        value.get("cost_usd"),
    )
    if all(item is None for item in raw):
        return None, None
    tokens = raw[:3]
    if any(
        item is not None
        and (not isinstance(item, int) or isinstance(item, bool) or item < 0)
        for item in tokens
    ):
        return None, "HARBOR_USAGE_INVALID"
    cost = raw[3]
    if cost is not None and (
        not isinstance(cost, (int, float)) or isinstance(cost, bool) or cost < 0
    ):
        return None, "HARBOR_USAGE_INVALID"
    return (
        UsageSummary(
            n_input_tokens=tokens[0],
            n_cache_tokens=tokens[1],
            n_output_tokens=tokens[2],
            cost_usd=float(cost) if cost is not None else None,
        ),
        None,
    )


def resource_summary(
    data: dict[str, Any],
) -> tuple[ResourceSummary | None, str | None]:
    raw_started = data.get("started_at")
    raw_finished = data.get("finished_at")
    if raw_started is None and raw_finished is None:
        return None, None
    started = parse_datetime(raw_started)
    finished = parse_datetime(raw_finished)
    if started is None or finished is None:
        return None, "HARBOR_TIMING_INVALID"
    try:
        elapsed = (finished - started).total_seconds()
    except TypeError:
        return None, "HARBOR_TIMING_INVALID"
    if elapsed < 0:
        return None, "HARBOR_TIMING_INVALID"
    return ResourceSummary(wall_time_sec=elapsed), None


def exception_reason(exception_type: str) -> TerminationReason:
    if exception_type in {
        "AgentAuthenticationError",
        "ApiUsageLimitError",
        "ModelNotFoundError",
    }:
        return TerminationReason.AGENT_UNAVAILABLE
    if "Timeout" in exception_type:
        return TerminationReason.TIMED_OUT
    if "Policy" in exception_type:
        return TerminationReason.POLICY_FAILED
    if "Environment" in exception_type or "Docker" in exception_type:
        return TerminationReason.SANDBOX_FAILED
    return TerminationReason.AGENT_FAILED


def patch_error_reason(error: PatchArtifactError) -> TerminationReason:
    if error.code == "PATCH_TOO_LARGE":
        return TerminationReason.PATCH_TOO_LARGE
    if error.code == "BINARY_PATCH_NOT_ALLOWED":
        return TerminationReason.BINARY_PATCH_NOT_ALLOWED
    return TerminationReason.PATCH_EXTRACTION_FAILED


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("Harbor JSON root must be an object")
    return value


def required_mapping(data: dict[str, Any], key: str) -> dict[str, Any]:
    value = data.get(key)
    if not isinstance(value, dict):
        raise ValueError(f"Harbor result has no {key} object")
    return value


def required_string(data: dict[str, Any], key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value:
        raise ValueError(f"Harbor result has no {key} string")
    return value


def modified_at(path: Path) -> datetime:
    return datetime.fromtimestamp(path.stat().st_mtime, tz=UTC)


def parse_datetime(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
