"""Recovery behavior shared by synthetic JobRepository adapters."""

from dataclasses import replace
from uuid import uuid4

from eval_platform.domain.jobs.decisions import JobStateConflict
from eval_platform.domain.jobs.models import StateEvent
from eval_platform.domain.jobs.policy import (
    RECOVERY_JOB_TERMINAL_STATUSES,
    RECOVERY_RUN_TERMINAL_STATUSES,
    recovery_is_due,
    recovery_job_outcome,
    recovery_run_outcome,
)


def recover(repository, request):
    with repository.lock:
        record = repository.get(request.job_id)
        if record.status in RECOVERY_JOB_TERMINAL_STATUSES and any(
            event.reason_code == "INTERRUPTION_RECOVERED"
            for event in record.state_events
        ):
            return record
        if not recovery_is_due(
            record.status, record.lease_expires_at, request.occurred_at
        ):
            raise JobStateConflict
        runs = tuple(_recover_run(run, request.occurred_at) for run in record.runs)
        interrupted = any(
            before.status not in RECOVERY_RUN_TERMINAL_STATUSES
            and after.status == "FAILED"
            for before, after in zip(record.runs, runs, strict=True)
        )
        target, code, summary = recovery_job_outcome(
            record.cancel_requested_by is not None,
            [run.status for run in runs],
            interrupted,
        )
        event = StateEvent(
            str(uuid4()),
            len(record.state_events) + 1,
            record.status,
            target,
            "INTERRUPTION_RECOVERED",
            request.occurred_at,
            request.actor_user_id,
            "过期执行租约已按持久化证据收束。",
        )
        recovered = replace(
            record,
            status=target,
            row_version=record.row_version + 1,
            runs=runs,
            state_events=record.state_events + (event,),
            failure_code=code,
            failure_summary=summary,
            finished_at=request.occurred_at,
        )
        repository.records[record.job_id] = recovered
        return recovered


def _recover_run(run, now):
    outcome = recovery_run_outcome(run.status, run.stage)
    if outcome is None:
        return run
    target, stage, code, summary = outcome
    event = StateEvent(
        str(uuid4()),
        len(run.state_events) + 1,
        run.status,
        target,
        "INTERRUPTION_PENDING_CANCELED" if target == "CANCELED" else code,
        now,
    )
    return replace(
        run,
        status=target,
        stage=stage,
        row_version=run.row_version + 1,
        failure_code=code,
        failure_summary=summary,
        finished_at=now,
        state_events=run.state_events + (event,),
    )
