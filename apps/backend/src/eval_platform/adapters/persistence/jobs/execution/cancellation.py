"""Worker-side cooperative stop after a trusted cancellation request."""

from datetime import datetime
from typing import Any

import psycopg

from eval_platform.adapters.persistence.jobs.execution.common import event, expiry
from eval_platform.domain.jobs.execution import JobLease, JobLeaseConflict, TrialStart

Connection = psycopg.Connection[Any]


def cancel_unstarted(
    connection: Connection,
    rows: list[dict[str, Any]],
    now: datetime,
    worker_id: str | None = None,
) -> None:
    for row in rows:
        if row["status"] not in {"PENDING", "PREPARING"}:
            continue
        connection.execute(
            "UPDATE evaluation_runs SET status='CANCELED',stage='canceled',"
            "row_version=row_version+1,finished_at=%s WHERE run_id=%s",
            (now, row["run_id"]),
        )
        event(
            connection,
            "run",
            row["run_id"],
            row["status"],
            "CANCELED",
            "JOB_CANCELED",
            worker_id,
            now,
        )


def stop_unstarted(
    connection: Connection,
    lease: JobLease,
    now: datetime,
    job: dict[str, Any],
) -> TrialStart:
    rows = connection.execute(
        "SELECT run_id,status,row_version FROM evaluation_runs WHERE job_id=%s "
        "AND status IN ('PENDING','PREPARING') ORDER BY run_id FOR UPDATE",
        (lease.job_id,),
    ).fetchall()
    cancel_unstarted(connection, rows, now, lease.worker_id)
    anchor = connection.execute(
        "SELECT row_version FROM evaluation_runs WHERE run_id=%s",
        (lease.run_id,),
    ).fetchone()
    if anchor is None:
        raise JobLeaseConflict
    expires = expiry(job["limit_snapshot"], now, job["trial_count"])
    job_version = job["row_version"] + 1
    connection.execute(
        "UPDATE evaluation_jobs SET row_version=%s,heartbeat_at=%s,"
        "lease_expires_at=%s WHERE job_id=%s",
        (job_version, now, expires, lease.job_id),
    )
    return TrialStart(
        JobLease(
            lease.job_id,
            lease.run_id,
            lease.worker_id,
            job_version,
            anchor["row_version"],
            expires,
        ),
        False,
    )
