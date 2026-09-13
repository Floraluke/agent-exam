import pytest

from eval_platform.application.job_lifecycle.retention import ArtifactRetention
from eval_platform.domain.catalog import ArtifactUnavailable
from eval_platform.domain.jobs.models import JobUnavailable
from jobs.artifacts.cleanup_support import (
    MEMBER,
    NOW,
    OWNER,
    FailingDelete,
    RetentionRecords,
    expired,
)
from jobs.execution.support.fakes import MemoryArtifacts


def test_owner_cleanup_is_exact_audited_and_idempotent():
    store = MemoryArtifacts()
    records = RetentionRecords(expired(store))
    retention = ArtifactRetention(records, store)

    first = retention.cleanup(OWNER, NOW)
    second = retention.cleanup(OWNER, NOW)

    assert (first.scanned, first.deleted, first.recovered) == (1, 1, 0)
    assert (second.scanned, second.deleted, second.recovered) == (0, 0, 0)
    assert records.item.reference.deleted_by == OWNER.user_id
    assert records.item.reference.deletion_reason == "raw_retention_expired"
    assert records.item.reference.object_key not in store.content


def test_database_failure_after_object_delete_is_recovered_on_retry():
    store = MemoryArtifacts()
    records = RetentionRecords(expired(store), fail_once=True)
    retention = ArtifactRetention(records, store)

    with pytest.raises(JobUnavailable):
        retention.cleanup(OWNER, NOW)
    assert records.item.reference.deleted_at is None
    assert records.item.reference.object_key not in store.content

    result = retention.cleanup(OWNER, NOW)
    assert (result.deleted, result.recovered) == (0, 1)
    assert records.item.reference.deleted_at == NOW


def test_object_failure_and_non_owner_never_write_deletion_audit():
    healthy = MemoryArtifacts()
    item = expired(healthy)
    failed = FailingDelete()
    failed.content.update(healthy.content)
    records = RetentionRecords(item)

    with pytest.raises(PermissionError):
        ArtifactRetention(records, healthy).cleanup(MEMBER, NOW)
    with pytest.raises(ArtifactUnavailable):
        ArtifactRetention(records, failed).cleanup(OWNER, NOW)

    assert records.marks == 0
    assert records.item.reference.deleted_at is None


def test_unexpected_missing_object_never_becomes_a_cleanup_audit():
    store = MemoryArtifacts()
    records = RetentionRecords(expired(store))
    del store.content[records.item.reference.object_key]
    retention = ArtifactRetention(records, store)

    with pytest.raises(ArtifactUnavailable):
        retention.cleanup(OWNER, NOW)
    with pytest.raises(ArtifactUnavailable):
        retention.cleanup(OWNER, NOW)

    assert records.marks == 0
    assert records.intent is not None and records.intent.verified_at is None
    assert records.item.reference.deleted_at is None
