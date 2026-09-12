"""Explicitly gated synthetic HTTP server for browser wiring tests only."""

import os
from datetime import UTC, datetime, timedelta
from pathlib import Path
from threading import Thread
from time import sleep

from catalog.conftest import task_bundle
from catalog.memory import (
    FixedSource,
    MemoryAgents,
    MemoryTasks,
)
from catalog.memory import (
    MemoryArtifacts as CatalogArtifacts,
)
from jobs.execution.support.fakes import Backend, Evaluator
from jobs.execution.support.fakes import MemoryArtifacts as RunArtifacts
from jobs.execution.support.memory import ExecutableMemoryJobs
from membership.memory import MemoryMembershipRepository

from eval_platform.adapters.identity.passwords import Argon2Passwords
from eval_platform.application.agent_registry import AgentRegistry
from eval_platform.application.execute_job import JobExecutor
from eval_platform.application.identity import IdentityService
from eval_platform.application.job_submission import JobSubmission
from eval_platform.application.membership import MembershipService
from eval_platform.application.owner_approval import OwnerApproval
from eval_platform.application.reporting import JobReporting
from eval_platform.application.task_catalog import TaskCatalog
from eval_platform.delivery.http.app import create_app
from eval_platform.delivery.http.config import HttpConfig
from eval_platform.delivery.job_presets import submission_policy
from eval_platform.delivery.worker.main import WorkerShell
from eval_platform.domain.agent import AgentConfiguration

if os.environ.get("AGENTEXAM_IDENTITY_BROWSER_TEST") != "1":
    raise RuntimeError("Synthetic identity server requires the browser-test gate")


def browser_clock():
    clock_file = (
        Path(__file__).resolve().parents[4] / "runtime/tests/identity-browser-clock.txt"
    )
    try:
        offset = int(clock_file.read_text(encoding="ascii"))
    except FileNotFoundError:
        offset = 0
    if not 0 <= offset <= 28800:
        raise ValueError("Browser-test clock offset is outside the test boundary")
    return datetime.now(UTC) + timedelta(seconds=offset)


repository = MemoryMembershipRepository()
passwords = Argon2Passwords()
service = IdentityService(repository, passwords, browser_clock)
service.bootstrap_owner("owner", "synthetic browser password")
task_source = FixedSource(task_bundle())
task_source.bundles["example__repo-2"] = task_bundle("example__repo-2")
tasks = TaskCatalog(
    MemoryTasks(),
    CatalogArtifacts(),
    task_source,
    {
        "swe-gym-lite-mypy-15413": "example__repo-1",
        "swe-gym-lite-example-2": "example__repo-2",
    },
)
agents = AgentRegistry(
    MemoryAgents(),
    {
        "codex-0153-terra-medium": (
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
    },
)
job_repository = ExecutableMemoryJobs()
jobs = JobSubmission(
    tasks,
    agents,
    job_repository,
    submission_policy("internal_test"),
    browser_clock,
)
run_artifacts = RunArtifacts()
worker = WorkerShell(
    job_repository,
    JobExecutor(
        job_repository,
        run_artifacts,
        Backend(run_artifacts, b"diff --git a/a.py b/a.py\n--- a/a.py\n+++ b/a.py\n"),
        Evaluator(run_artifacts),
        tasks.source,
        browser_clock,
    ),
    browser_clock,
)
app = create_app(
    service,
    HttpConfig(public_origin="https://127.0.0.1:3100"),
    MembershipService(repository, passwords, browser_clock),
    tasks,
    agents,
    jobs,
    OwnerApproval(job_repository, browser_clock),
    JobReporting(
        job_repository,
        run_artifacts,
        lambda scope: scope == "internal_test",
    ),
)


def run_synthetic_worker() -> None:
    while True:
        if not worker.run_once("internal-browser-worker"):
            sleep(0.05)


Thread(target=run_synthetic_worker, daemon=True).start()
