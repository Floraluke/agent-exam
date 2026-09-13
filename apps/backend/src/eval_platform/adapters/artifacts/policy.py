"""Closed artifact identities accepted by the durable MinIO adapter."""

from uuid import UUID

from eval_platform.domain.artifacts import (
    ARTIFACT_CONTENT_TYPES,
    RAW_ARTIFACT_TYPES,
)
from eval_platform.domain.catalog import ArtifactUnavailable
from eval_platform.domain.result import ArtifactRef

MAX_SNAPSHOT_BYTES = 50 * 1024 * 1024
_LONG_TERM_TYPES = {
    "agent_patch": ("text/x-diff", 1024 * 1024),
    "harness_report": ("application/json", MAX_SNAPSHOT_BYTES),
    "harness_summary": ("application/json", MAX_SNAPSHOT_BYTES),
    "harness_test_output": ("text/plain", MAX_SNAPSHOT_BYTES),
    "public_test_summary": ("application/json", MAX_SNAPSHOT_BYTES),
    "public_trajectory": ("application/x-ndjson", MAX_SNAPSHOT_BYTES),
}


def validate_reference(reference: ArtifactRef) -> None:
    task_snapshot = (
        reference.artifact_type == "task_source_snapshot"
        and reference.content_type == "application/json"
        and reference.object_key.startswith("tasks/")
    )
    run_artifact = _valid_run_reference(reference, _LONG_TERM_TYPES)
    raw_artifact = _valid_run_reference(
        reference,
        {
            key: (ARTIFACT_CONTENT_TYPES[key], MAX_SNAPSHOT_BYTES)
            for key in RAW_ARTIFACT_TYPES
        },
    )
    long_term = (
        reference.retention_class == "long_term"
        and reference.expires_at is None
        and not reference.truncated
    )
    raw = (
        reference.retention_class == "raw_30d"
        and reference.expires_at is not None
        and reference.original_size_bytes is not None
        and reference.original_size_bytes >= reference.size_bytes
        and reference.truncated
        == (reference.original_size_bytes > reference.size_bytes)
    )
    invalid = not ((task_snapshot or run_artifact) and long_term) and not (
        raw_artifact and raw
    )
    if (
        invalid
        or reference.deleted_at is not None
        or not 0 <= reference.size_bytes <= MAX_SNAPSHOT_BYTES
    ):
        raise ArtifactUnavailable


def _valid_run_reference(
    reference: ArtifactRef, types: dict[str, tuple[str, int]]
) -> bool:
    contract = types.get(reference.artifact_type)
    parts = reference.object_key.split("/")
    if contract is None or len(parts) != 4:
        return False
    try:
        run_id = str(UUID(parts[1]))
    except ValueError:
        return False
    content_type, maximum = contract
    return (
        parts == ["runs", run_id, reference.artifact_type, reference.sha256]
        and reference.content_type == content_type
        and reference.size_bytes <= maximum
    )
