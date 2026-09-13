from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from eval_platform.adapters.identity.passwords import Argon2Passwords
from eval_platform.application.identity import IdentityService
from eval_platform.application.reporting import LeaderboardReporting
from eval_platform.delivery.http.app import create_app
from eval_platform.delivery.http.config import HttpConfig
from eval_platform.domain.jobs.models import (
    LimitSnapshot,
    NetworkPolicySnapshot,
    ToolProfileSnapshot,
)
from eval_platform.domain.leaderboard import (
    AgentIdentity,
    AttemptMetrics,
    ComparisonScope,
    LeaderboardAttempt,
    LeaderboardTask,
    build_rows,
)
from tests.identity.memory import MemoryIdentityRepository
from tests.leaderboard.memory import MemoryLeaderboardRepository
from tests.leaderboard.postgres_support import isolated_postgres

ORIGIN = "https://testserver"
PASSWORD = "synthetic owner password"
WRITE_HEADERS = {"Origin": ORIGIN, "X-AgentExam-Request": "1"}


class Clock:
    def __init__(self) -> None:
        self.value = datetime(2026, 9, 13, tzinfo=UTC)

    def __call__(self) -> datetime:
        return self.value

    def advance(self, seconds: int) -> None:
        self.value += timedelta(seconds=seconds)


@dataclass
class LeaderboardAPI:
    client: TestClient
    repository: MemoryLeaderboardRepository

    def login(self):
        return self.client.post(
            "/api/v1/auth/login",
            json={"username": "owner", "password": PASSWORD},
            headers=WRITE_HEADERS,
        )


def fixed_rows():
    at = datetime(2026, 9, 13, tzinfo=UTC)
    scope = ComparisonScope(
        "swe-bench",
        "rev-1",
        "test",
        "org/repo",
        "closed_book",
        "network-deny-v1",
        NetworkPolicySnapshot("deny", "disabled", False),
        "codex-basic-v1",
        ToolProfileSnapshot("codex", "disabled", True),
        "default-single-host-v1",
        LimitSnapshot(1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0),
        "a" * 40,
        "b" * 40,
        "c" * 40,
        "job-run-v1",
    )
    agent = AgentIdentity(
        "11111111-1111-1111-1111-111111111111",
        "Synthetic Codex",
        "codex",
        "0.1.0",
        "openai_chatgpt",
        "gpt-5",
        "high",
        "d" * 64,
    )
    metrics = AttemptMetrics(10, None, 3, None, 2.5, 1.0, 256)
    attempt = LeaderboardAttempt(
        scope,
        agent,
        "22222222-2222-2222-2222-222222222222",
        "org__repo-1",
        "33333333-3333-3333-3333-333333333333",
        None,
        "44444444-4444-4444-4444-444444444444",
        at,
        at,
        "COMPLETED",
        "COMPLETED",
        None,
        True,
        at,
        metrics,
        "official",
    )
    tasks = (
        LeaderboardTask(attempt.task_id, attempt.instance_id, scope.repo),
        LeaderboardTask(
            "55555555-5555-5555-5555-555555555555", "org__repo-2", scope.repo
        ),
    )
    return build_rows(tasks, (attempt,), at)


@pytest.fixture
def leaderboard_api():
    identities = MemoryIdentityRepository()
    identity = IdentityService(identities, Argon2Passwords(), Clock())
    identity.bootstrap_owner("owner", PASSWORD)
    repository = MemoryLeaderboardRepository(fixed_rows())
    app = create_app(
        identity,
        HttpConfig(public_origin=ORIGIN),
        leaderboard=LeaderboardReporting(repository),
    )
    with TestClient(app, base_url=ORIGIN, raise_server_exceptions=False) as client:
        yield LeaderboardAPI(client, repository)


@pytest.fixture
def leaderboard_postgres():
    with isolated_postgres() as sandbox:
        yield sandbox
