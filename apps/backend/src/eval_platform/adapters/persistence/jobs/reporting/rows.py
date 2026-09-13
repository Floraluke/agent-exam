"""Validate stored leaderboard candidates before domain aggregation."""

from datetime import datetime
from typing import Any

from eval_platform.domain.agent import AgentConfiguration
from eval_platform.domain.jobs.models import (
    AgentSnapshot,
    LimitSnapshot,
    NetworkPolicySnapshot,
    TaskSnapshot,
    ToolProfileSnapshot,
)
from eval_platform.domain.leaderboard import (
    AgentIdentity,
    AttemptMetrics,
    ComparisonScope,
    LeaderboardAttempt,
)
from eval_platform.domain.result import ResourceSummary, UsageSummary


def read_attempt(row: dict[str, Any]) -> LeaderboardAttempt:
    task = TaskSnapshot(**_mapping(row["task_snapshot"]))
    agent = AgentSnapshot(**_mapping(row["agent_snapshot"]))
    _validate_agent(agent)
    resolved = row["resolved"]
    result_at = row["result_created_at"]
    _validate_result(row, resolved, result_at)
    finished_at = row["run_finished_at"] or row["job_finished_at"]
    if finished_at is None:
        finished_at = row["job_created_at"]
    if not isinstance(finished_at, datetime):
        raise ValueError("Stored finish time is invalid")
    if str(row["task_id"]) != task.task_id:
        raise ValueError("Frozen task identity changed")
    return LeaderboardAttempt(
        ComparisonScope(
            task.dataset_id,
            task.dataset_revision,
            task.split,
            task.repo,
            row["evaluation_track"],
            row["network_policy_id"],
            NetworkPolicySnapshot(**_mapping(row["network_policy_snapshot"])),
            row["tool_profile_id"],
            ToolProfileSnapshot(**_mapping(row["tool_profile_snapshot"])),
            row["limit_profile_id"],
            LimitSnapshot(**_mapping(row["limit_snapshot"])),
            row["harbor_revision"],
            row["swe_gym_revision"],
            row["swe_bench_fork_revision"],
            row["execution_contract_version"],
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
        row["job_created_at"],
        finished_at,
        row["job_status"],
        row["run_status"],
        row["failure_code"],
        resolved,
        result_at,
        _metrics(row["process_metrics"]),
        row["result_scope"],
    )


def _validate_agent(snapshot: AgentSnapshot) -> None:
    configuration = AgentConfiguration(
        snapshot.agent_configuration_id,
        snapshot.agent_type,
        snapshot.agent_version,
        snapshot.model_provider,
        snapshot.model,
        snapshot.authentication_type,
        snapshot.credential_profile_id,
        {"reasoning_effort": snapshot.reasoning_effort},
    )
    if configuration.fingerprint != snapshot.configuration_fingerprint:
        raise ValueError("Frozen Agent fingerprint changed")


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
    mapping = _mapping(value)
    if set(mapping) != {"usage", "resources"}:
        raise ValueError("Stored process metrics are invalid")
    usage = UsageSummary(**_mapping(mapping["usage"]))
    resources = ResourceSummary(**_mapping(mapping["resources"]))
    return AttemptMetrics(
        usage.n_input_tokens,
        usage.n_cache_tokens,
        usage.n_output_tokens,
        usage.cost_usd,
        resources.wall_time_sec,
        resources.cpu_time_sec,
        resources.peak_memory_bytes,
    )


def _mapping(value: object) -> dict[str, Any]:
    if not isinstance(value, dict) or not all(isinstance(key, str) for key in value):
        raise ValueError("Stored snapshot is not an object")
    return value
