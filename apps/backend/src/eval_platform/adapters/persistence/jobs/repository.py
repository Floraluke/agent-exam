"""PostgreSQL JobRepository Adapter."""

from datetime import datetime

from eval_platform.adapters.persistence.jobs import job_transaction
from eval_platform.adapters.persistence.jobs.decisions import decide
from eval_platform.adapters.persistence.jobs.execution import (
    batch,
    claims,
    finalization,
    reports,
    results,
)
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

    def start_run(self, lease: JobLease, run_id: str, now: datetime) -> JobLease:
        with job_transaction(self.dsn) as connection:
            return batch.start_run(connection, lease, run_id, now)

    def finish_run_execution(
        self, lease: JobLease, run_id: str, now: datetime
    ) -> JobLease:
        with job_transaction(self.dsn) as connection:
            return batch.finish_run_execution(connection, lease, run_id, now)

    def start_verifying(
        self, lease: JobLease, trial: ExecutionTrialResult, now: datetime
    ) -> JobLease:
        with job_transaction(self.dsn) as connection:
            return batch.start_verifying(connection, lease, trial, now)

    def complete(self, lease: JobLease, completion: RunCompletion) -> JobLease:
        with job_transaction(self.dsn) as connection:
            return results.complete(connection, lease, completion)

    def fail(
        self,
        lease: JobLease,
        run_id: str,
        code: str,
        summary: str,
        now: datetime,
        trial: ExecutionTrialResult | None = None,
    ) -> JobLease:
        with job_transaction(self.dsn) as connection:
            return results.fail(connection, lease, run_id, code, summary, now, trial)

    def start_finalizing(self, lease: JobLease, now: datetime) -> JobLease:
        with job_transaction(self.dsn) as connection:
            return finalization.start(connection, lease, now)

    def finish(
        self, lease: JobLease, now: datetime, failure_code: str | None = None
    ) -> None:
        with job_transaction(self.dsn) as connection:
            finalization.finish(connection, lease, now, failure_code)

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
