from dataclasses import replace

from eval_platform.domain.jobs.execution import (
    ProcessMetrics,
    RunReport,
)
from eval_platform.domain.result import ResourceSummary, UsageSummary
from jobs.execution.support.memory_cancellation import stop_unstarted
from jobs.execution.support.memory_state import (
    event,
    expiry,
    next_run,
    touch,
)
from jobs.execution.support.memory_state import (
    lease as make_lease,
)


def complete(repository, lease, completion):
    with repository.lock:
        job, run = repository._current(
            lease, completion.occurred_at, "EXECUTING", "VERIFYING"
        )
        result = completion.result
        run = replace(
            run,
            status="COMPLETED",
            stage="completed",
            row_version=run.row_version + 1,
            resolved_summary=result.resolved,
            finished_at=completion.occurred_at,
            state_events=run.state_events
            + (
                event(
                    run,
                    "COMPLETED",
                    "DETERMINISTIC_RESULT_STORED",
                    completion.occurred_at,
                    lease.worker_id,
                ),
            ),
        )
        job = touch(job, run, completion.occurred_at)
        repository.records[job.job_id] = job
        repository.reports[run.run_id] = RunReport(
            job.created_by,
            job.result_scope,
            run,
            result,
            completion.process_metrics,
            completion.artifacts,
            completion.warnings,
        )
        return make_lease(job, run)


def fail(repository, lease, run_id, code, summary, now, trial=None):
    with repository.lock:
        job, _anchor = repository._current(lease, now, "EXECUTING", None)
        run = next_run(job)
        if (
            run is None
            or run.run_id != run_id
            or run.status not in {"PENDING", "PREPARING", "RUNNING_AGENT", "VERIFYING"}
            or not code
            or not summary
        ):
            from eval_platform.domain.jobs.execution import JobLeaseConflict

            raise JobLeaseConflict
        if trial is not None and trial.run_id != run_id:
            from eval_platform.domain.jobs.execution import JobLeaseConflict

            raise JobLeaseConflict
        if job.status == "CANCEL_REQUESTED" and run.status in {
            "PENDING",
            "PREPARING",
        }:
            return stop_unstarted(repository, lease, now, job).lease
        run = replace(
            run,
            status="FAILED",
            stage="failed",
            row_version=run.row_version + 1,
            backend_job_ref=(trial.backend_job_ref if trial else run.backend_job_ref),
            backend_trial_ref=(
                trial.backend_trial_ref if trial else run.backend_trial_ref
            ),
            failure_code=code,
            failure_summary=summary,
            started_at=run.started_at or now,
            finished_at=now,
            state_events=run.state_events
            + (event(run, "FAILED", code, now, lease.worker_id),),
        )
        job = touch(job, run, now)
        repository.records[job.job_id] = job
        repository.reports[run.run_id] = RunReport(
            job.created_by,
            job.result_scope,
            run,
            None,
            ProcessMetrics(UsageSummary(), ResourceSummary()),
            (),
        )
        return make_lease(job, run)


def start_finalizing(repository, lease, now):
    with repository.lock:
        job, anchor = repository._current(lease, now, "EXECUTING", None)
        if next_run(job) is not None:
            from eval_platform.domain.jobs.execution import JobLeaseConflict

            raise JobLeaseConflict
        job = replace(
            job,
            status="FINALIZING",
            row_version=job.row_version + 1,
            heartbeat_at=now,
            lease_expires_at=expiry(job, now),
            state_events=job.state_events
            + (event(job, "FINALIZING", "FINALIZATION_STARTED", now, lease.worker_id),),
        )
        repository.records[job.job_id] = job
        return make_lease(job, anchor)


def finish(repository, lease, now, failure_code=None):
    with repository.lock:
        job, _anchor = repository._current(lease, now, "FINALIZING", None)
        failed = sum(run.status != "COMPLETED" for run in job.runs)
        completed = sum(run.status == "COMPLETED" for run in job.runs)
        canceling = job.cancel_requested_by is not None
        code = None if canceling else failure_code
        if not canceling and code is None and failed:
            code = "BATCH_PARTIAL_FAILURE" if completed else "BATCH_FAILED"
        target = (
            "CANCELED"
            if canceling
            else "COMPLETED"
            if code is None
            else "COMPLETED_WITH_ERRORS"
            if completed
            else "FAILED"
        )
        job = replace(
            job,
            status=target,
            row_version=job.row_version + 1,
            failure_code=code,
            failure_summary=(
                None
                if code is None
                else "批次包含未形成可信结果的运行。"
                if failed
                else "批次生命周期信号不完整或不一致。"
            ),
            finished_at=now,
            state_events=job.state_events
            + (
                event(
                    job,
                    target,
                    "JOB_CANCELED" if canceling else code or "JOB_COMPLETED",
                    now,
                    lease.worker_id,
                ),
            ),
        )
        repository.records[job.job_id] = job
