"""Recovery behavior shared by synthetic JobRepository adapters."""

from dataclasses import replace
from uuid import uuid4

from eval_platform.domain.jobs.decisions import JobStateConflict
from eval_platform.domain.jobs.models import StateEvent

_ACTIVE = {"PREPARING", "EXECUTING", "CANCEL_REQUESTED", "FINALIZING"}
_TERMINAL = {"COMPLETED", "FAILED", "CANCELED"}


def recover(repository, request):
    with repository.lock:
        record = repository.get(request.job_id)
        if record.status in _TERMINAL and any(
            event.reason_code == "INTERRUPTION_RECOVERED"
            for event in record.state_events
        ):
            return record
        if (
            record.status not in _ACTIVE
            or record.lease_expires_at is None
            or request.occurred_at < record.lease_expires_at
        ):
            raise JobStateConflict
        runs = tuple(_recover_run(run, request.occurred_at) for run in record.runs)
        interrupted = any(
            before.status not in _TERMINAL and after.status == "FAILED"
            for before, after in zip(record.runs, runs, strict=True)
        )
        completed = sum(run.status == "COMPLETED" for run in runs)
        canceling = record.status == "CANCEL_REQUESTED"
        target, code, summary = _outcome(canceling, interrupted, completed, runs)
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
    if run.status in _TERMINAL:
        return run
    target = "CANCELED" if run.status == "PENDING" else "FAILED"
    code = None if target == "CANCELED" else "INFRASTRUCTURE_INTERRUPTED"
    summary = None if code is None else f"运行在 {run.stage or run.status} 阶段中断。"
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
        stage="canceled" if target == "CANCELED" else "interrupted",
        row_version=run.row_version + 1,
        failure_code=code,
        failure_summary=summary,
        finished_at=now,
        state_events=run.state_events + (event,),
    )


def _outcome(canceling, interrupted, completed, runs):
    if canceling:
        return "CANCELED", None, None
    if interrupted:
        status = "COMPLETED_WITH_ERRORS" if completed else "FAILED"
        return status, "INFRASTRUCTURE_INTERRUPTED", "执行租约过期，批次已安全收束。"
    failed = any(run.status != "COMPLETED" for run in runs)
    if not failed:
        return "COMPLETED", None, None
    code = "BATCH_PARTIAL_FAILURE" if completed else "BATCH_FAILED"
    status = "COMPLETED_WITH_ERRORS" if completed else "FAILED"
    return status, code, "批次已按现有终态证据完成收束。"
