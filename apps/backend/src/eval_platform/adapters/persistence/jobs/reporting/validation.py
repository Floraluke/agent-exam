"""Fail-closed validation for frozen leaderboard evidence."""

from hashlib import sha256
from typing import Any

from eval_platform.domain.agent import AgentConfiguration
from eval_platform.domain.jobs.models import (
    AgentSnapshot,
    LimitSnapshot,
    NetworkPolicySnapshot,
    TaskSnapshot,
    ToolProfileSnapshot,
)


def read_task(value: object, row: dict[str, Any]) -> TaskSnapshot:
    snapshot = TaskSnapshot(**mapping(value))
    _texts(
        snapshot,
        (
            "task_id",
            "instance_id",
            "dataset_id",
            "dataset_revision",
            "split",
            "repo",
            "base_commit",
            "problem_statement",
            "environment_image",
            "raw_record_sha256",
            "problem_sha256",
            "artifact_id",
            "source_object_key",
            "source_sha256",
        ),
    )
    for name in ("raw_record_sha256", "problem_sha256", "source_sha256"):
        _digest(getattr(snapshot, name))
    if (
        sha256(snapshot.problem_statement.encode()).hexdigest()
        != snapshot.problem_sha256
    ):
        raise ValueError("Frozen task statement changed")
    frozen = (
        snapshot.task_id,
        snapshot.instance_id,
        snapshot.dataset_id,
        snapshot.dataset_revision,
        snapshot.split,
        snapshot.repo,
        snapshot.base_commit,
        snapshot.problem_statement,
        snapshot.environment_image,
        snapshot.raw_record_sha256,
        snapshot.problem_sha256,
        snapshot.artifact_id,
        snapshot.source_object_key,
        snapshot.source_sha256,
    )
    catalog = (
        str(row["catalog_task_id"]),
        row["catalog_instance_id"],
        row["catalog_dataset_id"],
        row["catalog_dataset_revision"],
        row["catalog_split"],
        row["catalog_repo"],
        row["catalog_base_commit"],
        row["catalog_problem_statement"],
        row["catalog_environment_image"],
        row["catalog_raw_record_sha256"],
        row["catalog_problem_sha256"],
        str(row["catalog_artifact_id"]),
        row["catalog_source_object_key"],
        row["catalog_source_sha256"],
    )
    if frozen != catalog:
        raise ValueError("Frozen task identity changed")
    return snapshot


def read_agent(value: object, row: dict[str, Any]) -> AgentSnapshot:
    snapshot = AgentSnapshot(**mapping(value))
    _texts(
        snapshot,
        (
            "agent_configuration_id",
            "display_name",
            "agent_type",
            "agent_version",
            "model_provider",
            "model",
            "authentication_type",
            "credential_profile_id",
            "reasoning_effort",
            "configuration_fingerprint",
        ),
    )
    configuration = AgentConfiguration(
        snapshot.agent_configuration_id,
        snapshot.agent_type,
        snapshot.agent_version,
        snapshot.model_provider,
        snapshot.model,
        snapshot.authentication_type,
        snapshot.credential_profile_id,
        {"reasoning_effort": snapshot.reasoning_effort},
    )
    frozen = (
        snapshot.agent_configuration_id,
        snapshot.display_name,
        snapshot.agent_type,
        snapshot.agent_version,
        snapshot.model_provider,
        snapshot.model,
        snapshot.authentication_type,
        snapshot.credential_profile_id,
        snapshot.reasoning_effort,
        snapshot.configuration_fingerprint,
    )
    catalog = (
        str(row["catalog_agent_configuration_id"]),
        row["catalog_agent_display_name"],
        row["catalog_agent_type"],
        row["catalog_agent_version"],
        row["catalog_model_provider"],
        row["catalog_model"],
        row["catalog_authentication_type"],
        row["catalog_credential_profile_id"],
        row["catalog_reasoning_effort"],
        row["catalog_configuration_fingerprint"],
    )
    if frozen != catalog:
        raise ValueError("Frozen Agent identity changed")
    if configuration.fingerprint != snapshot.configuration_fingerprint:
        raise ValueError("Frozen Agent fingerprint changed")
    return snapshot


def read_network(value: object) -> NetworkPolicySnapshot:
    snapshot = NetworkPolicySnapshot(**mapping(value))
    _texts(snapshot, ("mode", "web_search"))
    if type(snapshot.arbitrary_hosts) is not bool:
        raise ValueError("Frozen network policy is invalid")
    return snapshot


def read_tool(value: object) -> ToolProfileSnapshot:
    snapshot = ToolProfileSnapshot(**mapping(value))
    _texts(snapshot, ("agent_type", "web_search"))
    if type(snapshot.arbitrary_commands) is not bool:
        raise ValueError("Frozen tool policy is invalid")
    return snapshot


def read_limits(value: object) -> LimitSnapshot:
    snapshot = LimitSnapshot(**mapping(value))
    names = tuple(LimitSnapshot.__dataclass_fields__)
    for name in names:
        item = getattr(snapshot, name)
        if type(item) is not int or item < 0 or (name != "max_retries" and item == 0):
            raise ValueError("Frozen resource limit is invalid")
    return snapshot


def text(value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("Stored identity text is invalid")
    return value


def mapping(value: object) -> dict[str, Any]:
    if not isinstance(value, dict) or not all(isinstance(key, str) for key in value):
        raise ValueError("Stored snapshot is not an object")
    return value


def _texts(snapshot: object, names: tuple[str, ...]) -> None:
    for name in names:
        text(getattr(snapshot, name))


def _digest(value: str) -> None:
    if len(value) != 64 or any(char not in "0123456789abcdef" for char in value):
        raise ValueError("Frozen digest is invalid")
