"""Private raw-evidence retention policy behind the publication service."""

from collections.abc import Callable, Iterable
from datetime import datetime, timedelta
from hashlib import sha256

from eval_platform.application.ports.artifacts import ArtifactReader, ArtifactStore
from eval_platform.domain.result import ArtifactRef

_DIRECT_TYPES = {
    "harbor_trial_config": ("application/json", "trial-config.json"),
    "harbor_trial_result": ("application/json", "trial-result.json"),
    "agent_trajectory": ("application/json", "trajectory.json"),
    "harness_report": ("application/json", "harness-report.json"),
    "harness_summary": ("application/json", "harness-summary.json"),
    "harness_test_output": ("text/plain", "test-output.txt"),
}


def publish_raw(
    source_reader: ArtifactReader,
    destination: ArtifactStore,
    clock: Callable[[], datetime],
    run_id: str,
    sources: Iterable[ArtifactRef],
    artifact_limit: int,
    run_limit: int,
) -> tuple[tuple[ArtifactRef, ...], tuple[str, ...]]:
    if artifact_limit < 128 or run_limit < artifact_limit:
        raise ValueError("Raw artifact limits are invalid")
    published: list[ArtifactRef] = []
    retained_total = 0
    rejected = False
    for source in sources:
        kind, content_type, filename = raw_identity(source)
        retained_size = min(source.size_bytes, artifact_limit)
        if retained_total + retained_size > run_limit:
            rejected = True
            continue
        body = source_reader.read_bounded_verified(source, artifact_limit)
        retained = body.content
        digest = sha256(retained).hexdigest()
        created_at = clock()
        reference = ArtifactRef(
            f"runs/{run_id}/{kind}/{digest}",
            kind,
            len(retained),
            digest,
            content_type,
            "raw_30d",
            body.truncated,
            created_at=created_at,
            original_filename=filename,
            original_size_bytes=body.original_size_bytes,
            expires_at=created_at + timedelta(days=30),
        )
        destination.put_immutable(reference, retained)
        destination.read_verified(reference)
        published.append(reference)
        retained_total += len(retained)
    warnings = ("RAW_ARTIFACT_RUN_LIMIT_EXCEEDED",) if rejected else ()
    return tuple(published), warnings


def raw_identity(reference: ArtifactRef) -> tuple[str, str, str]:
    value = _DIRECT_TYPES.get(reference.artifact_type)
    if value is None:
        if (
            reference.artifact_type != "harness_log"
            or reference.content_type != "text/plain"
        ):
            raise ValueError("Raw evidence has an unsupported type")
        return "harness_log_raw", "text/plain", "harness.log"
    kind = reference.artifact_type
    if kind.startswith("harness_"):
        kind += "_raw"
    content_type, filename = value
    if reference.content_type != content_type:
        raise ValueError("Raw evidence content type is invalid")
    return kind, content_type, filename
