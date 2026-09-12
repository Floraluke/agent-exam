from dataclasses import asdict
from datetime import datetime
from typing import Any

import psycopg
from psycopg.types.json import Jsonb

from eval_platform.adapters.persistence.jobs.execution.common import current, event
from eval_platform.domain.jobs.execution import JobLease, RunArtifact, RunCompletion
from eval_platform.domain.jobs.models import JobUnavailable

Connection = psycopg.Connection[Any]


def complete(connection: Connection, lease: JobLease, completion: RunCompletion) -> str:
    current(connection, lease, completion.occurred_at, "EXECUTING", "VERIFYING")
    result = completion.result
    identifiers = {item.artifact_id for item in completion.artifacts}
    required = {result.report_artifact_id, result.test_output_artifact_id} - {None}
    if (
        result.run_id != lease.run_id
        or not completion.artifacts
        or not required <= identifiers
    ):
        raise JobUnavailable
    for item in completion.artifacts:
        _insert_artifact(connection, item, completion.occurred_at)
    connection.execute(
        "INSERT INTO deterministic_results "
        "(run_id,patch_exists,patch_successfully_applied,resolved,"
        "tests_status_summary,harness_revision,report_artifact_id,"
        "test_output_artifact_id,duration_ms,created_at) "
        "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
        (
            lease.run_id,
            result.patch_exists,
            result.patch_successfully_applied,
            result.resolved,
            Jsonb(result.tests_status_summary),
            result.harness_revision,
            result.report_artifact_id,
            result.test_output_artifact_id,
            result.duration_ms,
            result.created_at,
        ),
    )
    connection.execute(
        "UPDATE evaluation_runs SET status='COMPLETED',stage='completed',"
        "row_version=row_version+1,resolved_summary=%s,process_metrics=%s,"
        "warnings=%s,finished_at=%s WHERE run_id=%s",
        (
            result.resolved,
            Jsonb(asdict(completion.process_metrics)),
            Jsonb(list(completion.warnings)),
            completion.occurred_at,
            lease.run_id,
        ),
    )
    event(
        connection,
        "run",
        lease.run_id,
        "VERIFYING",
        "COMPLETED",
        "DETERMINISTIC_RESULT_STORED",
        lease.worker_id,
        completion.occurred_at,
    )
    connection.execute(
        "UPDATE evaluation_jobs SET status='FINALIZING',row_version=row_version+1,"
        "heartbeat_at=%s WHERE job_id=%s",
        (completion.occurred_at, lease.job_id),
    )
    event(
        connection,
        "job",
        lease.job_id,
        "EXECUTING",
        "FINALIZING",
        "FINALIZATION_STARTED",
        lease.worker_id,
        completion.occurred_at,
    )
    connection.execute(
        "UPDATE evaluation_jobs SET status='COMPLETED',row_version=row_version+1,"
        "finished_at=%s WHERE job_id=%s",
        (completion.occurred_at, lease.job_id),
    )
    event(
        connection,
        "job",
        lease.job_id,
        "FINALIZING",
        "COMPLETED",
        "JOB_COMPLETED",
        lease.worker_id,
        completion.occurred_at,
    )
    return str(lease.run_id)


def fail(
    connection: Connection,
    lease: JobLease,
    code: str,
    summary: str,
    now: datetime,
) -> str:
    row = current(connection, lease, now)
    if row["status"] not in {"PREPARING", "EXECUTING"} or row["run_status"] not in {
        "PREPARING",
        "RUNNING_AGENT",
        "VERIFYING",
    }:
        raise JobUnavailable
    if not code or len(code) > 128 or not summary or len(summary) > 500:
        raise JobUnavailable
    connection.execute(
        "UPDATE evaluation_runs SET status='FAILED',stage='failed',"
        "row_version=row_version+1,failure_code=%s,failure_summary=%s,"
        "finished_at=%s WHERE run_id=%s",
        (code, summary, now, lease.run_id),
    )
    event(
        connection,
        "run",
        lease.run_id,
        row["run_status"],
        "FAILED",
        code,
        lease.worker_id,
        now,
    )
    connection.execute(
        "UPDATE evaluation_jobs SET status='FAILED',row_version=row_version+1,"
        "failure_code=%s,failure_summary=%s,heartbeat_at=%s,finished_at=%s "
        "WHERE job_id=%s",
        (code, summary, now, now, lease.job_id),
    )
    event(
        connection,
        "job",
        lease.job_id,
        row["status"],
        "FAILED",
        code,
        lease.worker_id,
        now,
    )
    return str(lease.run_id)


def _insert_artifact(connection: Connection, item: RunArtifact, now: datetime) -> None:
    reference = item.reference
    parts = reference.object_key.split("/")
    if len(parts) < 4 or item.run_id != parts[1] or reference.deleted_at:
        raise JobUnavailable
    connection.execute(
        "INSERT INTO artifact_records (artifact_id,run_id,artifact_type,object_key,"
        "sha256,size_bytes,content_type,retention_class,redaction_status,truncated,"
        "created_at) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
        (
            item.artifact_id,
            item.run_id,
            reference.artifact_type,
            reference.object_key,
            reference.sha256,
            reference.size_bytes,
            reference.content_type,
            reference.retention_class,
            item.redaction_status,
            reference.truncated,
            reference.created_at or now,
        ),
    )
