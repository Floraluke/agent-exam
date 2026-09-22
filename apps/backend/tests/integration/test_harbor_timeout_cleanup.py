from __future__ import annotations

import json
import os
import re
import subprocess
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest

import eval_platform.adapters.execution.harbor.adapter as adapter_module
from eval_platform.adapters.execution.harbor.adapter import HarborExecutionAdapter
from eval_platform.adapters.execution.harbor.config_mapper import (
    ARTIFACT_CONTRACT_VERSION,
    HARBOR_REVISION,
    HarborJobPlan,
    HarborRunBinding,
    build_job_plan,
    harbor_agent_key,
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
_RESOURCE_COMMANDS = {
    "container": (["container", "ls", "--all"], ["container", "rm", "--force"]),
    "network": (["network", "ls"], ["network", "rm"]),
    "volume": (["volume", "ls"], ["volume", "rm", "--force"]),
    "image": (["image", "ls"], ["image", "rm", "--force"]),
}


def test_outer_timeout_removes_exact_harbor_compose_project(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    if os.environ.get("AGENTEXAM_RUN_HARBOR_TIMEOUT_INTEGRATION") != "1":
        pytest.skip("Set AGENTEXAM_RUN_HARBOR_TIMEOUT_INTEGRATION=1")

    repo_root = Path(__file__).resolve().parents[4]
    harbor_exe = repo_root / "framework/harbor/.venv/Scripts/harbor.exe"
    parquet = (
        repo_root
        / "runtime/cache/swe-gym-lite"
        / "61231f2c90b18985b42a1419738a240085a15107"
        / "train-0000.parquet"
    )
    task = SWEGymTaskSource(parquet).load(CANDIDATE_INSTANCE_ID).public
    task = replace(task, instance_id="agentexam_timeout_probe")
    limits = RunLimits(300, 1, 2048, 4096)
    request = _request(task, limits)
    monkeypatch.setattr(adapter_module, "build_job_plan", _nop_job_plan)
    monkeypatch.setattr(adapter_module, "process_timeout_sec", lambda _: 45)
    adapter = HarborExecutionAdapter(
        harbor_executable=harbor_exe,
        evidence_root=tmp_path / "evidence",
        project_root=repo_root,
        task_renderer=_render_blocking_collect,
    )
    projects: set[str] = set()
    try:
        (result,) = adapter.execute(request)
        projects = _trial_projects(tmp_path / "evidence" / request.job_id)
        assert projects, "Harbor did not persist a Trial identity before timeout"
        assert result.termination_reason is TerminationReason.TIMED_OUT
        assert "HARBOR_PROCESS_TIMEOUT" in result.warnings
        assert not {
            "HARBOR_COMPOSE_CLEANUP_FAILED",
            "HARBOR_COMPOSE_CLEANUP_UNVERIFIED",
        }.intersection(result.warnings)
        assert _collect_ready(tmp_path / "evidence" / request.job_id)
        leftovers = {project: _resources(project) for project in projects}
        assert not any(
            ids for resources in leftovers.values() for ids in resources.values()
        ), f"Harbor left Compose resources: {leftovers}"
    finally:
        projects |= _trial_projects(tmp_path / "evidence" / request.job_id)
        for project in projects:
            _remove_resources(project)


def _request(task: Any, limits: RunLimits) -> ExecutionJobRequest:
    agent = AgentConfiguration(
        "nop-probe-only",
        "codex",
        "0.0.0-probe",
        "openai_chatgpt",
        "model-must-be-confirmed",
        "chatgpt_auth_json",
        "not-accessed-by-nop",
        {"reasoning_effort": "low"},
    )
    return ExecutionJobRequest(
        "m0-harbor-timeout-probe",
        (ExecutionRunRequest("m0-timeout-run", task, agent),),
        limits,
        HARBOR_REVISION,
        ARTIFACT_CONTRACT_VERSION,
    )


def _nop_job_plan(
    request: Any, *, jobs_dir: Path, task_dirs: Any, network_hosts=()
) -> HarborJobPlan:
    plan = build_job_plan(
        request, jobs_dir=jobs_dir, task_dirs=task_dirs, network_hosts=network_hosts
    )
    config = {**plan.config, "agents": [{"name": "nop", "n_concurrent": 1}]}
    binding = HarborRunBinding(
        "m0-timeout-run",
        plan.bindings[0].task_path_key,
        harbor_agent_key(config["agents"][0]),
    )
    return HarborJobPlan(config, (binding,))


def _render_blocking_collect(task: Any, root: Path, limits: RunLimits) -> Path:
    task_dir = render_harbor_task(task, root, limits)
    script = task_dir / "environment/collect-patch.sh"
    script.write_text(
        "#!/usr/bin/env bash\nset -eu\nmkdir -p /logs/artifacts\n"
        "printf ready > /logs/artifacts/timeout-ready\nsleep 300\n",
        encoding="utf-8",
        newline="\n",
    )
    return task_dir


def _trial_projects(run_root: Path) -> set[str]:
    projects: set[str] = set()
    for path in run_root.glob("jobs/*/*/config.json"):
        value = json.loads(path.read_text(encoding="utf-8"))
        trial_name = value.get("trial_name")
        if isinstance(trial_name, str) and trial_name == path.parent.name:
            projects.add(re.sub(r"[^a-z0-9_-]", "-", f"{trial_name}__env".lower()))
    return projects


def _collect_ready(run_root: Path) -> bool:
    return any(run_root.glob("jobs/*/*/artifacts/logs/artifacts/timeout-ready"))


def _resources(project: str) -> dict[str, tuple[str, ...]]:
    return {kind: _resource_ids(kind, project) for kind in _RESOURCE_COMMANDS}


def _resource_ids(kind: str, project: str) -> tuple[str, ...]:
    list_args, _ = _RESOURCE_COMMANDS[kind]
    result = subprocess.run(
        [
            "docker",
            *list_args,
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
    return tuple(result.stdout.split())


def _remove_resources(project: str) -> None:
    for kind in ("container", "network", "volume", "image"):
        ids = _resource_ids(kind, project)
        if ids:
            _, remove_args = _RESOURCE_COMMANDS[kind]
            subprocess.run(
                ["docker", *remove_args, *ids],
                capture_output=True,
                timeout=30,
                check=False,
            )
