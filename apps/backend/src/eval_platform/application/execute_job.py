from collections.abc import Callable
from dataclasses import replace
from datetime import UTC, datetime
from uuid import uuid4

from eval_platform.application.ports.artifacts import ArtifactStore
from eval_platform.application.ports.evaluator import (
    EvaluationError,
    EvaluationRequest,
    PatchEvaluator,
)
from eval_platform.application.ports.execution import (
    ExecutionBackend,
    ExecutionJobRequest,
)
from eval_platform.application.ports.repositories import JobRepository
from eval_platform.application.ports.task_source import TaskSource
from eval_platform.domain.catalog import ArtifactUnavailable
from eval_platform.domain.jobs.execution import (
    ClaimedJob,
    JobLease,
    ProcessMetrics,
    RunArtifact,
    RunCompletion,
    StoredDeterministicResult,
    restore_agent,
    restore_public_task,
)
from eval_platform.domain.jobs.models import JobError
from eval_platform.domain.result import (
    ArtifactRef,
    DeterministicResult,
    ExecutionTrialResult,
    PatchValidationError,
    ResourceSummary,
    TerminationReason,
    UsageSummary,
    validate_patch_content,
)


class JobExecutor:
    def __init__(
        self,
        repository: JobRepository,
        artifacts: ArtifactStore,
        backend: ExecutionBackend,
        evaluator: PatchEvaluator,
        tasks: TaskSource,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self.repository = repository
        self.artifacts = artifacts
        self.backend = backend
        self.evaluator = evaluator
        self.tasks = tasks
        self.clock = clock

    def execute(self, claimed: ClaimedJob) -> bool:
        lease, job = claimed.lease, claimed.job
        try:
            if len(job.runs) != 1:
                raise ValueError("Task 06 only permits one run")
            run = job.runs[0]
            public_task = restore_public_task(run)
            bundle = self.tasks.load(run.task.instance_id)
            if bundle.public != public_task:
                raise ValueError("Frozen task does not match the evaluator source")
            agent = restore_agent(run)
            lease = self.repository.start_execution(lease, self.clock())
            request = ExecutionJobRequest.single_run(job, run, public_task, agent)
            trials = self.backend.execute(request)
            if len(trials) != 1 or trials[0].run_id != run.run_id:
                return self._fail(lease, "BACKEND_RESULT_IDENTITY_INVALID")
            trial = trials[0]
            if trial.termination_reason is not TerminationReason.COMPLETED:
                return self._fail(
                    lease, "EXECUTION_" + trial.termination_reason.value.upper()
                )
            if trial.patch_ref is None:
                return self._fail(lease, "PATCH_MISSING")
            patch = self.artifacts.read_verified(trial.patch_ref)
            patch_warnings = validate_patch_content(
                trial.patch_ref,
                patch,
                job.limit_snapshot.patch_warning_bytes,
                job.limit_snapshot.patch_max_bytes,
            )
            patch_ref = replace(
                trial.patch_ref,
                warnings=tuple(
                    dict.fromkeys(
                        (*trial.warnings, *trial.patch_ref.warnings, *patch_warnings)
                    )
                ),
            )
            trial = replace(trial, patch_ref=patch_ref, warnings=patch_ref.warnings)
            lease = self.repository.start_verifying(lease, trial, self.clock())
            result = self.evaluator.evaluate(
                EvaluationRequest(
                    run.run_id, bundle.evaluator, patch, agent.configuration_id
                )
            )
            completion = self._completion(job.swe_bench_fork_revision, trial, result)
            self.repository.complete(lease, completion)
            return True
        except (
            ArtifactUnavailable,
            EvaluationError,
            PatchValidationError,
            JobError,
        ) as error:
            code = getattr(error, "code", "EVIDENCE_UNAVAILABLE")
            return self._fail(lease, str(code))
        except (KeyError, OSError, RuntimeError, TypeError, ValueError):
            return self._fail(lease, "EXECUTION_PIPELINE_INVALID")

    def _completion(
        self,
        revision: str,
        trial: ExecutionTrialResult,
        result: DeterministicResult,
    ) -> RunCompletion:
        if result.run_id != trial.run_id or result.tests_status_summary is None:
            raise ValueError("Evaluator result identity is incomplete")
        patch_ref = trial.patch_ref
        if patch_ref is None:
            raise ValueError("Patch reference disappeared")
        references = (patch_ref, result.report_ref, *result.log_refs)
        verified = tuple(self._artifact(trial.run_id, item) for item in references)
        report = next(
            item
            for item in verified
            if item.reference.artifact_type in {"harness_report", "harness_summary"}
        )
        outputs = [
            item
            for item in verified
            if item.reference.artifact_type == "harness_test_output"
        ]
        if len(outputs) > 1 or (references[0].size_bytes and len(outputs) != 1):
            raise ValueError("Evaluator test output identity is incomplete")
        now = self.clock()
        stored = StoredDeterministicResult(
            trial.run_id,
            patch_ref.size_bytes > 0,
            result.patch_applied,
            result.resolved,
            result.tests_status_summary,
            revision,
            report.artifact_id,
            outputs[0].artifact_id if outputs else None,
            result.duration_ms,
            now,
        )
        metrics = ProcessMetrics(
            trial.usage or UsageSummary(),
            trial.resource_summary or ResourceSummary(),
        )
        return RunCompletion(
            stored,
            verified,
            metrics,
            trial.backend_job_ref,
            trial.backend_trial_ref,
            trial.warnings,
            now,
        )

    def _artifact(self, run_id: str, reference: ArtifactRef) -> RunArtifact:
        prefix = f"runs/{run_id}/{reference.artifact_type}/"
        if not reference.object_key.startswith(prefix):
            raise ValueError("Artifact owner identity mismatch")
        self.artifacts.read_verified(reference)
        return RunArtifact(str(uuid4()), run_id, reference)

    def _fail(self, lease: JobLease, code: str) -> bool:
        try:
            self.repository.fail(lease, code, "运行未形成可信结果。", self.clock())
        except JobError:
            pass
        return False
