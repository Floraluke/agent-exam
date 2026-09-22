from __future__ import annotations

import json
import os
import re
import subprocess
import uuid
from pathlib import Path

import pytest

from eval_platform.adapters.evaluation.swe_bench import SWEbenchEvaluator
from eval_platform.adapters.execution.harbor import adapter as harbor_module
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
from prototype_codex_harbor_e2e import run_prototype

pytestmark = pytest.mark.integration


def test_nop_patch_reaches_real_fork_without_model(tmp_path: Path, monkeypatch):
    if os.environ.get("AGENTEXAM_RUN_M0_INTEGRATION") != "1":
        pytest.skip("Set AGENTEXAM_RUN_M0_INTEGRATION=1 for the no-model pipeline")
    repo = Path(__file__).resolve().parents[4]
    tmp_path.resolve().relative_to(repo)
    source = SWEGymTaskSource(
        repo / "runtime/cache/swe-gym-lite" / DATASET_REVISION / "train-0000.parquet"
    )
    bundle = source.load(CANDIDATE_INSTANCE_ID)
    identity = f"m0-nop-pipeline-{uuid.uuid4().hex[:10]}"
    agent = AgentConfiguration(
        "nop-probe-only",
        "codex",
        "0.0.0-probe",
        "openai_chatgpt",
        "no-model-call",
        "chatgpt_auth_json",
        "not-accessed-by-nop",
        {"reasoning_effort": "low"},
    )
    limits = RunLimits(300, 1, 2048, 4096)
    request = ExecutionJobRequest(
        identity,
        (ExecutionRunRequest(identity, bundle.public, agent),),
        limits,
        HARBOR_REVISION,
        ARTIFACT_CONTRACT_VERSION,
    )
    root = tmp_path / "pipeline"
    monkeypatch.setattr(harbor_module, "build_job_plan", _nop_plan)
    for name in ("CODEX_AUTH_JSON_PATH", "OPENAI_API_KEY", "CODEX_API_KEY"):
        monkeypatch.delenv(name, raising=False)
    execution = HarborExecutionAdapter(
        harbor_executable=repo / "framework/harbor/.venv/Scripts/harbor.exe",
        evidence_root=root / "execution",
        project_root=repo,
        task_renderer=_render_probe,
    )
    evaluator = SWEbenchEvaluator(
        repo_root=repo,
        task_source=source,
        evidence_root=root / "evaluation",
        limits=RunLimits(300, 1, 4096, 8192),
    )
    result = run_prototype(
        request,
        bundle,
        execution=execution,
        evaluator=evaluator,
        evidence_dir=root,
        execution_kind="harbor_nop",
    )
    assert result.run_id == identity and result.patch_applied and not result.resolved
    frozen = json.loads((root / "request.json").read_text())
    assert frozen["execution_kind"] == "harbor_nop" and not frozen["ranking_eligible"]
    trial = json.loads((root / "execution.json").read_text())
    assert trial["warnings"] == ["TRAJECTORY_UNAVAILABLE"]
    patch = Path(trial["patch_ref"]["object_key"]).read_bytes()
    assert b"agentexam_m0_probe.txt" in patch
    fork = root / "evaluation" / identity
    assert (fork / "input/model.patch").read_bytes() == patch
    cleanup = json.loads((fork / "cleanup.json").read_text())
    assert cleanup["verified"] and cleanup["remaining_ids"] == []
    container = json.loads((fork / "container.json").read_text())
    assert container["host_config"]["NetworkMode"] == "none"
    assert container["mounts"] == []
    trial_paths = list(
        (root / "execution" / identity / "jobs" / identity).glob("*/result.json")
    )
    assert len(trial_paths) == 1
    actual = json.loads(trial_paths[0].read_text())
    assert actual["agent_info"]["name"] == "nop"
    project = re.sub(r"[^a-z0-9_-]", "-", f"{actual['trial_name']}__env".lower())
    for resource in ("container", "network", "volume", "image"):
        command = [
            "docker",
            resource,
            "ls",
            "-q",
            "--filter",
            f"label=com.docker.compose.project={project}",
        ]
        if resource == "container":
            command.append("--all")
        probe = subprocess.run(
            command, capture_output=True, text=True, check=True, timeout=30
        )
        assert not probe.stdout.strip(), f"Residual {resource}: {project}"


def _nop_plan(request, *, jobs_dir, task_dirs, network_hosts=()):
    plan = build_job_plan(
        request, jobs_dir=jobs_dir, task_dirs=task_dirs, network_hosts=network_hosts
    )
    config = {**plan.config, "agents": [{"name": "nop", "n_concurrent": 1}]}
    binding = HarborRunBinding(
        request.runs[0].run_id,
        plan.bindings[0].task_path_key,
        harbor_agent_key(config["agents"][0]),
    )
    return HarborJobPlan(config, (binding,))


def _render_probe(task, root, limits):
    directory = render_harbor_task(task, root, limits)
    # Test-only non-fixing edit: the production collect hook still exports it.
    hook = directory / "environment/collect-patch.sh"
    original = hook.read_text(encoding="utf-8")
    hook.write_text(
        "echo no-model-probe > /testbed/agentexam_m0_probe.txt\n" + original,
        encoding="utf-8",
        newline="\n",
    )
    return directory
