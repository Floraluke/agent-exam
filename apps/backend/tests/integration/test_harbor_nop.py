from __future__ import annotations

import json
import os
import re
import subprocess
from pathlib import Path

import pytest

from eval_platform.adapters.execution.harbor.artifacts import (
    validate_patch_artifact,
)
from eval_platform.adapters.execution.harbor.config_mapper import (
    ARTIFACT_CONTRACT_VERSION,
    HARBOR_REVISION,
    HarborJobPlan,
    HarborRunBinding,
    build_job_plan,
    harbor_agent_key,
)
from eval_platform.adapters.execution.harbor.process_runner import run_bounded_process
from eval_platform.adapters.execution.harbor.result_mapper import map_job_results
from eval_platform.adapters.execution.harbor_entry import (
    harbor_command,
    harbor_environment,
)
from eval_platform.adapters.tasks.swe_gym import (
    CANDIDATE_INSTANCE_ID,
    SWEGymTaskSource,
    render_harbor_task,
)
from eval_platform.application.ports.execution import (
    ExecutionJobRequest,
    ExecutionRunRequest,
    RunLimits,
)
from eval_platform.domain.agent import AgentConfiguration
from eval_platform.domain.result import TerminationReason

pytestmark = pytest.mark.integration


def test_harbor_nop_collects_empty_patch_and_cleans_environment(
    tmp_path: Path,
) -> None:
    if os.environ.get("AGENTEXAM_RUN_HARBOR_INTEGRATION") != "1":
        pytest.skip("Set AGENTEXAM_RUN_HARBOR_INTEGRATION=1 for the Docker probe")

    repo_root = Path(__file__).resolve().parents[4]
    harbor_exe = repo_root / "framework/harbor/.venv/Scripts/harbor.exe"
    parquet = (
        repo_root
        / "runtime/cache/swe-gym-lite"
        / "61231f2c90b18985b42a1419738a240085a15107"
        / "train-0000.parquet"
    )
    assert harbor_exe.is_file(), "The fixed Harbor environment is missing"
    assert parquet.is_file(), "The fixed SWE-Gym snapshot is missing"

    limits = RunLimits(
        wall_timeout_sec=300,
        cpus=1,
        memory_mb=2048,
        storage_mb=4096,
    )
    task = SWEGymTaskSource(parquet).load(CANDIDATE_INSTANCE_ID).public
    task_dir = render_harbor_task(task, tmp_path / "tasks", limits)
    request = ExecutionJobRequest(
        job_id="m0-harbor-nop",
        runs=(
            ExecutionRunRequest(
                run_id="m0-nop-run",
                task=task,
                agent=AgentConfiguration(
                    configuration_id="nop-probe-only",
                    agent_name="codex",
                    agent_version="0.0.0-probe",
                    model_provider="openai_chatgpt",
                    model_name="model-must-be-confirmed",
                    authentication_type="chatgpt_auth_json",
                    credential_configuration_id="not-accessed-by-nop",
                    critical_config={"reasoning_effort": "low"},
                ),
            ),
        ),
        limits=limits,
        backend_revision=HARBOR_REVISION,
        artifact_contract_version=ARTIFACT_CONTRACT_VERSION,
    )
    jobs_dir = tmp_path / "jobs"
    plan = build_job_plan(
        request,
        jobs_dir=jobs_dir,
        task_dirs={task.instance_id: task_dir},
    )
    config = plan.config
    config["agents"] = [{"name": "nop", "n_concurrent": 1}]
    probe_plan = HarborJobPlan(
        config=config,
        bindings=(
            HarborRunBinding(
                run_id="m0-nop-run",
                task_path_key=plan.bindings[0].task_path_key,
                agent_key=harbor_agent_key(config["agents"][0]),
            ),
        ),
    )
    config_path = tmp_path / "harbor-nop-config.json"
    config_path.write_text(
        json.dumps(config, indent=2, sort_keys=True), encoding="utf-8", newline="\n"
    )

    env = harbor_environment()
    outcome = run_bounded_process(
        harbor_command(harbor_exe, config_path),
        cwd=repo_root,
        env=env,
        timeout_sec=900,
        evidence_root=tmp_path,
    )
    stderr = (tmp_path / "harbor.stderr.log").read_text("utf-8", errors="replace")
    assert outcome.returncode == 0, stderr[-4000:]
    assert not outcome.timed_out and not outcome.warnings
    process_manifest = json.loads(
        (tmp_path / "harbor-process.json").read_text(encoding="utf-8")
    )
    assert not process_manifest["logs"]["stdout"]["truncated"]

    job_dir = jobs_dir / request.job_id
    (mapped_result,) = map_job_results(
        probe_plan,
        job_dir,
        process_returncode=outcome.returncode,
        process_warnings=outcome.warnings,
    )
    assert mapped_result.termination_reason is TerminationReason.COMPLETED
    assert mapped_result.patch_ref is not None
    assert mapped_result.warnings == ("TRAJECTORY_UNAVAILABLE",)
    job_result = json.loads((job_dir / "result.json").read_text(encoding="utf-8"))
    assert job_result["n_total_trials"] == 1
    assert job_result["stats"]["n_completed_trials"] == 1
    assert job_result["stats"]["n_errored_trials"] == 0
    assert "trial_results" not in job_result
    trial_result_paths = sorted(
        path for path in job_dir.glob("*/result.json") if path.parent.is_dir()
    )
    assert len(trial_result_paths) == 1
    trial_result = json.loads(trial_result_paths[0].read_text(encoding="utf-8"))
    assert trial_result["exception_info"] is None
    assert trial_result["verifier_result"] is None
    assert trial_result["agent_info"]["name"] == "nop"

    trial_name = trial_result["trial_name"]
    trial_dir = job_dir / trial_name
    saved_config = json.loads((trial_dir / "config.json").read_text(encoding="utf-8"))
    assert saved_config["verifier"]["disable"] is True
    assert config["environment"]["delete"] is True
    assert "delete" not in saved_config["environment"]

    patch = validate_patch_artifact(trial_dir / "artifacts/agentexam")
    assert patch.is_empty
    assert patch.size_bytes == 0
    manifest = json.loads(
        (trial_dir / "artifacts/manifest.json").read_text(encoding="utf-8")
    )
    assert manifest == [
        {
            "source": "/logs/artifacts",
            "destination": "artifacts/agentexam",
            "type": "directory",
            "status": "ok",
            "service": None,
        }
    ]
    _assert_compose_resources_removed(trial_name)


def _assert_compose_resources_removed(trial_name: str) -> None:
    project = re.sub(r"[^a-z0-9_-]", "-", f"{trial_name}__env".lower())
    for resource in ("container", "network", "volume"):
        result = subprocess.run(
            [
                "docker",
                resource,
                "ls",
                "--filter",
                f"label=com.docker.compose.project={project}",
                "--quiet",
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
            check=False,
        )
        assert result.returncode == 0, result.stderr
        assert not result.stdout.strip(), f"Harbor left a {resource}: {project}"
