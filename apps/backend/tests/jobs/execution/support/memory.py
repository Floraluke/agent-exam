"""Thread-safe executable JobRepository fake for execution tests."""

import re
from dataclasses import replace

from eval_platform.domain.jobs.execution import ClaimedJob, JobLeaseConflict, TrialStart
from eval_platform.domain.jobs.models import run_order_key
from jobs.execution.support import memory_reports, memory_results
from jobs.execution.support.memory_cancellation import stop_unstarted
from jobs.execution.support.memory_state import (
    event,
    expiry,
    next_pending,
    next_run,
    replace_run,
    touch,
    transition,
)
from jobs.execution.support.memory_state import (
    lease as make_lease,
)
from jobs.execution.support.retention import MemoryRetention
from jobs.memory import MemoryJobs

_ACTIVE = {"PREPARING", "EXECUTING", "FINALIZING"}


class ExecutableMemoryJobs(MemoryJobs, MemoryRetention):
    def __init__(self, *records):
        super().__init__()
        self.records.update((record.job_id, record) for record in records)
        self.reports = {}
        self.deletion_intents = {}

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
                    if record.status == "QUEUED"
                ),
                key=lambda item: (item.created_at, item.job_id),
            )
            if not candidates:
                return None
            job = candidates[0]
            first = min(job.runs, key=run_order_key)
            first = transition(first, "PREPARING", "WORKER_CLAIMED", now, worker_id)
            first = replace(first, stage="preparing", started_at=now)
            expires = expiry(job, now)
            job = replace(
                job,
                status="PREPARING",
                runs=replace_run(job.runs, first),
                row_version=job.row_version + 1,
                claimed_by=worker_id,
                claimed_at=now,
                heartbeat_at=now,
                lease_expires_at=expires,
                started_at=now,
                state_events=job.state_events
                + (event(job, "PREPARING", "WORKER_CLAIMED", now, worker_id),),
            )
            self.records[job.job_id] = job
            return ClaimedJob(job, make_lease(job, first))

    def start_execution(self, lease, now):
        with self.lock:
            job, anchor = self._current(lease, now, "PREPARING", "PREPARING")
            job = replace(
                job,
                status="EXECUTING",
                row_version=job.row_version + 1,
                heartbeat_at=now,
                lease_expires_at=expiry(job, now),
                state_events=job.state_events
                + (event(job, "EXECUTING", "EXECUTION_STARTED", now, lease.worker_id),),
            )
            self.records[job.job_id] = job
            return make_lease(job, anchor)

    def start_run(self, lease, run_id, now):
        with self.lock:
            current = self.records[lease.job_id]
            if current.status == "CANCEL_REQUESTED":
                job, _anchor = self._current(lease, now, "EXECUTING", None)
                return stop_unstarted(self, lease, now, job)
            job, _anchor = self._current(lease, now, "EXECUTING", None)
            run = next_pending(job)
            if (
                run is None
                or run.run_id != run_id
                or run.status not in {"PENDING", "PREPARING"}
            ):
                raise JobLeaseConflict
            if run.status == "PENDING":
                run = transition(
                    run, "PREPARING", "TRIAL_PREPARING", now, lease.worker_id
                )
            run = transition(
                run, "RUNNING_AGENT", "TRIAL_STARTED", now, lease.worker_id
            )
            run = replace(run, stage="running_agent", started_at=run.started_at or now)
            job = touch(job, run, now)
            self.records[job.job_id] = job
            return TrialStart(make_lease(job, run), True)

    def finish_run_execution(self, lease, run_id, now):
        with self.lock:
            job, run = self._current(lease, now, "EXECUTING", "RUNNING_AGENT")
            if run.run_id != run_id or run.stage != "running_agent":
                raise JobLeaseConflict
            run = transition(
                run, "RUNNING_AGENT", "TRIAL_FINISHED", now, lease.worker_id
            )
            run = replace(run, stage="collecting")
            job = touch(job, run, now)
            self.records[job.job_id] = job
            return make_lease(job, run)

    def start_verifying(self, lease, trial, now):
        with self.lock:
            job, _anchor = self._current(lease, now, "EXECUTING", None)
            run = next_run(job)
            if (
                run is None
                or trial.run_id != run.run_id
                or not trial.backend_job_ref
                or not trial.backend_trial_ref
                or run.status != "RUNNING_AGENT"
                or run.stage != "collecting"
            ):
                raise JobLeaseConflict
            run = transition(run, "VERIFYING", "PATCH_READY", now, lease.worker_id)
            run = replace(
                run,
                stage="verifying",
                backend_job_ref=trial.backend_job_ref,
                backend_trial_ref=trial.backend_trial_ref,
            )
            job = touch(job, run, now)
            self.records[job.job_id] = job
            return make_lease(job, run)

    def complete(self, lease, completion):
        return memory_results.complete(self, lease, completion)

    def fail(self, lease, run_id, code, summary, now, trial=None):
        return memory_results.fail(self, lease, run_id, code, summary, now, trial)

    def start_finalizing(self, lease, now):
        return memory_results.start_finalizing(self, lease, now)

    def finish(self, lease, now, failure_code=None):
        return memory_results.finish(self, lease, now, failure_code)

    def get_run_report(self, run_id):
        return memory_reports.get_run_report(self, run_id)

    def get_job_report(self, job_id):
        return memory_reports.get_job_report(self, job_id)

    def get_artifact_report(self, artifact_id):
        return memory_reports.get_artifact_report(self, artifact_id)

    def _current(self, lease, now, job_status, run_status):
        job = self.records[lease.job_id]
        run = next(item for item in job.runs if item.run_id == lease.run_id)
        cancellation_continuation = (
            job_status == "EXECUTING"
            and job.status == "CANCEL_REQUESTED"
            and job.cancel_requested_by is not None
            and job.cancel_requested_at is not None
        )
        version_matches = job.row_version == lease.job_version or (
            cancellation_continuation and job.row_version == lease.job_version + 1
        )
        if (
            job.claimed_by != lease.worker_id
            or not version_matches
            or run.row_version != lease.run_version
            or job.lease_expires_at != lease.lease_expires_at
            or now >= lease.lease_expires_at
            or (
                job_status is not None
                and job.status != job_status
                and not cancellation_continuation
            )
            or (run_status is not None and run.status != run_status)
        ):
            raise JobLeaseConflict
        return job, run
