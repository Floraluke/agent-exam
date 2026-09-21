from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from eval_platform.adapters.execution.harbor.config_mapper import (
    ARTIFACT_CONTRACT_VERSION,
    HARBOR_REVISION,
    build_job_plan,
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

REPO_ROOT = Path(__file__).resolve().parents[4]
PARQUET = (
    REPO_ROOT
    / "runtime/cache/swe-gym-lite"
    / "61231f2c90b18985b42a1419738a240085a15107/train-0000.parquet"
)
HARBOR_PYTHON = REPO_ROOT / "framework/harbor/.venv/Scripts/python.exe"


@pytest.mark.contract
@pytest.mark.parametrize("hosts", [(), ("allowed.agentexam.test",)])
def test_fixed_harbor_accepts_generated_job_and_public_task(
    tmp_path: Path, hosts
) -> None:
    if not PARQUET.is_file() or not HARBOR_PYTHON.is_file():
        pytest.skip("Fixed local data or Harbor environment is not restored")
    bundle = SWEGymTaskSource(PARQUET).load(CANDIDATE_INSTANCE_ID)
    limits = RunLimits(900, 1, 4096, 8192)
    task_dir = render_harbor_task(bundle.public, tmp_path / "tasks", limits)
    agent = AgentConfiguration(
        configuration_id="contract-codex",
        agent_name="codex",
        agent_version="0.153.0",
        model_provider="openai_chatgpt",
        model_name="model-must-be-confirmed",
        authentication_type="chatgpt_auth_json",
        credential_configuration_id="owner-login",
        critical_config={"reasoning_effort": "medium"},
    )
    request = ExecutionJobRequest(
        job_id="m0-contract",
        runs=(ExecutionRunRequest("m0-contract-run", bundle.public, agent),),
        limits=limits,
        backend_revision=HARBOR_REVISION,
        artifact_contract_version=ARTIFACT_CONTRACT_VERSION,
    )
    plan = build_job_plan(
        request,
        jobs_dir=tmp_path / "jobs",
        task_dirs={bundle.public.instance_id: task_dir},
        network_hosts=hosts,
    )
    config_path = tmp_path / "job.json"
    config_path.write_text(json.dumps(plan.config), encoding="utf-8")

    probe = (
        "import json,sys;"
        "from pathlib import Path;"
        "from harbor.models.job.config import JobConfig;"
        "from harbor.models.task.task import Task;"
        "from harbor.trial.network_policy import resolve_agent_env_baseline,"
        "resolve_agent_phase_policy,resolve_verifier_phase_policy;"
        "cfg=JobConfig.model_validate_json(Path(sys.argv[1]).read_text());"
        "task=Task(sys.argv[2],disable_verification=True);"
        "baseline=resolve_agent_env_baseline(task.config,cfg.environment);"
        "agent=resolve_agent_phase_policy(task.config,cfg.agents[0],baseline);"
        "verifier=resolve_verifier_phase_policy(task.config,None,baseline=baseline);"
        "assert agent==verifier==baseline;"
        "print(json.dumps({'attempts':cfg.n_attempts,"
        "'concurrency':cfg.n_concurrent_trials,'retry':cfg.retry.max_retries,"
        "'verifier_disabled':cfg.verifier.disable,"
        "'collect_hooks':len(task.config.verifier.collect),"
        "'artifacts':len(task.config.artifacts),"
        "'network':baseline.model_dump(mode='json')}))"
    )
    completed = subprocess.run(
        [str(HARBOR_PYTHON), "-c", probe, str(config_path), str(task_dir)],
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )

    assert completed.returncode == 0, completed.stderr
    assert json.loads(completed.stdout) == {
        "attempts": 1,
        "concurrency": 1,
        "retry": 0,
        "verifier_disabled": True,
        "collect_hooks": 1,
        "artifacts": 1,
        "network": {"network_mode": "allowlist", "allowed_hosts": list(hosts)},
    }
