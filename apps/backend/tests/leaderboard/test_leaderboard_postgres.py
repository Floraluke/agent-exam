from uuid import uuid4

import psycopg
import pytest
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from eval_platform.adapters.persistence.jobs.reporting import (
    PostgresLeaderboardRepository,
)
from eval_platform.domain.jobs.models import JobUnavailable
from eval_platform.domain.leaderboard import LeaderboardQuery
from tests.leaderboard.postgres_support import seed_leaderboard

pytestmark = pytest.mark.integration


def _update(dsn: str, statement: str, values: tuple[object, ...]) -> None:
    with psycopg.connect(dsn) as connection:
        connection.execute(statement, values)


def test_postgres_uses_full_denominator_and_rejects_corrupt_official_rows(
    leaderboard_postgres,
) -> None:
    dsn = leaderboard_postgres.dsn
    case = seed_leaderboard(dsn)
    with psycopg.connect(dsn) as connection:
        connection.execute(
            "UPDATE evaluation_runs SET agent_snapshot='{}'::jsonb WHERE job_id=%s",
            (case.internal.job_id,),
        )

    query = LeaderboardQuery("closed_book", "swe-bench", "rev-1", "test")
    repository = PostgresLeaderboardRepository(dsn, lambda: case.now)
    page = repository.page(query)

    assert len(page.items) == 1
    row = page.items[0]
    assert (row.total_tasks, row.resolved_count, row.unknown_count) == (2, 1, 1)
    assert [source.job_id for source in row.sources] == [case.official.job_id]
    assert row.metrics.n_input_tokens == 11
    assert (
        repository.page(
            LeaderboardQuery(
                "closed_book",
                "swe-bench",
                "rev-1",
                "test",
                tool_profile_id="missing",
            )
        ).items
        == ()
    )

    with psycopg.connect(dsn, row_factory=dict_row) as connection:
        run = connection.execute(
            "SELECT agent_snapshot,task_snapshot,backend_kind,backend_revision "
            "FROM evaluation_runs WHERE job_id=%s",
            (case.official.job_id,),
        ).fetchone()
        job = connection.execute(
            "SELECT network_policy_snapshot,limit_snapshot FROM evaluation_jobs "
            "WHERE job_id=%s",
            (case.official.job_id,),
        ).fetchone()
    assert run is not None and job is not None
    corruptions = (
        (
            "UPDATE evaluation_runs SET agent_snapshot=jsonb_set(agent_snapshot,"
            "'{agent_configuration_id}',to_jsonb(%s::text)) WHERE job_id=%s",
            (str(uuid4()), case.official.job_id),
            "UPDATE evaluation_runs SET agent_snapshot=%s WHERE job_id=%s",
            (Jsonb(run["agent_snapshot"]), case.official.job_id),
        ),
        (
            "UPDATE evaluation_runs SET agent_snapshot=jsonb_set(agent_snapshot,"
            "'{display_name}',to_jsonb(%s::text)) WHERE job_id=%s",
            ("Forged Agent", case.official.job_id),
            "UPDATE evaluation_runs SET agent_snapshot=%s WHERE job_id=%s",
            (Jsonb(run["agent_snapshot"]), case.official.job_id),
        ),
        (
            "UPDATE evaluation_runs SET task_snapshot=jsonb_set(task_snapshot,"
            "'{dataset_id}',to_jsonb(%s::text)) WHERE job_id=%s",
            ("moved-dataset", case.official.job_id),
            "UPDATE evaluation_runs SET task_snapshot=%s WHERE job_id=%s",
            (Jsonb(run["task_snapshot"]), case.official.job_id),
        ),
        (
            "UPDATE evaluation_jobs SET network_policy_snapshot=jsonb_set("
            "network_policy_snapshot,'{arbitrary_hosts}',to_jsonb(%s::text)) "
            "WHERE job_id=%s",
            ("false", case.official.job_id),
            "UPDATE evaluation_jobs SET network_policy_snapshot=%s WHERE job_id=%s",
            (Jsonb(job["network_policy_snapshot"]), case.official.job_id),
        ),
        (
            "UPDATE evaluation_jobs SET limit_snapshot=jsonb_set(limit_snapshot,"
            "'{agent_cpus}',to_jsonb(%s::integer)) WHERE job_id=%s",
            (-1, case.official.job_id),
            "UPDATE evaluation_jobs SET limit_snapshot=%s WHERE job_id=%s",
            (Jsonb(job["limit_snapshot"]), case.official.job_id),
        ),
        (
            "UPDATE evaluation_runs SET backend_kind='mock' WHERE job_id=%s",
            (case.official.job_id,),
            "UPDATE evaluation_runs SET backend_kind=%s WHERE job_id=%s",
            (run["backend_kind"], case.official.job_id),
        ),
        (
            "UPDATE evaluation_runs SET backend_revision=%s WHERE job_id=%s",
            ("f" * 40, case.official.job_id),
            "UPDATE evaluation_runs SET backend_revision=%s WHERE job_id=%s",
            (run["backend_revision"], case.official.job_id),
        ),
    )
    for corrupt, values, restore, restore_values in corruptions:
        _update(dsn, corrupt, values)
        with pytest.raises(JobUnavailable):
            repository.page(query)
        _update(dsn, restore, restore_values)
