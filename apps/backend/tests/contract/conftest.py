"""Synthetic M0 fixtures: deliberately contain markers to catch hidden-data leaks."""

from types import SimpleNamespace

import pytest

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
from eval_platform.domain.task import EvaluationTask, EvaluatorTaskData, TaskBundle


@pytest.fixture
def pipeline(tmp_path):
    public = EvaluationTask(
        "dataset",
        "revision",
        "train",
        "task-1",
        "org/repo",
        "a" * 40,
        "public issue",
        "image@sha256:fixed",
        "b" * 64,
    )
    hidden = EvaluatorTaskData("task-1", "1", "HIDDEN_GOLD", "HIDDEN_TEST", (), ())
    bundle = TaskBundle(public, hidden, b"HIDDEN_RAW")
    agent = AgentConfiguration(
        "config-1",
        "codex",
        "0.0.0-probe",
        "openai_chatgpt",
        "test-only",
        "chatgpt_auth_json",
        "secret-logical-id",
        {"reasoning_effort": "low"},
    )
    request = ExecutionJobRequest(
        "job-1",
        (ExecutionRunRequest("run-1", public, agent),),
        RunLimits(300, 1, 2048, 4096),
        HARBOR_REVISION,
        ARTIFACT_CONTRACT_VERSION,
    )
    return SimpleNamespace(root=tmp_path / "evidence", bundle=bundle, request=request)
