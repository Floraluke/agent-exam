from dataclasses import replace
from datetime import timedelta
from uuid import uuid4

from eval_platform.domain.jobs.execution import JobLease
from eval_platform.domain.jobs.models import StateEvent, run_order_key

_TERMINAL = {"COMPLETED", "FAILED", "CANCELED"}


def next_run(job):
    return next(
        (
            run
            for run in sorted(job.runs, key=run_order_key)
            if run.status not in _TERMINAL
        ),
        None,
    )


def next_pending(job):
    return next(
        (
            run
            for run in sorted(job.runs, key=run_order_key)
            if run.status in {"PENDING", "PREPARING"}
        ),
        None,
    )


def touch(job, run, now):
    return replace(
        job,
        runs=replace_run(job.runs, run),
        row_version=job.row_version + 1,
        heartbeat_at=now,
        lease_expires_at=expiry(job, now),
    )


def replace_run(runs, changed):
    return tuple(changed if run.run_id == changed.run_id else run for run in runs)


def expiry(job, now):
    limits = job.limit_snapshot
    seconds = (
        limits.agent_wall_timeout_sec + limits.evaluator_wall_timeout_sec
    ) * job.trial_count + 300
    return now + timedelta(seconds=seconds)


def lease(job, run):
    assert job.claimed_by is not None and job.lease_expires_at is not None
    return JobLease(
        job.job_id,
        run.run_id,
        job.claimed_by,
        job.row_version,
        run.row_version,
        job.lease_expires_at,
    )


def event(record, target, reason, now, worker):
    return StateEvent(
        str(uuid4()),
        len(record.state_events) + 1,
        record.status,
        target,
        reason,
        now,
        worker_id=worker,
    )


def transition(run, target, reason, now, worker):
    return replace(
        run,
        status=target,
        row_version=run.row_version + 1,
        state_events=run.state_events + (event(run, target, reason, now, worker),),
    )
