from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from eval_platform.domain.agent import AgentConfiguration
from eval_platform.domain.jobs.models import EvaluationJob, EvaluationRun
from eval_platform.domain.result import ExecutionTrialResult
from eval_platform.domain.task import EvaluationTask


@dataclass(frozen=True, slots=True)
class RunLimits:
    wall_timeout_sec: int
    cpus: int
    memory_mb: int
    storage_mb: int

    def __post_init__(self) -> None:
        if min(self.wall_timeout_sec, self.cpus, self.memory_mb, self.storage_mb) <= 0:
            raise ValueError("Execution limits must be positive")


@dataclass(frozen=True, slots=True)
class ExecutionRunRequest:
    run_id: str
    task: EvaluationTask
    agent: AgentConfiguration
    attempt_index: int = 1

    def __post_init__(self) -> None:
        if not self.run_id:
            raise ValueError("run_id must not be empty")
        if self.attempt_index != 1:
            raise ValueError("MVP permits exactly one attempt per Agent and task")


@dataclass(frozen=True, slots=True)
class ExecutionJobRequest:
    job_id: str
    runs: tuple[ExecutionRunRequest, ...]
    limits: RunLimits
    backend_revision: str
    artifact_contract_version: str
    evaluation_track: str = "closed_book"

    def __post_init__(self) -> None:
        if not self.job_id or not self.runs:
            raise ValueError("An execution job needs an identity and at least one run")
        if self.evaluation_track != "closed_book":
            raise ValueError("MVP only permits the closed_book evaluation track")
        run_ids = [run.run_id for run in self.runs]
        if len(run_ids) != len(set(run_ids)):
            raise ValueError("run_id values must be unique within a job")

    @classmethod
    def single_run(
        cls,
        job: EvaluationJob,
        run: EvaluationRun,
        task: EvaluationTask,
        agent: AgentConfiguration,
    ) -> ExecutionJobRequest:
        limits = job.limit_snapshot
        return cls(
            job.job_id,
            (ExecutionRunRequest(run.run_id, task, agent),),
            RunLimits(
                limits.agent_wall_timeout_sec,
                limits.agent_cpus,
                limits.agent_memory_mb,
                limits.agent_storage_mb,
            ),
            run.backend_revision,
            run.execution_contract_version,
            job.evaluation_track,
        )


class ExecutionBackend(Protocol):
    def execute(
        self,
        request: ExecutionJobRequest,
        progress: ExecutionProgressObserver | None = None,
    ) -> tuple[ExecutionTrialResult, ...]:
        """Execute registered runs without deciding whether their patches pass."""


class ExecutionProgressObserver(Protocol):
    """Accept normalized Trial identities; it never trusts backend log text."""

    def trial_started(self, run_id: str) -> bool:
        """Atomically permit a Trial; false means it must not be started."""

    def trial_finished(self, run_id: str) -> None: ...
