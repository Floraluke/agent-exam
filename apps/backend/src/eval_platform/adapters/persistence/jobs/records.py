from hashlib import sha256
from typing import Any

import psycopg

from eval_platform.adapters.persistence.jobs.state_validation import stored_job_valid
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
    actor, worker = row.get("actor_user_id"), row.get("worker_id")
    return StateEvent(
        event_id=str(row["event_id"]),
        sequence=row["sequence"],
        from_status=row["from_status"],
        to_status=row["to_status"],
        reason_code=row["reason_code"],
        occurred_at=row["occurred_at"],
        actor_user_id=None if actor is None else str(actor),
        note=row.get("note"),
        worker_id=worker,
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
    job_events = connection.execute(
        "SELECT * FROM job_state_events WHERE job_id=%s ORDER BY sequence", (job_id,)
    ).fetchall()
    run_events = connection.execute(
        "SELECT e.* FROM run_state_events e JOIN evaluation_runs r "
        "ON r.run_id=e.run_id WHERE r.job_id=%s ORDER BY e.run_id,e.sequence",
        (job_id,),
    ).fetchall()
    grouped: dict[str, list[StateEvent]] = {}
    for item in run_events:
        grouped.setdefault(str(item["run_id"]), []).append(_event(item))
    try:
        runs = tuple(_run(item, grouped) for item in run_rows)
        record = EvaluationJob(
            job_id=str(row["job_id"]),
            created_by=str(row["created_by"]),
            created_at=row["created_at"],
            status=row["status"],
            evaluation_track=row["evaluation_track"],
            result_scope=row["result_scope"],
            batch_preset=row["batch_preset"],
            limit_profile_id=row["limit_profile_id"],
            limit_snapshot=LimitSnapshot(**row["limit_snapshot"]),
            network_policy_id=row["network_policy_id"],
            network_policy_snapshot=NetworkPolicySnapshot(
                **row["network_policy_snapshot"]
            ),
            tool_profile_id=row["tool_profile_id"],
            tool_profile_snapshot=ToolProfileSnapshot(**row["tool_profile_snapshot"]),
            harbor_revision=row["harbor_revision"],
            swe_gym_revision=row["swe_gym_revision"],
            swe_bench_fork_revision=row["swe_bench_fork_revision"],
            runs=runs,
            state_events=tuple(_event(item) for item in job_events),
            owner_decided_by=(
                None
                if row["owner_decided_by"] is None
                else str(row["owner_decided_by"])
            ),
            owner_decided_at=row["owner_decided_at"],
            owner_decision_reason=row["owner_decision_reason"],
            cancel_requested_by=(
                None
                if row["cancel_requested_by"] is None
                else str(row["cancel_requested_by"])
            ),
            cancel_requested_at=row["cancel_requested_at"],
            cancel_reason=row["cancel_reason"],
            rerun_of_job_id=(
                None if row["rerun_of_job_id"] is None else str(row["rerun_of_job_id"])
            ),
            row_version=row["row_version"],
            claimed_by=row["claimed_by"],
            claimed_at=row["claimed_at"],
            heartbeat_at=row["heartbeat_at"],
            lease_expires_at=row["lease_expires_at"],
            failure_code=row["failure_code"],
            failure_summary=row["failure_summary"],
            started_at=row["started_at"],
            finished_at=row["finished_at"],
        )
    except (KeyError, TypeError, ValueError):
        raise JobUnavailable from None
    if record.trial_count != row["trial_count"] or not stored_job_valid(record):
        raise JobUnavailable
    return record


def _run(row: dict[str, Any], grouped: dict[str, list[StateEvent]]) -> EvaluationRun:
    run_id = str(row["run_id"])
    return EvaluationRun(
        run_id=run_id,
        job_id=str(row["job_id"]),
        task=_task(row["task_snapshot"]),
        agent=_agent(row["agent_snapshot"]),
        status=row["status"],
        backend_kind=row["backend_kind"],
        backend_revision=row["backend_revision"],
        execution_contract_version=row["execution_contract_version"],
        created_at=row["created_at"],
        state_events=tuple(grouped.get(run_id, [])),
        row_version=row["row_version"],
        stage=row["stage"],
        backend_job_ref=row["backend_job_ref"],
        backend_trial_ref=row["backend_trial_ref"],
        failure_code=row["failure_code"],
        failure_summary=row["failure_summary"],
        resolved_summary=row["resolved_summary"],
        started_at=row["started_at"],
        finished_at=row["finished_at"],
    )
