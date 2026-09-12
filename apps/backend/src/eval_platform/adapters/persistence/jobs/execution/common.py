import re
from datetime import datetime, timedelta
from typing import Any
from uuid import uuid4

import psycopg

from eval_platform.domain.jobs.execution import JobLease, JobLeaseConflict
from eval_platform.domain.jobs.policy import worker_lease_timeout_sec

Connection = psycopg.Connection[Any]


def current(
    connection: Connection,
    lease: JobLease,
    now: datetime,
    job_status: str | None = None,
    run_status: str | None = None,
) -> dict[str, Any]:
    row = connection.execute(
        "SELECT j.*,r.status AS run_status,r.row_version AS run_version "
        "FROM evaluation_jobs j JOIN evaluation_runs r ON r.job_id=j.job_id "
        "WHERE j.job_id=%s AND r.run_id=%s FOR UPDATE OF j,r",
        (lease.job_id, lease.run_id),
    ).fetchone()
    if (
        row is None
        or row["claimed_by"] != lease.worker_id
        or row["row_version"] != lease.job_version
        or row["run_version"] != lease.run_version
        or row["lease_expires_at"] != lease.lease_expires_at
        or now >= lease.lease_expires_at
        or (job_status is not None and row["status"] != job_status)
        or (run_status is not None and row["run_status"] != run_status)
    ):
        raise JobLeaseConflict
    return dict(row)


def event(
    connection: Connection,
    scope: str,
    identity: object,
    before: str,
    after: str,
    reason: str,
    worker: str,
    now: datetime,
) -> None:
    table, field = {
        "job": ("job_state_events", "job_id"),
        "run": ("run_state_events", "run_id"),
    }[scope]
    row = connection.execute(
        f"SELECT COALESCE(MAX(sequence),0)+1 AS value FROM {table} WHERE {field}=%s",
        (identity,),
    ).fetchone()
    if row is None:
        raise JobLeaseConflict
    sequence = row["value"]
    connection.execute(
        f"INSERT INTO {table} (event_id,{field},sequence,from_status,to_status,"
        "reason_code,worker_id,occurred_at) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
        (str(uuid4()), identity, sequence, before, after, reason, worker, now),
    )


def expiry(snapshot: object, now: datetime, trial_count: int = 1) -> datetime:
    if not isinstance(snapshot, dict):
        raise JobLeaseConflict
    agent = snapshot.get("agent_wall_timeout_sec")
    evaluator = snapshot.get("evaluator_wall_timeout_sec")
    if (
        type(agent) is not int
        or type(evaluator) is not int
        or min(agent, evaluator, trial_count) <= 0
    ):
        raise JobLeaseConflict
    seconds = worker_lease_timeout_sec(agent, evaluator, trial_count)
    return now + timedelta(seconds=seconds)


def validate_worker(value: str) -> None:
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,63}", value):
        raise ValueError("invalid worker identity")
