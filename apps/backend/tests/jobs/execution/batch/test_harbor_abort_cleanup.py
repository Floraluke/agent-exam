import json
from pathlib import Path

import pytest

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


class RejectingObserver:
    def trial_started(self, _run_id):
        raise RuntimeError("progress repository unavailable")

    def trial_finished(self, _run_id):
        raise AssertionError("the incomplete Trial cannot finish")


def _request():
    task = EvaluationTask(
        "dataset",
        "a" * 40,
        "train",
        "task-one",
        "owner/repo",
        "b" * 40,
        "Public issue",
        "example.invalid/task@sha256:" + "c" * 64,
        "d" * 64,
    )
    agent = AgentConfiguration(
        "agent-one",
        "codex",
        "0.153.0",
        "openai",
        "model",
        "chatgpt_auth_json",
        "owner-login",
        {"reasoning_effort": "medium"},
    )
    return ExecutionJobRequest(
        "job-one",
        (ExecutionRunRequest("run-one", task, agent),),
        RunLimits(1, 1, 1024, 2048),
        HARBOR_REVISION,
        ARTIFACT_CONTRACT_VERSION,
    )


def test_public_execute_cleans_compose_when_progress_storage_fails(
    tmp_path, monkeypatch
):
    executable = tmp_path / "harbor.exe"
    executable.write_bytes(b"fixed")
    (tmp_path / "python.exe").touch()

    def render(task, root, _limits):
        directory = root / task.instance_id
        directory.mkdir(parents=True)
        return directory

    adapter = HarborExecutionAdapter(
        executable, tmp_path / "evidence", tmp_path, task_renderer=render
    )
    job_dir = tmp_path / "evidence/job-one/jobs/job-one"
    cleaned = []

    def fail_during_poll(command, **kwargs):
        config = json.loads(Path(command[3]).read_text(encoding="utf-8"))
        trial_dir = job_dir / "trial-one"
        trial_dir.mkdir(parents=True)
        trial = {"task": config["tasks"][0], "agent": config["agents"][0]}
        (trial_dir / "config.json").write_text(json.dumps(trial), encoding="utf-8")
        kwargs["on_poll"]()
        raise AssertionError("observer should stop the process call")

    monkeypatch.setattr(adapter_module, "run_bounded_process", fail_during_poll)
    monkeypatch.setattr(
        adapter_module,
        "cleanup_timed_out_projects",
        lambda path: cleaned.append(path) or (),
    )

    with pytest.raises(RuntimeError, match="repository unavailable"):
        adapter.execute(_request(), RejectingObserver())

    assert cleaned == [job_dir]
