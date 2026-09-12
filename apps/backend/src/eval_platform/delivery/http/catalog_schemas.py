from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from eval_platform.domain.catalog import CatalogTask, RegisteredAgent


class RegisterPreset(BaseModel):
    model_config = ConfigDict(extra="forbid")
    preset_id: str = Field(min_length=1, max_length=64, pattern=r"^[a-z0-9-]+$")


class TaskSummary(BaseModel):
    task_id: str
    instance_id: str
    dataset_id: str
    dataset_revision: str
    split: str
    repo: str
    base_commit: str
    problem_statement_preview: str


class TaskDetail(TaskSummary):
    problem_statement: str

    @classmethod
    def from_record(cls, record: CatalogTask) -> "TaskDetail":
        task = record.task
        return cls(
            task_id=record.task_id,
            instance_id=task.instance_id,
            dataset_id=task.dataset_id,
            dataset_revision=task.dataset_revision,
            split=task.split,
            repo=task.repo,
            base_commit=task.base_commit,
            problem_statement_preview=task.problem_statement[:240],
            problem_statement=task.problem_statement,
        )


class TaskPage(BaseModel):
    items: list[TaskSummary]
    next_cursor: str | None


class PublicOptions(BaseModel):
    model_config = ConfigDict(extra="forbid")
    reasoning_effort: Literal["low", "medium", "high", "xhigh"]


class AgentSummary(BaseModel):
    agent_configuration_id: str
    display_name: str
    agent_type: Literal["codex"]
    agent_version: str
    model_provider: Literal["openai_chatgpt"]
    model: str
    configuration_fingerprint: str
    enabled: bool


class AgentDetail(AgentSummary):
    public_options: PublicOptions
    limit_profile_id: str | None

    @classmethod
    def from_record(cls, record: RegisteredAgent) -> "AgentDetail":
        configuration = record.configuration
        return cls(
            agent_configuration_id=configuration.configuration_id,
            display_name=record.display_name,
            agent_type="codex",
            agent_version=configuration.agent_version,
            model_provider="openai_chatgpt",
            model=configuration.model_name,
            configuration_fingerprint=configuration.fingerprint,
            enabled=record.enabled,
            public_options=PublicOptions.model_validate(
                dict(configuration.critical_config)
            ),
            limit_profile_id=record.limit_profile_id,
        )


class AgentPage(BaseModel):
    items: list[AgentSummary]
    next_cursor: str | None
