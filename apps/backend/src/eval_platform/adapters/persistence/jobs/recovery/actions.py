"""Atomically close an expired execution from persisted facts only."""

from datetime import datetime
from typing import Any
from uuid import uuid4

import psycopg

from eval_platform.adapters.persistence.jobs.records import read_job
from eval_platform.domain.jobs.decisions import JobStateConflict
from eval_platform.domain.jobs.execution import RecoveryRequest
from eval_platform.domain.jobs.models import EvaluationJob, JobNotFound, JobUnavailable

Connection = psycopg.Connection[Any]
_ACTIVE = {"PREPARING", "EXECUTING", "CANCEL_REQUESTED", "FINALIZING"}
_TERMINAL = {"COMPLETED", "FAILED", "CANCELED"}


def recover(connection: Connection, request: RecoveryRequest) -> EvaluationJob:
    job = connection.execute(
        "SELECT * FROM evaluation_jobs WHERE job_id=%s FOR UPDATE",
        (request.job_id,),
    ).fetchone()
    if job is None:
        raise JobNotFound
    if job["status"] in _TERMINAL and _was_recovered(connection, request.job_id):
        return _read(connection, request.job_id)
    if (
        job["status"] not in _ACTIVE
        or job["lease_expires_at"] is None
        or request.occurred_at < job["lease_expires_at"]
    ):
        raise JobStateConflict
    statuses, interrupted = _recover_runs(
        connection, request.job_id, request.occurred_at
    )
    target, code, summary = _outcome(
        job["status"] == "CANCEL_REQUESTED", interrupted, statuses
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
    connection: Connection, job_id: str, now: datetime
) -> tuple[list[str], bool]:
    rows = connection.execute(
        "SELECT r.*,d.run_id AS result_run_id FROM evaluation_runs r "
        "LEFT JOIN deterministic_results d ON d.run_id=r.run_id "
        "WHERE r.job_id=%s ORDER BY r.run_id FOR UPDATE OF r",
        (job_id,),
    ).fetchall()
    if not rows:
        raise JobUnavailable
    statuses, interrupted = [], False
    for row in rows:
        has_result = row["result_run_id"] is not None
        if (row["status"] == "COMPLETED") != has_result:
            raise JobUnavailable
        if row["status"] in _TERMINAL:
            statuses.append(row["status"])
            continue
        target = "CANCELED" if row["status"] == "PENDING" else "FAILED"
        code = None if target == "CANCELED" else "INFRASTRUCTURE_INTERRUPTED"
        summary = (
            None
            if code is None
            else f"运行在 {row['stage'] or row['status']} 阶段中断。"
        )
        interrupted = interrupted or code is not None
        connection.execute(
            "UPDATE evaluation_runs SET status=%s,stage=%s,row_version=row_version+1,"
            "failure_code=%s,failure_summary=%s,started_at=CASE WHEN %s='FAILED' "
            "THEN COALESCE(started_at,%s) ELSE started_at END,finished_at=%s "
            "WHERE run_id=%s",
            (
                target,
                "canceled" if target == "CANCELED" else "interrupted",
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


def _outcome(
    canceling: bool, interrupted: bool, statuses: list[str]
) -> tuple[str, str | None, str | None]:
    completed = statuses.count("COMPLETED")
    if canceling:
        return "CANCELED", None, None
    if interrupted:
        target = "COMPLETED_WITH_ERRORS" if completed else "FAILED"
        return target, "INFRASTRUCTURE_INTERRUPTED", "执行租约过期，批次已安全收束。"
    if completed == len(statuses):
        return "COMPLETED", None, None
    code = "BATCH_PARTIAL_FAILURE" if completed else "BATCH_FAILED"
    target = "COMPLETED_WITH_ERRORS" if completed else "FAILED"
    return target, code, "批次已按现有终态证据完成收束。"


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
