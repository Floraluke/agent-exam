from datetime import datetime
from typing import Any

import psycopg

from eval_platform.adapters.persistence.jobs.execution.common import (
    current,
    event,
    expiry,
)
from eval_platform.domain.jobs.execution import JobLease, JobLeaseConflict
from eval_platform.domain.jobs.models import JobUnavailable

Connection = psycopg.Connection[Any]


def start(connection: Connection, lease: JobLease, now: datetime) -> JobLease:
    job = current(connection, lease, now, "EXECUTING")
    if _has_open_run(connection, lease.job_id):
        raise JobLeaseConflict
    expires = expiry(job["limit_snapshot"], now, job["trial_count"])
    version = lease.job_version + 1
    connection.execute(
        "UPDATE evaluation_jobs SET status='FINALIZING',row_version=%s,"
        "heartbeat_at=%s,lease_expires_at=%s WHERE job_id=%s",
        (version, now, expires, lease.job_id),
    )
    event(
        connection,
        "job",
        lease.job_id,
        "EXECUTING",
        "FINALIZING",
        "FINALIZATION_STARTED",
        lease.worker_id,
        now,
    )
    return JobLease(
        lease.job_id,
        lease.run_id,
        lease.worker_id,
        version,
        lease.run_version,
        expires,
    )


def finish(
    connection: Connection,
    lease: JobLease,
    now: datetime,
    failure_code: str | None = None,
) -> None:
    current(connection, lease, now, "FINALIZING")
    counts = connection.execute(
        "SELECT count(*) FILTER (WHERE status='COMPLETED') AS completed,"
        "count(*) FILTER (WHERE status<>'COMPLETED') AS failed "
        "FROM evaluation_runs WHERE job_id=%s",
        (lease.job_id,),
    ).fetchone()
    if counts is None or (
        failure_code is not None and not 1 <= len(failure_code) <= 128
    ):
        raise JobUnavailable
    completed, failed = counts["completed"], counts["failed"]
    code = failure_code
    if code is None and failed:
        code = "BATCH_PARTIAL_FAILURE" if completed else "BATCH_FAILED"
    target = _target_status(code, completed)
    summary = None
    if code is not None:
        summary = (
            "批次包含未形成可信结果的运行。"
            if failed
            else "批次生命周期信号不完整或不一致。"
        )
    connection.execute(
        "UPDATE evaluation_jobs SET status=%s,row_version=row_version+1,"
        "failure_code=%s,failure_summary=%s,finished_at=%s WHERE job_id=%s",
        (target, code, summary, now, lease.job_id),
    )
    event(
        connection,
        "job",
        lease.job_id,
        "FINALIZING",
        target,
        code or "JOB_COMPLETED",
        lease.worker_id,
        now,
    )


def _target_status(code: str | None, completed: int) -> str:
    if code is None:
        return "COMPLETED"
    return "COMPLETED_WITH_ERRORS" if completed else "FAILED"


def _has_open_run(connection: Connection, job_id: str) -> bool:
    row = connection.execute(
        "SELECT EXISTS (SELECT 1 FROM evaluation_runs WHERE job_id=%s "
        "AND status NOT IN ('COMPLETED','FAILED','CANCELED')) AS present",
        (job_id,),
    ).fetchone()
    return row is None or bool(row["present"])
