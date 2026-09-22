"""Pure validation for fixed Fork summary and per-instance reports."""

from __future__ import annotations

from typing import Any, cast

from eval_platform.application.ports.evaluator import EvaluationRequest

OUTCOMES = ("resolved", "unresolved", "empty_patch", "error")


def instance_report(report: dict[str, Any], instance: str) -> dict[str, Any]:
    if set(report) != {instance} or not isinstance(report[instance], dict):
        raise ValueError("Instance report identity mismatch")
    result = cast(dict[str, Any], report[instance])
    for name in ("patch_exists", "patch_successfully_applied", "resolved"):
        if type(result.get(name)) is not bool:
            raise ValueError(f"Invalid report boolean: {name}")
    if not result["patch_exists"] or not result["patch_successfully_applied"]:
        raise ValueError("Report does not establish successful test-patch application")
    return result


def check_summary(summary: dict[str, Any], instance: str) -> None:
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
    outcomes: list[str] = []
    for name in (*OUTCOMES, "completed"):
        ids = _summary_category(summary, name, instance)
        if name in OUTCOMES:
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


def _summary_category(summary: dict[str, Any], name: str, instance: str) -> list[str]:
    ids = summary.get(f"{name}_ids")
    count = summary.get(f"{name}_instances")
    if ids not in ([], [instance]) or type(count) is not int or count != len(ids):
        raise ValueError(f"Invalid summary category: {name}")
    return cast(list[str], ids)


def check_tests(
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
