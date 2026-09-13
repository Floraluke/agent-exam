from datetime import UTC, datetime

from jobs.execution.support.fakes import Evaluator, MemoryArtifacts, artifact
from jobs.execution.support.fixtures import queued_batch
from jobs.execution.support.memory import ExecutableMemoryJobs

from eval_platform.application.execute_job import JobExecutor
from eval_platform.application.job_lifecycle.cancellation import JobCancellation
from eval_platform.delivery.worker.main import WorkerShell
from eval_platform.domain.identity import AuthenticatedActor
from eval_platform.domain.jobs.models import run_order_key
from eval_platform.domain.result import ExecutionTrialResult, TerminationReason


class CancelAfterFirstBackend:
    def __init__(self, store, cancellation, actor):
        self.store = store
        self.cancellation = cancellation
        self.actor = actor
        self.started = []

    def execute(self, request, progress=None):
        assert progress is not None
        first = request.runs[0]
        assert progress.trial_started(first.run_id)
        self.started.append(first.run_id)
        self.cancellation.cancel(
            self.actor, request.job_id, "停止后续 Trial", "executing-cancel-0001"
        )
        patch = artifact(
            self.store,
            first.run_id,
            "agent_patch",
            b"diff --git a/a b/a\n",
            "text/x-diff",
        )
        result = ExecutionTrialResult(
            first.run_id,
            request.job_id,
            "harbor-trial-one",
            TerminationReason.COMPLETED,
            patch,
            None,
        )
        progress.trial_finished(first.run_id)
        for run in request.runs[1:]:
            if progress.trial_started(run.run_id):
                raise AssertionError(
                    "a later Trial remained startable after cancellation"
                )
        return (result,)


class CancelAfterStatusSampleJobs(ExecutableMemoryJobs):
    def __init__(self, *records):
        super().__init__(*records)
        self.cancel_after_sample = None

    def get(self, job_id):
        record = super().get(job_id)
        callback = self.cancel_after_sample
        if callback is not None and record.status == "EXECUTING":
            self.cancel_after_sample = None
            callback()
        return record


class EmptyBackend:
    def execute(self, request, progress=None):
        assert progress is not None
        return ()


def test_executing_cancel_preserves_current_result_and_cancels_later_runs():
    now = datetime(2026, 9, 13, 1, 0, tzinfo=UTC)
    job, bundles = queued_batch(now)
    repository = ExecutableMemoryJobs(job)
    artifacts = MemoryArtifacts()
    cancellation = JobCancellation(repository, lambda: now)
    actor = AuthenticatedActor(job.created_by, "owner", "owner")
    backend = CancelAfterFirstBackend(artifacts, cancellation, actor)
    source_by_id = {bundle.public.instance_id: bundle for bundle in bundles}
    source = type(
        "Source", (), {"load": lambda self, identity: source_by_id[identity]}
    )()
    executor = JobExecutor(
        repository, artifacts, backend, Evaluator(artifacts), source, lambda: now
    )

    assert WorkerShell(repository, executor, lambda: now).run_once("cancel-worker")

    stored = repository.get(job.job_id)
    ordered = sorted(stored.runs, key=run_order_key)
    assert backend.started == [ordered[0].run_id]
    assert stored.status == "CANCELED"
    assert [run.status for run in ordered] == ["COMPLETED", "CANCELED", "CANCELED"]
    assert repository.get_run_report(ordered[0].run_id).deterministic_result
    assert all(
        "TRIAL_STARTED" not in {event.reason_code for event in run.state_events}
        for run in ordered[1:]
    )
    assert [event.reason_code for event in stored.state_events][-3:] == [
        "CANCEL_REQUESTED",
        "FINALIZATION_STARTED",
        "JOB_CANCELED",
    ]


def test_cancel_during_result_reconciliation_cancels_unstarted_runs():
    now = datetime(2026, 9, 13, 1, 30, tzinfo=UTC)
    job, bundles = queued_batch(now)
    repository = CancelAfterStatusSampleJobs(job)
    cancellation = JobCancellation(repository, lambda: now)
    actor = AuthenticatedActor(job.created_by, "owner", "owner")
    repository.cancel_after_sample = lambda: cancellation.cancel(
        actor, job.job_id, "对账期间停止", "reconcile-cancel-0001"
    )
    source_by_id = {bundle.public.instance_id: bundle for bundle in bundles}
    source = type(
        "Source", (), {"load": lambda self, identity: source_by_id[identity]}
    )()
    artifacts = MemoryArtifacts()
    executor = JobExecutor(
        repository,
        artifacts,
        EmptyBackend(),
        Evaluator(artifacts),
        source,
        lambda: now,
    )

    WorkerShell(repository, executor, lambda: now).run_once("race-cancel-worker")

    stored = repository.get(job.job_id)
    assert stored.status == "CANCELED"
    assert {run.status for run in stored.runs} == {"CANCELED"}
    assert all(run.failure_code is None for run in stored.runs)
