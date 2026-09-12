"""Thread-safe executable JobRepository fake for task-06 tests."""

import re
from dataclasses import replace
from datetime import timedelta
from uuid import uuid4

from eval_platform.domain.jobs.execution import ClaimedJob, JobLease, JobLeaseConflict
from eval_platform.domain.jobs.models import StateEvent
from jobs.execution import memory_results
from jobs.memory import MemoryJobs

_ACTIVE = {"PREPARING", "EXECUTING", "FINALIZING"}


class ExecutableMemoryJobs(MemoryJobs):
    def __init__(self, *records):
        super().__init__()
        self.records.update((record.job_id, record) for record in records)
        self.reports = {}

    def claim(self, worker_id, now):
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,63}", worker_id):
            raise ValueError("invalid worker identity")
        with self.lock:
            if any(record.status in _ACTIVE for record in self.records.values()):
                return None
            candidates = sorted(
                (
                    record
                    for record in self.records.values()
                    if record.status == "QUEUED" and record.trial_count == 1
                ),
                key=lambda item: (item.created_at, item.job_id),
            )
            if not candidates:
                return None
            job = candidates[0]
            run = replace(
                job.runs[0],
                status="PREPARING",
                stage="preparing",
                row_version=job.runs[0].row_version + 1,
                started_at=now,
                state_events=job.runs[0].state_events
                + (_event(job.runs[0], "PREPARING", "WORKER_CLAIMED", now, worker_id),),
            )
            expires = _expiry(job, now)
            job = replace(
                job,
                status="PREPARING",
                runs=(run,),
                row_version=job.row_version + 1,
                claimed_by=worker_id,
                claimed_at=now,
                heartbeat_at=now,
                lease_expires_at=expires,
                started_at=now,
                state_events=job.state_events
                + (_event(job, "PREPARING", "WORKER_CLAIMED", now, worker_id),),
            )
            self.records[job.job_id] = job
            return ClaimedJob(job, _lease(job, run))

    def start_execution(self, lease, now):
        with self.lock:
            job, run = self._current(lease, now, "PREPARING", "PREPARING")
            expires = _expiry(job, now)
            run = replace(
                run,
                status="RUNNING_AGENT",
                stage="running_agent",
                row_version=run.row_version + 1,
                state_events=run.state_events
                + (
                    _event(
                        run, "RUNNING_AGENT", "EXECUTION_STARTED", now, lease.worker_id
                    ),
                ),
            )
            job = replace(
                job,
                status="EXECUTING",
                runs=(run,),
                row_version=job.row_version + 1,
                heartbeat_at=now,
                lease_expires_at=expires,
                state_events=job.state_events
                + (
                    _event(job, "EXECUTING", "EXECUTION_STARTED", now, lease.worker_id),
                ),
            )
            self.records[job.job_id] = job
            return _lease(job, run)

    def start_verifying(self, lease, trial, now):
        with self.lock:
            job, run = self._current(lease, now, "EXECUTING", "RUNNING_AGENT")
            if trial.run_id != run.run_id:
                raise JobLeaseConflict
            expires = _expiry(job, now)
            run = replace(
                run,
                status="VERIFYING",
                stage="verifying",
                row_version=run.row_version + 1,
                backend_job_ref=trial.backend_job_ref,
                backend_trial_ref=trial.backend_trial_ref,
                state_events=run.state_events
                + (_event(run, "VERIFYING", "PATCH_READY", now, lease.worker_id),),
            )
            job = replace(
                job,
                runs=(run,),
                row_version=job.row_version + 1,
                heartbeat_at=now,
                lease_expires_at=expires,
            )
            self.records[job.job_id] = job
            return _lease(job, run)

    def complete(self, lease, completion):
        return memory_results.complete(self, lease, completion)

    def fail(self, lease, code, summary, now):
        return memory_results.fail(self, lease, code, summary, now)

    def get_run_report(self, run_id):
        return memory_results.get_run_report(self, run_id)

    def get_job_report(self, job_id):
        return memory_results.get_job_report(self, job_id)

    def _current(self, lease, now, job_status, run_status):
        job = self.records[lease.job_id]
        run = job.runs[0]
        if (
            job.claimed_by != lease.worker_id
            or job.row_version != lease.job_version
            or run.row_version != lease.run_version
            or job.lease_expires_at != lease.lease_expires_at
            or now >= lease.lease_expires_at
            or (job_status is not None and job.status != job_status)
            or (run_status is not None and run.status != run_status)
        ):
            raise JobLeaseConflict
        return job, run


def _expiry(job, now):
    limits = job.limit_snapshot
    seconds = limits.agent_wall_timeout_sec + limits.evaluator_wall_timeout_sec + 300
    return now + timedelta(seconds=seconds)


def _lease(job, run):
    assert job.claimed_by is not None and job.lease_expires_at is not None
    return JobLease(
        job.job_id,
        run.run_id,
        job.claimed_by,
        job.row_version,
        run.row_version,
        job.lease_expires_at,
    )


def _event(record, target, reason, now, worker):
    return StateEvent(
        str(uuid4()),
        len(record.state_events) + 1,
        record.status,
        target,
        reason,
        now,
        worker_id=worker,
    )
