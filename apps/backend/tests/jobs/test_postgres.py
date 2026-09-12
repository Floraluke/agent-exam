from contextlib import contextmanager
from dataclasses import replace
from hashlib import sha256
from uuid import uuid4

import pytest
from catalog.conftest import task_bundle
from catalog.memory import FixedSource, MemoryArtifacts
from fastapi.testclient import TestClient
from identity.conftest import ORIGIN, PASSWORD, WRITE_HEADERS

from eval_platform.adapters.identity.passwords import Argon2Passwords
from eval_platform.adapters.persistence.catalog import (
    initialize_schema as init_catalog,
)
from eval_platform.adapters.persistence.catalog.agents import PostgresAgentRepository
from eval_platform.adapters.persistence.catalog.tasks import PostgresTaskRepository
from eval_platform.adapters.persistence.jobs import initialize_schema as init_jobs
from eval_platform.adapters.persistence.jobs.repository import PostgresJobRepository
from eval_platform.application.agent_registry import AgentRegistry
from eval_platform.application.identity import IdentityService
from eval_platform.application.job_submission import JobSubmission
from eval_platform.application.task_catalog import TaskCatalog
from eval_platform.delivery.http.app import create_app
from eval_platform.delivery.http.config import HttpConfig
from eval_platform.delivery.job_presets import submission_policy
from eval_platform.domain.agent import AgentConfiguration
from eval_platform.domain.jobs.models import (
    JobIdempotencyConflict,
    JobNotFound,
    JobUnavailable,
)
from jobs.test_http import submission, submit

pytestmark = pytest.mark.integration


@contextmanager
def postgres_api(sandbox, *, initialize=True):
    if initialize:
        init_catalog(sandbox.dsn)
        init_jobs(sandbox.dsn)
    passwords = Argon2Passwords()
    identity = IdentityService(sandbox.repository, passwords)
    owner = identity.bootstrap_owner("owner", PASSWORD)
    source = FixedSource(task_bundle())
    source.bundles["example__repo-2"] = task_bundle("example__repo-2")
    tasks = TaskCatalog(
        PostgresTaskRepository(sandbox.dsn),
        MemoryArtifacts(),
        source,
        {"verified-task": "example__repo-1", "verified-task-2": "example__repo-2"},
    )
    agents = AgentRegistry(
        PostgresAgentRepository(sandbox.dsn),
        {
            "verified-codex": (
                "Synthetic Codex",
                AgentConfiguration(
                    "preset",
                    "codex",
                    "test-version",
                    "openai_chatgpt",
                    "test-model",
                    "chatgpt_auth_json",
                    "test-private-reference",
                    {"reasoning_effort": "medium"},
                ),
            )
        },
    )
    repository = PostgresJobRepository(sandbox.dsn)
    jobs = JobSubmission(tasks, agents, repository, submission_policy("internal_test"))
    app = create_app(
        identity,
        HttpConfig(public_origin=ORIGIN),
        tasks=tasks,
        agents=agents,
        jobs=jobs,
    )
    with TestClient(app, base_url=ORIGIN, raise_server_exceptions=False) as client:
        yield client, jobs, repository, owner


def login(client):
    return client.post(
        "/api/v1/auth/login",
        json={"username": "owner", "password": PASSWORD},
        headers=WRITE_HEADERS,
    )


def register(client, endpoint, preset):
    return client.post(
        endpoint, json={"preset_id": preset}, headers=WRITE_HEADERS
    ).json()


def test_explicit_upgrade_and_recreated_http_restore_frozen_job(postgres_sandbox):
    repository = PostgresJobRepository(postgres_sandbox.dsn)
    with pytest.raises(JobUnavailable):
        repository.list(None, {}, None, 20)
    with postgres_api(postgres_sandbox) as (client, jobs, repository, owner):
        assert login(client).status_code == 200
        task = register(client, "/api/v1/tasks/register", "verified-task")
        agent = register(client, "/api/v1/agent-configurations", "verified-codex")
        created = submit(
            type("API", (), {"client": client})(),
            submission(task["task_id"], agent["agent_configuration_id"]),
            "postgres-restore-0001",
        ).json()
        stored = repository.get(created["job_id"])
        assert stored.trial_count == 1
        assert len(stored.state_events) == len(stored.runs[0].state_events) == 1
    identity = IdentityService(postgres_sandbox.repository, Argon2Passwords())
    empty_tasks = TaskCatalog(
        PostgresTaskRepository(postgres_sandbox.dsn),
        MemoryArtifacts(),
        FixedSource(task_bundle()),
        {},
    )
    empty_agents = AgentRegistry(PostgresAgentRepository(postgres_sandbox.dsn), {})
    restored_jobs = JobSubmission(
        empty_tasks,
        empty_agents,
        PostgresJobRepository(postgres_sandbox.dsn),
        submission_policy("internal_test"),
    )
    app = create_app(identity, HttpConfig(public_origin=ORIGIN), jobs=restored_jobs)
    with TestClient(app, base_url=ORIGIN, raise_server_exceptions=False) as client:
        login(client)
        detail = client.get("/api/v1/jobs/" + created["job_id"])
        assert detail.status_code == 200
        assert detail.json()["task_snapshots"][0]["problem_statement"] == (
            "Fix the visible bug."
        )


def test_duplicate_run_failure_rolls_back_job_and_events(postgres_sandbox):
    with postgres_api(postgres_sandbox) as (client, jobs, repository, owner):
        login(client)
        first = register(client, "/api/v1/tasks/register", "verified-task")
        second = register(client, "/api/v1/tasks/register", "verified-task-2")
        agent = register(client, "/api/v1/agent-configurations", "verified-codex")
        original = jobs.submit(
            owner,
            [first["task_id"], second["task_id"]],
            [agent["agent_configuration_id"]],
            "closed_book",
            "demo",
            "default-single-host-v1",
            "rollback-source-0001",
        )
        broken_id = str(uuid4())
        duplicate_id = str(uuid4())
        runs = tuple(
            replace(run, job_id=broken_id, run_id=duplicate_id) for run in original.runs
        )
        broken = replace(original, job_id=broken_id, runs=runs)
        with pytest.raises(JobIdempotencyConflict):
            repository.create(
                broken,
                sha256(b"key").hexdigest(),
                sha256(b"body").hexdigest(),
            )
        with pytest.raises(JobNotFound):
            repository.get(broken_id)
