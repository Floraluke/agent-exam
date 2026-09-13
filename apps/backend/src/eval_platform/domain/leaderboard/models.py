"""Immutable leaderboard comparison, source and summary values."""

from dataclasses import dataclass
from datetime import datetime
from typing import Literal

from eval_platform.domain.jobs.models import (
    LimitSnapshot,
    NetworkPolicySnapshot,
    ToolProfileSnapshot,
)

Classification = Literal["resolved", "unresolved", "infrastructure_error", "unknown"]


@dataclass(frozen=True, slots=True)
class ComparisonScope:
    dataset_id: str
    dataset_revision: str
    split: str
    repo: str
    evaluation_track: str
    network_policy_id: str
    network_policy_snapshot: NetworkPolicySnapshot
    tool_profile_id: str
    tool_profile_snapshot: ToolProfileSnapshot
    limit_profile_id: str
    limit_snapshot: LimitSnapshot
    harbor_revision: str
    swe_gym_revision: str
    swe_bench_fork_revision: str
    execution_contract_version: str


@dataclass(frozen=True, slots=True)
class AgentIdentity:
    agent_configuration_id: str
    display_name: str
    agent_type: str
    agent_version: str
    model_provider: str
    model: str
    reasoning_effort: str
    configuration_fingerprint: str


@dataclass(frozen=True, slots=True)
class AttemptMetrics:
    n_input_tokens: int | None = None
    n_cache_tokens: int | None = None
    n_output_tokens: int | None = None
    cost_usd: float | None = None
    wall_time_sec: float | None = None
    cpu_time_sec: float | None = None
    peak_memory_bytes: int | None = None


@dataclass(frozen=True, slots=True)
class LeaderboardAttempt:
    scope: ComparisonScope
    agent: AgentIdentity
    task_id: str
    instance_id: str
    job_id: str
    rerun_of_job_id: str | None
    run_id: str
    job_created_at: datetime
    finished_at: datetime
    job_status: str
    run_status: str
    failure_code: str | None
    resolved: bool | None
    result_created_at: datetime | None
    metrics: AttemptMetrics
    result_scope: str

    def __post_init__(self) -> None:
        result_present = self.resolved is not None
        if result_present != (self.result_created_at is not None):
            raise ValueError("Deterministic result identity is incomplete")
        if result_present and self.run_status != "COMPLETED":
            raise ValueError("Only completed runs have deterministic results")


@dataclass(frozen=True, slots=True)
class LeaderboardTask:
    task_id: str
    instance_id: str
    repo: str


@dataclass(frozen=True, slots=True)
class MetricSummary:
    selected_runs: int
    n_input_tokens: int | None
    n_input_tokens_coverage: int
    n_cache_tokens: int | None
    n_cache_tokens_coverage: int
    n_output_tokens: int | None
    n_output_tokens_coverage: int
    cost_usd: float | None
    cost_usd_coverage: int
    wall_time_sec: float | None
    wall_time_sec_coverage: int
    cpu_time_sec: float | None
    cpu_time_sec_coverage: int
    peak_memory_bytes: int | None
    peak_memory_bytes_coverage: int


@dataclass(frozen=True, slots=True)
class LeaderboardSource:
    task_id: str
    instance_id: str
    job_id: str
    run_id: str
    rerun_of_job_id: str | None
    classification: Classification


@dataclass(frozen=True, slots=True)
class LeaderboardRow:
    rank: int
    scope: ComparisonScope
    agent: AgentIdentity
    total_tasks: int
    deterministic_count: int
    resolved_count: int
    unresolved_count: int
    infrastructure_error_count: int
    unknown_count: int
    metrics: MetricSummary
    sources: tuple[LeaderboardSource, ...]
    generated_at: datetime

    @property
    def resolved_rate(self) -> float:
        return self.resolved_count / self.total_tasks
