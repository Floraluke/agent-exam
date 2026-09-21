"""Trusted server presets. No user-supplied source paths, commands or model URLs."""

import os
from pathlib import Path

from eval_platform.adapters.artifacts.minio import MinioArtifactStore
from eval_platform.adapters.persistence.catalog.agents import PostgresAgentRepository
from eval_platform.adapters.persistence.catalog.tasks import PostgresTaskRepository
from eval_platform.adapters.tasks.swe_gym import CANDIDATE_INSTANCE_ID, SWEGymTaskSource
from eval_platform.application.agent_registry import AgentRegistry
from eval_platform.application.task_catalog import TaskCatalog
from eval_platform.domain.agent import (
    INTERNAL_TEST_AUTHENTICATION,
    INTERNAL_TEST_PROVIDER,
    AgentConfiguration,
)
from eval_platform.domain.task import TaskBundle

TASK_PRESETS = {
    # 旧题：M0 单题入口，身份不变
    "swe-gym-lite-mypy-15413": CANDIDATE_INSTANCE_ID,
    # 2026-09-21 通过三补丁门禁的五道新题（证据见任务 04 行动文档）
    "swe-gym-lite-mypy-15131": "python__mypy-15131",
    "swe-gym-lite-mypy-15139": "python__mypy-15139",
    "swe-gym-lite-mypy-15184": "python__mypy-15184",
    "swe-gym-lite-mypy-15208": "python__mypy-15208",
    "swe-gym-lite-mypy-15876": "python__mypy-15876",
}
AGENT_PRESETS = {
    "codex-0153-terra-medium": (
        "Codex 0.153.0 / gpt-5.6-terra / medium",
        AgentConfiguration(
            "codex-0153-terra-medium",
            "codex",
            "0.153.0",
            "openai_chatgpt",
            "gpt-5.6-terra",
            "chatgpt_auth_json",
            "owner-codex",
            {"reasoning_effort": "medium"},
        ),
    ),
}


# Only ever passed in by an internal_test deployment (owner machine runbook, or a test):
# production wiring uses AGENT_PRESETS above, which must not contain a fake provider.
INTERNAL_TEST_AGENT_PRESETS = {
    "internal-test-provider-proxy": (
        "Internal test / provider proxy",
        AgentConfiguration(
            "internal-test-provider-proxy",
            "codex",
            "0.153.0",
            INTERNAL_TEST_PROVIDER,
            "deepseek-flash",
            INTERNAL_TEST_AUTHENTICATION,
            "t05-fake-provider",
            {"reasoning_effort": "medium"},
        ),
    ),
}


class _ConfiguredTaskSource:
    def load(self, instance_id: str) -> TaskBundle:
        parquet = os.environ.get("AGENTEXAM_TASK_PARQUET", "")
        if not parquet or not Path(parquet).is_absolute():
            raise ValueError("A fixed local dataset path must be configured explicitly")
        return SWEGymTaskSource(Path(parquet)).load(instance_id)


def create_catalog(dsn: str) -> tuple[TaskCatalog, AgentRegistry]:
    tasks = TaskCatalog(
        PostgresTaskRepository(dsn),
        MinioArtifactStore(None, ""),
        _ConfiguredTaskSource(),
        TASK_PRESETS,
    )
    return tasks, AgentRegistry(PostgresAgentRepository(dsn), AGENT_PRESETS)
