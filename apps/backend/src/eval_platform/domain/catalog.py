"""Immutable catalog identities; storage details never enter public views."""

from dataclasses import dataclass
from datetime import datetime

from eval_platform.domain.agent import AgentConfiguration
from eval_platform.domain.result import ArtifactRef
from eval_platform.domain.task import EvaluationTask


class CatalogError(Exception):
    """Safe catalog failure category, with no dependency details."""


class CatalogForbidden(CatalogError):
    pass


class CatalogInvalid(CatalogError):
    pass


class CatalogConflict(CatalogError):
    pass


class CatalogUnavailable(CatalogError):
    pass


class ArtifactUnavailable(CatalogUnavailable):
    pass


class TaskNotFound(CatalogError):
    pass


class AgentConfigurationNotFound(CatalogError):
    pass


@dataclass(frozen=True, slots=True)
class CatalogTask:
    task_id: str
    task: EvaluationTask
    artifact_id: str
    source: ArtifactRef
    created_at: datetime

    @property
    def identity(self) -> tuple[str, str, str, str]:
        task = self.task
        return task.dataset_id, task.dataset_revision, task.split, task.instance_id


@dataclass(frozen=True, slots=True)
class RegisteredAgent:
    configuration: AgentConfiguration
    display_name: str
    created_at: datetime
    enabled: bool = True
    disabled_at: datetime | None = None
    limit_profile_id: str | None = None
