import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parents[2] / "apps" / "backend" / "tests"))
from local_persistence_scenario import local_scenario

INFRA_ROOT = Path(__file__).parents[1]
LOCAL_ROOT = INFRA_ROOT / "local"
START_SCRIPT = LOCAL_ROOT / "Start-AgentExam.ps1"
STOP_SCRIPT = LOCAL_ROOT / "Stop-AgentExam.ps1"


def _powershell(script: Path) -> subprocess.CompletedProcess[str]:
    executable = shutil.which("pwsh.exe")
    assert executable is not None
    return subprocess.run(
        [
            executable,
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            script,
        ],
        cwd=INFRA_ROOT.parent,
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


def _container_ids() -> dict[str, str]:
    identities = {}
    for service in ("postgres", "minio"):
        result = _compose("ps", "-q", service)
        assert result.returncode == 0, result.stderr
        identity = result.stdout.strip()
        assert len(identity) == 64
        identities[service] = identity
    return identities


def test_records_and_objects_survive_stop_start_and_container_rebuild():
    if os.environ.get("AGENTEXAM_RUN_LOCAL_PERSISTENCE_REBUILD") != "1":
        pytest.skip("真实本机容器重建验收未显式启用")

    with local_scenario() as scenario:
        scenario.verify()
        original_ids = _container_ids()
        try:
            stopped = _powershell(STOP_SCRIPT)
            assert stopped.returncode == 0, stopped.stderr
            assert json.loads(stopped.stdout)["operation"] == "stopped"
            started = _powershell(START_SCRIPT)
            assert started.returncode == 0, started.stderr
            assert _container_ids() == original_ids
            scenario.verify()

            stopped = _powershell(STOP_SCRIPT)
            assert stopped.returncode == 0, stopped.stderr
            removed = _compose("down")
            assert removed.returncode == 0, removed.stderr
            started = _powershell(START_SCRIPT)
            assert started.returncode == 0, started.stderr
            rebuilt_ids = _container_ids()
            assert rebuilt_ids.keys() == original_ids.keys()
            assert all(rebuilt_ids[name] != original_ids[name] for name in rebuilt_ids)
            scenario.verify()
        finally:
            _powershell(START_SCRIPT)
