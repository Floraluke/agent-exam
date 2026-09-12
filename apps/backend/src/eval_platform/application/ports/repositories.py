from typing import Protocol

from eval_platform.domain.catalog import CatalogTask, RegisteredAgent
from eval_platform.domain.jobs.decisions import OwnerDecision
from eval_platform.domain.jobs.models import EvaluationJob


class TaskRepository(Protocol):
    """Publish task + artifact index atomically, never exposing partial records.

    Same identity/content returns the original record; changed content conflicts.
    Query order is stable task UUID order, not a cross-page snapshot.
    """

    def publish(self, record: CatalogTask) -> CatalogTask: ...

    def get(self, task_id: str) -> CatalogTask: ...

    def list(
        self, filters: dict[str, str], cursor: str | None, limit: int
    ) -> list[CatalogTask]: ...


class AgentConfigurationRepository(Protocol):
    """Immutable fingerprint registration; disable preserves historical identity."""

    def register(self, record: RegisteredAgent) -> RegisteredAgent: ...

    def get(self, configuration_id: str) -> RegisteredAgent: ...

    def list(
        self,
        enabled: bool | None,
        cursor: str | None,
        limit: int,
    ) -> list[RegisteredAgent]: ...

    def disable(self, configuration_id: str) -> None: ...


class JobRepository(Protocol):
    """Atomically publish a complete frozen Job and resolve scoped replays."""

    def resolve_idempotency(
        self, created_by: str, key_hash: str, request_sha256: str
    ) -> EvaluationJob | None: ...

    def create(
        self, record: EvaluationJob, key_hash: str, request_sha256: str
    ) -> EvaluationJob: ...

    def get(self, job_id: str) -> EvaluationJob: ...

    def list(
        self,
        created_by: str | None,
        filters: dict[str, str],
        cursor: str | None,
        limit: int,
    ) -> list[EvaluationJob]: ...

    def decide(self, decision: OwnerDecision) -> EvaluationJob: ...
