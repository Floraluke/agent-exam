"""Cancellation behavior shared by synthetic JobRepository adapters."""

from dataclasses import replace
from uuid import uuid4

from eval_platform.domain.jobs.cancellation import CancellationResult
from eval_platform.domain.jobs.decisions import JobStateConflict
from eval_platform.domain.jobs.models import (
    JobIdempotencyConflict,
    StateEvent,
)


def cancel(repository, request):
    with repository.lock:
        record = repository.get(request.job_id)
        previous = repository.cancellations.get(request.job_id)
        if previous is not None:
            key_hash, request_sha, accepted_status = previous
            if key_hash == request.idempotency_key_hash:
                if request_sha != request.request_sha256:
                    raise JobIdempotencyConflict
                return CancellationResult(record, accepted_status)
            raise JobStateConflict
        direct = {"AWAITING_OWNER_APPROVAL", "QUEUED", "PREPARING"}
        if record.status not in {*direct, "EXECUTING"}:
            raise JobStateConflict
        if record.status == "PREPARING" and any(
            run.status not in {"PENDING", "PREPARING"} for run in record.runs
        ):
            raise JobStateConflict
        target = "CANCEL_REQUESTED" if record.status == "EXECUTING" else "CANCELED"
        event = StateEvent(
            str(uuid4()),
            len(record.state_events) + 1,
            record.status,
            target,
            "CANCEL_REQUESTED" if target == "CANCEL_REQUESTED" else "JOB_CANCELED",
            request.requested_at,
            request.actor_user_id,
            request.reason,
        )
        runs = record.runs
        if target == "CANCELED":
            runs = cancel_runs(runs, request.requested_at)
        canceled = replace(
            record,
            status=target,
            row_version=record.row_version + 1,
            runs=runs,
            state_events=record.state_events + (event,),
            cancel_requested_by=request.actor_user_id,
            cancel_requested_at=request.requested_at,
            cancel_reason=request.reason,
            finished_at=request.requested_at if target == "CANCELED" else None,
        )
        repository.records[record.job_id] = canceled
        repository.cancellations[record.job_id] = (
            request.idempotency_key_hash,
            request.request_sha256,
            target,
        )
        return CancellationResult(canceled, target)


def cancel_runs(runs, now, worker=None):
    return tuple(
        replace(
            run,
            status="CANCELED",
            stage="canceled",
            row_version=run.row_version + 1,
            finished_at=now,
            state_events=run.state_events
            + (
                StateEvent(
                    str(uuid4()),
                    len(run.state_events) + 1,
                    run.status,
                    "CANCELED",
                    "JOB_CANCELED",
                    now,
                    worker_id=worker,
                ),
            ),
        )
        if run.status in {"PENDING", "PREPARING"}
        else run
        for run in runs
    )
