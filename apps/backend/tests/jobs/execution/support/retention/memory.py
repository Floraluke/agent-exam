from dataclasses import replace

from eval_platform.domain.jobs.execution import ArtifactDeletionIntent
from eval_platform.domain.jobs.models import JobUnavailable


class MemoryRetention:
    def expired_artifacts(self, now, limit):
        with self.lock:
            items = [
                item
                for report in self.reports.values()
                for item in report.artifacts
                if item.reference.retention_class == "raw_30d"
                and item.reference.expires_at is not None
                and item.reference.expires_at <= now
                and item.reference.deleted_at is None
            ]
            return tuple(
                sorted(
                    items,
                    key=lambda item: (item.reference.expires_at, item.artifact_id),
                )[:limit]
            )

    def begin_artifact_deletion(
        self, item, actor_user_id, occurred_at, reason, intent_id
    ):
        with self.lock:
            current = self.deletion_intents.get(item.artifact_id)
            if current is None:
                current = ArtifactDeletionIntent(
                    item, intent_id, actor_user_id, reason, occurred_at
                )
                self.deletion_intents[item.artifact_id] = current
            if current.item != item or current.actor_user_id != actor_user_id:
                raise JobUnavailable
            return current

    def confirm_artifact_deletion(self, intent, occurred_at):
        with self.lock:
            current = self.deletion_intents.get(intent.item.artifact_id)
            if current != intent:
                raise JobUnavailable
            current = replace(intent, verified_at=occurred_at)
            self.deletion_intents[intent.item.artifact_id] = current
            return current

    def mark_artifact_deleted(self, intent, occurred_at):
        with self.lock:
            item = intent.item
            report = self.reports.get(item.run_id)
            if report is None:
                raise JobUnavailable
            matches = [
                candidate
                for candidate in report.artifacts
                if candidate.artifact_id == item.artifact_id
            ]
            if len(matches) != 1 or matches[0] != item:
                raise JobUnavailable
            reference = item.reference
            if (
                reference.retention_class != "raw_30d"
                or reference.expires_at is None
                or reference.expires_at > occurred_at
                or reference.deleted_at is not None
                or intent.reason != "raw_retention_expired"
                or intent.verified_at is None
                or self.deletion_intents.get(item.artifact_id) != intent
            ):
                raise JobUnavailable
            deleted = replace(
                item,
                reference=replace(
                    reference,
                    deleted_at=occurred_at,
                    deleted_by=intent.actor_user_id,
                    deletion_reason=intent.reason,
                ),
            )
            artifacts = tuple(
                deleted if candidate.artifact_id == item.artifact_id else candidate
                for candidate in report.artifacts
            )
            self.reports[item.run_id] = replace(report, artifacts=artifacts)
