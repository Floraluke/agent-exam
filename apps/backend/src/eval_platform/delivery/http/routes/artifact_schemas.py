"""Shared public artifact metadata schemas; object keys never leave Delivery."""

from datetime import datetime
from typing import Literal, cast

from pydantic import BaseModel

from eval_platform.application.reporting.evidence import ArtifactPage
from eval_platform.domain.jobs.execution import RunArtifact

ArtifactType = Literal[
    "agent_patch",
    "public_test_summary",
    "public_trajectory",
    "harness_report",
    "harness_summary",
    "harness_test_output",
    "harbor_trial_config",
    "harbor_trial_result",
    "agent_trajectory",
    "harness_report_raw",
    "harness_summary_raw",
    "harness_test_output_raw",
    "harness_log_raw",
]


class ArtifactItemResponse(BaseModel):
    artifact_id: str
    artifact_type: ArtifactType
    content_type: str
    size_bytes: int
    sha256: str
    created_at: datetime | None
    redaction_status: Literal["not_required", "redacted", "blocked"]
    warnings: list[str]
    retention_class: Literal["long_term", "raw_30d"]
    original_size_bytes: int
    truncated: bool
    expires_at: datetime | None
    deleted_at: datetime | None
    deleted_by: str | None
    deletion_reason: str | None
    content_status: Literal["available", "not_ready", "deleted"]

    @classmethod
    def from_record(cls, item: RunArtifact) -> "ArtifactItemResponse":
        reference = item.reference
        return cls(
            artifact_id=item.artifact_id,
            artifact_type=cast(ArtifactType, reference.artifact_type),
            content_type=reference.content_type,
            size_bytes=reference.size_bytes,
            sha256=reference.sha256,
            created_at=reference.created_at,
            redaction_status=cast(
                Literal["not_required", "redacted", "blocked"],
                item.redaction_status,
            ),
            warnings=list(reference.warnings),
            retention_class=cast(
                Literal["long_term", "raw_30d"], reference.retention_class
            ),
            original_size_bytes=reference.original_size_bytes or reference.size_bytes,
            truncated=reference.truncated,
            expires_at=reference.expires_at,
            deleted_at=reference.deleted_at,
            deleted_by=reference.deleted_by,
            deletion_reason=reference.deletion_reason,
            content_status=(
                "deleted"
                if reference.deleted_at is not None
                else "available"
                if reference.artifact_type
                in {"agent_patch", "public_test_summary", "public_trajectory"}
                else "not_ready"
            ),
        )


class ArtifactPageResponse(BaseModel):
    items: list[ArtifactItemResponse]
    next_cursor: str | None

    @classmethod
    def from_record(cls, page: ArtifactPage) -> "ArtifactPageResponse":
        return cls(
            items=[ArtifactItemResponse.from_record(item) for item in page.items],
            next_cursor=page.next_cursor,
        )
