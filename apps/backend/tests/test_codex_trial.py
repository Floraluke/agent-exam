"""Opt-in full fake-auth lifecycle; leakage detection is not protection acceptance."""

from __future__ import annotations

import json
import os
import re
import subprocess
from pathlib import Path

import pytest

from eval_platform.adapters.execution.harbor.lifecycle.cleanup import (
    _docker_resource_ids,
    cleanup_timed_out_projects,
)
from eval_platform.adapters.execution.harbor.config_mapper import (
    ARTIFACT_CONTRACT_VERSION,
    HARBOR_REVISION,
    build_job_plan,
)
from eval_platform.adapters.execution.harbor.process_runner import run_bounded_process
from eval_platform.adapters.execution.harbor.result_mapper import map_job_results
from eval_platform.adapters.execution.harbor_entry import harbor_environment
from eval_platform.adapters.tasks.swe_gym import (
    CANDIDATE_IMAGE,
    CANDIDATE_INSTANCE_ID,
    DATASET_REVISION,
    SWEGymTaskSource,
    render_harbor_task,
)
from eval_platform.application.ports.execution import (
    ExecutionJobRequest,
    ExecutionRunRequest,
    RunLimits,
)
from eval_platform.domain.agent import AgentConfiguration


@pytest.mark.integration
@pytest.mark.parametrize("mode", ["success", "failure", "timeout", "patch-secret"])
def test_full_synthetic_codex_trial(tmp_path: Path, mode: str) -> None:
    if os.environ.get("AGENTEXAM_RUN_CODEX_TRIAL_PROBE") != "1":
        pytest.skip("Set AGENTEXAM_RUN_CODEX_TRIAL_PROBE=1 for synthetic Docker trials")
    repo = Path(__file__).resolve().parents[3]
    harbor = repo / "framework/harbor/.venv/Scripts/python.exe"
    bundle = repo / (
        "runtime/prototype/m0-codex-install-20260907-01/docker-contract/"
        "test_fixed_codex_installs_offl0/input"
    )
    subprocess.run(
        ["docker", "image", "inspect", CANDIDATE_IMAGE],
        check=True,
        capture_output=True,
        timeout=30,
    )
    task = (
        SWEGymTaskSource(
            repo
            / "runtime/cache/swe-gym-lite"
            / DATASET_REVISION
            / "train-0000.parquet"
        )
        .load(CANDIDATE_INSTANCE_ID)
        .public
    )
    limits = RunLimits(12 if mode == "timeout" else 90, 1, 2048, 4096)
    task_dir = render_harbor_task(task, tmp_path / "tasks", limits)
    agent = AgentConfiguration(
        configuration_id="internal-synthetic-only",
        agent_name="codex",
        agent_version="0.153.0",
        model_provider="openai",
        model_name="gpt-5.6-terra",
        authentication_type="chatgpt",
        credential_configuration_id="synthetic-only",
        critical_config={"reasoning_effort": "medium"},
    )
    request = ExecutionJobRequest(
        job_id="synthetic-codex",
        runs=(ExecutionRunRequest("synthetic-run", task, agent),),
        limits=limits,
        backend_revision=HARBOR_REVISION,
        artifact_contract_version=ARTIFACT_CONTRACT_VERSION,
    )
    plan = build_job_plan(
        request, jobs_dir=tmp_path / "jobs", task_dirs={task.instance_id: task_dir}
    )
    (tmp_path / "config.json").write_text(json.dumps(plan.config, indent=2))
    job_dir = tmp_path / "jobs/synthetic-codex"
    try:
        outcome = run_bounded_process(
            [
                str(harbor),
                str(Path(__file__).with_name("codex_trial_probe.py")),
                str(tmp_path),
                str(bundle),
                mode,
            ],
            cwd=repo,
            env=harbor_environment(),
            timeout_sec=360,
            evidence_root=tmp_path,
        )
        assert outcome.returncode == 0 and not outcome.timed_out, (
            tmp_path / "harbor.stderr.log"
        ).read_text()[-4000:]
        results = list(job_dir.glob("*/result.json"))
        assert len(results) == 1
        result = json.loads(results[0].read_text())
        project = re.sub(r"[^a-z0-9_-]", "-", f"{result['trial_name']}__env".lower())
        remaining = {
            resource: _docker_resource_ids([resource, "ls", *flags], project)
            for resource, flags in (
                ("container", ["--all"]),
                ("network", []),
                ("volume", []),
            )
        }
        (tmp_path / "natural-cleanup.json").write_text(json.dumps(remaining, indent=2))
        assert not any(remaining.values()), remaining
        observations = json.loads((tmp_path / "probe-observations.json").read_text())
        assert len(observations["observations"]) == 1, result.get("exception_info")
        assert observations["observations"][0]["credential_directories_removed"]
        expected_error = {
            "failure": "NonZeroAgentExitCodeError",
            "timeout": "AgentTimeoutError",
        }.get(mode)
        exception = result.get("exception_info")
        assert (exception["exception_type"] if exception else None) == expected_error, (
            exception
        )
        (mapped,) = map_job_results(
            plan, job_dir, process_returncode=outcome.returncode
        )
        leaks = {}
        for path in job_dir.rglob("*"):
            if path.is_file():
                content = path.read_bytes()
                found = [
                    tag
                    for tag in ("ORIGINAL", "REFRESHED", "REFRESH-TOKEN")
                    if ("AGENTEXAM-SYNTHETIC-" + tag + "-ONLY").encode() in content
                ]
                if found:
                    leaks[path.relative_to(job_dir).as_posix()] = found
        (tmp_path / "output-audit.json").write_text(
            json.dumps(
                {
                    "synthetic_only": True,
                    "full_output_protection_passed": not leaks,
                    "findings": leaks,
                    "mapped_termination": mapped.termination_reason.value,
                    "patch_reference_returned": mapped.patch_ref is not None,
                },
                indent=2,
            )
        )
        assert any(name.endswith("codex.txt") for name in leaks), (
            "Positive leakage control missing"
        )
        assert any(name.endswith("trajectory.json") for name in leaks)
        if mode == "patch-secret":
            assert any(name.endswith("model.patch") for name in leaks)
            assert mapped.patch_ref is not None, "Existing unsafe admission changed"
    finally:
        if list(job_dir.glob("*/config.json")):
            assert cleanup_timed_out_projects(job_dir) == ()
