from dataclasses import asdict
from hashlib import sha256
from typing import Any

from psycopg import sql

from eval_platform.adapters.persistence.catalog import catalog_transaction
from eval_platform.domain.catalog import CatalogConflict, CatalogTask, TaskNotFound
from eval_platform.domain.result import ArtifactRef
from eval_platform.domain.task import EvaluationTask

_SELECT = """SELECT t.*, a.artifact_id, a.object_key, a.artifact_type, a.sha256,
    a.size_bytes, a.content_type, a.retention_class
    FROM evaluation_tasks t JOIN artifact_records a
    ON a.artifact_id = t.source_snapshot_ref AND a.task_id = t.task_id"""


def _record(row: dict[str, Any]) -> CatalogTask:
    task = EvaluationTask(
        **{
            key: row[key]
            for key in (
                "dataset_id",
                "dataset_revision",
                "split",
                "instance_id",
                "repo",
                "base_commit",
                "problem_statement",
                "environment_image",
                "raw_record_sha256",
            )
        }
    )
    reference = ArtifactRef(
        **{
            key: row[key]
            for key in (
                "object_key",
                "artifact_type",
                "size_bytes",
                "sha256",
                "content_type",
                "retention_class",
                "created_at",
            )
        },
    )
    return CatalogTask(
        str(row["task_id"]),
        task,
        str(row["artifact_id"]),
        reference,
        row["created_at"],
    )


class PostgresTaskRepository:
    def __init__(self, dsn: str) -> None:
        self.dsn = dsn

    def publish(self, record: CatalogTask) -> CatalogTask:
        values = {
            **asdict(record.task),
            "task_id": record.task_id,
            "source_snapshot_ref": record.artifact_id,
            "created_at": record.created_at,
            "problem_sha256": sha256(
                record.task.problem_statement.encode()
            ).hexdigest(),
        }
        with catalog_transaction(self.dsn) as connection:
            inserted = connection.execute(
                sql.SQL(
                    "INSERT INTO evaluation_tasks ({}) VALUES ({}) "
                    "ON CONFLICT (dataset_id,dataset_revision,split,instance_id) "
                    "DO NOTHING RETURNING task_id"
                ).format(
                    sql.SQL(",").join(map(sql.Identifier, values)),
                    sql.SQL(",").join(map(sql.Placeholder, values)),
                ),
                values,
            ).fetchone()
            if inserted is None:
                row = connection.execute(
                    _SELECT + " WHERE t.dataset_id=%s AND t.dataset_revision=%s "
                    "AND t.split=%s AND t.instance_id=%s",
                    record.identity,
                ).fetchone()
                if row is None:
                    raise CatalogConflict
                original = _record(row)
                if (
                    original.task != record.task
                    or original.source.sha256 != record.source.sha256
                    or original.source.size_bytes != record.source.size_bytes
                    or original.source.object_key != record.source.object_key
                ):
                    raise CatalogConflict
                return original
            source = record.source
            connection.execute(
                "INSERT INTO artifact_records "
                "(artifact_id,task_id,artifact_type,object_key,sha256,size_bytes,"
                "content_type,retention_class,created_at) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (
                    record.artifact_id,
                    record.task_id,
                    source.artifact_type,
                    source.object_key,
                    source.sha256,
                    source.size_bytes,
                    source.content_type,
                    source.retention_class,
                    record.created_at,
                ),
            )
        return record

    def get(self, task_id: str) -> CatalogTask:
        with catalog_transaction(self.dsn) as connection:
            row = connection.execute(
                _SELECT + " WHERE t.task_id=%s", (task_id,)
            ).fetchone()
        if row is None:
            raise TaskNotFound
        return _record(row)

    def list(
        self,
        filters: dict[str, str],
        cursor: str | None,
        limit: int,
    ) -> list[CatalogTask]:
        if filters.keys() - {"dataset_id", "split", "repo"} or not 1 <= limit <= 101:
            raise ValueError("Invalid repository query")
        conditions: list[sql.Composable] = [
            sql.SQL("t.{} = %s").format(sql.Identifier(key)) for key in filters
        ]
        values: list[Any] = list(filters.values())
        if cursor:
            conditions.append(sql.SQL("t.task_id > %s"))
            values.append(cursor)
        statement: sql.Composable = sql.SQL(_SELECT)
        if conditions:
            statement += sql.SQL(" WHERE ") + sql.SQL(" AND ").join(conditions)
        statement += sql.SQL(" ORDER BY t.task_id LIMIT %s")
        with catalog_transaction(self.dsn) as connection:
            rows = connection.execute(statement, [*values, limit]).fetchall()
        return [_record(row) for row in rows]
