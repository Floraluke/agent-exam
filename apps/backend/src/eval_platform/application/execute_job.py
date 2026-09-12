from collections.abc import Callable
from datetime import UTC, datetime

from eval_platform.application.execution.batch import BatchProgress
from eval_platform.application.execution.evidence import EvidencePublication
from eval_platform.application.ports.artifacts import ArtifactReader, ArtifactStore
from eval_platform.application.ports.evaluator import PatchEvaluator
from eval_platform.application.ports.execution import (
    ExecutionBackend,
    ExecutionJobRequest,
    ExecutionRunRequest,
    RunLimits,
)
from eval_platform.application.ports.repositories import JobRepository
from eval_platform.application.ports.task_source import TaskSource
from eval_platform.domain.jobs.execution import (
    ClaimedJob,
    restore_agent,
    restore_public_task,
)
from eval_platform.domain.jobs.models import EvaluationJob, run_order_key
from eval_platform.domain.task import TaskBundle


class JobExecutor:
    """Run one frozen matrix through one backend call and close every Run."""

    def __init__(
        self,
        repository: JobRepository,
        artifacts: ArtifactStore,
        backend: ExecutionBackend,
        evaluator: PatchEvaluator,
        tasks: TaskSource,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
        source_artifacts: ArtifactReader | None = None,
    ) -> None:
        self.repository = repository
        self.artifacts = artifacts
        self.backend = backend
        self.evaluator = evaluator
        self.tasks = tasks
        self.clock = clock
        self.evidence = EvidencePublication(source_artifacts or artifacts, artifacts)

    def execute(self, claimed: ClaimedJob) -> bool:
        job = claimed.job
        lease = self.repository.start_execution(claimed.lease, self.clock())
        bundles: dict[str, TaskBundle] = {}
        progress = BatchProgress(
            self.repository,
            self.artifacts,
            self.evaluator,
            self.evidence,
            job,
            lease,
            bundles,
            self.clock,
        )
        try:
            request = self._request(job, bundles)
            trials = self.backend.execute(request, progress)
            error = progress.reconcile(trials)
        except (KeyError, OSError, RuntimeError, TypeError, ValueError):
            error = "EXECUTION_PIPELINE_INVALID"
        if error is not None:
            progress.abort_remaining(error)
        return progress.finalize(error)

    def _request(
        self, job: EvaluationJob, bundles: dict[str, TaskBundle]
    ) -> ExecutionJobRequest:
        requests = []
        revisions: set[str] = set()
        contracts: set[str] = set()
        for run in sorted(job.runs, key=run_order_key):
            task = restore_public_task(run)
            bundle = self.tasks.load(run.task.instance_id)
            if bundle.public != task:
                raise ValueError("Frozen task does not match evaluator source")
            bundles[run.run_id] = bundle
            requests.append(ExecutionRunRequest(run.run_id, task, restore_agent(run)))
            revisions.add(run.backend_revision)
            contracts.add(run.execution_contract_version)
        if len(revisions) != 1 or len(contracts) != 1:
            raise ValueError("Frozen execution contract differs within one Job")
        limits = job.limit_snapshot
        return ExecutionJobRequest(
            job.job_id,
            tuple(requests),
            RunLimits(
                limits.agent_wall_timeout_sec,
                limits.agent_cpus,
                limits.agent_memory_mb,
                limits.agent_storage_mb,
            ),
            revisions.pop(),
            contracts.pop(),
            job.evaluation_track,
        )
