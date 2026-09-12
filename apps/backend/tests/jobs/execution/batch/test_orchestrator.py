from datetime import UTC, datetime

from jobs.execution.support.fakes import (
    Backend,
    Evaluator,
    FailingEvaluator,
    MemoryArtifacts,
    artifact,
)
from jobs.execution.support.fixtures import queued_batch
from jobs.execution.support.memory import ExecutableMemoryJobs

from eval_platform.application.execute_job import JobExecutor
from eval_platform.delivery.worker.main import WorkerShell
from eval_platform.domain.jobs.models import run_order_key
from eval_platform.domain.result import ExecutionTrialResult, TerminationReason


class NoisyBackend(Backend):
    def execute(self, request, progress=None):
        assert progress is not None
        progress.trial_started(request.runs[1].run_id)
        results = super().execute(request, progress)
        for result in results:
            progress.trial_started(result.run_id)
            progress.trial_finished(result.run_id)
        return results


class IncompleteBackend:
    def __init__(self, store):
        self.store, self.requests = store, []

    def execute(self, request, progress=None):
        self.requests.append(request)
        assert progress is not None
        first, second = request.runs[:2]
        progress.trial_started(first.run_id)
        first_result = ExecutionTrialResult(
            first.run_id,
            "harbor-batch-one",
            "harbor-trial-one",
            TerminationReason.COMPLETED,
            artifact(
                self.store,
                first.run_id,
                "agent_patch",
                b"diff --git a/a b/a\n",
                "text/x-diff",
            ),
            None,
        )
        progress.trial_finished(first.run_id)
        progress.trial_started(second.run_id)
        second_result = ExecutionTrialResult(
            second.run_id,
            "harbor-batch-one",
            "",
            TerminationReason.TIMED_OUT,
            None,
            None,
        )
        return first_result, second_result


def test_one_batch_backend_call_preserves_results_after_middle_failure():
    now = datetime(2026, 9, 12, 14, 0, tzinfo=UTC)
    job, bundles = queued_batch(now)
    repository, artifacts = ExecutableMemoryJobs(job), MemoryArtifacts()
    backend = Backend(artifacts, b"diff --git a/a b/a\n")
    evaluator = FailingEvaluator(artifacts, {job.runs[1].run_id})
    source = type(
        "Source",
        (),
        {
            "load": lambda self, identity: {
                bundle.public.instance_id: bundle for bundle in bundles
            }[identity]
        },
    )()
    executor = JobExecutor(
        repository, artifacts, backend, evaluator, source, lambda: now
    )

    assert WorkerShell(repository, executor, lambda: now).run_once("batch-worker")

    stored = repository.get(job.job_id)
    assert len(backend.requests) == 1
    assert tuple(item.run_id for item in backend.requests[0].runs) == tuple(
        item.run_id for item in sorted(job.runs, key=run_order_key)
    )
    assert stored.status == "COMPLETED_WITH_ERRORS"
    assert stored.failure_code == "BATCH_PARTIAL_FAILURE"
    assert [run.status for run in stored.runs] == ["COMPLETED", "FAILED", "COMPLETED"]
    assert stored.runs[1].failure_code == "HARNESS_FAILED"
    assert repository.get_run_report(job.runs[0].run_id).deterministic_result
    assert repository.get_run_report(job.runs[2].run_id).deterministic_result
    assert repository.get_run_report(job.runs[1].run_id).deterministic_result is None


def _execute(job, bundles, backend, evaluator, artifacts, now):
    repository = ExecutableMemoryJobs(job)
    sources = {bundle.public.instance_id: bundle for bundle in bundles}
    source = type("Source", (), {"load": lambda self, identity: sources[identity]})()
    executor = JobExecutor(
        repository, artifacts, backend, evaluator, source, lambda: now
    )
    assert WorkerShell(repository, executor, lambda: now).run_once("batch-worker")
    return repository


def test_duplicate_signals_are_idempotent_and_disorder_fails_closed():
    now = datetime(2026, 9, 12, 14, 30, tzinfo=UTC)
    job, bundles = queued_batch(now)
    artifacts = MemoryArtifacts()
    repository = _execute(
        job,
        bundles,
        NoisyBackend(artifacts, b"diff --git a/a b/a\n"),
        Evaluator(artifacts),
        artifacts,
        now,
    )

    stored = repository.get(job.job_id)
    assert stored.status == "COMPLETED_WITH_ERRORS"
    assert stored.failure_code == "BACKEND_PROGRESS_INVALID"
    assert all(run.status == "COMPLETED" for run in stored.runs)
    assert all(
        [event.reason_code for event in run.state_events].count("TRIAL_STARTED") == 1
        and [event.reason_code for event in run.state_events].count("TRIAL_FINISHED")
        == 1
        for run in stored.runs
    )


def test_timeout_and_missing_trial_keep_prior_result_and_close_matrix():
    now = datetime(2026, 9, 12, 15, 0, tzinfo=UTC)
    job, bundles = queued_batch(now)
    artifacts = MemoryArtifacts()
    repository = _execute(
        job,
        bundles,
        IncompleteBackend(artifacts),
        Evaluator(artifacts),
        artifacts,
        now,
    )

    stored = repository.get(job.job_id)
    by_id = {run.run_id: run for run in stored.runs}
    ordered = sorted(job.runs, key=run_order_key)
    assert stored.status == "COMPLETED_WITH_ERRORS"
    assert stored.failure_code == "BACKEND_RESULT_IDENTITY_INVALID"
    assert by_id[ordered[0].run_id].status == "COMPLETED"
    assert by_id[ordered[1].run_id].failure_code == "EXECUTION_TIMED_OUT"
    assert by_id[ordered[2].run_id].failure_code == "BACKEND_RESULT_IDENTITY_INVALID"
    assert repository.get_run_report(ordered[0].run_id).deterministic_result
