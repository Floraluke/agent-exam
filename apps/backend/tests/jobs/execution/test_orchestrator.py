from dataclasses import replace
from datetime import UTC, datetime

import pytest

from eval_platform.adapters.execution.harbor.config_mapper import build_job_plan
from eval_platform.application.execute_job import JobExecutor
from eval_platform.application.ports.execution import ExecutionJobRequest
from eval_platform.application.reporting import JobReporting
from eval_platform.delivery.worker.main import WorkerShell
from eval_platform.domain.catalog import ArtifactUnavailable
from eval_platform.domain.identity import AuthenticatedActor
from eval_platform.domain.jobs.execution import restore_agent, restore_public_task
from eval_platform.domain.result import ExecutionTrialResult, TerminationReason
from jobs.execution.support.fakes import Backend, Evaluator, MemoryArtifacts
from jobs.execution.support.fixtures import queued_job
from jobs.execution.support.memory import ExecutableMemoryJobs


def test_worker_executes_one_job_and_persists_layered_report():
    now = datetime(2026, 9, 12, 8, 0, tzinfo=UTC)
    job, bundle = queued_job(now)
    repository = ExecutableMemoryJobs(job)
    artifacts = MemoryArtifacts()
    patch = b"diff --git a/a.py b/a.py\n--- a/a.py\n+++ b/a.py\n"
    backend, evaluator = Backend(artifacts, patch), Evaluator(artifacts)
    source = type("Source", (), {"load": lambda self, instance_id: bundle})()
    executor = JobExecutor(
        repository, artifacts, backend, evaluator, source, lambda: now
    )

    assert WorkerShell(repository, executor, lambda: now).run_once("worker-one")

    stored = repository.get(job.job_id)
    report = repository.get_run_report(job.runs[0].run_id)
    assert stored.status == "COMPLETED"
    assert stored.runs[0].status == "COMPLETED"
    assert [event.to_status for event in stored.state_events][-3:] == [
        "EXECUTING",
        "FINALIZING",
        "COMPLETED",
    ]
    assert report.deterministic_result is not None
    assert report.deterministic_result.resolved is True
    assert report.deterministic_result.patch_exists is True
    assert report.process_metrics.usage.n_input_tokens == 11
    assert {item.reference.artifact_type for item in report.artifacts} == {
        "agent_patch",
        "harness_report",
        "harness_test_output",
    }
    assert len(backend.requests) == len(evaluator.requests) == 1
    assert backend.requests[0].job_id == job.job_id
    assert backend.requests[0].runs[0].run_id == job.runs[0].run_id
    assert evaluator.requests[0].model_patch == patch


def execute_patch(patch, evaluator_type=Evaluator):
    now = datetime(2026, 9, 12, 8, 0, tzinfo=UTC)
    job, bundle = queued_job(now)
    repository, artifacts = ExecutableMemoryJobs(job), MemoryArtifacts()
    backend, evaluator = Backend(artifacts, patch), evaluator_type(artifacts)
    source = type("Source", (), {"load": lambda self, instance_id: bundle})()
    worked = WorkerShell(
        repository,
        JobExecutor(repository, artifacts, backend, evaluator, source, lambda: now),
        lambda: now,
    ).run_once("worker-one")
    return worked, repository, evaluator, job


@pytest.mark.parametrize(
    ("patch", "exists", "warnings"),
    [
        (b"", False, ()),
        (
            b"diff --git a/a b/a\n" + b"+" * (256 * 1024),
            True,
            ("PATCH_SIZE_WARNING",),
        ),
    ],
    ids=("empty", "warning-threshold"),
)
def test_empty_and_warn_size_patches_are_preserved(patch, exists, warnings):
    worked, repository, _evaluator, job = execute_patch(patch)
    report = repository.get_run_report(job.runs[0].run_id)
    patch_artifact = next(
        item
        for item in report.artifacts
        if item.reference.artifact_type == "agent_patch"
    )
    assert worked and report.deterministic_result.patch_exists is exists
    if not exists:
        assert report.deterministic_result.patch_successfully_applied is False
        assert report.deterministic_result.resolved is False
    assert patch_artifact.reference.size_bytes == len(patch)
    assert patch_artifact.reference.warnings == warnings


