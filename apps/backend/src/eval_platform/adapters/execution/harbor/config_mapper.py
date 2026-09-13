from __future__ import annotations

import json
import os
import re
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from eval_platform.adapters.execution.network import validate_hosts
from eval_platform.application.ports.execution import ExecutionJobRequest
from eval_platform.domain.agent import AgentConfiguration
from eval_platform.domain.jobs.policy import execution_process_timeout_sec

HARBOR_REVISION = "6af8d6e31eced13b93849cdf80feeadf24603d15"
ARTIFACT_CONTRACT_VERSION = "agentexam.m0.v1"
_SAFE_ID = re.compile(r"[a-zA-Z0-9][a-zA-Z0-9._-]{0,63}")


@dataclass(frozen=True, slots=True)
class HarborJobPlan:
    config: dict[str, Any]
    bindings: tuple[HarborRunBinding, ...]

    @property
    def run_ids(self) -> tuple[str, ...]:
        return tuple(binding.run_id for binding in self.bindings)


@dataclass(frozen=True, slots=True)
class HarborRunBinding:
    run_id: str
    task_path_key: str
    agent_key: str


def build_job_plan(
    request: ExecutionJobRequest,
    *,
    jobs_dir: Path,
    task_dirs: Mapping[str, Path],
    network_hosts: tuple[str, ...] = (),
) -> HarborJobPlan:
    if request.backend_revision != HARBOR_REVISION:
        raise ValueError("Harbor revision is not registered")
    if request.artifact_contract_version != ARTIFACT_CONTRACT_VERSION:
        raise ValueError("Harbor artifact contract is not supported")
    validate_job_id(request.job_id)
    agents: dict[str, dict[str, Any]] = {}
    tasks: dict[str, dict[str, str]] = {}
    combinations: dict[tuple[str, str], str] = {}
    for run in request.runs:
        fingerprint = run.agent.fingerprint
        agents.setdefault(fingerprint, _map_agent(run.agent))
        task_dir = task_dirs.get(run.task.instance_id)
        if task_dir is None:
            raise ValueError(f"No rendered Harbor task for {run.task.instance_id}")
        tasks.setdefault(run.task.instance_id, {"path": str(task_dir.resolve())})
        combination = (run.task.instance_id, fingerprint)
        if combination in combinations:
            raise ValueError("Each Agent and task combination must be unique")
        combinations[combination] = run.run_id
    expected = {(task_id, fingerprint) for task_id in tasks for fingerprint in agents}
    if set(combinations) != expected:
        raise ValueError("Execution runs must form a complete Agent x task matrix")
    limits = request.limits
    config: dict[str, Any] = {
        "job_name": request.job_id,
        "jobs_dir": str(jobs_dir.resolve()),
        "n_attempts": 1,
        "n_concurrent_trials": 1,
        "quiet": False,
        "retry": {"max_retries": 0},
        "environment": {
            "type": "docker",
            "extra_allowed_hosts": list(validate_hosts(network_hosts)),
            "delete": True,
            "force_build": False,
            "cpu_enforcement_policy": "limit",
            "memory_enforcement_policy": "limit",
            "override_cpus": limits.cpus,
            "override_memory_mb": limits.memory_mb,
            "override_storage_mb": limits.storage_mb,
        },
        "verifier": {"disable": True},
        "agents": list(agents.values()),
        "tasks": list(tasks.values()),
    }
    bindings = tuple(
        HarborRunBinding(
            run_id=run.run_id,
            task_path_key=harbor_task_path_key(tasks[run.task.instance_id]["path"]),
            agent_key=harbor_agent_key(agents[run.agent.fingerprint]),
        )
        for run in request.runs
    )
    return HarborJobPlan(config=config, bindings=bindings)


def _map_agent(agent: AgentConfiguration) -> dict[str, Any]:
    if agent.agent_name != "codex":
        raise ValueError("M0 only permits the registered Codex Agent")
    allowed = {"reasoning_effort"}
    unknown = set(agent.critical_config) - allowed
    if unknown:
        raise ValueError(f"Unsupported Codex critical config: {sorted(unknown)}")
    effort = agent.critical_config.get("reasoning_effort")
    if effort not in {"low", "medium", "high", "xhigh"}:
        raise ValueError("Codex reasoning_effort must be explicitly registered")
    provider = (
        "openai" if agent.model_provider == "openai_chatgpt" else agent.model_provider
    )
    return {
        "name": "codex",
        "model_name": f"{provider}/{agent.model_name}",
        "n_concurrent": 1,
        "kwargs": {
            "version": agent.agent_version,
            "reasoning_effort": effort,
            "web_search": "disabled",
        },
    }


def harbor_task_path_key(path: str) -> str:
    return os.path.normcase(str(Path(path).resolve()))


def validate_job_id(job_id: str) -> None:
    if not _SAFE_ID.fullmatch(job_id):
        raise ValueError("job_id is not safe for a Harbor job name")


def harbor_agent_key(agent: Mapping[str, Any]) -> str:
    selected = {
        "kwargs": agent.get("kwargs", {}),
        "model_name": agent.get("model_name"),
        "name": agent.get("name"),
    }
    if not isinstance(selected["name"], str) or not isinstance(
        selected["kwargs"], Mapping
    ):
        raise ValueError("Harbor Agent config has no stable identity")
    return json.dumps(selected, sort_keys=True, separators=(",", ":"))


def process_timeout_sec(request: ExecutionJobRequest) -> int:
    return execution_process_timeout_sec(
        request.limits.wall_timeout_sec, len(request.runs)
    )
