"""Authorize explicit recovery without resuming an interrupted execution."""

from collections.abc import Callable
from datetime import UTC, datetime

from eval_platform.application.job_submission import JobSubmission
from eval_platform.application.ports.repositories import JobRepository
from eval_platform.domain.identity import AuthenticatedActor
from eval_platform.domain.jobs.decisions import JobStateConflict, OwnerApprovalRequired
from eval_platform.domain.jobs.execution import RecoveryRequest
from eval_platform.domain.jobs.models import EvaluationJob


class JobRecovery:
    def __init__(
        self,
        repository: JobRepository,
        submission: JobSubmission,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self.repository = repository
        self.submission = submission
        self.clock = clock

    def recover(self, actor: AuthenticatedActor, job_id: str) -> EvaluationJob:
        if actor.role != "owner":
            raise OwnerApprovalRequired
        return self.repository.recover(
            RecoveryRequest(job_id, actor.user_id, self.clock())
        )

    def retry(
        self,
        actor: AuthenticatedActor,
        job_id: str,
        idempotency_key: str,
    ) -> EvaluationJob:
        if actor.role != "owner":
            raise OwnerApprovalRequired
        source = self.repository.get(job_id)
        recovered = any(
            event.reason_code == "INTERRUPTION_RECOVERED"
            for event in source.state_events
        )
        if not recovered or source.status not in {
            "FAILED",
            "COMPLETED_WITH_ERRORS",
            "CANCELED",
        }:
            raise JobStateConflict
        tasks = sorted({run.task.task_id for run in source.runs})
        agents = sorted({run.agent.agent_configuration_id for run in source.runs})
        return self.submission.submit(
            actor,
            tasks,
            agents,
            source.evaluation_track,
            source.batch_preset,
            source.limit_profile_id,
            idempotency_key,
            created_by=source.created_by,
            rerun_of_job_id=source.job_id,
        )
