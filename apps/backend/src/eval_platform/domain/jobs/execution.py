"""Worker lease, persisted result and read-only report values."""

from dataclasses import dataclass
from datetime import datetime

from eval_platform.domain.agent import AgentConfiguration
from eval_platform.domain.jobs.models import (
    EvaluationJob,
    EvaluationRun,
    JobError,
    ResultScope,
    StateEvent,
)
from eval_platform.domain.result import ArtifactRef, ResourceSummary, UsageSummary
from eval_platform.domain.task import EvaluationTask


class JobLeaseConflict(JobError):
    """The worker identity, lease or optimistic version is no longer current."""


@dataclass(frozen=True, slots=True)
class RecoveryRequest:
    job_id: str
    actor_user_id: str
    occurred_at: datetime


@dataclass(frozen=True, slots=True)
class JobLease:
    job_id: str
    run_id: str
    worker_id: str
    job_version: int
    run_version: int
    lease_expires_at: datetime


@dataclass(frozen=True, slots=True)
class TrialStart:
    lease: JobLease
    started: bool


@dataclass(frozen=True, slots=True)
class ClaimedJob:
    job: EvaluationJob
    lease: JobLease


@dataclass(frozen=True, slots=True)
class RunArtifact:
    artifact_id: str
    run_id: str
    reference: ArtifactRef
    redaction_status: str = "not_required"


@dataclass(frozen=True, slots=True)
class StoredDeterministicResult:
    run_id: str
    patch_exists: bool
    patch_successfully_applied: bool
    resolved: bool
    tests_status_summary: dict[str, object]
    harness_revision: str
    report_artifact_id: str
    test_output_artifact_id: str | None
    duration_ms: int | None
    created_at: datetime


@dataclass(frozen=True, slots=True)
class ProcessMetrics:
    usage: UsageSummary
    resources: ResourceSummary


@dataclass(frozen=True, slots=True)
class RunCompletion:
    result: StoredDeterministicResult
    artifacts: tuple[RunArtifact, ...]
    process_metrics: ProcessMetrics
    backend_job_ref: str
    backend_trial_ref: str
    warnings: tuple[str, ...]
    occurred_at: datetime


@dataclass(frozen=True, slots=True)
class RunReport:
    created_by: str
    result_scope: ResultScope
    run: EvaluationRun
    deterministic_result: StoredDeterministicResult | None
    process_metrics: ProcessMetrics
    artifacts: tuple[RunArtifact, ...]
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class JobReport:
    created_by: str
    job: EvaluationJob
    run_reports: tuple[RunReport, ...]


def restore_public_task(run: EvaluationRun) -> EvaluationTask:
    task = run.task
    return EvaluationTask(
        task.dataset_id,
        task.dataset_revision,
        task.split,
        task.instance_id,
        task.repo,
        task.base_commit,
        task.problem_statement,
        task.environment_image,
        task.raw_record_sha256,
    )


def restore_agent(run: EvaluationRun) -> AgentConfiguration:
    agent = run.agent
    configuration = AgentConfiguration(
        agent.agent_configuration_id,
        agent.agent_type,
        agent.agent_version,
        agent.model_provider,
        agent.model,
        agent.authentication_type,
        agent.credential_profile_id,
        {"reasoning_effort": agent.reasoning_effort},
    )
    if configuration.fingerprint != agent.configuration_fingerprint:
        raise ValueError("Frozen Agent configuration fingerprint changed")
    return configuration


def initial_events_valid(events: tuple[StateEvent, ...]) -> bool:
    return (
        bool(events)
        and events[0].reason_code == "JOB_SUBMITTED"
        and all(event.sequence == index for index, event in enumerate(events, 1))
    )


def pending_run_valid(run: EvaluationRun) -> bool:
    return run.status == "PENDING" and initial_events_valid(run.state_events)
