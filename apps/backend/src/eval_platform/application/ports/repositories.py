from datetime import datetime
from typing import Protocol

from eval_platform.domain.catalog import CatalogTask, RegisteredAgent
from eval_platform.domain.jobs.cancellation import CancellationRequest
from eval_platform.domain.jobs.decisions import OwnerDecision
from eval_platform.domain.jobs.execution import (
    ClaimedJob,
    JobLease,
    JobReport,
    RunCompletion,
    RunReport,
    TrialStart,
)
from eval_platform.domain.jobs.models import EvaluationJob
from eval_platform.domain.result import ExecutionTrialResult


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

    def cancel(self, request: CancellationRequest) -> EvaluationJob: ...

    def claim(self, worker_id: str, now: datetime) -> ClaimedJob | None: ...

    def start_execution(self, lease: JobLease, now: datetime) -> JobLease: ...

    def start_run(self, lease: JobLease, run_id: str, now: datetime) -> TrialStart: ...

    def finish_run_execution(
        self, lease: JobLease, run_id: str, now: datetime
    ) -> JobLease: ...

    def start_verifying(
        self, lease: JobLease, trial: ExecutionTrialResult, now: datetime
    ) -> JobLease: ...

    def complete(self, lease: JobLease, completion: RunCompletion) -> JobLease: ...

    def fail(
        self,
        lease: JobLease,
        run_id: str,
        code: str,
        summary: str,
        now: datetime,
        trial: ExecutionTrialResult | None = None,
    ) -> JobLease: ...

    def start_finalizing(self, lease: JobLease, now: datetime) -> JobLease: ...

    def finish(
        self,
        lease: JobLease,
        now: datetime,
        failure_code: str | None = None,
    ) -> None: ...

    def get_run_report(self, run_id: str) -> RunReport: ...

    def get_artifact_report(self, artifact_id: str) -> RunReport: ...

    def get_job_report(self, job_id: str) -> JobReport: ...
