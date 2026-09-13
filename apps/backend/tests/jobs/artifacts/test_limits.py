from dataclasses import replace
from datetime import UTC, datetime, timedelta
from hashlib import sha256

import pytest

from eval_platform.adapters.artifacts.local import LocalArtifactReader
from eval_platform.application.execution.evidence import EvidencePublication
from eval_platform.domain.result import ArtifactRef
from jobs.execution.support.fakes import MemoryArtifacts

MIB = 1024 * 1024
RUN_ID = "5e87af1c-a652-4c64-a1a3-e454e4638ebd"
NOW = datetime(2026, 9, 13, 8, 0, tzinfo=UTC)


def source(store, kind: str, content: bytes, content_type: str) -> ArtifactRef:
    reference = ArtifactRef(
        f"private/{kind}",
        kind,
        len(content),
        sha256(content).hexdigest(),
        content_type,
        created_at=NOW,
    )
    store.content[reference.object_key] = content
    return reference


def test_raw_artifact_exact_boundary_is_retained_without_truncation():
    content = b"a" * (50 * MIB)
    origin, durable = MemoryArtifacts(), MemoryArtifacts()
    reference = source(origin, "agent_trajectory", content, "application/json")

    published, warnings = EvidencePublication(origin, durable, lambda: NOW).publish_raw(
        RUN_ID, (reference,), 50 * MIB, 200 * MIB
    )

    assert warnings == ()
    assert len(published) == 1
    retained = published[0]
    assert retained.retention_class == "raw_30d"
    assert retained.size_bytes == retained.original_size_bytes == 50 * MIB
    assert retained.truncated is False
    assert retained.expires_at == NOW + timedelta(days=30)
    assert durable.read_verified(retained) == content


def test_raw_artifact_over_boundary_retains_verifiable_head_tail_and_marker():
    content = b"h" * (25 * MIB) + b"center" + b"t" * (25 * MIB)
    origin, durable = MemoryArtifacts(), MemoryArtifacts()
    reference = source(origin, "agent_trajectory", content, "application/json")

    published, warnings = EvidencePublication(origin, durable, lambda: NOW).publish_raw(
        RUN_ID, (reference,), 50 * MIB, 200 * MIB
    )

    assert warnings == ()
    retained = published[0]
    body = durable.read_verified(retained)
    assert retained.truncated is True
    assert retained.original_size_bytes == 50 * MIB + len(b"center")
    assert retained.size_bytes == len(body) == 50 * MIB
    assert sha256(body).hexdigest() == retained.sha256
    assert b"AGENTEXAM_RAW_ARTIFACT_TRUNCATED" in body
    assert body.startswith(b"h" * 1024) and body.endswith(b"t" * 1024)


def test_oversized_local_source_is_verified_without_loading_unbounded_body(tmp_path):
    content = b"h" * (25 * MIB) + b"center" + b"t" * (25 * MIB)
    path = tmp_path / "trajectory.json"
    path.write_bytes(content)
    reference = ArtifactRef(
        str(path),
        "agent_trajectory",
        len(content),
        sha256(content).hexdigest(),
        "application/json",
        created_at=NOW,
    )
    durable = MemoryArtifacts()

    published, _warnings = EvidencePublication(
        LocalArtifactReader(tmp_path), durable, lambda: NOW
    ).publish_raw(RUN_ID, (reference,), 50 * MIB, 200 * MIB)

    body = durable.read_verified(published[0])
    assert len(body) == 50 * MIB
    assert body.startswith(b"h" * 1024) and body.endswith(b"t" * 1024)


def test_raw_run_exact_limit_is_kept_and_next_artifact_is_explicitly_rejected():
    content = b"x" * (50 * MIB)
    origin, durable = MemoryArtifacts(), MemoryArtifacts()
    sources = tuple(
        source(origin, kind, content, content_type)
        for kind, content_type in (
            ("harbor_trial_config", "application/json"),
            ("harbor_trial_result", "application/json"),
            ("agent_trajectory", "application/json"),
            ("harness_report", "application/json"),
            ("harness_test_output", "text/plain"),
        )
    )

    published, warnings = EvidencePublication(origin, durable, lambda: NOW).publish_raw(
        RUN_ID, sources, 50 * MIB, 200 * MIB
    )

    assert sum(item.size_bytes for item in published) == 200 * MIB
    assert len(published) == 4
    assert warnings == ("RAW_ARTIFACT_RUN_LIMIT_EXCEEDED",)
    assert all(item.size_bytes <= 50 * MIB for item in published)


def test_supported_text_log_is_stored_as_restricted_expiring_raw_evidence():
    origin, durable = MemoryArtifacts(), MemoryArtifacts()
    reference = source(origin, "harness_log", b"safe synthetic log\n", "text/plain")

    published, warnings = EvidencePublication(origin, durable, lambda: NOW).publish_raw(
        RUN_ID, (reference,), 50 * MIB, 200 * MIB
    )

    assert warnings == ()
    assert published[0].artifact_type == "harness_log_raw"
    assert published[0].original_filename == "harness.log"
    assert durable.read_verified(published[0]) == b"safe synthetic log\n"


def test_raw_reference_rejects_incomplete_retention_identity_and_early_audit():
    body = b"raw"
    reference = ArtifactRef(
        f"runs/{RUN_ID}/agent_trajectory/{sha256(body).hexdigest()}",
        "agent_trajectory",
        len(body),
        sha256(body).hexdigest(),
        "application/json",
        "raw_30d",
        created_at=NOW,
        original_filename="trajectory.json",
        original_size_bytes=len(body),
        expires_at=NOW + timedelta(days=30),
    )

    invalid = (
        {"original_filename": "private/path.json"},
        {"expires_at": NOW},
        {"deleted_at": NOW, "deleted_by": OWNER_ID, "deletion_reason": "expired"},
    )
    for changes in invalid:
        with pytest.raises(ValueError):
            replace(reference, **changes)


OWNER_ID = "00000000-0000-4000-8000-000000000001"
