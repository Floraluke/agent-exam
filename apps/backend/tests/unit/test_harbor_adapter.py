from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import pytest

from eval_platform.adapters.execution import harbor_entry
from eval_platform.adapters.execution.harbor import adapter as adapter_module
from eval_platform.adapters.execution.harbor.adapter import HarborExecutionAdapter
from eval_platform.adapters.execution.harbor.config_mapper import (
    ARTIFACT_CONTRACT_VERSION,
    HARBOR_REVISION,
)
from eval_platform.adapters.execution.harbor.process_evidence import CapturedLog
from eval_platform.adapters.execution.harbor.process_runner import ProcessOutcome
from eval_platform.application.ports.execution import (
    ExecutionJobRequest,
    ExecutionRunRequest,
    RunLimits,
)
from eval_platform.domain.agent import AgentConfiguration
from eval_platform.domain.result import TerminationReason
from eval_platform.domain.task import EvaluationTask


def _request(job_id: str = "adapter-test") -> ExecutionJobRequest:
    task = EvaluationTask(
        dataset_id="SWE-Gym/SWE-Gym-Lite",
        dataset_revision="a" * 40,
        split="train",
        instance_id="python__mypy-15413",
        repo="python/mypy",
        base_commit="b" * 40,
        problem_statement="Public issue",
        environment_image="example.invalid/task@sha256:" + "c" * 64,
        raw_record_sha256="d" * 64,
    )
    agent = AgentConfiguration(
        configuration_id="codex-prototype",
        agent_name="codex",
        agent_version="0.153.0",
        model_provider="openai",
        model_name="model-must-be-confirmed",
        authentication_type="chatgpt_auth_json",
        credential_configuration_id="owner-codex-login",
        critical_config={"reasoning_effort": "medium"},
    )
    return ExecutionJobRequest(
        job_id=job_id,
        runs=(ExecutionRunRequest("run-one", task, agent),),
        limits=RunLimits(300, 1, 2048, 4096),
        backend_revision=HARBOR_REVISION,
        artifact_contract_version=ARTIFACT_CONTRACT_VERSION,
    )


def _adapter(tmp_path: Path) -> HarborExecutionAdapter:
    executable = tmp_path / "harbor.exe"
    executable.write_bytes(b"placeholder")
    executable.with_name("python.exe").touch()
    return HarborExecutionAdapter(executable, tmp_path / "evidence", tmp_path)


def _write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8", newline="\n")


def _write_successful_harbor_result(config_path: Path) -> None:
    config = json.loads(config_path.read_text(encoding="utf-8"))
    job_dir = Path(config["jobs_dir"]) / config["job_name"]
    trial_dir = job_dir / "trial-one"
    trial_config = {"task": config["tasks"][0], "agent": config["agents"][0]}
    _write_json(job_dir / "result.json", {"id": "harbor-job-id"})
    _write_json(trial_dir / "config.json", trial_config)
    _write_json(
        trial_dir / "result.json",
        {
            "id": "harbor-trial-id",
            "config": trial_config,
            "exception_info": None,
            "agent_result": None,
        },
    )
    artifact_dir = trial_dir / "artifacts/agentexam"
    artifact_dir.mkdir(parents=True)
    content = b""
    (artifact_dir / "model.patch").write_bytes(content)
    (artifact_dir / "patch.sha256").write_text(
        hashlib.sha256(content).hexdigest(), encoding="ascii"
    )
    (artifact_dir / "patch.bytes").write_text("0", encoding="ascii")
    (artifact_dir / "patch.binary").write_text("0", encoding="ascii")


def _outcome(
    root: Path,
    *,
    returncode: int = 0,
    timed_out: bool = False,
    warnings: tuple[str, ...] = (),
    stdout: bytes = b"harbor ok",
    stderr: bytes = b"",
) -> ProcessOutcome:
    stdout_path = root / "harbor.stdout.log"
    stderr_path = root / "harbor.stderr.log"
    stdout_path.write_bytes(stdout)
    stderr_path.write_bytes(stderr)
    return ProcessOutcome(
        returncode,
        timed_out,
        CapturedLog(stdout_path.resolve(), len(stdout), False),
        CapturedLog(stderr_path.resolve(), len(stderr), False),
        warnings,
    )


def test_executes_fixed_cli_and_maps_result(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[tuple[list[str], dict[str, Any]]] = []

    def fake_run(command: list[str], **kwargs: Any) -> ProcessOutcome:
        calls.append((command, kwargs))
        _write_successful_harbor_result(Path(command[3]))
        return _outcome(kwargs["evidence_root"])

    monkeypatch.setattr(adapter_module, "run_bounded_process", fake_run)
    result = _adapter(tmp_path).execute(_request())[0]

    assert result.termination_reason is TerminationReason.COMPLETED
    assert result.run_id == "run-one" and result.patch_ref is not None
    command, kwargs = calls[0]
    assert command[1:] == [
        str(Path(harbor_entry.__file__).resolve()),
        "--config",
        str((tmp_path / "evidence/adapter-test/harbor-config.json").resolve()),
        "--harbor-root",
        str((tmp_path / "harbor.exe").resolve().parents[2]),
    ]
    assert kwargs["env"]["HARBOR_TELEMETRY"] == "disabled"
    assert kwargs["env"]["PYTHONIOENCODING"] == "utf-8"
    assert kwargs["env"]["PYTHONUTF8"] == "1"
    assert kwargs["timeout_sec"] == 2640
    run_root = tmp_path / "evidence/adapter-test"
    assert (run_root / "harbor.stdout.log").read_text() == "harbor ok"
    frozen = (run_root / "harbor-config.json").read_text(encoding="utf-8")
    assert "CODEX_AUTH_JSON_PATH" not in frozen
    assert "owner-codex-login" not in frozen


def test_refuses_to_overwrite_existing_evidence(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fake_run(command: list[str], **kwargs: Any) -> ProcessOutcome:
        _write_successful_harbor_result(Path(command[3]))
        return _outcome(kwargs["evidence_root"], stdout=b"")

    monkeypatch.setattr(adapter_module, "run_bounded_process", fake_run)
    adapter = _adapter(tmp_path)
    adapter.execute(_request())

    with pytest.raises(FileExistsError, match="Refusing to overwrite"):
        adapter.execute(_request())


def test_process_timeout_is_explicit_and_keeps_partial_logs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fake_timeout(_command: list[str], **kwargs: Any) -> ProcessOutcome:
        return _outcome(
            kwargs["evidence_root"],
            returncode=124,
            timed_out=True,
            warnings=("HARBOR_PROCESS_TIMEOUT", "HARBOR_STDERR_TRUNCATED"),
            stdout=b"partial stdout",
            stderr=b"timeout stderr",
        )

    monkeypatch.setattr(adapter_module, "run_bounded_process", fake_timeout)
    result = _adapter(tmp_path).execute(_request("timeout-test"))[0]

    assert result.termination_reason is TerminationReason.TIMED_OUT
    assert result.backend_job_ref == "timeout-test"
    assert result.warnings == (
        "HARBOR_JOB_RESULT_MISSING",
        "HARBOR_PROCESS_TIMEOUT",
        "HARBOR_STDERR_TRUNCATED",
        "HARBOR_COMPOSE_CLEANUP_UNVERIFIED",
    )
    run_root = tmp_path / "evidence/timeout-test"
    assert (run_root / "harbor.stdout.log").read_text() == "partial stdout"
    assert (run_root / "harbor.stderr.log").read_text() == "timeout stderr"
