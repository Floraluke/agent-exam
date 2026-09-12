"""Immutable Job, Run and submission values with safe failure categories."""

from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
from typing import Literal

from eval_platform.domain.catalog import CatalogTask, RegisteredAgent

JobStatus = Literal["AWAITING_OWNER_APPROVAL"]
RunStatus = Literal["PENDING"]
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


class JobNotFound(JobError):
    pass


class JobUnavailable(JobError):
    pass


@dataclass(frozen=True, slots=True)
class LimitSnapshot:
    agent_wall_timeout_sec: int
    agent_cpus: int
    agent_memory_mb: int
    agent_storage_mb: int
    evaluator_wall_timeout_sec: int
    evaluator_cpus: int
    evaluator_memory_mb: int
    pids_limit: int
    patch_warning_bytes: int
    patch_max_bytes: int
    raw_artifact_max_bytes: int
    raw_run_max_bytes: int
    concurrency: int
    max_retries: int


@dataclass(frozen=True, slots=True)
class NetworkPolicySnapshot:
    mode: str
    web_search: str
    arbitrary_hosts: bool


@dataclass(frozen=True, slots=True)
class ToolProfileSnapshot:
    agent_type: str
    web_search: str
    arbitrary_commands: bool


@dataclass(frozen=True, slots=True)
class TaskSnapshot:
    task_id: str
    instance_id: str
    dataset_id: str
    dataset_revision: str
    split: str
    repo: str
    base_commit: str
    problem_statement: str
    environment_image: str
    raw_record_sha256: str
    problem_sha256: str
    artifact_id: str
    source_object_key: str
    source_sha256: str

    @classmethod
    def from_record(cls, record: CatalogTask) -> "TaskSnapshot":
        task, source = record.task, record.source
        return cls(
            record.task_id,
            task.instance_id,
            task.dataset_id,
            task.dataset_revision,
            task.split,
            task.repo,
            task.base_commit,
            task.problem_statement,
            task.environment_image,
            task.raw_record_sha256,
            sha256(task.problem_statement.encode()).hexdigest(),
            record.artifact_id,
            source.object_key,
            source.sha256,
        )


@dataclass(frozen=True, slots=True)
class AgentSnapshot:
    agent_configuration_id: str
    display_name: str
    agent_type: str
    agent_version: str
    model_provider: str
    model: str
    authentication_type: str
    credential_profile_id: str
    reasoning_effort: str
    configuration_fingerprint: str

    @classmethod
    def from_record(cls, record: RegisteredAgent) -> "AgentSnapshot":
        configuration = record.configuration
        return cls(
            configuration.configuration_id,
            record.display_name,
            configuration.agent_name,
            configuration.agent_version,
            configuration.model_provider,
            configuration.model_name,
            configuration.authentication_type,
            configuration.credential_configuration_id,
            str(configuration.critical_config["reasoning_effort"]),
            configuration.fingerprint,
        )


@dataclass(frozen=True, slots=True)
class StateEvent:
    event_id: str
    sequence: int
    from_status: str | None
    to_status: str
    reason_code: str
    occurred_at: datetime


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

    @property
    def trial_count(self) -> int:
        return len(self.runs)
