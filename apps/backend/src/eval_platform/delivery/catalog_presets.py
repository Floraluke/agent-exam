"""Trusted server presets. No user-supplied source paths, commands or model URLs."""

import os
from pathlib import Path

from eval_platform.adapters.artifacts.minio import MinioArtifactStore
from eval_platform.adapters.persistence.catalog.agents import PostgresAgentRepository
from eval_platform.adapters.persistence.catalog.tasks import PostgresTaskRepository
from eval_platform.adapters.tasks.swe_gym import CANDIDATE_INSTANCE_ID, SWEGymTaskSource
from eval_platform.application.agent_registry import AgentRegistry
from eval_platform.application.task_catalog import TaskCatalog
from eval_platform.domain.agent import AgentConfiguration
from eval_platform.domain.task import TaskBundle

TASK_PRESETS = {"swe-gym-lite-mypy-15413": CANDIDATE_INSTANCE_ID}
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
