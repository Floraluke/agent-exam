from datetime import datetime
from typing import Any

import psycopg

from eval_platform.adapters.persistence.jobs.execution.common import (
    current,
    event,
    expiry,
    validate_worker,
)
from eval_platform.domain.jobs.execution import JobLease

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
    job = connection.execute(
        "SELECT job_id,row_version,limit_snapshot,trial_count "
        "FROM evaluation_jobs WHERE status='QUEUED' "
        "ORDER BY created_at,job_id FOR UPDATE SKIP LOCKED LIMIT 1"
    ).fetchone()
    if job is None:
        return None
    run = connection.execute(
        "SELECT run_id,row_version FROM evaluation_runs WHERE job_id=%s "
        "AND status='PENDING' ORDER BY task_id,agent_configuration_id,run_id "
        "FOR UPDATE SKIP LOCKED LIMIT 1",
        (job["job_id"],),
    ).fetchone()
    if run is None:
        return None
    expires = expiry(job["limit_snapshot"], now, job["trial_count"])
    job_version, run_version = job["row_version"] + 1, run["row_version"] + 1
    connection.execute(
        "UPDATE evaluation_jobs SET status='PREPARING',row_version=%s,"
        "claimed_by=%s,claimed_at=%s,heartbeat_at=%s,lease_expires_at=%s,"
        "started_at=%s WHERE job_id=%s",
        (job_version, worker, now, now, expires, now, job["job_id"]),
    )
    connection.execute(
        "UPDATE evaluation_runs SET status='PREPARING',stage='preparing',"
        "row_version=%s,started_at=%s WHERE run_id=%s",
        (run_version, now, run["run_id"]),
    )
    event(
        connection,
        "job",
        job["job_id"],
        "QUEUED",
        "PREPARING",
        "WORKER_CLAIMED",
        worker,
        now,
    )
    event(
        connection,
        "run",
        run["run_id"],
        "PENDING",
        "PREPARING",
        "WORKER_CLAIMED",
        worker,
        now,
    )
    return JobLease(
        str(job["job_id"]),
        str(run["run_id"]),
        worker,
        job_version,
        run_version,
        expires,
    )


def start_execution(connection: Connection, lease: JobLease, now: datetime) -> JobLease:
    job = current(connection, lease, now, "PREPARING", "PREPARING")
    expires = expiry(job["limit_snapshot"], now, job["trial_count"])
    job_version = lease.job_version + 1
    connection.execute(
        "UPDATE evaluation_jobs SET status='EXECUTING',row_version=%s,"
        "heartbeat_at=%s,lease_expires_at=%s WHERE job_id=%s",
        (job_version, now, expires, lease.job_id),
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
    return JobLease(
        lease.job_id,
        lease.run_id,
        lease.worker_id,
        job_version,
        lease.run_version,
        expires,
    )
