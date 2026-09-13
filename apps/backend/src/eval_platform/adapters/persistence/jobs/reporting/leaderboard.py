"""PostgreSQL leaderboard read projection with production scope isolation."""

from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

import psycopg

from eval_platform.adapters.persistence.jobs import job_transaction
from eval_platform.adapters.persistence.jobs.reporting.rows import read_attempt
from eval_platform.domain.jobs.models import JobInputError, JobUnavailable
from eval_platform.domain.leaderboard import (
    LeaderboardPage,
    LeaderboardQuery,
    LeaderboardTask,
    build_rows,
    paginate,
)

Connection = psycopg.Connection[Any]
_ATTEMPTS = """
SELECT j.job_id,j.rerun_of_job_id,j.created_at AS job_created_at,
 j.finished_at AS job_finished_at,j.status AS job_status,j.result_scope,
 j.evaluation_track,j.network_policy_id,j.network_policy_snapshot,
 j.tool_profile_id,j.tool_profile_snapshot,j.limit_profile_id,j.limit_snapshot,
 j.harbor_revision,j.swe_gym_revision,j.swe_bench_fork_revision,
 r.run_id,r.task_id,r.agent_configuration_id,r.task_snapshot,r.agent_snapshot,
 r.execution_contract_version,r.backend_kind,r.backend_revision,
 r.status AS run_status,r.failure_code,r.started_at AS run_started_at,
 r.resolved_summary,r.process_metrics,r.finished_at AS run_finished_at,
 d.resolved,d.created_at AS result_created_at,d.patch_exists,
 d.patch_successfully_applied,d.harness_revision,
 t.task_id AS catalog_task_id,t.instance_id AS catalog_instance_id,
 t.dataset_id AS catalog_dataset_id,t.dataset_revision AS catalog_dataset_revision,
 t.split AS catalog_split,t.repo AS catalog_repo,t.base_commit AS catalog_base_commit,
 t.problem_statement AS catalog_problem_statement,
 t.environment_image AS catalog_environment_image,
 t.raw_record_sha256 AS catalog_raw_record_sha256,
 t.problem_sha256 AS catalog_problem_sha256,
 s.artifact_id AS catalog_artifact_id,s.object_key AS catalog_source_object_key,
 s.sha256 AS catalog_source_sha256,
 c.agent_configuration_id AS catalog_agent_configuration_id,
 c.display_name AS catalog_agent_display_name,c.agent_type AS catalog_agent_type,
 c.agent_version AS catalog_agent_version,c.model_provider AS catalog_model_provider,
 c.model AS catalog_model,c.authentication_type AS catalog_authentication_type,
 c.credential_profile_id AS catalog_credential_profile_id,
 c.public_options->>'reasoning_effort' AS catalog_reasoning_effort,
 c.configuration_fingerprint AS catalog_configuration_fingerprint
FROM evaluation_jobs j JOIN evaluation_runs r ON r.job_id=j.job_id
JOIN evaluation_tasks t ON t.task_id=r.task_id
JOIN artifact_records s ON s.artifact_id=t.source_snapshot_ref AND s.task_id=t.task_id
JOIN agent_configurations c ON c.agent_configuration_id=r.agent_configuration_id
LEFT JOIN deterministic_results d ON d.run_id=r.run_id
WHERE j.result_scope='official'
  AND j.status IN ('COMPLETED','COMPLETED_WITH_ERRORS','FAILED','CANCELED')
  AND j.evaluation_track=%s
  AND t.dataset_id=%s
  AND t.dataset_revision=%s
  AND t.split=%s
"""


class PostgresLeaderboardRepository:
    def __init__(
        self,
        dsn: str,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self.dsn = dsn
        self.clock = clock

    def page(self, query: LeaderboardQuery) -> LeaderboardPage:
        if (
            query.evaluation_track != "closed_book"
            or not query.dataset_id.strip()
            or not query.dataset_revision.strip()
            or not query.split.strip()
        ):
            raise JobInputError("INVALID_REQUEST")
        with job_transaction(self.dsn) as connection:
            tasks = self._tasks(connection, query)
            attempt_rows = connection.execute(*_attempt_statement(query)).fetchall()
        try:
            attempts = tuple(read_attempt(row) for row in attempt_rows)
            rows = build_rows(tasks, attempts, self.clock())
        except (AttributeError, KeyError, OverflowError, TypeError, ValueError):
            raise JobUnavailable from None
        return paginate(rows, query.cursor, query.limit)

    @staticmethod
    def _tasks(
        connection: Connection, query: LeaderboardQuery
    ) -> tuple[LeaderboardTask, ...]:
        statement = (
            "SELECT task_id,instance_id,repo FROM evaluation_tasks "
            "WHERE dataset_id=%s AND dataset_revision=%s AND split=%s"
        )
        values: list[object] = [
            query.dataset_id,
            query.dataset_revision,
            query.split,
        ]
        if query.repo is not None:
            statement += " AND repo=%s"
            values.append(query.repo)
        statement += " ORDER BY task_id"
        rows = connection.execute(statement, values).fetchall()
        return tuple(
            LeaderboardTask(str(row["task_id"]), row["instance_id"], row["repo"])
            for row in rows
        )


def _attempt_statement(query: LeaderboardQuery) -> tuple[str, list[object]]:
    statement = _ATTEMPTS
    values: list[object] = [
        query.evaluation_track,
        query.dataset_id,
        query.dataset_revision,
        query.split,
    ]
    if query.repo is not None:
        statement += " AND t.repo=%s"
        values.append(query.repo)
    if query.tool_profile_id is not None:
        statement += " AND j.tool_profile_id=%s"
        values.append(query.tool_profile_id)
    statement += " ORDER BY j.created_at,j.job_id,r.run_id"
    return statement, values
