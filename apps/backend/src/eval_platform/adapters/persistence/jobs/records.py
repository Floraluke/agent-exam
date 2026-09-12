"""Restore frozen Job records and fail closed on malformed stored snapshots."""

from hashlib import sha256
from typing import Any

import psycopg

from eval_platform.domain.agent import AgentConfiguration
from eval_platform.domain.jobs.models import (
    AgentSnapshot,
    EvaluationJob,
    EvaluationRun,
    JobUnavailable,
    LimitSnapshot,
    NetworkPolicySnapshot,
    StateEvent,
    TaskSnapshot,
    ToolProfileSnapshot,
)


def _event(row: dict[str, Any]) -> StateEvent:
    return StateEvent(
        str(row["event_id"]),
        row["sequence"],
        row["from_status"],
        row["to_status"],
        row["reason_code"],
        row["occurred_at"],
    )


def _task(value: object) -> TaskSnapshot:
    try:
        snapshot = TaskSnapshot(**_mapping(value))
    except (TypeError, ValueError):
        raise JobUnavailable from None
    if (
        sha256(snapshot.problem_statement.encode()).hexdigest()
        != snapshot.problem_sha256
    ):
        raise JobUnavailable
    return snapshot


def _agent(value: object) -> AgentSnapshot:
    try:
        snapshot = AgentSnapshot(**_mapping(value))
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
    except (TypeError, ValueError, KeyError):
        raise JobUnavailable from None
    if configuration.fingerprint != snapshot.configuration_fingerprint:
        raise JobUnavailable
    return snapshot


def _mapping(value: object) -> dict[str, Any]:
    if not isinstance(value, dict) or not all(isinstance(key, str) for key in value):
        raise ValueError("Stored snapshot is not an object")
    return value


def read_job(connection: psycopg.Connection[Any], job_id: str) -> EvaluationJob | None:
    row = connection.execute(
        "SELECT * FROM evaluation_jobs WHERE job_id=%s", (job_id,)
    ).fetchone()
    if row is None:
        return None
    run_rows = connection.execute(
        "SELECT * FROM evaluation_runs WHERE job_id=%s ORDER BY run_id", (job_id,)
    ).fetchall()
    job_event_rows = connection.execute(
        "SELECT * FROM job_state_events WHERE job_id=%s ORDER BY sequence", (job_id,)
    ).fetchall()
    run_event_rows = connection.execute(
        "SELECT e.* FROM run_state_events e JOIN evaluation_runs r "
        "ON r.run_id=e.run_id WHERE r.job_id=%s ORDER BY e.run_id,e.sequence",
        (job_id,),
    ).fetchall()
    grouped: dict[str, list[StateEvent]] = {}
    for item in run_event_rows:
        grouped.setdefault(str(item["run_id"]), []).append(_event(item))
    try:
        runs = tuple(
            EvaluationRun(
                str(item["run_id"]),
                str(item["job_id"]),
                _task(item["task_snapshot"]),
                _agent(item["agent_snapshot"]),
                item["status"],
                item["backend_kind"],
                item["backend_revision"],
                item["execution_contract_version"],
                item["created_at"],
                tuple(grouped.get(str(item["run_id"]), [])),
            )
            for item in run_rows
        )
        record = EvaluationJob(
            str(row["job_id"]),
            str(row["created_by"]),
            row["created_at"],
            row["status"],
            row["evaluation_track"],
            row["result_scope"],
            row["batch_preset"],
            row["limit_profile_id"],
            LimitSnapshot(**row["limit_snapshot"]),
            row["network_policy_id"],
            NetworkPolicySnapshot(**row["network_policy_snapshot"]),
            row["tool_profile_id"],
            ToolProfileSnapshot(**row["tool_profile_snapshot"]),
            row["harbor_revision"],
            row["swe_gym_revision"],
            row["swe_bench_fork_revision"],
            runs,
            tuple(_event(item) for item in job_event_rows),
        )
    except (KeyError, TypeError, ValueError):
        raise JobUnavailable from None
    if (
        record.trial_count != row["trial_count"]
        or len(record.state_events) != 1
        or any(len(run.state_events) != 1 for run in record.runs)
        or record.status != "AWAITING_OWNER_APPROVAL"
        or any(run.status != "PENDING" for run in record.runs)
    ):
        raise JobUnavailable
    return record
