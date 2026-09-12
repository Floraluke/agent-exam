"""PostgreSQL JobRepository Adapter."""

from datetime import datetime

from eval_platform.adapters.persistence.jobs import job_transaction
from eval_platform.adapters.persistence.jobs.decisions import decide
from eval_platform.adapters.persistence.jobs.execution import claims, reports, results
from eval_platform.adapters.persistence.jobs.publication import publish
from eval_platform.adapters.persistence.jobs.records import read_job
from eval_platform.domain.jobs.decisions import OwnerDecision
from eval_platform.domain.jobs.execution import (
    ClaimedJob,
    JobLease,
    JobReport,
    RunCompletion,
    RunReport,
)
from eval_platform.domain.jobs.models import (
    EvaluationJob,
    JobIdempotencyConflict,
    JobNotFound,
    JobUnavailable,
)
from eval_platform.domain.result import ExecutionTrialResult


class PostgresJobRepository:
    def __init__(self, dsn: str) -> None:
        self.dsn = dsn

    def resolve_idempotency(
        self, created_by: str, key_hash: str, request_sha256: str
    ) -> EvaluationJob | None:
        with job_transaction(self.dsn) as connection:
            row = connection.execute(
                "SELECT job_id,request_sha256 FROM evaluation_jobs "
                "WHERE created_by=%s AND idempotency_key_hash=%s",
                (created_by, key_hash),
            ).fetchone()
            if row is None:
                return None
            if row["request_sha256"] != request_sha256:
                raise JobIdempotencyConflict
            record = read_job(connection, str(row["job_id"]))
        if record is None:
            raise JobUnavailable
        return record

    def create(
        self, record: EvaluationJob, key_hash: str, request_sha256: str
    ) -> EvaluationJob:
        with job_transaction(self.dsn) as connection:
            job_id = publish(connection, record, key_hash, request_sha256)
            stored = read_job(connection, job_id)
        if stored is None:
            raise JobUnavailable
        return stored

    def get(self, job_id: str) -> EvaluationJob:
        with job_transaction(self.dsn) as connection:
            record = read_job(connection, job_id)
        if record is None:
            raise JobNotFound
        return record

    def decide(self, decision: OwnerDecision) -> EvaluationJob:
        with job_transaction(self.dsn) as connection:
            job_id = decide(connection, decision)
            record = read_job(connection, job_id)
        if record is None:
            raise JobUnavailable
        return record

    def claim(self, worker_id: str, now: datetime) -> ClaimedJob | None:
        with job_transaction(self.dsn) as connection:
            lease = claims.claim(connection, worker_id, now)
            if lease is None:
                return None
            record = read_job(connection, lease.job_id)
        if record is None:
            raise JobUnavailable
        return ClaimedJob(record, lease)

    def start_execution(self, lease: JobLease, now: datetime) -> JobLease:
        with job_transaction(self.dsn) as connection:
            return claims.start_execution(connection, lease, now)

    def start_verifying(
        self, lease: JobLease, trial: ExecutionTrialResult, now: datetime
    ) -> JobLease:
        with job_transaction(self.dsn) as connection:
            return claims.start_verifying(connection, lease, trial, now)

    def complete(self, lease: JobLease, completion: RunCompletion) -> RunReport:
        with job_transaction(self.dsn) as connection:
            run_id = results.complete(connection, lease, completion)
            return reports.read_run_report(connection, run_id)

    def fail(
        self, lease: JobLease, code: str, summary: str, now: datetime
    ) -> RunReport:
        with job_transaction(self.dsn) as connection:
            run_id = results.fail(connection, lease, code, summary, now)
            return reports.read_run_report(connection, run_id)

    def get_run_report(self, run_id: str) -> RunReport:
        with job_transaction(self.dsn) as connection:
            return reports.read_run_report(connection, run_id)

    def get_job_report(self, job_id: str) -> JobReport:
        with job_transaction(self.dsn) as connection:
            return reports.read_job_report(connection, job_id)

    def list(
        self,
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
        with job_transaction(self.dsn) as connection:
            rows = connection.execute(statement, [*values, limit]).fetchall()
            records = [read_job(connection, str(row["job_id"])) for row in rows]
        if any(item is None for item in records):
            raise JobUnavailable
        return [item for item in records if item is not None]
