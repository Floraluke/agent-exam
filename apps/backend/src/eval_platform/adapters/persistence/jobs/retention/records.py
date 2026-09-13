"""Exact, auditable PostgreSQL side of owner-controlled object expiry."""

from datetime import datetime
from typing import Any

import psycopg

from eval_platform.adapters.persistence.jobs.retention.state import (
    artifact,
    completed,
    same_intent,
)
from eval_platform.adapters.persistence.jobs.retention.state import (
    intent as intent_from,
)
from eval_platform.domain.jobs.execution import ArtifactDeletionIntent, RunArtifact
from eval_platform.domain.jobs.models import JobUnavailable

Connection = psycopg.Connection[Any]


def expired_artifacts(
    connection: Connection, now: datetime, limit: int
) -> tuple[RunArtifact, ...]:
    if not 1 <= limit <= 100:
        raise ValueError("Cleanup limit must be between 1 and 100")
    rows = connection.execute(
        "SELECT * FROM artifact_records WHERE retention_class='raw_30d' "
        "AND expires_at<=%s AND deleted_at IS NULL "
        "ORDER BY expires_at,artifact_id LIMIT %s",
        (now, limit),
    ).fetchall()
    try:
        return tuple(artifact(row) for row in rows)
    except (KeyError, TypeError, ValueError):
        raise JobUnavailable from None


def begin_artifact_deletion(
    connection: Connection,
    item: RunArtifact,
    actor_user_id: str,
    occurred_at: datetime,
    reason: str,
    intent_id: str,
) -> ArtifactDeletionIntent:
    reference = item.reference
    if reason != "raw_retention_expired" or reference.expires_at is None:
        raise ValueError("Deletion intent reason or expiry is invalid")
    row = connection.execute(
        "UPDATE artifact_records ar SET deletion_intent_id=%s,"
        "deletion_intent_at=%s,deletion_intent_by=%s,deletion_intent_reason=%s "
        "FROM accounts a WHERE ar.artifact_id=%s AND ar.run_id=%s "
        "AND ar.object_key=%s AND ar.sha256=%s AND ar.size_bytes=%s "
        "AND ar.original_size_bytes=%s AND ar.retention_class='raw_30d' "
        "AND ar.expires_at=%s AND ar.expires_at<=%s AND ar.deleted_at IS NULL "
        "AND ar.deletion_intent_id IS NULL AND a.user_id=%s AND a.role='owner' "
        "AND a.active RETURNING ar.*",
        (
            intent_id,
            occurred_at,
            actor_user_id,
            reason,
            item.artifact_id,
            item.run_id,
            reference.object_key,
            reference.sha256,
            reference.size_bytes,
            reference.original_size_bytes,
            reference.expires_at,
            occurred_at,
            actor_user_id,
        ),
    ).fetchone()
    if row is None:
        row = connection.execute(
            "SELECT * FROM artifact_records WHERE artifact_id=%s",
            (item.artifact_id,),
        ).fetchone()
    try:
        if row is None:
            raise ValueError
        intent = intent_from(row, item)
        if intent.actor_user_id != actor_user_id or intent.reason != reason:
            raise ValueError
        return intent
    except (KeyError, TypeError, ValueError):
        raise JobUnavailable from None


def confirm_artifact_deletion(
    connection: Connection,
    intent: ArtifactDeletionIntent,
    occurred_at: datetime,
) -> ArtifactDeletionIntent:
    row = connection.execute(
        "UPDATE artifact_records SET deletion_verified_at=%s "
        "WHERE artifact_id=%s AND run_id=%s AND deletion_intent_id=%s "
        "AND deletion_intent_by=%s AND deletion_intent_reason=%s "
        "AND deletion_verified_at IS NULL AND deleted_at IS NULL RETURNING *",
        (
            occurred_at,
            intent.item.artifact_id,
            intent.item.run_id,
            intent.intent_id,
            intent.actor_user_id,
            intent.reason,
        ),
    ).fetchone()
    if row is None:
        row = connection.execute(
            "SELECT * FROM artifact_records WHERE artifact_id=%s",
            (intent.item.artifact_id,),
        ).fetchone()
    if row is None:
        raise JobUnavailable
    try:
        current = intent_from(row, intent.item)
        if not same_intent(current, intent):
            raise ValueError
        if current.verified_at is None:
            raise ValueError
        return current
    except (KeyError, TypeError, ValueError):
        raise JobUnavailable from None


def mark_artifact_deleted(
    connection: Connection,
    intent: ArtifactDeletionIntent,
    occurred_at: datetime,
) -> None:
    item, reference = intent.item, intent.item.reference
    if intent.verified_at is None or occurred_at < intent.verified_at:
        raise ValueError("Deletion audit lacks verified intent")
    row = connection.execute(
        "UPDATE artifact_records ar SET deleted_at=%s,deleted_by=%s,"
        "deletion_reason=%s WHERE ar.artifact_id=%s "
        "AND ar.run_id=%s AND ar.object_key=%s AND ar.sha256=%s "
        "AND ar.size_bytes=%s AND ar.original_size_bytes=%s "
        "AND ar.retention_class='raw_30d' AND ar.expires_at=%s "
        "AND ar.deletion_intent_id=%s AND ar.deletion_intent_by=%s "
        "AND ar.deletion_intent_reason=%s AND ar.deletion_verified_at=%s "
        "AND ar.expires_at<=%s AND ar.deleted_at IS NULL RETURNING ar.artifact_id",
        (
            occurred_at,
            intent.actor_user_id,
            intent.reason,
            item.artifact_id,
            item.run_id,
            reference.object_key,
            reference.sha256,
            reference.size_bytes,
            reference.original_size_bytes,
            reference.expires_at,
            intent.intent_id,
            intent.actor_user_id,
            intent.reason,
            intent.verified_at,
            occurred_at,
        ),
    ).fetchone()
    if row is not None:
        return
    stored = connection.execute(
        "SELECT * FROM artifact_records WHERE artifact_id=%s",
        (item.artifact_id,),
    ).fetchone()
    if stored is None or not completed(stored, intent):
        raise JobUnavailable
