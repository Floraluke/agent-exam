from dataclasses import asdict
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from eval_platform.domain.leaderboard import LeaderboardPage, LeaderboardRow


class ComparisonScopeResponse(BaseModel):
    dataset_id: str
    dataset_revision: str
    split: str
    repo: str
    evaluation_track: str
    network_policy_id: str
    network_policy_snapshot: dict[str, object]
    tool_profile_id: str
    tool_profile_snapshot: dict[str, object]
    limit_profile_id: str
    limit_snapshot: dict[str, object]
    harbor_revision: str
    swe_gym_revision: str
    swe_bench_fork_revision: str
    execution_contract_version: str


class AgentIdentityResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    agent_configuration_id: str
    display_name: str
    agent_type: str
    agent_version: str
    model_provider: str
    model: str
    reasoning_effort: str
    configuration_fingerprint: str


class MetricValueResponse(BaseModel):
    value: int | float | None
    coverage: int


class ProcessMetricsResponse(BaseModel):
    selected_runs: int
    n_input_tokens: MetricValueResponse
    n_cache_tokens: MetricValueResponse
    n_output_tokens: MetricValueResponse
    cost_usd: MetricValueResponse
    wall_time_sec: MetricValueResponse
    cpu_time_sec: MetricValueResponse
    peak_memory_bytes: MetricValueResponse


class SourceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    task_id: str
    instance_id: str
    job_id: str
    run_id: str
    rerun_of_job_id: str | None
    classification: str


class LeaderboardRowResponse(BaseModel):
    rank: int
    comparison_scope: ComparisonScopeResponse
    agent: AgentIdentityResponse
    total_tasks: int
    deterministic_count: int
    resolved_count: int
    unresolved_count: int
    infrastructure_error_count: int
    unknown_count: int
    resolved_rate: float
    process_metrics: ProcessMetricsResponse
    sources: list[SourceResponse]
    quality_tiebreak: None = None
    generated_at: datetime

    @classmethod
    def from_record(cls, row: LeaderboardRow) -> "LeaderboardRowResponse":
        metrics = row.metrics

        def metric(name: str) -> MetricValueResponse:
            return MetricValueResponse(
                value=getattr(metrics, name),
                coverage=getattr(metrics, f"{name}_coverage"),
            )

        return cls(
            rank=row.rank,
            comparison_scope=ComparisonScopeResponse.model_validate(asdict(row.scope)),
            agent=AgentIdentityResponse.model_validate(row.agent),
            total_tasks=row.total_tasks,
            deterministic_count=row.deterministic_count,
            resolved_count=row.resolved_count,
            unresolved_count=row.unresolved_count,
            infrastructure_error_count=row.infrastructure_error_count,
            unknown_count=row.unknown_count,
            resolved_rate=row.resolved_rate,
            process_metrics=ProcessMetricsResponse(
                selected_runs=metrics.selected_runs,
                n_input_tokens=metric("n_input_tokens"),
                n_cache_tokens=metric("n_cache_tokens"),
                n_output_tokens=metric("n_output_tokens"),
                cost_usd=metric("cost_usd"),
                wall_time_sec=metric("wall_time_sec"),
                cpu_time_sec=metric("cpu_time_sec"),
                peak_memory_bytes=metric("peak_memory_bytes"),
            ),
            sources=[SourceResponse.model_validate(item) for item in row.sources],
            generated_at=row.generated_at,
        )


class LeaderboardPageResponse(BaseModel):
    items: list[LeaderboardRowResponse]
    next_cursor: str | None

    @classmethod
    def from_record(cls, page: LeaderboardPage) -> "LeaderboardPageResponse":
        return cls(
            items=[LeaderboardRowResponse.from_record(item) for item in page.items],
            next_cursor=page.next_cursor,
        )
