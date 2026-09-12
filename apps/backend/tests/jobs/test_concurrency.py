from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

from eval_platform.domain.jobs.models import JobConfigurationDisabled
from jobs.test_postgres import postgres_api


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
