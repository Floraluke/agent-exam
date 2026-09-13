"""Server-owned Job submission and execution-lifecycle policy."""

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime

from eval_platform.domain.jobs.models import (
    LimitSnapshot,
    NetworkPolicySnapshot,
    ResultScope,
    ToolProfileSnapshot,
)

ENVIRONMENT_BUILD_TIMEOUT_SEC = 1800
AGENT_SETUP_TIMEOUT_SEC = 360
RESULT_COLLECTION_TIMEOUT_SEC = 60
PROCESS_TERMINATION_GRACE_SEC = 120
FINALIZATION_GRACE_SEC = 300
RECOVERABLE_JOB_STATUSES = frozenset(
    {"PREPARING", "EXECUTING", "CANCEL_REQUESTED", "FINALIZING"}
)
RECOVERY_JOB_TERMINAL_STATUSES = frozenset(
    {"COMPLETED", "COMPLETED_WITH_ERRORS", "FAILED", "CANCELED"}
)
RECOVERY_RUN_TERMINAL_STATUSES = frozenset({"COMPLETED", "FAILED", "CANCELED"})


def recovery_is_due(
    status: str, lease_expires_at: datetime | None, occurred_at: datetime
) -> bool:
    """Return whether an active Job's persisted lease is expired."""
    return (
        status in RECOVERABLE_JOB_STATUSES
        and lease_expires_at is not None
        and occurred_at >= lease_expires_at
    )


def recovery_run_outcome(
    status: str, stage: str | None
) -> tuple[str, str, str | None, str | None] | None:
    """Classify one non-terminal Run without inspecting live infrastructure."""
    if status in RECOVERY_RUN_TERMINAL_STATUSES:
        return None
    if status == "PENDING":
        return "CANCELED", "canceled", None, None
    return (
        "FAILED",
        "interrupted",
        "INFRASTRUCTURE_INTERRUPTED",
        f"运行在 {stage or status} 阶段中断。",
    )


def recovery_job_outcome(
    canceling: bool, statuses: list[str], interrupted: bool
) -> tuple[str, str | None, str | None]:
    """Classify the Job from persisted post-recovery Run statuses."""
    completed = statuses.count("COMPLETED")
    if canceling:
        return "CANCELED", None, None
    if interrupted:
        target = "COMPLETED_WITH_ERRORS" if completed else "FAILED"
        return target, "INFRASTRUCTURE_INTERRUPTED", "执行租约过期，批次已安全收束。"
    if completed == len(statuses):
        return "COMPLETED", None, None
    code = "BATCH_PARTIAL_FAILURE" if completed else "BATCH_FAILED"
    target = "COMPLETED_WITH_ERRORS" if completed else "FAILED"
    return target, code, "批次已按现有终态证据完成收束。"


def execution_process_timeout_sec(agent_timeout_sec: int, trial_count: int) -> int:
    """Bound one sequential backend process, including each Trial's setup."""
    return trial_count * (
        ENVIRONMENT_BUILD_TIMEOUT_SEC
        + AGENT_SETUP_TIMEOUT_SEC
        + agent_timeout_sec
        + RESULT_COLLECTION_TIMEOUT_SEC
        + PROCESS_TERMINATION_GRACE_SEC
    )


def worker_lease_timeout_sec(
    agent_timeout_sec: int, evaluator_timeout_sec: int, trial_count: int
) -> int:
    """Keep the lease valid through backend, evaluation, and final persistence."""
    backend = execution_process_timeout_sec(agent_timeout_sec, trial_count)
    evaluators = evaluator_timeout_sec * trial_count
    return backend + evaluators + FINALIZATION_GRACE_SEC


@dataclass(frozen=True, slots=True)
class BatchPreset:
    batch_preset: str
    minimum_tasks: int
    maximum_tasks: int


@dataclass(frozen=True, slots=True)
class LimitProfile:
    limit_profile_id: str
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

    def snapshot(self) -> LimitSnapshot:
        return LimitSnapshot(
            **{name: getattr(self, name) for name in LimitSnapshot.__dataclass_fields__}
        )


@dataclass(frozen=True, slots=True)
class SubmissionPolicy:
    batch_presets: tuple[BatchPreset, ...]
    limit_profiles: tuple[LimitProfile, ...]
    result_scope: ResultScope
    network_policy_id: str
    network_policy_snapshot: NetworkPolicySnapshot
    tool_profile_id: str
    tool_profile_snapshot: ToolProfileSnapshot
    harbor_revision: str
    swe_gym_revision: str
    swe_bench_fork_revision: str
    execution_contract_version: str
    maximum_agent_configurations: int = 3
    maximum_runs: int = 60

    def batch(self, preset_id: str) -> BatchPreset | None:
        return next(
            (item for item in self.batch_presets if item.batch_preset == preset_id),
            None,
        )

    def limits(self, profile_id: str) -> LimitProfile | None:
        return next(
            (
                item
                for item in self.limit_profiles
                if item.limit_profile_id == profile_id
            ),
            None,
        )


def canonical_request_sha(
    tasks: tuple[str, ...],
    agents: tuple[str, ...],
    track: str,
    batch: str,
    limits: str,
    rerun_of_job_id: str | None = None,
) -> str:
    payload: dict[str, object] = {
        "task_ids": tasks,
        "agent_configuration_ids": agents,
        "evaluation_track": track,
        "batch_preset": batch,
        "limit_profile_id": limits,
    }
    if rerun_of_job_id is not None:
        payload["rerun_of_job_id"] = rerun_of_job_id
    body = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(body.encode()).hexdigest()
