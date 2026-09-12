"""Versioned trusted Job policy composition; contains no model credential values."""

from eval_platform.adapters.evaluation.swe_bench import FORK_REVISION
from eval_platform.adapters.execution.harbor.artifacts import (
    PATCH_MAX_BYTES,
    PATCH_WARNING_BYTES,
    RAW_ARTIFACT_MAX_BYTES,
)
from eval_platform.adapters.execution.harbor.config_mapper import (
    ARTIFACT_CONTRACT_VERSION,
    HARBOR_REVISION,
)
from eval_platform.adapters.tasks.swe_gym import DATASET_REVISION
from eval_platform.domain.jobs.models import (
    NetworkPolicySnapshot,
    ResultScope,
    ToolProfileSnapshot,
)
from eval_platform.domain.jobs.policy import BatchPreset, LimitProfile, SubmissionPolicy


def submission_policy(result_scope: ResultScope = "official") -> SubmissionPolicy:
    return SubmissionPolicy(
        batch_presets=(
            BatchPreset("demo", 1, 3),
            BatchPreset("quick", 5, 5),
            BatchPreset("standard", 10, 20),
        ),
        limit_profiles=(
            LimitProfile(
                "default-single-host-v1",
                900,
                1,
                4096,
                8192,
                300,
                1,
                4096,
                64,
                PATCH_WARNING_BYTES,
                PATCH_MAX_BYTES,
                RAW_ARTIFACT_MAX_BYTES,
                200 * 1024 * 1024,
                1,
                0,
            ),
        ),
        result_scope=result_scope,
        network_policy_id="agentexam-closed-book-v1",
        network_policy_snapshot=NetworkPolicySnapshot(
            "registered_model_endpoints_only", "disabled", False
        ),
        tool_profile_id="codex-fixed-v1",
        tool_profile_snapshot=ToolProfileSnapshot("codex", "disabled", False),
        harbor_revision=HARBOR_REVISION,
        swe_gym_revision=DATASET_REVISION,
        swe_bench_fork_revision=FORK_REVISION,
        execution_contract_version=ARTIFACT_CONTRACT_VERSION,
    )
