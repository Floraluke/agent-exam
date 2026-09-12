"""Frozen task, Agent, policy and resource values stored with a Job."""

from dataclasses import dataclass
from hashlib import sha256

from eval_platform.domain.catalog import CatalogTask, RegisteredAgent


@dataclass(frozen=True, slots=True)
class LimitSnapshot:
    agent_wall_timeout_sec: int
    agent_cpus: int
    agent_memory_mb: int
    agent_storage_mb: int
    evaluator_wall_timeout_sec: int
    evaluator_cpus: int
    evaluator_memory_mb: int
    pids_limit: int
    patch_warning_bytes: int
    patch_max_bytes: int
    raw_artifact_max_bytes: int
    raw_run_max_bytes: int
    concurrency: int
    max_retries: int


@dataclass(frozen=True, slots=True)
class NetworkPolicySnapshot:
    mode: str
    web_search: str
    arbitrary_hosts: bool


@dataclass(frozen=True, slots=True)
class ToolProfileSnapshot:
    agent_type: str
    web_search: str
    arbitrary_commands: bool


@dataclass(frozen=True, slots=True)
class TaskSnapshot:
    task_id: str
    instance_id: str
    dataset_id: str
    dataset_revision: str
    split: str
    repo: str
    base_commit: str
    problem_statement: str
    environment_image: str
    raw_record_sha256: str
    problem_sha256: str
    artifact_id: str
    source_object_key: str
    source_sha256: str

    @classmethod
    def from_record(cls, record: CatalogTask) -> "TaskSnapshot":
        task, source = record.task, record.source
        return cls(
            record.task_id,
            task.instance_id,
            task.dataset_id,
            task.dataset_revision,
            task.split,
            task.repo,
            task.base_commit,
            task.problem_statement,
            task.environment_image,
            task.raw_record_sha256,
            sha256(task.problem_statement.encode()).hexdigest(),
            record.artifact_id,
            source.object_key,
            source.sha256,
        )


@dataclass(frozen=True, slots=True)
class AgentSnapshot:
    agent_configuration_id: str
    display_name: str
    agent_type: str
    agent_version: str
    model_provider: str
    model: str
    authentication_type: str
    credential_profile_id: str
    reasoning_effort: str
    configuration_fingerprint: str

    @classmethod
    def from_record(cls, record: RegisteredAgent) -> "AgentSnapshot":
        configuration = record.configuration
        return cls(
            configuration.configuration_id,
            record.display_name,
            configuration.agent_name,
            configuration.agent_version,
            configuration.model_provider,
            configuration.model_name,
            configuration.authentication_type,
            configuration.credential_configuration_id,
            str(configuration.critical_config["reasoning_effort"]),
            configuration.fingerprint,
        )
