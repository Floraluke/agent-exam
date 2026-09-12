from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path
from typing import Any

from eval_platform.adapters.execution.harbor.artifacts import PatchArtifactError
from eval_platform.adapters.execution.harbor.config_mapper import (
    HarborJobPlan,
    harbor_agent_key,
    harbor_task_path_key,
)
from eval_platform.adapters.execution.harbor.result_values import (
    exception_reason,
    file_ref,
    patch_error_reason,
    patch_ref,
    read_json,
    required_mapping,
    required_string,
    resource_summary,
    trajectory_ref,
    usage_summary,
)
from eval_platform.domain.result import ExecutionTrialResult, TerminationReason


def map_job_results(
    plan: HarborJobPlan,
    job_dir: Path,
    *,
    process_returncode: int,
    process_failure_reason: TerminationReason | None = None,
    process_warnings: tuple[str, ...] = (),
) -> tuple[ExecutionTrialResult, ...]:
    try:
        job_ref = required_string(read_json(job_dir / "result.json"), "id")
    except (OSError, ValueError, json.JSONDecodeError):
        return _missing_results(
            plan,
            str(job_dir.resolve()),
            process_failure_reason or TerminationReason.INFRASTRUCTURE_INTERRUPTED,
            _failure_warnings("HARBOR_JOB_RESULT_MISSING", process_warnings),
        )

    bindings = {
        (binding.task_path_key, binding.agent_key): binding for binding in plan.bindings
    }
    mapped: dict[str, ExecutionTrialResult] = {}
    protocol_warnings: list[str] = []
    for result_path in sorted(job_dir.glob("*/result.json")):
        try:
            trial_data = read_json(result_path)
            binding = bindings.get(trial_key(trial_data))
            if binding is None:
                protocol_warnings.append("UNEXPECTED_HARBOR_TRIAL")
                continue
            if binding.run_id in mapped:
                protocol_warnings.append("DUPLICATE_HARBOR_TRIAL")
                continue
            mapped[binding.run_id] = _map_trial(
                run_id=binding.run_id,
                job_ref=job_ref,
                trial_dir=result_path.parent,
                trial_data=trial_data,
                process_returncode=process_returncode,
                process_warnings=process_warnings,
            )
        except (OSError, ValueError, json.JSONDecodeError):
            protocol_warnings.append("INVALID_HARBOR_TRIAL_RESULT")

    results: list[ExecutionTrialResult] = []
    for binding in plan.bindings:
        result = mapped.get(binding.run_id)
        if result is None:
            reason = process_failure_reason or (
                TerminationReason.BACKEND_PROTOCOL_ERROR
                if process_returncode == 0
                else TerminationReason.INFRASTRUCTURE_INTERRUPTED
            )
            result = _failed_result(
                binding.run_id,
                job_ref,
                reason,
                _failure_warnings("HARBOR_TRIAL_RESULT_MISSING", process_warnings),
            )
        if protocol_warnings:
            result = replace(
                result,
                warnings=(*result.warnings, *dict.fromkeys(protocol_warnings)),
            )
        results.append(result)
    return tuple(results)


def trial_key(data: dict[str, Any]) -> tuple[str, str]:
    config = required_mapping(data, "config")
    task = required_mapping(config, "task")
    agent = required_mapping(config, "agent")
    return (
        harbor_task_path_key(required_string(task, "path")),
        harbor_agent_key(agent),
    )


def _map_trial(
    *,
    run_id: str,
    job_ref: str,
    trial_dir: Path,
    trial_data: dict[str, Any],
    process_returncode: int,
    process_warnings: tuple[str, ...],
) -> ExecutionTrialResult:
    trial_ref = required_string(trial_data, "id")
    warnings: list[str] = []
    raw_config_ref = file_ref(
        trial_dir / "config.json", "harbor_trial_config", "application/json"
    )
    raw_result_ref = file_ref(
        trial_dir / "result.json", "harbor_trial_result", "application/json"
    )
    exception = trial_data.get("exception_info")
    patch = None
    if exception is None:
        try:
            patch = patch_ref(trial_dir)
            reason = TerminationReason.COMPLETED
        except PatchArtifactError as error:
            reason = patch_error_reason(error)
            warnings.append(error.code)
    else:
        if not isinstance(exception, dict):
            raise ValueError("Harbor exception_info must be an object or null")
        reason = exception_reason(required_string(exception, "exception_type"))

    trajectory, trajectory_warning = trajectory_ref(trial_dir)
    usage, usage_warning = usage_summary(trial_data.get("agent_result"))
    resources, timing_warning = resource_summary(trial_data)
    warnings.extend(
        warning
        for warning in (trajectory_warning, usage_warning, timing_warning)
        if warning is not None
    )
    warnings.extend(process_warnings)
    if process_returncode != 0 and "HARBOR_PROCESS_TIMEOUT" not in process_warnings:
        warnings.append(f"HARBOR_PROCESS_EXIT_{process_returncode}")
    return ExecutionTrialResult(
        run_id=run_id,
        backend_job_ref=job_ref,
        backend_trial_ref=trial_ref,
        termination_reason=reason,
        patch_ref=patch,
        trajectory_ref=trajectory,
        raw_config_ref=raw_config_ref,
        raw_result_ref=raw_result_ref,
        usage=usage,
        resource_summary=resources,
        warnings=tuple(warnings),
    )


def _missing_results(
    plan: HarborJobPlan,
    job_ref: str,
    reason: TerminationReason,
    warnings: tuple[str, ...],
) -> tuple[ExecutionTrialResult, ...]:
    return tuple(
        _failed_result(binding.run_id, job_ref, reason, warnings)
        for binding in plan.bindings
    )


def _failed_result(
    run_id: str,
    job_ref: str,
    reason: TerminationReason,
    warnings: tuple[str, ...],
) -> ExecutionTrialResult:
    return ExecutionTrialResult(
        run_id=run_id,
        backend_job_ref=job_ref,
        backend_trial_ref="",
        termination_reason=reason,
        patch_ref=None,
        trajectory_ref=None,
        warnings=warnings,
    )


def _failure_warnings(
    primary: str, process_warnings: tuple[str, ...]
) -> tuple[str, ...]:
    return primary, *process_warnings
