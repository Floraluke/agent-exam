from dataclasses import replace
from datetime import UTC, datetime, timedelta
from hashlib import sha256

from eval_platform.domain.catalog import ArtifactUnavailable
from eval_platform.domain.identity import AuthenticatedActor
from eval_platform.domain.jobs.execution import ArtifactDeletionIntent, RunArtifact
from eval_platform.domain.jobs.models import JobUnavailable
from eval_platform.domain.result import ArtifactRef
from jobs.execution.support.fakes import MemoryArtifacts

NOW = datetime(2026, 10, 14, 8, 0, tzinfo=UTC)
RUN_ID = "5e87af1c-a652-4c64-a1a3-e454e4638ebd"
OWNER = AuthenticatedActor("00000000-0000-4000-8000-000000000001", "owner", "owner")
MEMBER = AuthenticatedActor(
    "00000000-0000-4000-8000-000000000002", "member", "collaborator"
)


def expired(store: MemoryArtifacts) -> RunArtifact:
    body = b"synthetic raw evidence"
    digest = sha256(body).hexdigest()
    reference = ArtifactRef(
        f"runs/{RUN_ID}/agent_trajectory/{digest}",
        "agent_trajectory",
        len(body),
        digest,
        "application/json",
        "raw_30d",
        created_at=NOW - timedelta(days=31),
        original_filename="trajectory.json",
        original_size_bytes=len(body),
        expires_at=NOW - timedelta(days=1),
    )
    store.content[reference.object_key] = body
    return RunArtifact(
        "00000000-0000-4000-8000-000000000003", RUN_ID, reference, "blocked"
    )


class RetentionRecords:
    def __init__(self, item: RunArtifact, *, fail_once: bool = False):
        self.item = item
        self.fail_once = fail_once
        self.marks = 0
        self.intent: ArtifactDeletionIntent | None = None

    def expired_artifacts(self, now, limit):
        reference = self.item.reference
        if reference.deleted_at is not None or reference.expires_at > now:
            return ()
        return (self.item,)

    def begin_artifact_deletion(
        self, item, actor_user_id, occurred_at, reason, intent_id
    ):
        if self.intent is None:
            self.intent = ArtifactDeletionIntent(
                item, intent_id, actor_user_id, reason, occurred_at
            )
        return self.intent

    def confirm_artifact_deletion(self, intent, occurred_at):
        assert intent == self.intent
        self.intent = replace(intent, verified_at=occurred_at)
        return self.intent

    def mark_artifact_deleted(self, intent, occurred_at):
        self.marks += 1
        if self.fail_once:
            self.fail_once = False
            raise JobUnavailable
        assert intent == self.intent and intent.verified_at is not None
        reference = replace(
            intent.item.reference,
            deleted_at=occurred_at,
            deleted_by=intent.actor_user_id,
            deletion_reason=intent.reason,
        )
        self.item = replace(intent.item, reference=reference)


class FailingDelete(MemoryArtifacts):
    def delete_verified(self, reference):
        raise ArtifactUnavailable
