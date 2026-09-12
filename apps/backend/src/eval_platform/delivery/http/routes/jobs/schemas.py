"""Strict public Job HTTP shapes; private credential references stay excluded."""

from dataclasses import asdict
from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from eval_platform.domain.jobs.models import EvaluationJob, JobStatus, RunStatus
from eval_platform.domain.jobs.policy import SubmissionPolicy


class JobRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    task_ids: list[UUID] = Field(max_length=60)
    agent_configuration_ids: list[UUID] = Field(max_length=60)
    evaluation_track: str = Field(min_length=1, max_length=64)
    batch_preset: str = Field(min_length=1, max_length=64)
    limit_profile_id: str = Field(min_length=1, max_length=64)


class StateEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    sequence: int
    from_status: str | None
    to_status: str
    reason_code: str
    occurred_at: datetime
    actor_user_id: str | None
    note: str | None


class TaskSnapshotResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    task_id: str
    instance_id: str
    dataset_id: str
    dataset_revision: str
    split: str
    repo: str
    base_commit: str
    problem_statement: str


class AgentSnapshotResponse(BaseModel):
    agent_configuration_id: str
    display_name: str
    agent_type: str
    agent_version: str
    model_provider: str
    model: str
    reasoning_effort: str
    configuration_fingerprint: str


class RunResponse(BaseModel):
    run_id: str
    task_id: str
    agent_configuration_id: str
    status: RunStatus
    backend_kind: str
    backend_revision: str
    execution_contract_version: str
    state_events: list[StateEventResponse]


class JobSummary(BaseModel):
    job_id: str
    status: JobStatus
    evaluation_track: Literal["closed_book"]
    result_scope: Literal["official", "internal_test"]
    batch_preset: str
    limit_profile_id: str
    trial_count: int
    run_ids: list[str]
    estimated_finish_at: None = None
    created_at: datetime
    owner_decided_by: str | None
    owner_decided_at: datetime | None
    owner_decision_reason: str | None

    @classmethod
    def from_record(cls, record: EvaluationJob) -> "JobSummary":
        return cls(
            job_id=record.job_id,
            status=record.status,
            evaluation_track="closed_book",
            result_scope=record.result_scope,
            batch_preset=record.batch_preset,
            limit_profile_id=record.limit_profile_id,
            trial_count=record.trial_count,
            run_ids=[run.run_id for run in record.runs],
            created_at=record.created_at,
            owner_decided_by=record.owner_decided_by,
            owner_decided_at=record.owner_decided_at,
            owner_decision_reason=record.owner_decision_reason,
        )


class JobDetail(JobSummary):
    task_snapshots: list[TaskSnapshotResponse]
    agent_snapshots: list[AgentSnapshotResponse]
    limit_snapshot: dict[str, int]
    network_policy_id: str
    network_policy_snapshot: dict[str, object]
    tool_profile_id: str
    tool_profile_snapshot: dict[str, object]
    harbor_revision: str
    swe_gym_revision: str
    swe_bench_fork_revision: str
    job_state_events: list[StateEventResponse]
    runs: list[RunResponse]

    @classmethod
    def from_record(cls, record: EvaluationJob) -> "JobDetail":
        summary = JobSummary.from_record(record).model_dump()
        tasks = {run.task.task_id: run.task for run in record.runs}
        agents = {run.agent.agent_configuration_id: run.agent for run in record.runs}
        return cls(
            **summary,
            task_snapshots=[
                TaskSnapshotResponse.model_validate(item) for item in tasks.values()
            ],
            agent_snapshots=[
                AgentSnapshotResponse(
                    **{
                        key: getattr(item, key)
                        for key in AgentSnapshotResponse.model_fields
                    }
                )
                for item in agents.values()
            ],
            limit_snapshot=asdict(record.limit_snapshot),
            network_policy_id=record.network_policy_id,
            network_policy_snapshot=asdict(record.network_policy_snapshot),
            tool_profile_id=record.tool_profile_id,
            tool_profile_snapshot=asdict(record.tool_profile_snapshot),
            harbor_revision=record.harbor_revision,
            swe_gym_revision=record.swe_gym_revision,
            swe_bench_fork_revision=record.swe_bench_fork_revision,
            job_state_events=[
                StateEventResponse.model_validate(item) for item in record.state_events
            ],
            runs=[
                RunResponse(
                    run_id=run.run_id,
                    task_id=run.task.task_id,
                    agent_configuration_id=run.agent.agent_configuration_id,
                    status=run.status,
                    backend_kind=run.backend_kind,
                    backend_revision=run.backend_revision,
                    execution_contract_version=run.execution_contract_version,
                    state_events=[
                        StateEventResponse.model_validate(item)
                        for item in run.state_events
                    ],
                )
                for run in record.runs
            ],
        )


class JobPage(BaseModel):
    items: list[JobSummary]
    next_cursor: str | None


class JobOptionsResponse(BaseModel):
    batch_presets: list[dict[str, int | str]]
    evaluation_tracks: list[str]
    limit_profiles: list[dict[str, int | str]]
    maximum_agent_configurations: int
    maximum_runs: int

    @classmethod
    def from_policy(cls, policy: SubmissionPolicy) -> "JobOptionsResponse":
        return cls(
            batch_presets=[
                {
                    "batch_preset": item.batch_preset,
                    "minimum_tasks": item.minimum_tasks,
                    "maximum_tasks": item.maximum_tasks,
                }
                for item in policy.batch_presets
            ],
            evaluation_tracks=["closed_book"],
            limit_profiles=[
                {"limit_profile_id": item.limit_profile_id, **asdict(item.snapshot())}
                for item in policy.limit_profiles
            ],
            maximum_agent_configurations=policy.maximum_agent_configurations,
            maximum_runs=policy.maximum_runs,
        )
