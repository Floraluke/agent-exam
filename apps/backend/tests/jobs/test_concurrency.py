from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import psycopg
import pytest
from identity.conftest import WRITE_HEADERS

from eval_platform.application.owner_approval import OwnerApproval
from eval_platform.domain.jobs.decisions import JobStateConflict
from eval_platform.domain.jobs.models import JobConfigurationDisabled
from jobs.test_postgres import login, postgres_api


def test_concurrent_same_key_creates_exactly_one_complete_job(postgres_sandbox):
    with postgres_api(postgres_sandbox) as (client, jobs, repository, owner):
        task = jobs.tasks.register(owner, "verified-task")
        agent = jobs.agents.register(owner, "verified-codex")
        barrier = Barrier(2, timeout=10)

        def create(_):
            barrier.wait()
            return jobs.submit(
                owner,
                [task.task_id],
                [agent.configuration.configuration_id],
                "closed_book",
                "demo",
                "default-single-host-v1",
                "concurrent-replay-0001",
            )

        with ThreadPoolExecutor(max_workers=2) as pool:
            first, second = pool.map(create, range(2))
        assert first == second
        assert repository.list(None, {}, None, 20) == [first]
        assert first.trial_count == 1
        assert len(first.state_events) == len(first.runs[0].state_events) == 1


def test_submit_disable_race_is_consistent(postgres_sandbox):
    with postgres_api(postgres_sandbox) as (client, jobs, repository, owner):
        task = jobs.tasks.register(owner, "verified-task")
        agent = jobs.agents.register(owner, "verified-codex")
        barrier = Barrier(2, timeout=10)

        def create():
            barrier.wait()
            try:
                return jobs.submit(
                    owner,
                    [task.task_id],
                    [agent.configuration.configuration_id],
                    "closed_book",
                    "demo",
                    "default-single-host-v1",
                    "disable-race-0001",
                )
            except JobConfigurationDisabled:
                return None

        def disable():
            barrier.wait()
            jobs.agents.disable(owner, agent.configuration.configuration_id)

        with ThreadPoolExecutor(max_workers=2) as pool:
            created = pool.submit(create)
            disabled = pool.submit(disable)
            record = created.result()
            disabled.result()
        records = repository.list(None, {}, None, 20)
        assert records == ([] if record is None else [record])
        assert all(item.trial_count == 1 for item in records)


def test_concurrent_approve_and_reject_choose_exactly_one_decision(
    postgres_sandbox,
):
    with postgres_api(postgres_sandbox) as (client, jobs, repository, owner):
        task = jobs.tasks.register(owner, "verified-task")
        agent = jobs.agents.register(owner, "verified-codex")
        created = jobs.submit(
            owner,
            [task.task_id],
            [agent.configuration.configuration_id],
            "closed_book",
            "demo",
            "default-single-host-v1",
            "decision-race-source-0001",
        )
        approvals = OwnerApproval(repository)
        barrier = Barrier(2, timeout=10)

        def decide(kind):
            barrier.wait()
            try:
                return approvals.decide(
                    owner,
                    created.job_id,
                    kind,
                    kind,
                    f"decision-race-{kind}-0001",
                )
            except JobStateConflict:
                return None

        with ThreadPoolExecutor(max_workers=2) as pool:
            approved = pool.submit(decide, "approve")
            rejected = pool.submit(decide, "reject")
            outcomes = (approved.result(), rejected.result())

        assert sum(item is not None for item in outcomes) == 1
        stored = repository.get(created.job_id)
        assert stored.status in {"QUEUED", "REJECTED"}
        assert len(stored.state_events) == 2
        expected_run = "PENDING" if stored.status == "QUEUED" else "CANCELED"
        assert {run.status for run in stored.runs} == {expected_run}


def test_failed_decision_event_rolls_back_status_and_audit(postgres_sandbox):
    with postgres_api(postgres_sandbox) as (client, jobs, repository, owner):
        login(client)
        task = jobs.tasks.register(owner, "verified-task")
        agent = jobs.agents.register(owner, "verified-codex")
        created = jobs.submit(
            owner,
            [task.task_id],
            [agent.configuration.configuration_id],
            "closed_book",
            "demo",
            "default-single-host-v1",
            "postgres-decision-rollback-source-0001",
        )
        with psycopg.connect(postgres_sandbox.dsn) as connection:
            connection.execute(
                "CREATE FUNCTION fail_decision_event() RETURNS trigger LANGUAGE "
                "plpgsql AS $$ BEGIN IF NEW.sequence=2 THEN RAISE EXCEPTION "
                "'synthetic'; END IF; RETURN NEW; END $$"
            )
            connection.execute(
                "CREATE TRIGGER fail_decision_event BEFORE INSERT ON job_state_events "
                "FOR EACH ROW EXECUTE FUNCTION fail_decision_event()"
            )
        response = client.post(
            f"/api/v1/jobs/{created.job_id}/reject",
            json={},
            headers={**WRITE_HEADERS, "Idempotency-Key": "rollback-decision-0001"},
        )
        stored = repository.get(created.job_id)
        assert response.status_code == 503
        assert stored.status == "AWAITING_OWNER_APPROVAL"
        assert len(stored.state_events) == 1
        assert {run.status for run in stored.runs} == {"PENDING"}


@pytest.mark.parametrize(
    ("kind", "status", "run_status", "reason"),
    (
        ("approve", "QUEUED", "PENDING", "  stored decision  "),
        ("reject", "REJECTED", "CANCELED", None),
    ),
)
def test_postgres_decision_restores_and_replays_complete_job(
    postgres_sandbox, kind, status, run_status, reason
):
    with postgres_api(postgres_sandbox) as (client, jobs, repository, owner):
        assert login(client).status_code == 200
        tasks = [
            jobs.tasks.register(owner, preset).task_id
            for preset in ("verified-task", "verified-task-2")
        ]
        agent = jobs.agents.register(owner, "verified-codex")
        created = jobs.submit(
            owner,
            tasks,
            [agent.configuration.configuration_id],
            "closed_book",
            "demo",
            "default-single-host-v1",
            f"postgres-{kind}-source-0001",
        )
        headers = {**WRITE_HEADERS, "Idempotency-Key": f"postgres-{kind}-0001"}
        body = {} if reason is None else {"reason": reason}
        response = client.post(
            f"/api/v1/jobs/{created.job_id}/{kind}", json=body, headers=headers
        )
        replay = client.post(
            f"/api/v1/jobs/{created.job_id}/{kind}", json=body, headers=headers
        )
        stored = repository.get(created.job_id)
        assert response.status_code == 200 and replay.json() == response.json()
        assert stored.status == status and stored.owner_decided_by == owner.user_id
        assert stored.owner_decision_reason == (reason.strip() if reason else None)
        assert len(stored.state_events) == 2
        assert {run.status for run in stored.runs} == {run_status}
        assert all(
            len(run.state_events) == (2 if kind == "reject" else 1)
            for run in stored.runs
        )
