"""Explicitly gated synthetic HTTP server for browser wiring tests only."""

import os
from datetime import UTC, datetime, timedelta
from pathlib import Path

from catalog.conftest import task_bundle
from catalog.memory import FixedSource, MemoryAgents, MemoryArtifacts, MemoryTasks
from jobs.memory import MemoryJobs
from membership.memory import MemoryMembershipRepository

from eval_platform.adapters.identity.passwords import Argon2Passwords
from eval_platform.application.agent_registry import AgentRegistry
from eval_platform.application.identity import IdentityService
from eval_platform.application.job_submission import JobSubmission
from eval_platform.application.membership import MembershipService
from eval_platform.application.task_catalog import TaskCatalog
from eval_platform.delivery.http.app import create_app
from eval_platform.delivery.http.config import HttpConfig
from eval_platform.delivery.job_presets import submission_policy
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
tasks = TaskCatalog(
    MemoryTasks(),
    MemoryArtifacts(),
    FixedSource(task_bundle()),
    {"swe-gym-lite-mypy-15413": "example__repo-1"},
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
jobs = JobSubmission(
    tasks,
    agents,
    MemoryJobs(),
    submission_policy("internal_test"),
    browser_clock,
)
app = create_app(
    service,
    HttpConfig(public_origin="https://127.0.0.1:3100"),
    MembershipService(repository, passwords, browser_clock),
    tasks,
    agents,
    jobs,
)
