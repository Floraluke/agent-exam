"""Atomic owner decision transition for one frozen Job."""

from typing import Any
from uuid import uuid4

import psycopg

from eval_platform.domain.jobs.decisions import JobStateConflict, OwnerDecision
from eval_platform.domain.jobs.models import JobIdempotencyConflict, JobNotFound


def decide(connection: psycopg.Connection[Any], decision: OwnerDecision) -> str:
    row = connection.execute(
        "SELECT status,owner_decision_key_hash,owner_decision_request_sha256 "
        "FROM evaluation_jobs WHERE job_id=%s FOR UPDATE",
        (decision.job_id,),
    ).fetchone()
    if row is None:
        raise JobNotFound
    if row["owner_decision_key_hash"] == decision.idempotency_key_hash:
        if row["owner_decision_request_sha256"] == decision.request_sha256:
            return decision.job_id
        raise JobIdempotencyConflict
    if row["status"] != "AWAITING_OWNER_APPROVAL":
        raise JobStateConflict

    connection.execute(
        "UPDATE evaluation_jobs SET status=%s,row_version=1,owner_decided_by=%s,"
        "owner_decided_at=%s,owner_decision_reason=%s,owner_decision_key_hash=%s,"
        "owner_decision_request_sha256=%s WHERE job_id=%s",
        (
            decision.target_status,
            decision.actor_user_id,
            decision.decided_at,
            decision.reason,
            decision.idempotency_key_hash,
            decision.request_sha256,
            decision.job_id,
        ),
    )
    connection.execute(
        "INSERT INTO job_state_events "
        "(event_id,job_id,sequence,from_status,to_status,reason_code,"
        "actor_user_id,occurred_at,note) VALUES (%s,%s,2,%s,%s,%s,%s,%s,%s)",
        (
            str(uuid4()),
            decision.job_id,
            "AWAITING_OWNER_APPROVAL",
            decision.target_status,
            decision.reason_code,
            decision.actor_user_id,
            decision.decided_at,
            decision.reason,
        ),
    )
    if decision.cancels_runs:
        _cancel_runs(connection, decision)
    return decision.job_id


def _cancel_runs(connection: psycopg.Connection[Any], decision: OwnerDecision) -> None:
    rows = connection.execute(
        "UPDATE evaluation_runs SET status='CANCELED',row_version=1 "
        "WHERE job_id=%s AND status='PENDING' RETURNING run_id",
        (decision.job_id,),
    ).fetchall()
    for row in rows:
        connection.execute(
            "INSERT INTO run_state_events "
            "(event_id,run_id,sequence,from_status,to_status,reason_code,occurred_at) "
            "VALUES (%s,%s,2,'PENDING','CANCELED','JOB_REJECTED',%s)",
            (str(uuid4()), row["run_id"], decision.decided_at),
        )
