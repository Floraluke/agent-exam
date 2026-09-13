"""Owner-controlled expiry cleanup without pretending cross-store atomicity."""

from dataclasses import dataclass
from datetime import datetime
from uuid import uuid4

from eval_platform.application.ports.artifacts import ArtifactStore
from eval_platform.application.ports.repositories import JobRepository
from eval_platform.domain.identity import AuthenticatedActor


@dataclass(frozen=True, slots=True)
class RetentionResult:
    scanned: int
    deleted: int
    recovered: int


class ArtifactRetention:
    def __init__(self, repository: JobRepository, artifacts: ArtifactStore) -> None:
        self.repository = repository
        self.artifacts = artifacts

    def cleanup(
        self,
        actor: AuthenticatedActor,
        now: datetime,
        limit: int = 100,
    ) -> RetentionResult:
        if actor.role != "owner":
            raise PermissionError("Only the local owner can clean expired artifacts")
        if not 1 <= limit <= 100:
            raise ValueError("Cleanup limit must be between 1 and 100")
        items = self.repository.expired_artifacts(now, limit)
        deleted = recovered = 0
        for item in items:
            intent = self.repository.begin_artifact_deletion(
                item,
                actor.user_id,
                now,
                "raw_retention_expired",
                str(uuid4()),
            )
            if intent.verified_at is None:
                self.artifacts.read_bounded_verified(item.reference, 128)
                intent = self.repository.confirm_artifact_deletion(intent, now)
            removed = self.artifacts.delete_verified(item.reference)
            deleted_at = now if removed else intent.verified_at
            if deleted_at is None:
                raise RuntimeError("Deletion proof disappeared")
            self.repository.mark_artifact_deleted(intent, deleted_at)
            if removed:
                deleted += 1
            else:
                recovered += 1
        return RetentionResult(len(items), deleted, recovered)
