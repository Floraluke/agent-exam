"""Validate stored leaderboard candidates before domain aggregation."""

from datetime import datetime
from typing import Any

from eval_platform.adapters.persistence.jobs.reporting.validation import (
    mapping,
    read_agent,
    read_limits,
    read_network,
    read_task,
    read_tool,
    text,
)
from eval_platform.domain.leaderboard import (
    AgentIdentity,
    AttemptMetrics,
    ComparisonScope,
    LeaderboardAttempt,
)
from eval_platform.domain.result import ResourceSummary, UsageSummary


def read_attempt(row: dict[str, Any]) -> LeaderboardAttempt:
    task = read_task(row["task_snapshot"], row)
    agent = read_agent(row["agent_snapshot"], row)
    if (
        row["backend_kind"] != "harbor"
        or row["backend_revision"] != row["harbor_revision"]
    ):
        raise ValueError("Official execution identity changed")
    resolved = row["resolved"]
    result_at = row["result_created_at"]
    _validate_result(row, resolved, result_at)
    finished_at = row["run_finished_at"] or row["job_finished_at"]
    if finished_at is None:
        finished_at = row["job_created_at"]
    if not isinstance(finished_at, datetime):
        raise ValueError("Stored finish time is invalid")
    started_at = row["run_started_at"]
    if started_at is not None and not isinstance(started_at, datetime):
        raise ValueError("Stored start time is invalid")
    created_at = row["job_created_at"]
    if not isinstance(created_at, datetime):
        raise ValueError("Stored creation time is invalid")
    return LeaderboardAttempt(
        ComparisonScope(
            task.dataset_id,
            task.dataset_revision,
            task.split,
            task.repo,
            text(row["evaluation_track"]),
            text(row["network_policy_id"]),
            read_network(row["network_policy_snapshot"]),
            text(row["tool_profile_id"]),
            read_tool(row["tool_profile_snapshot"]),
            text(row["limit_profile_id"]),
            read_limits(row["limit_snapshot"]),
            text(row["harbor_revision"]),
            text(row["swe_gym_revision"]),
            text(row["swe_bench_fork_revision"]),
            text(row["execution_contract_version"]),
        ),
        AgentIdentity(
            agent.agent_configuration_id,
            agent.display_name,
            agent.agent_type,
            agent.agent_version,
            agent.model_provider,
            agent.model,
            agent.reasoning_effort,
            agent.configuration_fingerprint,
        ),
        task.task_id,
        task.instance_id,
        str(row["job_id"]),
        None if row["rerun_of_job_id"] is None else str(row["rerun_of_job_id"]),
        str(row["run_id"]),
        created_at,
        started_at,
        finished_at,
        row["job_status"],
        row["run_status"],
        row["failure_code"],
        resolved,
        result_at,
        _metrics(row["process_metrics"]),
        row["result_scope"],
    )


def _validate_result(row: dict[str, Any], resolved: object, result_at: object) -> None:
    present = result_at is not None
    if present != (row["run_status"] == "COMPLETED"):
        raise ValueError("Completed Run result is incomplete")
    if not present:
        if resolved is not None or row["resolved_summary"] is not None:
            raise ValueError("Non-completed Run has result data")
        return
    if not isinstance(resolved, bool) or row["resolved_summary"] != resolved:
        raise ValueError("Result summary changed")
    patch_exists = row["patch_exists"]
    patch_applied = row["patch_successfully_applied"]
    if resolved and not patch_applied or patch_applied and not patch_exists:
        raise ValueError("Result boolean evidence is impossible")
    if row["harness_revision"] != row["swe_bench_fork_revision"]:
        raise ValueError("Harness revision changed")


def _metrics(value: object) -> AttemptMetrics:
    if value is None:
        return AttemptMetrics()
    values = mapping(value)
    if set(values) != {"usage", "resources"}:
        raise ValueError("Stored process metrics are invalid")
    usage = UsageSummary(**mapping(values["usage"]))
    resources = ResourceSummary(**mapping(values["resources"]))
    return AttemptMetrics(
        usage.n_input_tokens,
        usage.n_cache_tokens,
        usage.n_output_tokens,
        usage.cost_usd,
        resources.wall_time_sec,
        resources.cpu_time_sec,
        resources.peak_memory_bytes,
    )
