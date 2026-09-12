from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from eval_platform.adapters.execution.harbor.config_mapper import (
    HarborJobPlan,
    HarborRunBinding,
    harbor_agent_key,
    harbor_task_path_key,
)
from eval_platform.adapters.execution.harbor.result_mapper import map_job_results
from eval_platform.domain.result import TerminationReason

_AGENT = {"name": "nop", "n_concurrent": 1}


def _write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8", newline="\n")


def _plan(task_dir: Path) -> HarborJobPlan:
    return HarborJobPlan(
        config={"job_name": "platform-job"},
        bindings=(
            HarborRunBinding(
                run_id="run-one",
                task_path_key=harbor_task_path_key(str(task_dir)),
                agent_key=harbor_agent_key(_AGENT),
            ),
        ),
    )


def _write_job(job_dir: Path) -> None:
    _write_json(job_dir / "result.json", {"id": "C:\\private\\harbor-job"})


def _write_patch(trial_dir: Path, content: bytes = b"") -> None:
    artifact_dir = trial_dir / "artifacts/agentexam"
    artifact_dir.mkdir(parents=True)
    (artifact_dir / "model.patch").write_bytes(content)
    (artifact_dir / "patch.sha256").write_text(
        f"{hashlib.sha256(content).hexdigest()}\n", encoding="ascii"
    )
    (artifact_dir / "patch.bytes").write_text(f"{len(content)}\n", encoding="ascii")
    (artifact_dir / "patch.binary").write_text("0\n", encoding="ascii")


def _write_trial(
    job_dir: Path,
    task_dir: Path,
    *,
    exception_type: str | None = None,
    agent_result: Any = None,
    started_at: Any = "2026-09-06T04:14:35Z",
    finished_at: Any = "2026-09-06T04:14:52Z",
    include_patch: bool = True,
    include_trajectory: bool = False,
) -> Path:
    trial_dir = job_dir / "trial-one"
    config = {"task": {"path": str(task_dir.resolve())}, "agent": _AGENT}
    result = {
        "id": "harbor-trial-id",
        "config": config,
        "exception_info": (
            {"exception_type": exception_type} if exception_type is not None else None
        ),
        "agent_result": agent_result,
        "started_at": started_at,
        "finished_at": finished_at,
    }
    _write_json(trial_dir / "config.json", config)
    _write_json(trial_dir / "result.json", result)
    if exception_type is None and include_patch:
        _write_patch(trial_dir)
    if include_trajectory:
        _write_json(trial_dir / "agent/trajectory.json", {"steps": []})
    return trial_dir


def test_maps_completed_trial_and_preserves_nonzero_process_warning(
    tmp_path: Path,
) -> None:
    task_dir = tmp_path / "task"
    task_dir.mkdir()
    job_dir = tmp_path / "job"
    _write_job(job_dir)
    _write_trial(
        job_dir,
        task_dir,
        agent_result={
            "n_input_tokens": 10,
            "n_cache_tokens": 2,
            "n_output_tokens": 3,
            "cost_usd": 0.25,
        },
        include_trajectory=True,
    )
    (result,) = map_job_results(_plan(task_dir), job_dir, process_returncode=7)
    assert result.termination_reason is TerminationReason.COMPLETED
    assert result.backend_job_ref == "platform-job"
    assert result.backend_trial_ref == "harbor-trial-id"
    assert result.patch_ref is not None and result.patch_ref.size_bytes == 0
    assert result.trajectory_ref is not None
    assert result.raw_config_ref is not None and result.raw_result_ref is not None
    assert result.usage is not None and result.usage.n_input_tokens == 10
    assert result.resource_summary is not None
    assert result.resource_summary.wall_time_sec == 17
    assert result.warnings == ("HARBOR_PROCESS_EXIT_7",)


def test_missing_job_summary_keeps_finished_trial_on_process_timeout(
    tmp_path: Path,
) -> None:
    first_task, second_task = tmp_path / "first", tmp_path / "second"
    job_dir = tmp_path / "incomplete-job"
    first = _plan(first_task).bindings[0]
    plan = HarborJobPlan(
        {"job_name": "platform-job"},
        (
            first,
            HarborRunBinding(
                "run-two", harbor_task_path_key(str(second_task)), first.agent_key
            ),
        ),
    )
    _write_trial(job_dir, first_task)

    first_result, second_result = map_job_results(
        plan,
        job_dir,
        process_returncode=124,
        process_failure_reason=TerminationReason.TIMED_OUT,
        process_warnings=("HARBOR_PROCESS_TIMEOUT",),
    )

    assert first_result.termination_reason is TerminationReason.COMPLETED
    assert first_result.backend_job_ref == "platform-job"
    assert "HARBOR_JOB_RESULT_MISSING" in first_result.warnings
    assert second_result.termination_reason is TerminationReason.TIMED_OUT
    assert second_result.warnings == (
        "HARBOR_JOB_RESULT_MISSING",
        "HARBOR_PROCESS_TIMEOUT",
    )


def test_missing_trial_after_clean_exit_is_protocol_error(tmp_path: Path) -> None:
    task_dir = tmp_path / "task"
    job_dir = tmp_path / "job"
    _write_job(job_dir)

    (result,) = map_job_results(_plan(task_dir), job_dir, process_returncode=0)

    assert result.termination_reason is TerminationReason.BACKEND_PROTOCOL_ERROR
    assert result.warnings == ("HARBOR_TRIAL_RESULT_MISSING",)


def test_maps_harbor_exception_without_extracting_patch(tmp_path: Path) -> None:
    task_dir = tmp_path / "task"
    job_dir = tmp_path / "job"
    _write_job(job_dir)
    _write_trial(job_dir, task_dir, exception_type="AgentTimeoutError")

    (result,) = map_job_results(_plan(task_dir), job_dir, process_returncode=0)

    assert result.termination_reason is TerminationReason.TIMED_OUT
    assert result.patch_ref is None


def test_patch_failure_does_not_become_completed(tmp_path: Path) -> None:
    task_dir = tmp_path / "task"
    job_dir = tmp_path / "job"
    _write_job(job_dir)
    _write_trial(job_dir, task_dir, include_patch=False)

    (result,) = map_job_results(_plan(task_dir), job_dir, process_returncode=0)

    assert result.termination_reason is TerminationReason.PATCH_EXTRACTION_FAILED
    assert result.patch_ref is None
    assert "PATCH_MISSING" in result.warnings


def test_unexpected_trial_is_not_guessed_into_run(tmp_path: Path) -> None:
    expected_task = tmp_path / "expected-task"
    actual_task = tmp_path / "other-task"
    job_dir = tmp_path / "job"
    _write_job(job_dir)
    _write_trial(job_dir, actual_task)

    (result,) = map_job_results(_plan(expected_task), job_dir, process_returncode=0)

    assert result.termination_reason is TerminationReason.BACKEND_PROTOCOL_ERROR
    assert result.warnings == (
        "HARBOR_TRIAL_RESULT_MISSING",
        "UNEXPECTED_HARBOR_TRIAL",
    )
