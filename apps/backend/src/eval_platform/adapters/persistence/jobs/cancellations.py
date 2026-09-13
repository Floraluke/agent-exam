"""Atomic trusted cancellation transition for one Job."""

from typing import Any
from uuid import uuid4

import psycopg

from eval_platform.domain.jobs.cancellation import CancellationRequest
from eval_platform.domain.jobs.decisions import JobStateConflict
from eval_platform.domain.jobs.models import JobIdempotencyConflict, JobNotFound

Connection = psycopg.Connection[Any]
_DIRECT = {"AWAITING_OWNER_APPROVAL", "QUEUED", "PREPARING"}


def cancel(connection: Connection, request: CancellationRequest) -> str:
    row = connection.execute(
        "SELECT status,cancel_request_key_hash,cancel_request_sha256 "
        "FROM evaluation_jobs WHERE job_id=%s FOR UPDATE",
        (request.job_id,),
    ).fetchone()
    if row is None:
        raise JobNotFound
    if row["cancel_request_key_hash"] == request.idempotency_key_hash:
        if row["cancel_request_sha256"] == request.request_sha256:
            return request.job_id
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
    target = "CANCEL_REQUESTED" if status == "EXECUTING" else "CANCELED"
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
        _cancel_unstarted_runs(connection, request, runs)
    return request.job_id


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


def _cancel_unstarted_runs(
    connection: Connection,
    request: CancellationRequest,
    runs: list[dict[str, Any]],
) -> None:
    connection.execute(
        "UPDATE evaluation_runs SET status='CANCELED',stage='canceled',"
        "row_version=row_version+1,finished_at=%s WHERE job_id=%s "
        "AND status IN ('PENDING','PREPARING')",
        (request.requested_at, request.job_id),
    )
    for row in runs:
        if row["status"] not in {"PENDING", "PREPARING"}:
            continue
        connection.execute(
            "INSERT INTO run_state_events "
            "(event_id,run_id,sequence,from_status,to_status,reason_code,occurred_at) "
            "SELECT %s,%s,COALESCE(max(sequence),0)+1,%s,'CANCELED',"
            "'JOB_CANCELED',%s FROM run_state_events WHERE run_id=%s",
            (
                str(uuid4()),
                row["run_id"],
                row["status"],
                request.requested_at,
                row["run_id"],
            ),
        )
