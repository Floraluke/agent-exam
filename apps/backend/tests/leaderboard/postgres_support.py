import os
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from uuid import uuid4

import psycopg
import pytest
from psycopg import sql
from psycopg.conninfo import conninfo_to_dict, make_conninfo

from eval_platform.adapters.identity.passwords import Argon2Passwords
from eval_platform.adapters.persistence.catalog import initialize_schema as init_catalog
from eval_platform.adapters.persistence.catalog.agents import PostgresAgentRepository
from eval_platform.adapters.persistence.catalog.tasks import PostgresTaskRepository
from eval_platform.adapters.persistence.identity import PostgresIdentityRepository
from eval_platform.adapters.persistence.jobs import initialize_schema as init_jobs
from eval_platform.adapters.persistence.jobs.repository import PostgresJobRepository
from eval_platform.application.execute_job import JobExecutor
from eval_platform.application.identity import IdentityService
from eval_platform.application.owner_approval import OwnerApproval
from eval_platform.delivery.job_presets import submission_policy
from eval_platform.delivery.worker.main import WorkerShell
from eval_platform.domain.agent import AgentConfiguration
from eval_platform.domain.catalog import CatalogTask, RegisteredAgent
from eval_platform.domain.jobs.factory import build_job
from eval_platform.domain.jobs.models import AgentSnapshot, EvaluationJob, TaskSnapshot
from eval_platform.domain.result import ArtifactRef
from eval_platform.domain.task import EvaluationTask, EvaluatorTaskData, TaskBundle
from tests.jobs.execution.support.fakes import Backend, Evaluator, MemoryArtifacts


@dataclass(frozen=True, slots=True)
class LeaderboardPostgres:
    dsn: str


@dataclass(frozen=True, slots=True)
class SeededLeaderboard:
    now: datetime
    official: EvaluationJob
    internal: EvaluationJob


@contextmanager
def isolated_postgres():
    if os.environ.get("AGENTEXAM_RUN_LEADERBOARD_POSTGRES") != "1":
        pytest.skip("专属排行榜 PostgreSQL 测试未显式启用")
    dsn = os.environ.get("AGENTEXAM_TEST_DATABASE_URL", "")
    try:
        settings = conninfo_to_dict(dsn)
    except psycopg.Error:
        pytest.fail("无效的专属测试数据库配置", pytrace=False)
    if (
        settings.get("host") != "127.0.0.1"
        or settings.get("dbname") != "agentexam_identity_test"
        or settings.get("user") != "agentexam_identity_test"
        or settings.get("port") in {None, "5432"}
    ):
        pytest.fail("拒绝非专属回环测试数据库", pytrace=False)
    database = "leaderboard_" + uuid4().hex
    with psycopg.connect(dsn, autocommit=True, connect_timeout=3) as connection:
        connection.execute(
            sql.SQL("CREATE DATABASE {}").format(sql.Identifier(database))
        )
        try:
            yield LeaderboardPostgres(make_conninfo(dsn, dbname=database))
        finally:
            connection.execute(
                sql.SQL("DROP DATABASE {}").format(sql.Identifier(database))
            )


class FixedBundles:
    def __init__(self, bundles: tuple[TaskBundle, ...]) -> None:
        self.bundles = {item.public.instance_id: item for item in bundles}

    def load(self, instance_id: str) -> TaskBundle:
        return self.bundles[instance_id]


def seed_leaderboard(dsn: str) -> SeededLeaderboard:
    identity = PostgresIdentityRepository(dsn)
    identity.initialize_schema()
    init_catalog(dsn)
    init_jobs(dsn)
    owner = IdentityService(identity, Argon2Passwords()).bootstrap_owner(
        "owner", "synthetic owner password"
    )
    now = datetime.now(UTC)
    first, first_bundle = _task(1, now)
    second, second_bundle = _task(2, now)
    tasks = PostgresTaskRepository(dsn)
    first, second = tasks.publish(first), tasks.publish(second)
    configuration = PostgresAgentRepository(dsn).register(_agent(now))
    jobs = PostgresJobRepository(dsn)
    bundles = FixedBundles((first_bundle, second_bundle))
    official = _complete(jobs, owner, first, configuration, bundles, "official", now)
    internal = _complete(
        jobs,
        owner,
        first,
        configuration,
        bundles,
        "internal_test",
        now + timedelta(minutes=1),
    )
    return SeededLeaderboard(now, official, internal)


def _task(index: int, now: datetime) -> tuple[CatalogTask, TaskBundle]:
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


def _agent(now: datetime) -> RegisteredAgent:
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


def _complete(repository, owner, task, agent, bundles, scope, now) -> EvaluationJob:
    policy = submission_policy(scope)
    limits = policy.limits("default-single-host-v1")
    assert limits is not None
    record = build_job(
        owner,
        (TaskSnapshot.from_record(task),),
        (AgentSnapshot.from_record(agent),),
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
