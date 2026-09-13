"""Repository facade for owner-controlled artifact retention transactions."""

from datetime import datetime

from eval_platform.adapters.persistence.jobs import job_transaction
from eval_platform.adapters.persistence.jobs.retention.records import (
    begin_artifact_deletion,
    confirm_artifact_deletion,
    expired_artifacts,
    mark_artifact_deleted,
)
from eval_platform.domain.jobs.execution import ArtifactDeletionIntent, RunArtifact


class PostgresArtifactRetention:
    dsn: str

    def expired_artifacts(self, now: datetime, limit: int) -> tuple[RunArtifact, ...]:
        with job_transaction(self.dsn) as connection:
            return expired_artifacts(connection, now, limit)

    def begin_artifact_deletion(
        self,
        item: RunArtifact,
        actor_user_id: str,
        occurred_at: datetime,
        reason: str,
        intent_id: str,
    ) -> ArtifactDeletionIntent:
        with job_transaction(self.dsn) as connection:
            return begin_artifact_deletion(
                connection, item, actor_user_id, occurred_at, reason, intent_id
            )

    def confirm_artifact_deletion(
        self, intent: ArtifactDeletionIntent, occurred_at: datetime
    ) -> ArtifactDeletionIntent:
        with job_transaction(self.dsn) as connection:
            return confirm_artifact_deletion(connection, intent, occurred_at)

    def mark_artifact_deleted(
        self, intent: ArtifactDeletionIntent, occurred_at: datetime
    ) -> None:
        with job_transaction(self.dsn) as connection:
            mark_artifact_deleted(connection, intent, occurred_at)
