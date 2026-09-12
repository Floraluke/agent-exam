"""Thin Worker shell: claim once, then delegate all business flow."""

from collections.abc import Callable
from datetime import UTC, datetime

from eval_platform.application.execute_job import JobExecutor
from eval_platform.application.ports.repositories import JobRepository


class WorkerShell:
    def __init__(
        self,
        repository: JobRepository,
        executor: JobExecutor,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self.repository = repository
        self.executor = executor
        self.clock = clock

    def run_once(self, worker_id: str) -> bool:
        claimed = self.repository.claim(worker_id, self.clock())
        if claimed is None:
            return False
        self.executor.execute(claimed)
        return True
