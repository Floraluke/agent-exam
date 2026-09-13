from datetime import datetime
from typing import Any

import psycopg

from eval_platform.adapters.persistence.jobs.execution.cancellation import (
    stop_unstarted,
)
from eval_platform.adapters.persistence.jobs.execution.common import (
    current,
    event,
    expiry,
)
from eval_platform.domain.jobs.execution import JobLease, JobLeaseConflict, TrialStart
from eval_platform.domain.result import ExecutionTrialResult

Connection = psycopg.Connection[Any]


def start_run(
    connection: Connection, lease: JobLease, run_id: str, now: datetime
) -> TrialStart:
    job = current(connection, lease, now, "EXECUTING")
    if job["status"] == "CANCEL_REQUESTED":
        return stop_unstarted(connection, lease, now, job)
    run = _next_pending(connection, lease.job_id)
    if (
        run is None
        or str(run["run_id"]) != run_id
        or run["status"] not in {"PENDING", "PREPARING"}
    ):
        raise JobLeaseConflict
    before = run["status"]
    if before == "PENDING":
        event(
            connection,
            "run",
            run_id,
            "PENDING",
            "PREPARING",
            "TRIAL_PREPARING",
            lease.worker_id,
            now,
        )
        before = "PREPARING"
    event(
        connection,
        "run",
        run_id,
        before,
        "RUNNING_AGENT",
        "TRIAL_STARTED",
        lease.worker_id,
        now,
    )
    run_version = run["row_version"] + 1
    connection.execute(
        "UPDATE evaluation_runs SET status='RUNNING_AGENT',stage='running_agent',"
        "row_version=%s,started_at=COALESCE(started_at,%s) WHERE run_id=%s",
        (run_version, now, run_id),
    )
    return TrialStart(
        _touch_job(connection, lease, job, run_id, run_version, now), True
    )


def finish_run_execution(
    connection: Connection, lease: JobLease, run_id: str, now: datetime
) -> JobLease:
    job = current(connection, lease, now, "EXECUTING", "RUNNING_AGENT")
    row = connection.execute(
        "SELECT stage FROM evaluation_runs WHERE run_id=%s FOR UPDATE", (run_id,)
    ).fetchone()
    if run_id != lease.run_id or row is None or row["stage"] != "running_agent":
        raise JobLeaseConflict
    run_version = lease.run_version + 1
    connection.execute(
        "UPDATE evaluation_runs SET stage='collecting',row_version=%s WHERE run_id=%s",
        (run_version, run_id),
    )
    event(
        connection,
        "run",
        run_id,
        "RUNNING_AGENT",
        "RUNNING_AGENT",
        "TRIAL_FINISHED",
        lease.worker_id,
        now,
    )
    return _touch_job(connection, lease, job, run_id, run_version, now)


def start_verifying(
    connection: Connection,
    lease: JobLease,
    trial: ExecutionTrialResult,
    now: datetime,
) -> JobLease:
    job = current(connection, lease, now, "EXECUTING")
    run = _next_run(connection, lease.job_id)
    if (
        run is None
        or trial.run_id != str(run["run_id"])
        or not trial.backend_job_ref
        or not trial.backend_trial_ref
        or run["status"] != "RUNNING_AGENT"
        or run["stage"] != "collecting"
    ):
        raise JobLeaseConflict
    run_version = run["row_version"] + 1
    connection.execute(
        "UPDATE evaluation_runs SET status='VERIFYING',stage='verifying',"
        "row_version=%s,backend_job_ref=%s,backend_trial_ref=%s WHERE run_id=%s",
        (run_version, trial.backend_job_ref, trial.backend_trial_ref, trial.run_id),
    )
    event(
        connection,
        "run",
        trial.run_id,
        "RUNNING_AGENT",
        "VERIFYING",
        "PATCH_READY",
        lease.worker_id,
        now,
    )
    return _touch_job(connection, lease, job, trial.run_id, run_version, now)


def _next_run(connection: Connection, job_id: str) -> dict[str, Any] | None:
    return connection.execute(
        "SELECT run_id,status,stage,row_version FROM evaluation_runs WHERE job_id=%s "
        "AND status NOT IN ('COMPLETED','FAILED','CANCELED') "
        "ORDER BY task_id,agent_configuration_id,run_id FOR UPDATE LIMIT 1",
        (job_id,),
    ).fetchone()


def _next_pending(connection: Connection, job_id: str) -> dict[str, Any] | None:
    return connection.execute(
        "SELECT run_id,status,row_version FROM evaluation_runs WHERE job_id=%s "
        "AND status IN ('PENDING','PREPARING') "
        "ORDER BY task_id,agent_configuration_id,run_id FOR UPDATE LIMIT 1",
        (job_id,),
    ).fetchone()


def _touch_job(
    connection: Connection,
    lease: JobLease,
    job: dict[str, Any],
    run_id: str,
    run_version: int,
    now: datetime,
) -> JobLease:
    expires = expiry(job["limit_snapshot"], now, job["trial_count"])
    version = job["row_version"] + 1
    connection.execute(
        "UPDATE evaluation_jobs SET row_version=%s,heartbeat_at=%s,"
        "lease_expires_at=%s WHERE job_id=%s",
        (version, now, expires, lease.job_id),
    )
    return JobLease(
        lease.job_id, run_id, lease.worker_id, version, run_version, expires
    )
