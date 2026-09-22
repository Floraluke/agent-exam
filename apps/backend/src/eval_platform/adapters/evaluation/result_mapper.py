from __future__ import annotations

import hashlib
import json
import os
import re
from pathlib import Path
from typing import Any

from eval_platform.adapters.evaluation.result_validation import (
    check_summary,
    check_tests,
    instance_report,
)
from eval_platform.application.ports.evaluator import EvaluationError, EvaluationRequest
from eval_platform.domain.result import ArtifactRef, DeterministicResult

_MAX_BYTES = 50 * 1024 * 1024


def safe_identity(value: str) -> str:
    if not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9_.-]{0,99}", value):
        raise ValueError("Evaluator identities must be safe single path components")
    return value


def artifact(path: Path, root: Path, kind: str) -> ArtifactRef:
    path, root = _local_path(path), _local_path(root)
    if path.is_symlink() or not path.is_file():
        raise EvaluationError("HARNESS_EVIDENCE_MISSING", path.name)
    key = path.resolve().relative_to(root.resolve()).as_posix()
    size = path.stat().st_size
    if size > _MAX_BYTES:
        raise EvaluationError("HARNESS_EVIDENCE_TOO_LARGE", path.name)
    with path.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    return ArtifactRef(
        key,
        kind,
        size,
        digest,
        "application/json" if path.suffix == ".json" else "text/plain",
    )


def map_evaluation(
    request: EvaluationRequest, directory: Path, *, artifact_root: Path
) -> DeterministicResult:
    directory = _local_path(directory)
    run_id = safe_identity(request.run_id)
    model = safe_identity(request.model_name_or_path)
    instance = safe_identity(request.task.instance_id)
    summary_path = directory / f"{model}.{run_id}.json"
    summary_ref = artifact(summary_path, artifact_root, "harness_summary")
    summary = _object(summary_path)
    logs = directory / "logs/run_evaluation" / run_id / model / instance
    refs = _evidence(directory, logs, summary_ref, artifact_root)
    try:
        check_summary(summary, instance)
        if summary["empty_patch_ids"]:
            return _empty_result(request, run_id, summary_ref, refs)
        return _reported_result(
            request, run_id, instance, summary, logs, artifact_root, refs
        )
    except (KeyError, TypeError, ValueError) as error:
        raise EvaluationError("HARNESS_REPORT_INVALID", str(error), refs) from error


def _evidence(
    directory: Path, logs: Path, summary_ref: ArtifactRef, artifact_root: Path
) -> tuple[ArtifactRef, ...]:
    evidence = [summary_ref]
    for path in (
        directory / "fork.stdout.log",
        directory / "fork.stderr.log",
        logs / "run_instance.log",
        logs / "test_output.txt",
    ):
        if path.exists():
            evidence.append(artifact(path, artifact_root, "harness_log"))
    return tuple(evidence)


def _empty_result(
    request: EvaluationRequest,
    run_id: str,
    summary_ref: ArtifactRef,
    refs: tuple[ArtifactRef, ...],
) -> DeterministicResult:
    if request.model_patch != b"":
        raise ValueError("Nonempty prediction classified as empty")
    counts: dict[str, object] = {
        "FAIL_TO_PASS": {"success": 0, "failure": len(request.task.fail_to_pass)},
        "PASS_TO_PASS": {"success": len(request.task.pass_to_pass), "failure": 0},
    }
    return DeterministicResult(run_id, False, False, summary_ref, refs[1:], counts)


def _reported_result(
    request: EvaluationRequest,
    run_id: str,
    instance: str,
    summary: dict[str, Any],
    logs: Path,
    artifact_root: Path,
    refs: tuple[ArtifactRef, ...],
) -> DeterministicResult:
    if not request.model_patch:
        raise ValueError("Empty prediction classified as nonempty")
    if summary["error_ids"]:
        raise EvaluationError(
            "HARNESS_EVALUATION_FAILED", "Fixed Fork did not complete the task", refs
        )
    report_path = logs / "report.json"
    report_ref = artifact(report_path, artifact_root, "harness_report")
    result = instance_report(_object(report_path), instance)
    counts = check_tests(result, request)
    expected = (
        summary["resolved_ids"] if result["resolved"] else summary["unresolved_ids"]
    )
    if expected != [instance]:
        raise ValueError("Summary and instance report disagree")
    saved_patch = logs / "patch.diff"
    artifact(saved_patch, artifact_root, "evaluation_patch")
    if saved_patch.read_bytes() != request.model_patch:
        raise ValueError("Harness prediction differs from submitted patch")
    if not (logs / "test_output.txt").is_file():
        raise ValueError("Test output is missing")
    return DeterministicResult(
        run_id, result["resolved"], True, report_ref, refs, counts
    )


def _local_path(path: Path) -> Path:
    """Read long WSL-produced paths without requiring a Windows global setting."""
    value = str(path.absolute())
    if os.name != "nt" or value.startswith("\\\\?\\"):
        return path
    if value.startswith("\\\\"):
        return Path("\\\\?\\UNC\\" + value[2:])
    return Path("\\\\?\\" + value)


def _object(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError) as error:
        raise EvaluationError("HARNESS_REPORT_INVALID", path.name) from error
    if not isinstance(value, dict):
        raise EvaluationError("HARNESS_REPORT_INVALID", "Expected a JSON object")
    return value
