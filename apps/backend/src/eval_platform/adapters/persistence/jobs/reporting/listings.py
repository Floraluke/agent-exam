"""Stable authorized Job listing query behind the repository adapter."""

from typing import Any

import psycopg

from eval_platform.adapters.persistence.jobs.records import read_job
from eval_platform.domain.jobs.models import EvaluationJob, JobUnavailable


def list_jobs(
    connection: psycopg.Connection[Any],
    created_by: str | None,
    filters: dict[str, str],
    cursor: str | None,
    limit: int,
) -> list[EvaluationJob]:
    if not 1 <= limit <= 101 or filters.keys() - {
        "status",
        "evaluation_track",
        "result_scope",
    }:
        raise ValueError("Invalid repository page size")
    conditions, values = [], []
    if created_by is not None:
        conditions.append("created_by=%s")
        values.append(created_by)
    for field, value in filters.items():
        conditions.append(field + "=%s")
        values.append(value)
    if cursor is not None:
        conditions.append("job_id>%s")
        values.append(cursor)
    statement = "SELECT job_id FROM evaluation_jobs"
    if conditions:
        statement += " WHERE " + " AND ".join(conditions)
    statement += " ORDER BY job_id LIMIT %s"
    rows = connection.execute(statement, [*values, limit]).fetchall()
    records = [read_job(connection, str(row["job_id"])) for row in rows]
    if any(item is None for item in records):
        raise JobUnavailable
    return [item for item in records if item is not None]
