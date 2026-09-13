from dataclasses import replace
from hashlib import sha256
from uuid import uuid4

import pytest
from catalog.conftest import task_bundle
from catalog.memory import FixedSource, MemoryArtifacts
from fastapi.testclient import TestClient
from identity.conftest import ORIGIN, WRITE_HEADERS

from eval_platform.adapters.identity.passwords import Argon2Passwords
from eval_platform.adapters.persistence.catalog.agents import PostgresAgentRepository
from eval_platform.adapters.persistence.catalog.tasks import PostgresTaskRepository
from eval_platform.adapters.persistence.jobs.repository import PostgresJobRepository
from eval_platform.application.agent_registry import AgentRegistry
from eval_platform.application.identity import IdentityService
from eval_platform.application.job_submission import JobSubmission
from eval_platform.application.task_catalog import TaskCatalog
from eval_platform.delivery.http.app import create_app
from eval_platform.delivery.http.config import HttpConfig
from eval_platform.delivery.job_presets import submission_policy
from eval_platform.domain.jobs.models import (
    JobIdempotencyConflict,
    JobNotFound,
    JobUnavailable,
)
from jobs.support.postgres_api import login, postgres_api, register
from jobs.test_http import submission, submit

pytestmark = pytest.mark.integration


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


def test_malformed_catalog_ids_are_validation_errors(postgres_sandbox):
    with postgres_api(postgres_sandbox) as (client, jobs, repository, owner):
        assert login(client).status_code == 200
        response = client.post(
            "/api/v1/jobs",
            json={
                "task_ids": ["not-a-uuid"],
                "agent_configuration_ids": ["also-not-a-uuid"],
                "evaluation_track": "closed_book",
                "batch_preset": "demo",
                "limit_profile_id": "default-single-host-v1",
            },
            headers={**WRITE_HEADERS, "Idempotency-Key": "malformed-pg-0001"},
        )
        assert response.status_code == 422


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
