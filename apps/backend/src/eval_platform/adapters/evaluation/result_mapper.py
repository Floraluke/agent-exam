from __future__ import annotations

import hashlib
import json
import os
import re
from pathlib import Path
from typing import Any

from eval_platform.application.ports.evaluator import EvaluationError, EvaluationRequest
from eval_platform.domain.result import ArtifactRef, DeterministicResult

_MAX_BYTES = 50 * 1024 * 1024
_OUTCOMES = ("resolved", "unresolved", "empty_patch", "error")


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
    evidence = [summary_ref]
    for path in (
        directory / "fork.stdout.log",
        directory / "fork.stderr.log",
        logs / "run_instance.log",
        logs / "test_output.txt",
    ):
        if path.exists():
            evidence.append(artifact(path, artifact_root, "harness_log"))
    refs = tuple(evidence)
    try:
        _check_summary(summary, instance)
        if summary["empty_patch_ids"]:
            if request.model_patch != b"":
                raise ValueError("Nonempty prediction classified as empty")
            counts: dict[str, object] = {
                "FAIL_TO_PASS": {
                    "success": 0,
                    "failure": len(request.task.fail_to_pass),
                },
                "PASS_TO_PASS": {
                    "success": len(request.task.pass_to_pass),
                    "failure": 0,
                },
            }
            return DeterministicResult(
                run_id, False, False, summary_ref, refs[1:], counts
            )
        if not request.model_patch:
            raise ValueError("Empty prediction classified as nonempty")
        if summary["error_ids"]:
            raise EvaluationError(
                "HARNESS_EVALUATION_FAILED",
                "Fixed Fork did not complete the task",
                refs,
            )
        report_path = logs / "report.json"
        report_ref = artifact(report_path, artifact_root, "harness_report")
        report = _object(report_path)
        if set(report) != {instance} or not isinstance(report[instance], dict):
            raise ValueError("Instance report identity mismatch")
        result = report[instance]
        for name in ("patch_exists", "patch_successfully_applied", "resolved"):
            if type(result.get(name)) is not bool:
                raise ValueError(f"Invalid report boolean: {name}")
        if not result["patch_exists"] or not result["patch_successfully_applied"]:
            raise ValueError(
                "Report does not establish successful test-patch application"
            )
        counts = _check_tests(result, request)
        expected_ids = (
            summary["resolved_ids"] if result["resolved"] else summary["unresolved_ids"]
        )
        if expected_ids != [instance]:
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
    except (KeyError, TypeError, ValueError) as error:
        raise EvaluationError("HARNESS_REPORT_INVALID", str(error), refs) from error


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


def _check_summary(summary: dict[str, Any], instance: str) -> None:
    if type(summary.get("schema_version")) is not int or summary["schema_version"] != 2:
        raise ValueError("Unsupported Fork summary schema")
    if (
        summary.get("submitted_ids") != [instance]
        or summary.get("incomplete_ids") != []
    ):
        raise ValueError("Summary task identity mismatch")
    for name in ("total_instances", "submitted_instances"):
        if type(summary.get(name)) is not int or summary[name] != 1:
            raise ValueError("Expected a single-task summary")
    outcomes = []
    for name in (*_OUTCOMES, "completed"):
        ids = summary.get(f"{name}_ids")
        count = summary.get(f"{name}_instances")
        if ids not in ([], [instance]) or type(count) is not int or count != len(ids):
            raise ValueError(f"Invalid summary category: {name}")
        if name in _OUTCOMES:
            outcomes.extend(ids)
    if outcomes != [instance]:
        raise ValueError("Summary outcomes must be disjoint and complete")
    if summary["completed_ids"] != summary["resolved_ids"] + summary["unresolved_ids"]:
        raise ValueError("Summary completion is inconsistent")
    if (
        summary.get("unstopped_containers") != []
        or summary.get("unstopped_instances") != 0
    ):
        raise ValueError("Fork reported a container cleanup failure")


def _check_tests(
    result: dict[str, Any], request: EvaluationRequest
) -> dict[str, object]:
    tests = result.get("tests_status")
    if not isinstance(tests, dict):
        raise ValueError("Detailed test classification is missing")
    all_passed = True
    counts: dict[str, object] = {}
    for name, expected in (
        ("FAIL_TO_PASS", request.task.fail_to_pass),
        ("PASS_TO_PASS", request.task.pass_to_pass),
    ):
        group = tests.get(name)
        if not isinstance(group, dict):
            raise ValueError(f"Missing test group: {name}")
        success, failure = group.get("success"), group.get("failure")
        if not isinstance(success, list) or not isinstance(failure, list):
            raise ValueError("Test classifications must be lists")
        entries = success + failure
        if any(not isinstance(item, str) for item in entries):
            raise ValueError("Test IDs must be strings")
        if len(entries) != len(set(entries)) or set(entries) != set(expected):
            raise ValueError("Test classification does not cover the frozen task")
        all_passed = all_passed and not failure
        counts[name] = {"success": len(success), "failure": len(failure)}
    if result["resolved"] != all_passed:
        raise ValueError("Resolved flag contradicts test classifications")
    return counts
