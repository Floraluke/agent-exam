"""Persist one returned Trial result behind the execution lifecycle seam."""

from collections.abc import Callable
from dataclasses import replace
from datetime import datetime

from eval_platform.application.execution.completion import CompletionFactory
from eval_platform.application.execution.evidence import EvidencePublication
from eval_platform.application.ports.artifacts import ArtifactStore
from eval_platform.application.ports.evaluator import (
    EvaluationError,
    EvaluationRequest,
    PatchEvaluator,
)
from eval_platform.application.ports.repositories import JobRepository
from eval_platform.domain.catalog import ArtifactUnavailable
from eval_platform.domain.jobs.execution import JobLease
from eval_platform.domain.jobs.models import EvaluationJob, EvaluationRun, JobError
from eval_platform.domain.result import (
    ExecutionTrialResult,
    PatchValidationError,
    TerminationReason,
    validate_patch_content,
)
from eval_platform.domain.task import TaskBundle


class RunResultProcessor:
    def __init__(
        self,
        repository: JobRepository,
        artifacts: ArtifactStore,
        evaluator: PatchEvaluator,
        evidence: EvidencePublication,
        job: EvaluationJob,
        bundles: dict[str, TaskBundle],
        clock: Callable[[], datetime],
    ) -> None:
        self.repository, self.evaluator = repository, evaluator
        self.evidence, self.job = evidence, job
        self.bundles, self.clock = bundles, clock
        self.completions = CompletionFactory(job, artifacts, evidence, clock)
        self._active_lease: JobLease | None = None

    def handle(
        self, lease: JobLease, run: EvaluationRun, trial: ExecutionTrialResult
    ) -> tuple[JobLease, bool]:
        self._active_lease = lease
        try:
            return self._process(run, trial)
        except JobError as error:
            code = getattr(error, "code", "EVIDENCE_UNAVAILABLE")
        except (ArtifactUnavailable, EvaluationError, PatchValidationError) as error:
            code = getattr(error, "code", "EVIDENCE_UNAVAILABLE")
        except (KeyError, OSError, RuntimeError, TypeError, ValueError):
            code = "EXECUTION_PIPELINE_INVALID"
        assert self._active_lease is not None
        return self.fail(self._active_lease, run.run_id, str(code)), True

    def _process(
        self, run: EvaluationRun, trial: ExecutionTrialResult
    ) -> tuple[JobLease, bool]:
        assert self._active_lease is not None
        lease = self._active_lease
        if not trial.backend_job_ref:
            return self.fail(
                lease, run.run_id, "BACKEND_RESULT_IDENTITY_INVALID"
            ), True
        if trial.termination_reason is not TerminationReason.COMPLETED:
            code = "EXECUTION_" + trial.termination_reason.value.upper()
            return self.fail(lease, run.run_id, code, trial), True
        if not trial.backend_trial_ref:
            lease = self.fail(
                lease, run.run_id, "BACKEND_RESULT_IDENTITY_INVALID", trial
            )
            return lease, True
        if trial.patch_ref is None:
            return self.fail(lease, run.run_id, "PATCH_MISSING", trial), True
        patch_ref, patch = self.evidence.prepare_patch(run.run_id, trial.patch_ref)
        warnings = validate_patch_content(
            patch_ref,
            patch,
            self.job.limit_snapshot.patch_warning_bytes,
            self.job.limit_snapshot.patch_max_bytes,
        )
        patch_ref = replace(
            patch_ref,
            warnings=tuple(
                dict.fromkeys((*trial.warnings, *patch_ref.warnings, *warnings))
            ),
        )
        self.evidence.persist(patch_ref, patch)
        trial = replace(trial, patch_ref=patch_ref, warnings=patch_ref.warnings)
        lease = self.repository.start_verifying(lease, trial, self.clock())
        self._active_lease = lease
        bundle = self.bundles[run.run_id]
        result = self.evaluator.evaluate(
            EvaluationRequest(
                run.run_id,
                bundle.evaluator,
                patch,
                run.agent.agent_configuration_id,
            )
        )
        completed = self.repository.complete(
            lease, self.completions.build(run, trial, result)
        )
        return completed, False

    def fail(
        self,
        lease: JobLease,
        run_id: str,
        code: str,
        trial: ExecutionTrialResult | None = None,
    ) -> JobLease:
        return self.repository.fail(
            lease,
            run_id,
            code,
            "运行未形成可信结果。",
            self.clock(),
            trial,
        )
