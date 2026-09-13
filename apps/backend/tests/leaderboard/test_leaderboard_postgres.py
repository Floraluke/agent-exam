from datetime import UTC, datetime, timedelta
from hashlib import sha256
from uuid import uuid4

import psycopg
import pytest

from eval_platform.adapters.identity.passwords import Argon2Passwords
from eval_platform.adapters.persistence.catalog import initialize_schema as init_catalog
from eval_platform.adapters.persistence.catalog.agents import PostgresAgentRepository
from eval_platform.adapters.persistence.catalog.tasks import PostgresTaskRepository
from eval_platform.adapters.persistence.identity import PostgresIdentityRepository
from eval_platform.adapters.persistence.jobs import initialize_schema as init_jobs
from eval_platform.adapters.persistence.jobs.reporting import (
    PostgresLeaderboardRepository,
)
from eval_platform.adapters.persistence.jobs.repository import PostgresJobRepository
from eval_platform.application.execute_job import JobExecutor
from eval_platform.application.identity import IdentityService
from eval_platform.application.owner_approval import OwnerApproval
from eval_platform.delivery.job_presets import submission_policy
from eval_platform.delivery.worker.main import WorkerShell
from eval_platform.domain.agent import AgentConfiguration
from eval_platform.domain.catalog import CatalogTask, RegisteredAgent
from eval_platform.domain.jobs.factory import build_job
from eval_platform.domain.jobs.models import AgentSnapshot, TaskSnapshot
from eval_platform.domain.leaderboard import LeaderboardQuery
from eval_platform.domain.result import ArtifactRef
from eval_platform.domain.task import EvaluationTask, EvaluatorTaskData, TaskBundle
from tests.jobs.execution.support.fakes import Backend, Evaluator, MemoryArtifacts

pytestmark = pytest.mark.integration


class FixedBundles:
    """Synthetic task source used only by the isolated PostgreSQL test."""

    def __init__(self, bundles: tuple[TaskBundle, ...]) -> None:
        self.bundles = {item.public.instance_id: item for item in bundles}

    def load(self, instance_id: str) -> TaskBundle:
        return self.bundles[instance_id]


def task(index: int, now: datetime) -> tuple[CatalogTask, TaskBundle]:
    task_id = str(uuid4())
    raw = f'{{"instance_id":"org__repo-{index}"}}'.encode()
    digest = sha256(raw).hexdigest()
    public = EvaluationTask(
        "swe-bench",
        "rev-1",
        "test",
        f"org__repo-{index}",
        "org/repo",
        str(index) * 40,
        f"Fix issue {index}",
        "registry.invalid/swebench@sha256:" + "a" * 64,
        digest,
    )
    source = ArtifactRef(
        f"tasks/{task_id}/source/{digest}",
        "task_source_snapshot",
        len(raw),
        digest,
        "application/json",
        "long_term",
        created_at=now,
    )
    record = CatalogTask(task_id, public, str(uuid4()), source, now)
    hidden = EvaluatorTaskData(public.instance_id, "rev-1", "", "", ("test",), ())
    return record, TaskBundle(public, hidden, raw)


def agent(now: datetime) -> RegisteredAgent:
    configuration = AgentConfiguration(
        str(uuid4()),
        "codex",
        "0.1.0",
        "openai_chatgpt",
        "gpt-5",
        "chatgpt_auth_json",
        "private-reference",
        {"reasoning_effort": "high"},
    )
    return RegisteredAgent(configuration, "Synthetic Codex", now)


def complete_job(
    repository: PostgresJobRepository,
    owner,
    task_record: CatalogTask,
    agent_record: RegisteredAgent,
    bundles: FixedBundles,
    scope: str,
    now: datetime,
):
    policy = submission_policy(scope)
    limits = policy.limits("default-single-host-v1")
    assert limits is not None
    record = build_job(
        owner,
        (TaskSnapshot.from_record(task_record),),
        (AgentSnapshot.from_record(agent_record),),
        "demo",
        "default-single-host-v1",
        limits.snapshot(),
        policy,
        now,
    )
    key = sha256((record.job_id + "key").encode()).hexdigest()
    stored = repository.create(record, key, sha256(record.job_id.encode()).hexdigest())
    OwnerApproval(repository, lambda: now + timedelta(seconds=1)).decide(
        owner, stored.job_id, "approve", None, record.job_id + "-approve"
    )
    artifacts = MemoryArtifacts()
    executor = JobExecutor(
        repository,
        artifacts,
        Backend(artifacts, b"diff --git a/a.py b/a.py\n+fixed\n"),
        Evaluator(artifacts),
        bundles,
        lambda: now + timedelta(seconds=2),
    )
    assert WorkerShell(
        repository, executor, lambda: now + timedelta(seconds=2)
    ).run_once("worker-" + scope)
    return repository.get(stored.job_id)


def test_postgres_uses_full_denominator_and_excludes_internal_rows_before_parsing(
    leaderboard_postgres,
) -> None:
    dsn = leaderboard_postgres.dsn
    identity = PostgresIdentityRepository(dsn)
    identity.initialize_schema()
    init_catalog(dsn)
    init_jobs(dsn)
    owner = IdentityService(identity, Argon2Passwords()).bootstrap_owner(
        "owner", "synthetic owner password"
    )
    now = datetime.now(UTC)
    first, first_bundle = task(1, now)
    second, second_bundle = task(2, now)
    tasks = PostgresTaskRepository(dsn)
    first, second = tasks.publish(first), tasks.publish(second)
    configuration = PostgresAgentRepository(dsn).register(agent(now))
    jobs = PostgresJobRepository(dsn)
    bundles = FixedBundles((first_bundle, second_bundle))
    official = complete_job(jobs, owner, first, configuration, bundles, "official", now)
    internal = complete_job(
        jobs,
        owner,
        first,
        configuration,
        bundles,
        "internal_test",
        now + timedelta(minutes=1),
    )
    with psycopg.connect(dsn) as connection:
        connection.execute(
            "UPDATE evaluation_runs SET agent_snapshot='{}'::jsonb WHERE job_id=%s",
            (internal.job_id,),
        )

    query = LeaderboardQuery("closed_book", "swe-bench", "rev-1", "test")
    page = PostgresLeaderboardRepository(dsn, lambda: now).page(query)

    assert len(page.items) == 1
    row = page.items[0]
    assert (row.total_tasks, row.resolved_count, row.unknown_count) == (2, 1, 1)
    assert [source.job_id for source in row.sources] == [official.job_id]
    assert row.metrics.n_input_tokens == 11
    assert (
        PostgresLeaderboardRepository(dsn)
        .page(
            LeaderboardQuery(
                "closed_book", "swe-bench", "rev-1", "test", tool_profile_id="missing"
            )
        )
        .items
        == ()
    )
