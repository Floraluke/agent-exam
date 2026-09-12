from datetime import datetime
from typing import Any

import psycopg

from eval_platform.adapters.persistence.jobs.execution.common import (
    current,
    event,
    expiry,
    validate_worker,
)
from eval_platform.domain.jobs.execution import JobLease, JobLeaseConflict
from eval_platform.domain.result import ExecutionTrialResult

Connection = psycopg.Connection[Any]
_CLAIM_LOCK = 9460606


def claim(connection: Connection, worker: str, now: datetime) -> JobLease | None:
    validate_worker(worker)
    connection.execute("SELECT pg_advisory_xact_lock(%s)", (_CLAIM_LOCK,))
    active = connection.execute(
        "SELECT 1 FROM evaluation_jobs WHERE status IN "
        "('PREPARING','EXECUTING','FINALIZING') LIMIT 1"
    ).fetchone()
    if active is not None:
        return None
    row = connection.execute(
        "SELECT j.job_id,j.row_version,j.limit_snapshot,r.run_id,"
        "r.row_version AS run_version FROM evaluation_jobs j "
        "JOIN evaluation_runs r ON r.job_id=j.job_id "
        "WHERE j.status='QUEUED' AND j.trial_count=1 AND r.status='PENDING' "
        "ORDER BY j.created_at,j.job_id FOR UPDATE OF j,r SKIP LOCKED LIMIT 1"
    ).fetchone()
    if row is None:
        return None
    expires = expiry(row["limit_snapshot"], now)
    job_version, run_version = row["row_version"] + 1, row["run_version"] + 1
    connection.execute(
        "UPDATE evaluation_jobs SET status='PREPARING',row_version=%s,"
        "claimed_by=%s,claimed_at=%s,heartbeat_at=%s,lease_expires_at=%s,"
        "started_at=%s WHERE job_id=%s",
        (job_version, worker, now, now, expires, now, row["job_id"]),
    )
    connection.execute(
        "UPDATE evaluation_runs SET status='PREPARING',stage='preparing',"
        "row_version=%s,started_at=%s WHERE run_id=%s",
        (run_version, now, row["run_id"]),
    )
    event(
        connection,
        "job",
        row["job_id"],
        "QUEUED",
        "PREPARING",
        "WORKER_CLAIMED",
        worker,
        now,
    )
    event(
        connection,
        "run",
        row["run_id"],
        "PENDING",
        "PREPARING",
        "WORKER_CLAIMED",
        worker,
        now,
    )
    return JobLease(
        str(row["job_id"]),
        str(row["run_id"]),
        worker,
        job_version,
        run_version,
        expires,
    )


def start_execution(connection: Connection, lease: JobLease, now: datetime) -> JobLease:
    job = current(connection, lease, now, "PREPARING", "PREPARING")
    expires = expiry(job["limit_snapshot"], now)
    job_version, run_version = lease.job_version + 1, lease.run_version + 1
    connection.execute(
        "UPDATE evaluation_jobs SET status='EXECUTING',row_version=%s,"
        "heartbeat_at=%s,lease_expires_at=%s WHERE job_id=%s",
        (job_version, now, expires, lease.job_id),
    )
    connection.execute(
        "UPDATE evaluation_runs SET status='RUNNING_AGENT',stage='running_agent',"
        "row_version=%s WHERE run_id=%s",
        (run_version, lease.run_id),
    )
    event(
        connection,
        "job",
        lease.job_id,
        "PREPARING",
        "EXECUTING",
        "EXECUTION_STARTED",
        lease.worker_id,
        now,
    )
    event(
        connection,
        "run",
        lease.run_id,
        "PREPARING",
        "RUNNING_AGENT",
        "EXECUTION_STARTED",
        lease.worker_id,
        now,
    )
    return JobLease(
        lease.job_id, lease.run_id, lease.worker_id, job_version, run_version, expires
    )


def start_verifying(
    connection: Connection,
    lease: JobLease,
    trial: ExecutionTrialResult,
    now: datetime,
) -> JobLease:
    job = current(connection, lease, now, "EXECUTING", "RUNNING_AGENT")
    if (
        trial.run_id != lease.run_id
        or not trial.backend_job_ref
        or not trial.backend_trial_ref
    ):
        raise JobLeaseConflict
    expires = expiry(job["limit_snapshot"], now)
    job_version, run_version = lease.job_version + 1, lease.run_version + 1
    connection.execute(
        "UPDATE evaluation_jobs SET row_version=%s,heartbeat_at=%s,"
        "lease_expires_at=%s WHERE job_id=%s",
        (job_version, now, expires, lease.job_id),
    )
    connection.execute(
        "UPDATE evaluation_runs SET status='VERIFYING',stage='verifying',"
        "row_version=%s,backend_job_ref=%s,backend_trial_ref=%s WHERE run_id=%s",
        (run_version, trial.backend_job_ref, trial.backend_trial_ref, lease.run_id),
    )
    event(
        connection,
        "run",
        lease.run_id,
        "RUNNING_AGENT",
        "VERIFYING",
        "PATCH_READY",
        lease.worker_id,
        now,
    )
    return JobLease(
        lease.job_id, lease.run_id, lease.worker_id, job_version, run_version, expires
    )
