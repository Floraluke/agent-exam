from datetime import UTC, datetime

from jobs.execution.support.fakes import Backend, Evaluator, MemoryArtifacts
from jobs.execution.support.fixtures import queued_batch
from jobs.execution.support.memory import ExecutableMemoryJobs

from eval_platform.application.execute_job import JobExecutor
from eval_platform.delivery.worker.main import WorkerShell
from eval_platform.domain.catalog import ArtifactUnavailable
from eval_platform.domain.jobs.models import run_order_key


class FailingArtifacts(MemoryArtifacts):
    def __init__(self, failed_run_id):
        super().__init__()
        self.failed_run_id = failed_run_id

    def put_immutable(self, reference, content):
        if f"runs/{self.failed_run_id}/" in reference.object_key:
            raise ArtifactUnavailable
        super().put_immutable(reference, content)


def test_middle_object_store_failure_keeps_prior_and_later_results():
    now = datetime(2026, 9, 12, 15, 45, tzinfo=UTC)
    job, bundles = queued_batch(now)
    ordered = sorted(job.runs, key=run_order_key)
    source = MemoryArtifacts()
    destination = FailingArtifacts(ordered[1].run_id)
    repository = ExecutableMemoryJobs(job)
    task_source = type(
        "Source",
        (),
        {
            "load": lambda self, identity: {
                item.public.instance_id: item for item in bundles
            }[identity]
        },
    )()
    executor = JobExecutor(
        repository,
        destination,
        Backend(source, b"diff --git a/a b/a\n"),
        Evaluator(source),
        task_source,
        lambda: now,
        source,
    )

    assert WorkerShell(repository, executor, lambda: now).run_once("store-worker")

    stored = repository.get(job.job_id)
    by_id = {run.run_id: run for run in stored.runs}
    assert stored.status == "COMPLETED_WITH_ERRORS"
    assert by_id[ordered[0].run_id].status == "COMPLETED"
    assert by_id[ordered[1].run_id].failure_code == "EVIDENCE_UNAVAILABLE"
    assert by_id[ordered[2].run_id].status == "COMPLETED"
