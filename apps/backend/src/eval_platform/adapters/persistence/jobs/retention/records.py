"""Exact, auditable PostgreSQL side of owner-controlled object expiry."""

from datetime import datetime
from typing import Any

import psycopg

from eval_platform.domain.jobs.execution import RunArtifact
from eval_platform.domain.jobs.models import JobUnavailable
from eval_platform.domain.result import ArtifactRef

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
        return tuple(_artifact(row) for row in rows)
    except (KeyError, TypeError, ValueError):
        raise JobUnavailable from None


def mark_artifact_deleted(
    connection: Connection,
    item: RunArtifact,
    actor_user_id: str,
    occurred_at: datetime,
    reason: str,
) -> None:
    reference = item.reference
    if reason != "raw_retention_expired" or reference.expires_at is None:
        raise ValueError("Deletion audit reason or expiry is invalid")
    row = connection.execute(
        "UPDATE artifact_records ar SET deleted_at=%s,deleted_by=%s,"
        "deletion_reason=%s FROM accounts a WHERE ar.artifact_id=%s "
        "AND ar.run_id=%s AND ar.object_key=%s AND ar.sha256=%s "
        "AND ar.size_bytes=%s AND ar.original_size_bytes=%s "
        "AND ar.retention_class='raw_30d' AND ar.expires_at=%s "
        "AND ar.expires_at<=%s AND ar.deleted_at IS NULL "
        "AND a.user_id=%s AND a.role='owner' AND a.active RETURNING ar.artifact_id",
        (
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
    if row is not None:
        return
    stored = connection.execute(
        "SELECT run_id,object_key,sha256,size_bytes,original_size_bytes,expires_at,"
        "deleted_at,deleted_by,deletion_reason FROM artifact_records "
        "WHERE artifact_id=%s",
        (item.artifact_id,),
    ).fetchone()
    if stored is None or not _same_completed(stored, item, actor_user_id, reason):
        raise JobUnavailable


def _artifact(row: dict[str, Any]) -> RunArtifact:
    run_id = str(row["run_id"])
    reference = ArtifactRef(
        row["object_key"],
        row["artifact_type"],
        row["size_bytes"],
        row["sha256"],
        row["content_type"],
        row["retention_class"],
        row["truncated"],
        row["deleted_at"],
        row["created_at"],
        original_filename=row["original_filename"],
        original_size_bytes=row["original_size_bytes"],
        expires_at=row["expires_at"],
        deleted_by=None if row["deleted_by"] is None else str(row["deleted_by"]),
        deletion_reason=row["deletion_reason"],
    )
    return RunArtifact(
        str(row["artifact_id"]), run_id, reference, row["redaction_status"]
    )


def _same_completed(
    row: dict[str, Any], item: RunArtifact, actor_user_id: str, reason: str
) -> bool:
    reference = item.reference
    return (
        str(row["run_id"]) == item.run_id
        and row["object_key"] == reference.object_key
        and row["sha256"] == reference.sha256
        and row["size_bytes"] == reference.size_bytes
        and row["original_size_bytes"] == reference.original_size_bytes
        and row["expires_at"] == reference.expires_at
        and row["deleted_at"] is not None
        and str(row["deleted_by"]) == actor_user_id
        and row["deletion_reason"] == reason
    )
