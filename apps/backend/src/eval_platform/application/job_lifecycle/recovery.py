"""Authorize explicit recovery without resuming an interrupted execution."""

from collections.abc import Callable
from datetime import UTC, datetime

from eval_platform.application.ports.repositories import JobRepository
from eval_platform.domain.identity import AuthenticatedActor
from eval_platform.domain.jobs.decisions import OwnerApprovalRequired
from eval_platform.domain.jobs.execution import RecoveryRequest
from eval_platform.domain.jobs.models import EvaluationJob


class JobRecovery:
    def __init__(
        self,
        repository: JobRepository,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self.repository = repository
        self.clock = clock

    def recover(self, actor: AuthenticatedActor, job_id: str) -> EvaluationJob:
        if actor.role != "owner":
            raise OwnerApprovalRequired
        return self.repository.recover(
            RecoveryRequest(job_id, actor.user_id, self.clock())
        )
