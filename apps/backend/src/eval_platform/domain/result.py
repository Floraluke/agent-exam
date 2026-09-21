from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

_SAFE_BACKEND_REF = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}")
_SAFE_FILENAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}")


class TerminationReason(StrEnum):
    COMPLETED = "completed"
    AGENT_UNAVAILABLE = "agent_unavailable"
    AGENT_FAILED = "agent_failed"
    TIMED_OUT = "timed_out"
    SANDBOX_FAILED = "sandbox_failed"
    POLICY_FAILED = "policy_failed"
    PATCH_EXTRACTION_FAILED = "patch_extraction_failed"
    PATCH_TOO_LARGE = "PATCH_TOO_LARGE"
    BINARY_PATCH_NOT_ALLOWED = "BINARY_PATCH_NOT_ALLOWED"
    BACKEND_PROTOCOL_ERROR = "backend_protocol_error"
    INFRASTRUCTURE_INTERRUPTED = "INFRASTRUCTURE_INTERRUPTED"


@dataclass(frozen=True, slots=True)
class ArtifactRef:
    object_key: str
    artifact_type: str
    size_bytes: int
    sha256: str
    content_type: str
    retention_class: str = "prototype"
    truncated: bool = False
    deleted_at: datetime | None = None
    created_at: datetime | None = None
    warnings: tuple[str, ...] = ()
    original_filename: str | None = None
    original_size_bytes: int | None = None
    expires_at: datetime | None = None
    deleted_by: str | None = None
    deletion_reason: str | None = None

    def __post_init__(self) -> None:
        _validate_artifact_identity(self)
        _validate_artifact_retention(self)


def _validate_artifact_identity(reference: ArtifactRef) -> None:
    if not reference.object_key or not reference.artifact_type:
        raise ValueError("Artifact identity must not be empty")
    if reference.size_bytes < 0:
        raise ValueError("Artifact size must not be negative")
    if len(reference.sha256) != 64 or any(
        char not in "0123456789abcdef" for char in reference.sha256
    ):
        raise ValueError("Artifact SHA-256 must be lowercase hexadecimal")
    original = reference.original_size_bytes
    if original is not None and original < reference.size_bytes:
        raise ValueError("Artifact original size must cover retained content")
    filename = reference.original_filename
    if filename is not None and _SAFE_FILENAME.fullmatch(filename) is None:
        raise ValueError("Artifact filename must not contain a path")
    if reference.truncated and (original is None or original == reference.size_bytes):
        raise ValueError("Truncated artifact must record a larger original size")


def _validate_artifact_retention(reference: ArtifactRef) -> None:
    audit = (reference.deleted_at, reference.deleted_by, reference.deletion_reason)
    if any(item is None for item in audit) and any(item is not None for item in audit):
        raise ValueError("Artifact deletion audit must be complete")
    if reference.deleted_at is not None and reference.retention_class != "raw_30d":
        raise ValueError("Only expiring raw artifacts can be deleted")
    if reference.retention_class != "raw_30d":
        return
    original = reference.original_size_bytes
    if (
        reference.created_at is None
        or reference.expires_at is None
        or original is None
        or reference.original_filename is None
        or reference.expires_at <= reference.created_at
        or reference.truncated != (original > reference.size_bytes)
        or (
            reference.deleted_at is not None
            and reference.deleted_at < reference.expires_at
        )
    ):
        raise ValueError("Raw artifact retention identity is invalid")


@dataclass(frozen=True, slots=True)
class UsageSummary:
    n_input_tokens: int | None = None
    n_cache_tokens: int | None = None
    n_output_tokens: int | None = None
    cost_usd: float | None = None

    def __post_init__(self) -> None:
        values = (self.n_input_tokens, self.n_cache_tokens, self.n_output_tokens)
        if any(value is not None and value < 0 for value in values):
            raise ValueError("Token usage must not be negative")
        if self.cost_usd is not None and self.cost_usd < 0:
            raise ValueError("Cost must not be negative")


@dataclass(frozen=True, slots=True)
class ResourceSummary:
    wall_time_sec: float | None = None
    cpu_time_sec: float | None = None
    peak_memory_bytes: int | None = None

    def __post_init__(self) -> None:
        values = (self.wall_time_sec, self.cpu_time_sec, self.peak_memory_bytes)
        if any(value is not None and value < 0 for value in values):
            raise ValueError("Resource usage must not be negative")


@dataclass(frozen=True, slots=True)
class ExecutionTrialResult:
    run_id: str
    backend_job_ref: str
    backend_trial_ref: str
    termination_reason: TerminationReason
    patch_ref: ArtifactRef | None
    trajectory_ref: ArtifactRef | None
    raw_config_ref: ArtifactRef | None = None
    raw_result_ref: ArtifactRef | None = None
    usage: UsageSummary | None = None
    resource_summary: ResourceSummary | None = None
    warnings: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if _SAFE_BACKEND_REF.fullmatch(self.backend_job_ref) is None or (
            self.backend_trial_ref
            and _SAFE_BACKEND_REF.fullmatch(self.backend_trial_ref) is None
        ):
            raise ValueError("Backend references must be safe opaque identities")
        if (
            self.termination_reason is TerminationReason.COMPLETED
            and self.patch_ref is None
        ):
            raise ValueError("A completed execution must include a patch artifact")


@dataclass(frozen=True, slots=True)
class DeterministicResult:
    run_id: str
    resolved: bool
    patch_applied: bool
    report_ref: ArtifactRef
    log_refs: tuple[ArtifactRef, ...] = ()
    tests_status_summary: dict[str, object] | None = None
    duration_ms: int | None = None


class PatchValidationError(ValueError):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def validate_patch_content(
    reference: ArtifactRef,
    content: bytes,
    warning_bytes: int,
    maximum_bytes: int,
) -> tuple[str, ...]:
    if reference.artifact_type != "agent_patch":
        raise PatchValidationError("PATCH_IDENTITY_INVALID")
    if len(content) != reference.size_bytes:
        raise PatchValidationError("PATCH_SIZE_MISMATCH")
    from hashlib import sha256

    if sha256(content).hexdigest() != reference.sha256:
        raise PatchValidationError("PATCH_HASH_MISMATCH")
    if len(content) > maximum_bytes:
        raise PatchValidationError("PATCH_TOO_LARGE")
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError:
        raise PatchValidationError("BINARY_PATCH_NOT_ALLOWED") from None
    if "\x00" in text or "GIT binary patch" in text or "Binary files " in text:
        raise PatchValidationError("BINARY_PATCH_NOT_ALLOWED")
    if content and not text.startswith("diff --git "):
        raise PatchValidationError("PATCH_FORMAT_INVALID")
    return ("PATCH_SIZE_WARNING",) if len(content) > warning_bytes else ()
