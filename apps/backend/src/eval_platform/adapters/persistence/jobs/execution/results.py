from dataclasses import asdict
from datetime import datetime
from typing import Any

import psycopg
from psycopg.types.json import Jsonb

from eval_platform.adapters.persistence.jobs.execution.batch import (
    _next_run,
    _touch_job,
)
from eval_platform.adapters.persistence.jobs.execution.cancellation import (
    stop_unstarted,
)
from eval_platform.adapters.persistence.jobs.execution.common import current, event
from eval_platform.domain.jobs.execution import (
    JobLease,
    JobLeaseConflict,
    RunArtifact,
    RunCompletion,
)
from eval_platform.domain.jobs.models import JobUnavailable
from eval_platform.domain.result import ExecutionTrialResult

Connection = psycopg.Connection[Any]


def complete(
    connection: Connection, lease: JobLease, completion: RunCompletion
) -> JobLease:
    job = current(connection, lease, completion.occurred_at, "EXECUTING", "VERIFYING")
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
    run_version = lease.run_version + 1
    connection.execute(
        "UPDATE evaluation_runs SET status='COMPLETED',stage='completed',"
        "row_version=%s,resolved_summary=%s,process_metrics=%s,warnings=%s,"
        "finished_at=%s WHERE run_id=%s",
        (
            run_version,
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
    return _touch_job(
        connection,
        lease,
        job,
        lease.run_id,
        run_version,
        completion.occurred_at,
    )


def fail(
    connection: Connection,
    lease: JobLease,
    run_id: str,
    code: str,
    summary: str,
    now: datetime,
    trial: ExecutionTrialResult | None = None,
) -> JobLease:
    job = current(connection, lease, now, "EXECUTING")
    run = _next_run(connection, lease.job_id)
    if (
        run is None
        or str(run["run_id"]) != run_id
        or run["status"] not in {"PENDING", "PREPARING", "RUNNING_AGENT", "VERIFYING"}
        or not code
        or len(code) > 128
        or not summary
        or len(summary) > 500
        or (trial is not None and trial.run_id != run_id)
    ):
        raise JobLeaseConflict
    if job["status"] == "CANCEL_REQUESTED" and run["status"] in {
        "PENDING",
        "PREPARING",
    }:
        return stop_unstarted(connection, lease, now, job).lease
    backend_job_ref = trial.backend_job_ref if trial is not None else None
    backend_trial_ref = trial.backend_trial_ref if trial is not None else None
    run_version = run["row_version"] + 1
    connection.execute(
        "UPDATE evaluation_runs SET status='FAILED',stage='failed',row_version=%s,"
        "backend_job_ref=COALESCE(%s,backend_job_ref),"
        "backend_trial_ref=COALESCE(%s,backend_trial_ref),failure_code=%s,"
        "failure_summary=%s,started_at=COALESCE(started_at,%s),finished_at=%s "
        "WHERE run_id=%s",
        (
            run_version,
            backend_job_ref,
            backend_trial_ref,
            code,
            summary,
            now,
            now,
            run_id,
        ),
    )
    event(
        connection,
        "run",
        run_id,
        run["status"],
        "FAILED",
        code,
        lease.worker_id,
        now,
    )
    return _touch_job(connection, lease, job, run_id, run_version, now)


def _insert_artifact(connection: Connection, item: RunArtifact, now: datetime) -> None:
    reference = item.reference
    parts = reference.object_key.split("/")
    if len(parts) < 4 or item.run_id != parts[1] or reference.deleted_at:
        raise JobUnavailable
    connection.execute(
        "INSERT INTO artifact_records (artifact_id,run_id,artifact_type,object_key,"
        "original_filename,sha256,size_bytes,original_size_bytes,content_type,"
        "retention_class,expires_at,redaction_status,truncated,created_at) "
        "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
        (
            item.artifact_id,
            item.run_id,
            reference.artifact_type,
            reference.object_key,
            reference.original_filename or _filename(reference.artifact_type),
            reference.sha256,
            reference.size_bytes,
            reference.original_size_bytes or reference.size_bytes,
            reference.content_type,
            reference.retention_class,
            reference.expires_at,
            item.redaction_status,
            reference.truncated,
            reference.created_at or now,
        ),
    )


def _filename(kind: str) -> str:
    return {
        "agent_patch": "agent.patch",
        "harness_report": "harness-report.json",
        "harness_summary": "harness-summary.json",
        "harness_test_output": "test-output.txt",
        "public_test_summary": "test-summary.json",
        "public_trajectory": "trajectory.jsonl",
    }.get(kind, "artifact.bin")
