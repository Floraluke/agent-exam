"""PostgreSQL JobRepository Adapter."""

from datetime import datetime

from eval_platform.adapters.persistence.jobs import cancellations, job_transaction
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
from eval_platform.adapters.persistence.jobs.recovery.actions import recover
from eval_platform.adapters.persistence.jobs.reporting.listings import list_jobs
from eval_platform.adapters.persistence.jobs.retention import (
    expired_artifacts,
    mark_artifact_deleted,
)
from eval_platform.domain.jobs.cancellation import (
    CancellationRequest,
    CancellationResult,
)
from eval_platform.domain.jobs.decisions import OwnerDecision
from eval_platform.domain.jobs.execution import (
    ClaimedJob,
    JobLease,
    JobReport,
    RecoveryRequest,
    RunArtifact,
    RunCompletion,
    RunReport,
    TrialStart,
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

    def cancel(self, request: CancellationRequest) -> CancellationResult:
        with job_transaction(self.dsn) as connection:
            job_id, accepted_status = cancellations.cancel(connection, request)
            record = read_job(connection, job_id)
        if record is None:
            raise JobUnavailable
        return CancellationResult(record, accepted_status)

    def recover(self, request: RecoveryRequest) -> EvaluationJob:
        with job_transaction(self.dsn) as connection:
            return recover(connection, request)

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

    def start_run(self, lease: JobLease, run_id: str, now: datetime) -> TrialStart:
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

    def get_artifact_report(self, artifact_id: str) -> RunReport:
        with job_transaction(self.dsn) as connection:
            return reports.read_artifact_report(connection, artifact_id)

    def expired_artifacts(self, now: datetime, limit: int) -> tuple[RunArtifact, ...]:
        with job_transaction(self.dsn) as connection:
            return expired_artifacts(connection, now, limit)

    def mark_artifact_deleted(
        self,
        item: RunArtifact,
        actor_user_id: str,
        occurred_at: datetime,
        reason: str,
    ) -> None:
        with job_transaction(self.dsn) as connection:
            mark_artifact_deleted(connection, item, actor_user_id, occurred_at, reason)

    def list(
        self,
        created_by: str | None,
        filters: dict[str, str],
        cursor: str | None,
        limit: int,
    ) -> list[EvaluationJob]:
        with job_transaction(self.dsn) as connection:
            return list_jobs(connection, created_by, filters, cursor, limit)
