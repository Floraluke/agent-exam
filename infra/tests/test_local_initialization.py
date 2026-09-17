import json
import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

SCRIPT = Path(__file__).parents[1] / "local" / "Initialize-AgentExam.ps1"
POSTGRES_IMAGE = (
    "docker.io/library/postgres@sha256:"
    "a2c20749c564b4eb73a77bfda626f8a3cde1bbfae020fb97c616a00cdc1a2181"
)
MINIO_IMAGE = (
    "quay.io/minio/aistor/minio@sha256:"
    "dfa8e241413464755a9cd90574b15030d6a5703c74ec73928abb6d9c5f4f42ce"
)


def test_validate_only_reports_fixed_non_secret_deployment_state():
    if os.environ.get("AGENTEXAM_RUN_LOCAL_DEPLOYMENT") != "1":
        pytest.skip("真实本机部署检查未显式启用")
    powershell = shutil.which("pwsh.exe")
    assert powershell is not None

    result = subprocess.run(
        [
            powershell,
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            SCRIPT,
            "-ValidateOnly",
        ],
        cwd=SCRIPT.parents[2],
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )

    assert result.returncode == 0, result.stderr
    state = json.loads(result.stdout)
    assert set(state) == {
        "ready",
        "dataRoot",
        "project",
        "dockerServer",
        "postgresImage",
        "minioImage",
        "licensePresent",
        "initializationState",
    }
    assert state["ready"] is True
    assert state["dataRoot"] == "D:\\AgentExamData"
    assert state["project"] == "agentexam-local"
    assert re.fullmatch(r"\d+\.\d+\.\d+", state["dockerServer"])
    assert state["postgresImage"] == POSTGRES_IMAGE
    assert state["minioImage"] == MINIO_IMAGE
    assert state["licensePresent"] is True
    assert state["initializationState"] in {"fresh", "partial", "complete"}
    assert "password" not in result.stdout.lower()


def test_initialize_is_repeatable_after_reaching_complete_state():
    if os.environ.get("AGENTEXAM_RUN_LOCAL_INITIALIZATION") != "1":
        pytest.skip("真实本机首次初始化未显式启用")
    powershell = shutil.which("pwsh.exe")
    assert powershell is not None

    command = [
        powershell,
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        SCRIPT,
    ]
    first = subprocess.run(
        command,
        cwd=SCRIPT.parents[2],
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )

    assert first.returncode == 0, first.stderr
    assert json.loads(first.stdout)["initializationState"] == "complete"
    assert "password" not in (first.stdout + first.stderr).lower()

    second = subprocess.run(
        command,
        cwd=SCRIPT.parents[2],
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    assert second.returncode == 0, second.stderr
    assert json.loads(second.stdout)["initializationState"] == "complete"
