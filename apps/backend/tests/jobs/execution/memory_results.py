from dataclasses import replace
from uuid import uuid4

from eval_platform.domain.jobs.execution import (
    JobLeaseConflict,
    JobReport,
    ProcessMetrics,
    RunReport,
)
from eval_platform.domain.jobs.models import StateEvent
from eval_platform.domain.result import ResourceSummary, UsageSummary


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
                _event(
                    run,
                    "COMPLETED",
                    "DETERMINISTIC_RESULT_STORED",
                    completion.occurred_at,
                    lease.worker_id,
                ),
            ),
        )
        finalizing = _event(
            job,
            "FINALIZING",
            "FINALIZATION_STARTED",
            completion.occurred_at,
            lease.worker_id,
        )
        completed = StateEvent(
            str(uuid4()),
            finalizing.sequence + 1,
            "FINALIZING",
            "COMPLETED",
            "JOB_COMPLETED",
            completion.occurred_at,
            worker_id=lease.worker_id,
        )
        job = replace(
            job,
            status="COMPLETED",
            runs=(run,),
            row_version=job.row_version + 2,
            heartbeat_at=completion.occurred_at,
            finished_at=completion.occurred_at,
            state_events=job.state_events + (finalizing, completed),
        )
        repository.records[job.job_id] = job
        report = RunReport(
            job.created_by,
            run,
            result,
            completion.process_metrics,
            completion.artifacts,
        )
        repository.reports[run.run_id] = report
        return report


def fail(repository, lease, code, summary, now):
    with repository.lock:
        job, run = repository._current(lease, now, None, None)
        run = replace(
            run,
            status="FAILED",
            stage="failed",
            row_version=run.row_version + 1,
            failure_code=code,
            failure_summary=summary,
            finished_at=now,
            state_events=run.state_events
            + (_event(run, "FAILED", code, now, lease.worker_id),),
        )
        job = replace(
            job,
            status="FAILED",
            runs=(run,),
            row_version=job.row_version + 1,
            failure_code=code,
            failure_summary=summary,
            heartbeat_at=now,
            finished_at=now,
            state_events=job.state_events
            + (_event(job, "FAILED", code, now, lease.worker_id),),
        )
        repository.records[job.job_id] = job
        metrics = ProcessMetrics(UsageSummary(), ResourceSummary())
        report = RunReport(job.created_by, run, None, metrics, ())
        repository.reports[run.run_id] = report
        return report


def get_run_report(repository, run_id):
    try:
        return repository.reports[run_id]
    except KeyError:
        raise JobLeaseConflict from None


def get_job_report(repository, job_id):
    job = repository.get(job_id)
    reports = tuple(
        repository.reports[run.run_id]
        for run in job.runs
        if run.run_id in repository.reports
    )
    return JobReport(job.created_by, job, reports)


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
