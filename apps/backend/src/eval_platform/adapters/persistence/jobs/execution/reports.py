from typing import Any

import psycopg

from eval_platform.adapters.persistence.jobs.records import read_job
from eval_platform.domain.jobs.execution import (
    JobReport,
    ProcessMetrics,
    RunArtifact,
    RunReport,
    StoredDeterministicResult,
)
from eval_platform.domain.jobs.models import JobNotFound, JobUnavailable
from eval_platform.domain.result import ArtifactRef, ResourceSummary, UsageSummary

Connection = psycopg.Connection[Any]


def read_run_report(connection: Connection, run_id: str) -> RunReport:
    owner = connection.execute(
        "SELECT j.job_id,j.created_by FROM evaluation_runs r JOIN evaluation_jobs j "
        "ON j.job_id=r.job_id WHERE r.run_id=%s",
        (run_id,),
    ).fetchone()
    if owner is None:
        raise JobNotFound
    job = read_job(connection, str(owner["job_id"]))
    if job is None:
        raise JobUnavailable
    run = next((item for item in job.runs if item.run_id == run_id), None)
    if run is None:
        raise JobUnavailable
    result_row = connection.execute(
        "SELECT * FROM deterministic_results WHERE run_id=%s", (run_id,)
    ).fetchone()
    artifact_rows = connection.execute(
        "SELECT * FROM artifact_records WHERE run_id=%s "
        "ORDER BY artifact_type,artifact_id",
        (run_id,),
    ).fetchall()
    metrics_row = connection.execute(
        "SELECT process_metrics,warnings FROM evaluation_runs WHERE run_id=%s",
        (run_id,),
    ).fetchone()
    if metrics_row is None:
        raise JobUnavailable
    result = None if result_row is None else _result(result_row)
    if run.status == "COMPLETED" and result is None:
        raise JobUnavailable
    return RunReport(
        str(owner["created_by"]),
        job.result_scope,
        run,
        result,
        _metrics(metrics_row["process_metrics"]),
        tuple(_artifact(item, metrics_row["warnings"]) for item in artifact_rows),
    )


def read_job_report(connection: Connection, job_id: str) -> JobReport:
    job = read_job(connection, job_id)
    if job is None:
        raise JobNotFound
    reports = tuple(read_run_report(connection, run.run_id) for run in job.runs)
    return JobReport(job.created_by, job, reports)


def read_artifact_report(connection: Connection, artifact_id: str) -> RunReport:
    row = connection.execute(
        "SELECT run_id FROM artifact_records WHERE artifact_id=%s "
        "AND run_id IS NOT NULL",
        (artifact_id,),
    ).fetchone()
    if row is None:
        raise JobNotFound
    return read_run_report(connection, str(row["run_id"]))


def _result(row: dict[str, Any]) -> StoredDeterministicResult:
    output = row["test_output_artifact_id"]
    return StoredDeterministicResult(
        str(row["run_id"]),
        row["patch_exists"],
        row["patch_successfully_applied"],
        row["resolved"],
        row["tests_status_summary"],
        row["harness_revision"],
        str(row["report_artifact_id"]),
        None if output is None else str(output),
        row["duration_ms"],
        row["created_at"],
    )


def _metrics(value: object) -> ProcessMetrics:
    if value is None:
        return ProcessMetrics(UsageSummary(), ResourceSummary())
    if not isinstance(value, dict) or set(value) != {"usage", "resources"}:
        raise JobUnavailable
    try:
        usage, resources = value["usage"], value["resources"]
        return ProcessMetrics(UsageSummary(**usage), ResourceSummary(**resources))
    except (TypeError, ValueError):
        raise JobUnavailable from None


def _artifact(row: dict[str, Any], warnings: object) -> RunArtifact:
    items = warnings if isinstance(warnings, list) else []
    patch_warnings = (
        tuple(item for item in items if item == "PATCH_SIZE_WARNING")
        if row["artifact_type"] == "agent_patch"
        else ()
    )
    reference = ArtifactRef(
        row["object_key"],
        row["artifact_type"],
        row["size_bytes"],
        row["sha256"],
        row["content_type"],
        row["retention_class"],
        row["truncated"],
        created_at=row["created_at"],
        warnings=patch_warnings,
    )
    return RunArtifact(
        str(row["artifact_id"]),
        str(row["run_id"]),
        reference,
        row["redaction_status"],
    )
