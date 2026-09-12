"""Immutable Job, Run and submission values with safe failure categories."""

from dataclasses import dataclass
from datetime import datetime
from typing import Literal

from eval_platform.domain.jobs.snapshots import (
    AgentSnapshot as AgentSnapshot,
)
from eval_platform.domain.jobs.snapshots import (
    LimitSnapshot as LimitSnapshot,
)
from eval_platform.domain.jobs.snapshots import (
    NetworkPolicySnapshot as NetworkPolicySnapshot,
)
from eval_platform.domain.jobs.snapshots import (
    TaskSnapshot as TaskSnapshot,
)
from eval_platform.domain.jobs.snapshots import (
    ToolProfileSnapshot as ToolProfileSnapshot,
)

JobStatus = Literal[
    "AWAITING_OWNER_APPROVAL",
    "QUEUED",
    "PREPARING",
    "EXECUTING",
    "FINALIZING",
    "COMPLETED",
    "COMPLETED_WITH_ERRORS",
    "FAILED",
    "REJECTED",
]
RunStatus = Literal[
    "PENDING",
    "PREPARING",
    "RUNNING_AGENT",
    "VERIFYING",
    "COMPLETED",
    "FAILED",
    "CANCELED",
]
ResultScope = Literal["official", "internal_test"]


class JobError(Exception):
    """Safe Job submission failure category."""


class JobInputError(JobError):
    def __init__(self, code: str) -> None:
        self.code = code


class JobConfigurationDisabled(JobError):
    pass


class JobIdempotencyConflict(JobError):
    pass


class EvidenceNotFound(JobError):
    pass


class EvidenceNotReady(JobError):
    pass


class JobNotFound(JobError):
    pass


class JobUnavailable(JobError):
    pass


@dataclass(frozen=True, slots=True)
class StateEvent:
    event_id: str
    sequence: int
    from_status: str | None
    to_status: str
    reason_code: str
    occurred_at: datetime
    actor_user_id: str | None = None
    note: str | None = None
    worker_id: str | None = None


@dataclass(frozen=True, slots=True)
class EvaluationRun:
    run_id: str
    job_id: str
    task: TaskSnapshot
    agent: AgentSnapshot
    status: RunStatus
    backend_kind: str
    backend_revision: str
    execution_contract_version: str
    created_at: datetime
    state_events: tuple[StateEvent, ...]
    row_version: int = 0
    stage: str | None = None
    backend_job_ref: str | None = None
    backend_trial_ref: str | None = None
    failure_code: str | None = None
    failure_summary: str | None = None
    resolved_summary: bool | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None


def run_order_key(run: EvaluationRun) -> tuple[str, str, str]:
    """Match Harbor's deterministic task-then-Agent Cartesian order."""

    return (
        run.task.task_id,
        run.agent.agent_configuration_id,
        run.run_id,
    )


@dataclass(frozen=True, slots=True)
class EvaluationJob:
    job_id: str
    created_by: str
    created_at: datetime
    status: JobStatus
    evaluation_track: str
    result_scope: ResultScope
    batch_preset: str
    limit_profile_id: str
    limit_snapshot: LimitSnapshot
    network_policy_id: str
    network_policy_snapshot: NetworkPolicySnapshot
    tool_profile_id: str
    tool_profile_snapshot: ToolProfileSnapshot
    harbor_revision: str
    swe_gym_revision: str
    swe_bench_fork_revision: str
    runs: tuple[EvaluationRun, ...]
    state_events: tuple[StateEvent, ...]
    owner_decided_by: str | None = None
    owner_decided_at: datetime | None = None
    owner_decision_reason: str | None = None
    row_version: int = 0
    claimed_by: str | None = None
    claimed_at: datetime | None = None
    heartbeat_at: datetime | None = None
    lease_expires_at: datetime | None = None
    failure_code: str | None = None
    failure_summary: str | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None

    @property
    def trial_count(self) -> int:
        return len(self.runs)
