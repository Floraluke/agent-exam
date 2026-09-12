from datetime import UTC, datetime, timedelta

from jobs.execution.support.fakes import Backend, Evaluator, MemoryArtifacts
from jobs.execution.support.fixtures import queued_job
from jobs.execution.support.memory import ExecutableMemoryJobs

from eval_platform.application.execute_job import JobExecutor
from eval_platform.delivery.worker.main import WorkerShell


class MutableClock:
    def __init__(self, current):
        self.current = current

    def __call__(self):
        return self.current


class DelayedBackend(Backend):
    def __init__(self, store, clock):
        super().__init__(store, b"diff --git a/a b/a\n")
        self.clock = clock

    def execute(self, request, progress=None):
        assert progress is not None
        progress.trial_started(request.runs[0].run_id)
        self.clock.current += timedelta(minutes=30)
        return super().execute(request, progress)


def test_lease_remains_valid_during_legal_backend_setup_budget():
    clock = MutableClock(datetime(2026, 9, 12, 15, 30, tzinfo=UTC))
    job, bundle = queued_job(clock())
    repository, artifacts = ExecutableMemoryJobs(job), MemoryArtifacts()
    source = type("Source", (), {"load": lambda _self, _identity: bundle})()
    executor = JobExecutor(
        repository,
        artifacts,
        DelayedBackend(artifacts, clock),
        Evaluator(artifacts),
        source,
        clock,
    )

    assert WorkerShell(repository, executor, clock).run_once("delayed-worker")
    assert repository.get(job.job_id).status == "COMPLETED"
