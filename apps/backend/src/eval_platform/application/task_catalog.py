from collections.abc import Mapping
from datetime import UTC, datetime
from hashlib import sha256
from urllib.parse import quote
from uuid import uuid4

from eval_platform.application.ports.artifacts import ArtifactStore
from eval_platform.application.ports.repositories import TaskRepository
from eval_platform.application.ports.task_source import TaskSource
from eval_platform.domain.catalog import (
    CatalogForbidden,
    CatalogInvalid,
    CatalogTask,
    CatalogUnavailable,
)
from eval_platform.domain.identity import AuthenticatedActor
from eval_platform.domain.result import ArtifactRef


class TaskCatalog:
    def __init__(
        self,
        repository: TaskRepository,
        artifacts: ArtifactStore,
        source: TaskSource,
        presets: Mapping[str, str],
    ) -> None:
        self.repository = repository
        self.artifacts = artifacts
        self.source = source
        self.presets = dict(presets)

    def register(self, actor: AuthenticatedActor, preset_id: str) -> CatalogTask:
        if actor.role != "owner":
            raise CatalogForbidden
        instance_id = self.presets.get(preset_id)
        if instance_id is None:
            raise CatalogInvalid
        try:
            bundle = self.source.load(instance_id)
        except (OSError, ValueError):
            raise CatalogUnavailable from None
        digest = sha256(bundle.raw_record_json).hexdigest()
        if digest != bundle.public.raw_record_sha256:
            raise CatalogUnavailable
        task = bundle.public
        parts = (task.dataset_id, task.dataset_revision, task.split, task.instance_id)
        key = "tasks/" + "/".join(quote(part, safe="") for part in parts)
        now = datetime.now(UTC)
        reference = ArtifactRef(
            object_key=f"{key}/{digest}/task.json",
            artifact_type="task_source_snapshot",
            size_bytes=len(bundle.raw_record_json),
            sha256=digest,
            content_type="application/json",
            retention_class="long_term",
            created_at=now,
        )
        self.artifacts.put_immutable(reference, bundle.raw_record_json)
        self.artifacts.read_verified(reference)
        # No transaction is held while accessing object storage.
        record = CatalogTask(str(uuid4()), task, str(uuid4()), reference, now)
        return self.repository.publish(record)

    def get(self, actor: AuthenticatedActor, task_id: str) -> CatalogTask:
        record = self.repository.get(task_id)
        self.artifacts.read_verified(record.source)
        return record

    def list(
        self,
        actor: AuthenticatedActor,
        filters: dict[str, str],
        cursor: str | None,
        limit: int,
    ) -> tuple[list[CatalogTask], str | None]:
        if not 1 <= limit <= 100 or filters.keys() - {"dataset_id", "split", "repo"}:
            raise CatalogInvalid
        records = self.repository.list(filters, cursor, limit + 1)
        page = records[:limit]
        for record in page:
            self.artifacts.read_verified(record.source)
        return page, page[-1].task_id if len(records) > limit else None