def test_frozen_run_contract_builds_the_existing_harbor_job_plan(tmp_path):
    job, _bundle = queued_job(datetime(2026, 9, 12, 8, 0, tzinfo=UTC))
    run = job.runs[0]
    request = ExecutionJobRequest.single_run(
        job, run, restore_public_task(run), restore_agent(run)
    )

    plan = build_job_plan(
        request,
        jobs_dir=tmp_path / "jobs",
        task_dirs={run.task.instance_id: tmp_path / "task"},
    )

    assert request.artifact_contract_version == run.execution_contract_version
    assert plan.run_ids == (run.run_id,)


@pytest.mark.parametrize(
    ("patch", "code"),
    [
        (b"not a diff", "PATCH_FORMAT_INVALID"),
        (b"diff --git a/a b/a\n\x00", "BINARY_PATCH_NOT_ALLOWED"),
        (b"diff --git a/a b/a\n" + b"+" * (1024 * 1024), "PATCH_TOO_LARGE"),
    ],
    ids=("format", "binary", "hard-limit"),
)
def test_invalid_patch_is_infrastructure_failure_not_a_score(patch, code):
    worked, repository, evaluator, job = execute_patch(patch)
    report = repository.get_run_report(job.runs[0].run_id)
    assert worked and report.run.failure_code == code
    assert report.deterministic_result is None and evaluator.requests == []


class FailedBackend:
    def execute(self, request):
        run_id = request.runs[0].run_id
        return (
            ExecutionTrialResult(
                run_id,
                "harbor-job-one",
                "harbor-trial-one",
                TerminationReason.AGENT_FAILED,
                None,
                None,
            ),
        )


def test_agent_failure_is_distinct_from_a_normal_unresolved_result():
    now = datetime(2026, 9, 12, 8, 0, tzinfo=UTC)
    job, bundle = queued_job(now)
    repository, artifacts = ExecutableMemoryJobs(job), MemoryArtifacts()
    source = type("Source", (), {"load": lambda self, instance_id: bundle})()
    executor = JobExecutor(
        repository,
        artifacts,
        FailedBackend(),
        Evaluator(artifacts),
        source,
        lambda: now,
    )
    assert WorkerShell(repository, executor, lambda: now).run_once("worker-one")
    failed = repository.get_run_report(job.runs[0].run_id)
    assert failed.run.failure_code == "EXECUTION_AGENT_FAILED"
    assert failed.deterministic_result is None

    class UnresolvedEvaluator(Evaluator):
        def evaluate(self, request):
            return replace(super().evaluate(request), resolved=False)

    worked, repository, _evaluator, job = execute_patch(
        b"diff --git a/a b/a\n", UnresolvedEvaluator
    )
    unresolved = repository.get_run_report(job.runs[0].run_id)
    assert worked and unresolved.run.status == "COMPLETED"
    assert unresolved.deterministic_result is not None
    assert unresolved.deterministic_result.resolved is False


def test_reporting_fails_closed_when_durable_evidence_is_missing():
    now = datetime(2026, 9, 12, 8, 0, tzinfo=UTC)
    job, bundle = queued_job(now)
    repository, artifacts = ExecutableMemoryJobs(job), MemoryArtifacts()
    source = type("Source", (), {"load": lambda self, instance_id: bundle})()
    executor = JobExecutor(
        repository,
        artifacts,
        Backend(artifacts, b"diff --git a/a b/a\n"),
        Evaluator(artifacts),
        source,
        lambda: now,
    )
    assert WorkerShell(repository, executor, lambda: now).run_once("worker-one")
    report = repository.get_run_report(job.runs[0].run_id)
    artifacts.content.pop(report.artifacts[0].reference.object_key)

    reporting = JobReporting(repository, artifacts)
    actor = AuthenticatedActor(job.created_by, "creator", "collaborator")
    with pytest.raises(ArtifactUnavailable):
        reporting.run(actor, job.runs[0].run_id)
