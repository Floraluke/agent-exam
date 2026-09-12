from contextlib import contextmanager
from dataclasses import dataclass

import pytest
from catalog.conftest import task_bundle
from catalog.memory import FixedSource, MemoryAgents, MemoryArtifacts, MemoryTasks
from fastapi.testclient import TestClient
from identity.conftest import (
    ORIGIN,
    PASSWORD,
    WRITE_HEADERS,
    Clock,
    postgres_sandbox,  # noqa: F401
)
from membership.memory import MemoryMembershipRepository

from eval_platform.adapters.identity.passwords import Argon2Passwords
from eval_platform.application.agent_registry import AgentRegistry
from eval_platform.application.identity import IdentityService
from eval_platform.application.job_submission import JobSubmission
from eval_platform.application.membership import MembershipService
from eval_platform.application.owner_approval import OwnerApproval
from eval_platform.application.reporting import JobReporting
from eval_platform.application.task_catalog import TaskCatalog
from eval_platform.delivery.http.app import create_app
from eval_platform.delivery.http.config import HttpConfig
from eval_platform.delivery.job_presets import submission_policy
from eval_platform.domain.agent import AgentConfiguration
from jobs.execution.support.fakes import MemoryArtifacts as RunArtifacts
from jobs.execution.support.memory import ExecutableMemoryJobs


@dataclass
class JobAPI:
    client: TestClient
    clock: Clock
    repository: ExecutableMemoryJobs
    jobs: JobSubmission
    run_artifacts: RunArtifacts

    def login(self, username="owner", password=PASSWORD):
        return self.client.post(
            "/api/v1/auth/login",
            json={"username": username, "password": password},
            headers=WRITE_HEADERS,
        )

    def register_catalogs(self):
        task = self.register_task("verified-task")
        agent = self.register_agent("verified-codex")
        return task, agent

    def register_task(self, preset):
        return self.client.post(
            "/api/v1/tasks/register",
            json={"preset_id": preset},
            headers=WRITE_HEADERS,
        ).json()

    def register_agent(self, preset):
        return self.client.post(
            "/api/v1/agent-configurations",
            json={"preset_id": preset},
            headers=WRITE_HEADERS,
        ).json()


@contextmanager
def job_api(result_scope="internal_test", scope_visible=None):
    clock = Clock()
    identities = MemoryMembershipRepository()
    passwords = Argon2Passwords()
    identity = IdentityService(identities, passwords, clock)
    identity.bootstrap_owner("owner", PASSWORD)
    source = FixedSource(task_bundle())
    task_presets = {"verified-task": "example__repo-1"}
    for index in range(2, 22):
        instance_id = f"example__repo-{index}"
        source.bundles[instance_id] = task_bundle(instance_id)
        task_presets[f"verified-task-{index}"] = instance_id
    tasks = TaskCatalog(
        MemoryTasks(),
        MemoryArtifacts(),
        source,
        task_presets,
    )
    agent_presets = {}
    for index in range(1, 5):
        suffix = "" if index == 1 else f"-{index}"
        agent_presets[f"verified-codex{suffix}"] = (
            f"Synthetic Codex {index}",
            AgentConfiguration(
                f"test-preset-{index}",
                "codex",
                "test-version",
                "openai_chatgpt",
                f"test-model-{index}",
                "chatgpt_auth_json",
                f"private-test-reference-{index}",
                {"reasoning_effort": "medium"},
            ),
        )
    agents = AgentRegistry(
        MemoryAgents(),
        agent_presets,
    )
    membership = MembershipService(identities, passwords, clock)
    job_repository = ExecutableMemoryJobs()
    run_artifacts = RunArtifacts()
    jobs = JobSubmission(
        tasks,
        agents,
        job_repository,
        submission_policy(result_scope=result_scope),
        clock,
    )
    reporting = (
        JobReporting(job_repository, run_artifacts)
        if scope_visible is None
        else JobReporting(job_repository, run_artifacts, scope_visible)
    )
    app = create_app(
        identity,
        HttpConfig(public_origin=ORIGIN),
        membership,
        tasks,
        agents,
        jobs,
        OwnerApproval(job_repository, clock),
        reporting,
    )
    with TestClient(app, base_url=ORIGIN, raise_server_exceptions=False) as client:
        yield JobAPI(client, clock, job_repository, jobs, run_artifacts)


@pytest.fixture
def jobs_api():
    with job_api() as api:
        yield api


@pytest.fixture
def internal_reports_api():
    with job_api(scope_visible=lambda scope: scope == "internal_test") as api:
        yield api
