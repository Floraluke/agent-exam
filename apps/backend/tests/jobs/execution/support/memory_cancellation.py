"""Cooperative cancellation transition for the executable memory adapter."""

from dataclasses import replace

from eval_platform.domain.jobs.execution import TrialStart
from jobs.execution.support.memory_state import expiry
from jobs.execution.support.memory_state import lease as make_lease
from jobs.support.cancellation import cancel_runs


def stop_unstarted(repository, lease, now, job):
    job = replace(
        job,
        runs=cancel_runs(job.runs, now, lease.worker_id),
        row_version=job.row_version + 1,
        heartbeat_at=now,
        lease_expires_at=expiry(job, now),
    )
    anchor = next(run for run in job.runs if run.run_id == lease.run_id)
    repository.records[job.job_id] = job
    return TrialStart(make_lease(job, anchor), False)
