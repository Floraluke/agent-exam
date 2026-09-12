from datetime import UTC, datetime

from eval_platform.application.execute_job import JobExecutor
from eval_platform.delivery.worker.main import WorkerShell
from jobs.execution.fixtures import queued_job
from jobs.execution.memory import ExecutableMemoryJobs
from jobs.execution.support import Backend, Evaluator, MemoryArtifacts


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
