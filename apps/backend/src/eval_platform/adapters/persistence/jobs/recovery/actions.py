"""Atomically close an expired execution from persisted facts only."""

from datetime import datetime
from typing import Any
from uuid import uuid4

import psycopg

from eval_platform.adapters.persistence.jobs.records import read_job
from eval_platform.domain.jobs.decisions import JobStateConflict
from eval_platform.domain.jobs.execution import RecoveryRequest
from eval_platform.domain.jobs.models import EvaluationJob, JobNotFound, JobUnavailable
from eval_platform.domain.jobs.policy import (
    RECOVERY_JOB_TERMINAL_STATUSES,
    recovery_is_due,
    recovery_job_outcome,
    recovery_run_outcome,
)

Connection = psycopg.Connection[Any]


def recover(connection: Connection, request: RecoveryRequest) -> EvaluationJob:
    job = connection.execute(
        "SELECT * FROM evaluation_jobs WHERE job_id=%s FOR UPDATE",
        (request.job_id,),
    ).fetchone()
    if job is None:
        raise JobNotFound
    if job["status"] in RECOVERY_JOB_TERMINAL_STATUSES and _was_recovered(
        connection, request.job_id
    ):
        return _read(connection, request.job_id)
    if not recovery_is_due(job["status"], job["lease_expires_at"], request.occurred_at):
        raise JobStateConflict
    statuses, interrupted = _recover_runs(
        connection,
        request.job_id,
        job["swe_bench_fork_revision"],
        request.occurred_at,
    )
    target, code, summary = recovery_job_outcome(
        job["cancel_requested_by"] is not None, statuses, interrupted
    )
    connection.execute(
        "UPDATE evaluation_jobs SET status=%s,row_version=row_version+1,"
        "failure_code=%s,failure_summary=%s,finished_at=%s WHERE job_id=%s",
        (target, code, summary, request.occurred_at, request.job_id),
    )
    connection.execute(
        "INSERT INTO job_state_events "
        "(event_id,job_id,sequence,from_status,to_status,reason_code,"
        "actor_user_id,occurred_at,note) "
        "SELECT %s,%s,COALESCE(max(sequence),0)+1,%s,%s,"
        "'INTERRUPTION_RECOVERED',%s,%s,%s FROM job_state_events WHERE job_id=%s",
        (
            str(uuid4()),
            request.job_id,
            job["status"],
            target,
            request.actor_user_id,
            request.occurred_at,
            "过期执行租约已按持久化证据收束。",
            request.job_id,
        ),
    )
    return _read(connection, request.job_id)


def _recover_runs(
    connection: Connection, job_id: str, harness_revision: str, now: datetime
) -> tuple[list[str], bool]:
    rows = connection.execute(
        "SELECT r.*,d.run_id AS result_run_id,d.patch_exists AS result_patch_exists,"
        "d.patch_successfully_applied AS result_patch_applied,"
        "d.resolved AS result_resolved,d.harness_revision AS result_revision "
        "FROM evaluation_runs r "
        "LEFT JOIN deterministic_results d ON d.run_id=r.run_id "
        "WHERE r.job_id=%s ORDER BY r.run_id FOR UPDATE OF r",
        (job_id,),
    ).fetchall()
    if not rows:
        raise JobUnavailable
    statuses, interrupted = [], False
    for row in rows:
        has_result = row["result_run_id"] is not None
        if (row["status"] == "COMPLETED") != has_result or (
            has_result and not _result_evidence_valid(row, harness_revision)
        ):
            raise JobUnavailable
        outcome = recovery_run_outcome(row["status"], row["stage"])
        if outcome is None:
            statuses.append(row["status"])
            continue
        target, stage, code, summary = outcome
        interrupted = interrupted or code is not None
        connection.execute(
            "UPDATE evaluation_runs SET status=%s,stage=%s,row_version=row_version+1,"
            "failure_code=%s,failure_summary=%s,started_at=CASE WHEN %s='FAILED' "
            "THEN COALESCE(started_at,%s) ELSE started_at END,finished_at=%s "
            "WHERE run_id=%s",
            (
                target,
                stage,
                code,
                summary,
                target,
                now,
                now,
                row["run_id"],
            ),
        )
        _run_event(connection, row, target, code, now)
        statuses.append(target)
    return statuses, interrupted


def _result_evidence_valid(row: dict[str, Any], expected_revision: str) -> bool:
    return (
        row["resolved_summary"] == row["result_resolved"]
        and row["result_revision"] == expected_revision
        and (not row["result_patch_applied"] or row["result_patch_exists"])
        and (not row["result_resolved"] or row["result_patch_applied"])
    )


def _run_event(
    connection: Connection,
    row: dict[str, Any],
    target: str,
    code: str | None,
    now: datetime,
) -> None:
    reason = code or "INTERRUPTION_PENDING_CANCELED"
    connection.execute(
        "INSERT INTO run_state_events "
        "(event_id,run_id,sequence,from_status,to_status,reason_code,occurred_at) "
        "SELECT %s,%s,COALESCE(max(sequence),0)+1,%s,%s,%s,%s "
        "FROM run_state_events WHERE run_id=%s",
        (
            str(uuid4()),
            row["run_id"],
            row["status"],
            target,
            reason,
            now,
            row["run_id"],
        ),
    )


def _was_recovered(connection: Connection, job_id: str) -> bool:
    row = connection.execute(
        "SELECT EXISTS (SELECT 1 FROM job_state_events WHERE job_id=%s "
        "AND reason_code='INTERRUPTION_RECOVERED') AS present",
        (job_id,),
    ).fetchone()
    return row is not None and bool(row["present"])


def _read(connection: Connection, job_id: str) -> EvaluationJob:
    record = read_job(connection, job_id)
    if record is None:
        raise JobUnavailable
    return record
