import json
import os
import shutil
import subprocess
import time
from pathlib import Path

import pytest

LOCAL_ROOT = Path(__file__).parents[1] / "local"
STATUS_SCRIPT = LOCAL_ROOT / "Get-AgentExamStatus.ps1"
START_SCRIPT = LOCAL_ROOT / "Start-AgentExam.ps1"
STOP_SCRIPT = LOCAL_ROOT / "Stop-AgentExam.ps1"
DEPLOYMENT_STATE = Path(r"D:\AgentExamData\private\deployment-state.json")
INFRA_ROOT = LOCAL_ROOT.parent


def _run_script(script: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
    powershell = shutil.which("pwsh.exe")
    assert powershell is not None
    return subprocess.run(
        [
            powershell,
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            script,
            *arguments,
        ],
        cwd=LOCAL_ROOT.parents[1],
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )


def _compose(*arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            "docker",
            "compose",
            "--env-file",
            INFRA_ROOT / ".env.example",
            "-f",
            INFRA_ROOT / "compose.yaml",
            *arguments,
        ],
        cwd=INFRA_ROOT.parent,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )


def test_status_reports_only_the_managed_complete_deployment():
    if os.environ.get("AGENTEXAM_RUN_LOCAL_DEPLOYMENT") != "1":
        pytest.skip("真实本机生命周期检查未显式启用")
    result = _run_script(STATUS_SCRIPT)

    assert result.returncode == 0, result.stderr
    status = json.loads(result.stdout)
    assert set(status) == {"project", "initializationState", "services", "worker"}
    assert status["project"] == "agentexam-local"
    assert status["initializationState"] == "complete"
    assert status["services"] == {"postgres": "running", "minio": "running"}
    assert set(status["worker"]) == {"activeJobs", "stopRequested"}
    assert status["worker"]["activeJobs"] == 0
    assert isinstance(status["worker"]["stopRequested"], bool)
    assert "password" not in (result.stdout + result.stderr).lower()


def test_start_is_repeatable_without_reinitializing_the_deployment():
    if os.environ.get("AGENTEXAM_RUN_LOCAL_DEPLOYMENT") != "1":
        pytest.skip("真实本机生命周期检查未显式启用")
    state_before = DEPLOYMENT_STATE.read_bytes()

    for _ in range(2):
        result = _run_script(START_SCRIPT)
        assert result.returncode == 0, result.stderr
        outcome = json.loads(result.stdout)
        assert outcome["operation"] == "started"
        assert outcome["services"] == {"postgres": "running", "minio": "running"}
        assert outcome["worker"] == {"activeJobs": 0, "stopRequested": False}
        assert "password" not in (result.stdout + result.stderr).lower()

    assert DEPLOYMENT_STATE.read_bytes() == state_before


def test_stop_keeps_deployment_data_and_start_restores_services():
    if os.environ.get("AGENTEXAM_RUN_LOCAL_DEPLOYMENT") != "1":
        pytest.skip("真实本机生命周期检查未显式启用")
    state_before = DEPLOYMENT_STATE.read_bytes()

    try:
        stopped = _run_script(STOP_SCRIPT)
        assert stopped.returncode == 0, stopped.stderr
        stop_status = json.loads(stopped.stdout)
        assert stop_status["operation"] == "stopped"
        assert stop_status["services"] == {"postgres": "stopped", "minio": "stopped"}
        assert stop_status["worker"] == {"activeJobs": None, "stopRequested": True}
        assert DEPLOYMENT_STATE.read_bytes() == state_before
    finally:
        restarted = _run_script(START_SCRIPT)

    assert restarted.returncode == 0, restarted.stderr
    start_status = json.loads(restarted.stdout)
    assert start_status["services"] == {"postgres": "running", "minio": "running"}
    assert start_status["worker"] == {"activeJobs": 0, "stopRequested": False}
    assert DEPLOYMENT_STATE.read_bytes() == state_before


def test_start_does_not_cancel_a_stop_request_while_services_are_running():
    if os.environ.get("AGENTEXAM_RUN_LOCAL_DEPLOYMENT") != "1":
        pytest.skip("真实本机生命周期检查未显式启用")

    stopped = _run_script(STOP_SCRIPT)
    assert stopped.returncode == 0, stopped.stderr
    try:
        bypass = _compose("start")
        assert bypass.returncode == 0, bypass.stderr
        time.sleep(3)
        refused = _run_script(START_SCRIPT)
        assert refused.returncode != 0
        assert "still running under a stop request" in refused.stderr
        status = json.loads(_run_script(STATUS_SCRIPT).stdout)
        assert status["worker"]["stopRequested"] is True
    finally:
        _run_script(STOP_SCRIPT)
        restarted = _run_script(START_SCRIPT)

    assert restarted.returncode == 0, restarted.stderr
