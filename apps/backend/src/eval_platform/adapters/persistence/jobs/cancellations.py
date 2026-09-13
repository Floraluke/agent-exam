"""Atomic trusted cancellation transition for one Job."""

from typing import Any
from uuid import uuid4

import psycopg

from eval_platform.adapters.persistence.jobs.execution.cancellation import (
    cancel_unstarted,
)
from eval_platform.domain.jobs.cancellation import (
    CancellationRequest,
    CancellationStatus,
)
from eval_platform.domain.jobs.decisions import JobStateConflict
from eval_platform.domain.jobs.models import (
    JobIdempotencyConflict,
    JobNotFound,
    JobUnavailable,
)

Connection = psycopg.Connection[Any]
_DIRECT = {"AWAITING_OWNER_APPROVAL", "QUEUED", "PREPARING"}


def cancel(
    connection: Connection, request: CancellationRequest
) -> tuple[str, CancellationStatus]:
    row = connection.execute(
        "SELECT status,cancel_request_key_hash,cancel_request_sha256 "
        "FROM evaluation_jobs WHERE job_id=%s FOR UPDATE",
        (request.job_id,),
    ).fetchone()
    if row is None:
        raise JobNotFound
    if row["cancel_request_key_hash"] == request.idempotency_key_hash:
        if row["cancel_request_sha256"] == request.request_sha256:
            return request.job_id, _accepted_status(connection, request.job_id)
        raise JobIdempotencyConflict
    status = row["status"]
    if status not in {*_DIRECT, "EXECUTING"}:
        raise JobStateConflict
    runs = connection.execute(
        "SELECT run_id,status FROM evaluation_runs WHERE job_id=%s "
        "ORDER BY run_id FOR UPDATE",
        (request.job_id,),
    ).fetchall()
    if status == "PREPARING" and any(
        run["status"] not in {"PENDING", "PREPARING"} for run in runs
    ):
        raise JobStateConflict
    target: CancellationStatus = (
        "CANCEL_REQUESTED" if status == "EXECUTING" else "CANCELED"
    )
    connection.execute(
        "UPDATE evaluation_jobs SET status=%s,row_version=row_version+1,"
        "cancel_requested_by=%s,cancel_requested_at=%s,cancel_reason=%s,"
        "cancel_request_key_hash=%s,cancel_request_sha256=%s,"
        "finished_at=CASE WHEN %s='CANCELED' THEN %s ELSE finished_at END "
        "WHERE job_id=%s",
        (
            target,
            request.actor_user_id,
            request.requested_at,
            request.reason,
            request.idempotency_key_hash,
            request.request_sha256,
            target,
            request.requested_at,
            request.job_id,
        ),
    )
    _job_event(connection, request, status, target)
    if target == "CANCELED":
        cancel_unstarted(connection, runs, request.requested_at)
    return request.job_id, target


def _job_event(
    connection: Connection,
    request: CancellationRequest,
    before: str,
    target: str,
) -> None:
    connection.execute(
        "INSERT INTO job_state_events "
        "(event_id,job_id,sequence,from_status,to_status,reason_code,"
        "actor_user_id,occurred_at,note) SELECT %s,%s,COALESCE(max(sequence),0)+1,"
        "%s,%s,%s,%s,%s,%s FROM job_state_events WHERE job_id=%s",
        (
            str(uuid4()),
            request.job_id,
            before,
            target,
            "CANCEL_REQUESTED" if target == "CANCEL_REQUESTED" else "JOB_CANCELED",
            request.actor_user_id,
            request.requested_at,
            request.reason,
            request.job_id,
        ),
    )


def _accepted_status(connection: Connection, job_id: str) -> CancellationStatus:
    row = connection.execute(
        "SELECT to_status FROM job_state_events WHERE job_id=%s "
        "AND reason_code IN ('CANCEL_REQUESTED','JOB_CANCELED') "
        "ORDER BY sequence LIMIT 1",
        (job_id,),
    ).fetchone()
    if row is None or row["to_status"] not in {"CANCEL_REQUESTED", "CANCELED"}:
        raise JobUnavailable
    return "CANCEL_REQUESTED" if row["to_status"] == "CANCEL_REQUESTED" else "CANCELED"
