from __future__ import annotations

import asyncio
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from eval_platform.adapters.execution.codex.uploads import CodexUploads
from eval_platform.adapters.execution.harbor import adapter as adapter_module
from eval_platform.adapters.execution.harbor.adapter import HarborExecutionAdapter
from eval_platform.adapters.execution.harbor.config_mapper import (
    ARTIFACT_CONTRACT_VERSION,
    HARBOR_REVISION,
)
from eval_platform.application.ports.execution import (
    ExecutionJobRequest,
    ExecutionRunRequest,
    RunLimits,
)
from eval_platform.domain.agent import AgentConfiguration
from eval_platform.domain.task import EvaluationTask


class TransferEnvironment:
    default_user = "65534:65534"

    def __init__(self, *, failure=False):
        self.calls = []
        self.failure = failure

    async def _run_docker_compose_command(self, args, **kwargs):
        self.calls.append((args, kwargs))
        return SimpleNamespace(
            return_code=1 if self.failure else 0,
            stdout="SYNTHETIC-PRIVATE-DIAGNOSTIC" if self.failure else None,
            stderr=None,
        )


@pytest.mark.parametrize("target", sorted(CodexUploads.TARGETS))
def test_private_transfer_uses_stdin_and_non_root_exclusive_creation(tmp_path, target):
    source = tmp_path / "synthetic-file"
    content = b"SYNTHETIC-PRIVATE-CONTENT"
    source.write_bytes(content)
    environment = TransferEnvironment()
    asyncio.run(CodexUploads(environment).upload_file(source, target))
    ((args, options),) = environment.calls
    assert args[:7] == ["exec", "-T", "-u", "65534:65534", "main", "sh", "-c"]
    assert args[-1] == f"set -C; umask 077; cat > {target}"
    assert content.decode() not in repr(args) and str(source) not in repr(args)
    assert options == {"check": False, "timeout_sec": 30, "stdin_data": content}


@pytest.mark.parametrize("user", [None, "root", "0:0", "65534", "65534:0;id"])
def test_private_transfer_rejects_unknown_user_before_touching_files(user):
    with pytest.raises(ValueError, match="CODEX_UPLOAD_USER_INVALID"):
        CodexUploads(SimpleNamespace(default_user=user))


@pytest.mark.parametrize("size", [0, 65537])
def test_private_transfer_is_bounded_and_rejects_invalid_input(tmp_path, size):
    source = tmp_path / "synthetic-file"
    source.write_bytes(b"a" * size)
    environment = TransferEnvironment()
    with pytest.raises(RuntimeError, match="^CODEX_PRIVATE_UPLOAD_FAILED$"):
        asyncio.run(
            CodexUploads(environment).upload_file(
                source, next(iter(CodexUploads.TARGETS))
            )
        )
    assert not environment.calls


def test_private_transfer_rejects_other_targets_before_opening_a_source(tmp_path):
    environment = TransferEnvironment()
    with pytest.raises(ValueError, match="CODEX_UPLOAD_TARGET_INVALID"):
        asyncio.run(
            CodexUploads(environment).upload_file(
                tmp_path / "does-not-exist", "/logs/auth.json"
            )
        )
    assert not environment.calls


def test_private_transfer_diagnostics_and_missing_paths_do_not_escape(tmp_path):
    environment = TransferEnvironment(failure=True)
    source = tmp_path / "synthetic-private-host-path"
    target = "/tmp/codex-secrets/auth.json"
    for present in (False, True):
        if present:
            source.write_bytes(b"SYNTHETIC-PRIVATE-CONTENT")
        with pytest.raises(RuntimeError) as error:
            asyncio.run(CodexUploads(environment).upload_file(source, target))
        assert str(error.value) == "CODEX_PRIVATE_UPLOAD_FAILED"
        assert error.value.__suppress_context__


def test_private_transfer_rejects_symlink_source(tmp_path, monkeypatch):
    source = tmp_path / "synthetic-file"
    source.write_bytes(b"fake")
    monkeypatch.setattr(type(source), "is_symlink", lambda self: True)
    environment = TransferEnvironment()
    with pytest.raises(RuntimeError, match="CODEX_PRIVATE_UPLOAD_FAILED"):
        asyncio.run(
            CodexUploads(environment).upload_file(
                source, "/tmp/codex-secrets/auth.json"
            )
        )
    assert not environment.calls


def test_adapter_stages_private_inputs_outside_the_job_config(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    archive, auth = tmp_path / "fixed.tgz", tmp_path / "auth.json"
    archive.write_bytes(b"fixed-placeholder")
    auth.write_text("{}")
    executable = tmp_path / "harbor.exe"
    executable.touch()
    executable.with_name("python.exe").touch()
    task = EvaluationTask(
        "dataset",
        "revision",
        "train",
        "task",
        "org/repo",
        "a" * 40,
        "public issue",
        "image@sha256:" + "b" * 64,
        "c" * 64,
    )
    agent = AgentConfiguration(
        "fixed",
        "codex",
        "0.153.0",
        "openai",
        "gpt-5.6-terra",
        "chatgpt_auth_json",
        "owner-login",
        {"reasoning_effort": "medium"},
    )
    request = ExecutionJobRequest(
        "job",
        (ExecutionRunRequest("run", task, agent),),
        RunLimits(60, 1, 512, 512),
        HARBOR_REVISION,
        ARTIFACT_CONTRACT_VERSION,
    )
    captured: dict[str, Any] = {}

    def prepare(_source: Path, destination: Path) -> Path:
        captured["bundle_root"] = destination
        destination.mkdir()
        return destination

    def stop(_self: Any, *_args: Any) -> tuple[()]:
        return ()

    monkeypatch.setattr(adapter_module, "prepare_codex_bundle", prepare)
    monkeypatch.setattr(HarborExecutionAdapter, "_run", stop)
    adapter = HarborExecutionAdapter(
        executable,
        tmp_path / "evidence",
        tmp_path,
        codex_archive=archive,
        codex_auth_path=auth,
    )
    assert adapter.execute(request) == ()
    assert captured["bundle_root"] == tmp_path / "evidence/job/codex-input"
    config = (tmp_path / "evidence/job/harbor-config.json").read_text()
    assert str(auth.resolve()) not in config and str(archive.resolve()) not in config
    assert str(auth.resolve()) not in repr(adapter)
