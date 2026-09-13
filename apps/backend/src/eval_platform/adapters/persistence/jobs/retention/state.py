"""Closed row parsing for an artifact deletion intent and final audit."""

from typing import Any

from eval_platform.domain.jobs.execution import ArtifactDeletionIntent, RunArtifact
from eval_platform.domain.result import ArtifactRef


def artifact(row: dict[str, Any]) -> RunArtifact:
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
        str(row["artifact_id"]),
        str(row["run_id"]),
        reference,
        row["redaction_status"],
    )


def intent(row: dict[str, Any], item: RunArtifact) -> ArtifactDeletionIntent:
    if artifact(row) != item:
        raise ValueError("Artifact deletion identity changed")
    return ArtifactDeletionIntent(
        item,
        str(row["deletion_intent_id"]),
        str(row["deletion_intent_by"]),
        row["deletion_intent_reason"],
        row["deletion_intent_at"],
        row["deletion_verified_at"],
    )


def same_intent(
    current: ArtifactDeletionIntent, expected: ArtifactDeletionIntent
) -> bool:
    return (
        current.item == expected.item
        and current.intent_id == expected.intent_id
        and current.actor_user_id == expected.actor_user_id
        and current.reason == expected.reason
        and current.initiated_at == expected.initiated_at
    )


def completed(row: dict[str, Any], expected: ArtifactDeletionIntent) -> bool:
    try:
        reference = expected.item.reference
        return (
            str(row["run_id"]) == expected.item.run_id
            and row["object_key"] == reference.object_key
            and row["sha256"] == reference.sha256
            and row["size_bytes"] == reference.size_bytes
            and row["original_size_bytes"] == reference.original_size_bytes
            and row["expires_at"] == reference.expires_at
            and row["deletion_intent_id"] == expected.intent_id
            and str(row["deletion_intent_by"]) == expected.actor_user_id
            and row["deletion_intent_reason"] == expected.reason
            and row["deletion_verified_at"] == expected.verified_at
            and row["deleted_at"] is not None
            and str(row["deleted_by"]) == expected.actor_user_id
            and row["deletion_reason"] == expected.reason
        )
    except (KeyError, TypeError, ValueError):
        return False
