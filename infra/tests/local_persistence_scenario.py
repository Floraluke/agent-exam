from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import psycopg
from psycopg import conninfo, sql

from catalog.conftest import task_bundle
from catalog.memory import FixedSource
from jobs.execution.support.fakes import Backend, Evaluator

from eval_platform.adapters.artifacts.config import MinioConfig, create_client
from eval_platform.adapters.artifacts.minio import MinioArtifactStore
from eval_platform.adapters.identity.passwords import Argon2Passwords
from eval_platform.adapters.persistence.bootstrap import initialize_empty_database
from eval_platform.adapters.persistence.catalog.agents import PostgresAgentRepository
from eval_platform.adapters.persistence.catalog.tasks import PostgresTaskRepository
from eval_platform.adapters.persistence.identity import PostgresIdentityRepository
from eval_platform.adapters.persistence.jobs.repository import PostgresJobRepository
from eval_platform.application.agent_registry import AgentRegistry
from eval_platform.application.execute_job import JobExecutor
from eval_platform.application.identity import IdentityService
from eval_platform.application.job_submission import JobSubmission
from eval_platform.application.owner_approval import OwnerApproval
from eval_platform.application.task_catalog import TaskCatalog
from eval_platform.delivery.job_presets import submission_policy
from eval_platform.delivery.worker.main import WorkerShell
from eval_platform.domain.agent import AgentConfiguration

PRIVATE_ROOT = Path(r"D:\AgentExamData\private")


def _database_dsn(database: str) -> str:
    password = (PRIVATE_ROOT / "postgres-password").read_text(encoding="utf-8")
    connection = (
        "host=127.0.0.1 port=55432 "
        f"dbname={database} user=agentexam_admin connect_timeout=3"
    )
    return conninfo.make_conninfo(connection, password=password)


def _artifact_store() -> MinioArtifactStore:
    secret = (PRIVATE_ROOT / "minio-app-password").read_text(encoding="utf-8")
    config = MinioConfig(
        "http://127.0.0.1:59000",
        "agentexam-private",
        "agentexam-app",
        secret,
    )
    return MinioArtifactStore(create_client(config), config.bucket)


class RecordingStore:
    def __init__(self, delegate):
        self.delegate = delegate
        self.bodies = {}

    def put_immutable(self, reference, content):
        self.delegate.put_immutable(reference, content)
        self.bodies[reference.object_key] = (reference, bytes(content))

    def read_verified(self, reference):
        return self.delegate.read_verified(reference)

    def read_bounded_verified(self, reference, maximum):
        return self.delegate.read_bounded_verified(reference, maximum)


@dataclass
class Scenario:
    dsn: str
    account: object
    task: object
    agent: object
    job: object
    report: object
    bodies: dict

    def verify(self) -> None:
        identities = PostgresIdentityRepository(self.dsn)
        assert identities.find_account(self.account.actor.username) == self.account
        assert PostgresTaskRepository(self.dsn).get(self.task.task_id) == self.task
        configuration_id = self.agent.configuration.configuration_id
        assert PostgresAgentRepository(self.dsn).get(configuration_id) == self.agent
        jobs = PostgresJobRepository(self.dsn)
        assert jobs.get(self.job.job_id) == self.job
        assert jobs.get_run_report(self.job.runs[0].run_id) == self.report
        store = _artifact_store()
        for reference, content in self.bodies.values():
            assert store.read_verified(reference) == content


def _create_database(database: str) -> str:
    with psycopg.connect(_database_dsn("postgres"), autocommit=True) as connection:
        connection.execute(
            sql.SQL("CREATE DATABASE {}").format(sql.Identifier(database))
        )
    dsn = _database_dsn(database)
    try:
        initialize_empty_database(dsn)
    except Exception:
        _drop_database(database)
        raise
    return dsn


def _drop_database(database: str) -> None:
    with psycopg.connect(_database_dsn("postgres"), autocommit=True) as connection:
        connection.execute(sql.SQL("DROP DATABASE {}").format(sql.Identifier(database)))


def _populate(database: str, dsn: str, store: RecordingStore) -> Scenario:
    suffix = database.removeprefix("ae_persist_")
    identity = PostgresIdentityRepository(dsn)
    actor = IdentityService(identity, Argon2Passwords()).bootstrap_owner(
        "persist-" + suffix, "synthetic persistence password"
    )
    account = identity.find_account(actor.username)
    assert account is not None
    bundle = task_bundle("agentexam__persist-" + suffix, "agentexam/persistence")
    source = FixedSource(bundle)
    tasks = TaskCatalog(
        PostgresTaskRepository(dsn),
        store,
        source,
        {"persistence": bundle.public.instance_id},
    )
    task = tasks.register(actor, "persistence")
    agents = AgentRegistry(
        PostgresAgentRepository(dsn),
        {
            "persistence": (
                "Synthetic Persistence Agent",
                AgentConfiguration(
                    "preset",
                    "codex",
                    "synthetic",
                    "openai_chatgpt",
                    "synthetic-model",
                    "chatgpt_auth_json",
                    "synthetic-profile",
                    {"reasoning_effort": "low"},
                ),
            )
        },
    )
    agent = agents.register(actor, "persistence")
    repository = PostgresJobRepository(dsn)
    jobs = JobSubmission(tasks, agents, repository, submission_policy("internal_test"))
    job = jobs.submit(
        actor,
        [task.task_id],
        [agent.configuration.configuration_id],
        "closed_book",
        "demo",
        "default-single-host-v1",
        "persist-" + suffix,
    )
    OwnerApproval(repository).decide(
        actor, job.job_id, "approve", None, "approve-" + suffix
    )
    now = datetime.now(UTC)
    executor = JobExecutor(
        repository,
        store,
        Backend(store, b"diff --git a/a.py b/a.py\n+synthetic\n"),
        Evaluator(store),
        source,
        lambda: now,
        store,
    )
    assert WorkerShell(repository, executor, lambda: now).run_once("persist-" + suffix)
    completed = repository.get(job.job_id)
    report = repository.get_run_report(completed.runs[0].run_id)
    assert completed.status == "COMPLETED" and report.deterministic_result is not None
    return Scenario(dsn, account, task, agent, completed, report, store.bodies)


@contextmanager
def local_scenario():
    database = "ae_persist_" + uuid4().hex[:12]
    recorder = RecordingStore(_artifact_store())
    dsn = _create_database(database)
    try:
        yield _populate(database, dsn, recorder)
    finally:
        try:
            client = _artifact_store().client
            for object_key in recorder.bodies:
                client.delete_object(Bucket="agentexam-private", Key=object_key)
        finally:
            _drop_database(database)
