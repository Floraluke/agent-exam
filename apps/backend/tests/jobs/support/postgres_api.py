"""Shared real-PostgreSQL HTTP fixture for Job acceptance tests."""

from contextlib import contextmanager

from catalog.conftest import task_bundle
from catalog.memory import FixedSource
from catalog.memory import MemoryArtifacts as CatalogArtifacts
from fastapi.testclient import TestClient
from identity.conftest import ORIGIN, PASSWORD, WRITE_HEADERS

from eval_platform.adapters.identity.passwords import Argon2Passwords
from eval_platform.adapters.persistence.catalog import initialize_schema as init_catalog
from eval_platform.adapters.persistence.catalog.agents import PostgresAgentRepository
from eval_platform.adapters.persistence.catalog.tasks import PostgresTaskRepository
from eval_platform.adapters.persistence.jobs import initialize_schema as init_jobs
from eval_platform.adapters.persistence.jobs.repository import PostgresJobRepository
from eval_platform.application.agent_registry import AgentRegistry
from eval_platform.application.identity import IdentityService
from eval_platform.application.job_lifecycle.cancellation import JobCancellation
from eval_platform.application.job_lifecycle.recovery import JobRecovery
from eval_platform.application.job_submission import JobSubmission
from eval_platform.application.owner_approval import OwnerApproval
from eval_platform.application.reporting import JobReporting
from eval_platform.application.task_catalog import TaskCatalog
from eval_platform.delivery.http.app import create_app
from eval_platform.delivery.http.config import HttpConfig
from eval_platform.delivery.job_presets import submission_policy
from eval_platform.domain.agent import AgentConfiguration


@contextmanager
def postgres_api(sandbox, *, initialize=True, report_store=None, recovery_clock=None):
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
        CatalogArtifacts(),
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
        approvals=OwnerApproval(repository),
        cancellations=JobCancellation(repository),
        recovery=(
            JobRecovery(repository, jobs)
            if recovery_clock is None
            else JobRecovery(repository, jobs, recovery_clock)
        ),
        reporting=(
            JobReporting(
                repository, report_store, lambda scope: scope == "internal_test"
            )
            if report_store is not None
            else None
        ),
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
