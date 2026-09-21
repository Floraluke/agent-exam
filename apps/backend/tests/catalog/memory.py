"""Synthetic adapters for external source/database/object-storage boundaries."""

from dataclasses import replace
from datetime import UTC, datetime
from hashlib import sha256

from eval_platform.domain.catalog import (
    AgentConfigurationNotFound,
    ArtifactUnavailable,
    CatalogConflict,
    TaskNotFound,
)


class MemoryTasks:
    def __init__(self):
        self.records = {}

    def publish(self, record):
        for original in self.records.values():
            if original.identity == record.identity:
                if original.task != record.task or original.source != record.source:
                    # Timestamps are metadata, not content identity.
                    if original.task != record.task:
                        raise CatalogConflict
                return original
        self.records[record.task_id] = record
        return record

    def get(self, task_id):
        if task_id not in self.records:
            raise TaskNotFound
        return self.records[task_id]

    def list(self, filters, cursor, limit):
        return [
            record
            for key, record in sorted(self.records.items())
            if (cursor is None or key > cursor)
            and all(
                getattr(record.task, field) == value for field, value in filters.items()
            )
        ][:limit]


class MemoryArtifacts:
    def __init__(self):
        self.objects = {}

    def put_immutable(self, reference, content):
        if reference.object_key not in self.objects:
            self.objects[reference.object_key] = content
        self.read_verified(reference)

    def read_verified(self, reference):
        data = self.objects.get(reference.object_key)
        if data is None or len(data) != reference.size_bytes:
            raise ArtifactUnavailable
        if sha256(data).hexdigest() != reference.sha256:
            raise ArtifactUnavailable
        return data


class FixedSource:
    def __init__(self, bundle):
        self.bundles = {bundle.public.instance_id: bundle}

    def load(self, instance_id):
        return self.bundles[instance_id]


class MemoryAgents:
    def __init__(self):
        self.records = {}

    def register(self, record):
        for original in self.records.values():
            if original.configuration.fingerprint == record.configuration.fingerprint:
                return original
        self.records[record.configuration.configuration_id] = record
        return record

    def get(self, configuration_id):
        if configuration_id not in self.records:
            raise AgentConfigurationNotFound
        return self.records[configuration_id]

    def list(self, agent_type, enabled, cursor, limit):
        return [
            record
            for key, record in sorted(self.records.items())
            if (agent_type is None or record.configuration.agent_name == agent_type)
            and (enabled is None or record.enabled == enabled)
            and (cursor is None or key > cursor)
        ][:limit]

    def disable(self, configuration_id):
        record = self.get(configuration_id)
        if record.enabled:
            self.records[configuration_id] = replace(
                record,
                enabled=False,
                disabled_at=datetime.now(UTC),
            )
