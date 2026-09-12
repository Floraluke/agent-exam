from typing import Protocol

from eval_platform.domain.catalog import CatalogTask, RegisteredAgent


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
