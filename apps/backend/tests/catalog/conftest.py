import json
import os
from contextlib import contextmanager
from hashlib import sha256
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from identity.conftest import (
    ORIGIN,
    PASSWORD,
    Clock,
    IdentityAPI,
    postgres_sandbox,  # noqa: F401
)
from membership.memory import MemoryMembershipRepository

from catalog.memory import FixedSource, MemoryAgents, MemoryArtifacts, MemoryTasks
from eval_platform.adapters.artifacts.config import MinioConfig, create_client
from eval_platform.adapters.artifacts.minio import MinioArtifactStore
from eval_platform.adapters.identity.passwords import Argon2Passwords
from eval_platform.application.agent_registry import AgentRegistry
from eval_platform.application.identity import IdentityService
from eval_platform.application.membership import MembershipService
from eval_platform.application.task_catalog import TaskCatalog
from eval_platform.delivery.http.app import create_app
from eval_platform.delivery.http.config import HttpConfig
from eval_platform.domain.agent import AgentConfiguration
from eval_platform.domain.task import EvaluationTask, EvaluatorTaskData, TaskBundle


def task_bundle(instance_id="example__repo-1", repo="example/repo"):
    raw = json.dumps(
        {
            "instance_id": instance_id,
            "repo": repo,
            "problem_statement": "Fix the visible bug.",
            "patch": "HIDDEN_ANSWER",
        },
        sort_keys=True,
    ).encode()
    return TaskBundle(
        EvaluationTask(
            "synthetic-dataset",
            "a" * 40,
            "train",
            instance_id,
            repo,
            "b" * 40,
            "Fix the visible bug.",
            "synthetic-image@sha256:" + "c" * 64,
            sha256(raw).hexdigest(),
        ),
        EvaluatorTaskData(
            instance_id,
            "test",
            "HIDDEN_ANSWER",
            "HIDDEN_ANSWER",
            ("hidden_test",),
            ("hidden_pass",),
        ),
        raw,
    )


DEFAULT_AGENT_PRESETS = {
    "verified-codex": (
        "Synthetic Codex",
        AgentConfiguration(
            "test-preset",
            "codex",
            "test-version",
            "openai_chatgpt",
            "test-model",
            "chatgpt_auth_json",
            "private-test-reference",
            {"reasoning_effort": "medium"},
        ),
    )
}


@contextmanager
def catalog_api(
    repository=None,
    artifacts=None,
    source=None,
    agents=None,
    presets=None,
    agent_presets=None,
):
    clock = Clock()
    identities = MemoryMembershipRepository()
    passwords = Argon2Passwords()
    identity = IdentityService(identities, passwords, clock)
    identity.bootstrap_owner("owner", PASSWORD)
    tasks = TaskCatalog(
        repository or MemoryTasks(),
        artifacts or MemoryArtifacts(),
        source or FixedSource(task_bundle()),
        presets or {"verified-task": "example__repo-1"},
    )
    registry = AgentRegistry(
        agents or MemoryAgents(),
        agent_presets or DEFAULT_AGENT_PRESETS,
    )
    app = create_app(
        identity,
        HttpConfig(public_origin=ORIGIN),
        MembershipService(identities, passwords, clock),
        tasks,
        registry,
    )
    with TestClient(app, base_url=ORIGIN, raise_server_exceptions=False) as client:
        yield IdentityAPI(client, identity, clock)


@pytest.fixture
def identity_api():
    with catalog_api() as api:
        yield api


@pytest.fixture
def minio_sandbox():
    if os.environ.get("AGENTEXAM_RUN_CATALOG_MINIO") != "1":
        pytest.skip("专属 MinIO 集成未显式启用")
    config = MinioConfig.from_environment()
    if (
        config.endpoint != "http://127.0.0.1:9000"
        or not config.access_key.startswith("ae_test_")
        or config.bucket != "agentexam-synthetic-test"
    ):
        pytest.fail("拒绝非专属对象存储测试配置", pytrace=False)
    client = create_client(config)
    bucket = "ae-catalog-test-" + uuid4().hex
    client.create_bucket(Bucket=bucket)
    try:
        yield MinioArtifactStore(client, bucket), client, bucket
    finally:
        contents = client.list_objects_v2(Bucket=bucket).get("Contents", [])
        for item in contents:
            client.delete_object(Bucket=bucket, Key=item["Key"])
        client.delete_bucket(Bucket=bucket)
