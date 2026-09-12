"""Server-owned submission presets; callers select IDs, never resource values."""

import hashlib
import json
from dataclasses import dataclass

from eval_platform.domain.jobs.models import (
    LimitSnapshot,
    NetworkPolicySnapshot,
    ResultScope,
    ToolProfileSnapshot,
)


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
) -> str:
    body = json.dumps(
        {
            "task_ids": tasks,
            "agent_configuration_ids": agents,
            "evaluation_track": track,
            "batch_preset": batch,
            "limit_profile_id": limits,
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(body.encode()).hexdigest()
