from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from eval_platform.domain.agent import CONTROLLED_AGENT_TYPES, CONTROLLED_PROVIDERS
from eval_platform.domain.catalog import (
    CatalogTask,
    CatalogUnavailable,
    RegisteredAgent,
)


def _controlled(value: str, allowed: tuple[str, ...], code: str) -> Any:
    """Publish a record's own identity, or refuse instead of misreporting it.

    The controlled sets live in the domain; a value outside them means a record
    escaped the registry and the CHECK constraint, so failing closed is the only
    safe answer. The code stays inside the process: the error handler maps this
    to 503 DEPENDENCY_UNAVAILABLE, the contract's answer for a damaged catalog
    record, which reports the failure without echoing the value or the code.
    """
    if value not in allowed:
        raise CatalogUnavailable(code)
    return value


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
    """Public identity. Values come from the record; a test pins them to the
    controlled sets, so the enum and the domain constants cannot drift apart."""

    agent_configuration_id: str
    display_name: str
    agent_type: Literal["codex"]
    agent_version: str
    # The enums are pinned to the domain constants by the agent-identity test.
    model_provider: Literal["openai_chatgpt", "internal_test_fake"]
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
            agent_type=_controlled(
                configuration.agent_name,
                CONTROLLED_AGENT_TYPES,
                "UNCONTROLLED_AGENT_TYPE",
            ),
            agent_version=configuration.agent_version,
            model_provider=_controlled(
                configuration.model_provider,
                CONTROLLED_PROVIDERS,
                "UNCONTROLLED_PROVIDER",
            ),
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
