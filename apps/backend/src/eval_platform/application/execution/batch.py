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
from eval_platform.domain.jobs.models import (
    EvaluationJob,
    EvaluationRun,
    JobError,
    run_order_key,
)
from eval_platform.domain.result import (
    ExecutionTrialResult,
    PatchValidationError,
    TerminationReason,
    validate_patch_content,
)
from eval_platform.domain.task import TaskBundle

_INCOMPLETE_BATCH_WARNINGS = frozenset(
    "HARBOR_JOB_RESULT_MISSING UNEXPECTED_HARBOR_TRIAL DUPLICATE_HARBOR_TRIAL "
    "INVALID_HARBOR_TRIAL_RESULT HARBOR_PROCESS_TIMEOUT".split()
)


class BatchProgress:
    """Persist ordered lifecycle signals, then publish each returned result."""

    def __init__(
        self,
        repository: JobRepository,
        artifacts: ArtifactStore,
        evaluator: PatchEvaluator,
        evidence: EvidencePublication,
        job: EvaluationJob,
        lease: JobLease,
        bundles: dict[str, TaskBundle],
        clock: Callable[[], datetime],
    ) -> None:
        self.repository, self.evaluator = repository, evaluator
        self.evidence, self.job, self.lease = evidence, job, lease
        self.bundles, self.clock = bundles, clock
        self.completions = CompletionFactory(job, artifacts, evidence, clock)
        self.runs = tuple(sorted(job.runs, key=run_order_key))
        self.started: set[str] = set()
        self.ended: set[str] = set()
        self.closed: set[str] = set()
        self.had_run_failure = False
        self.protocol_error: str | None = None

    def trial_started(self, run_id: str) -> None:
        if run_id in self.started:
            return
        expected = self._next_signal()
        if expected is None or expected.run_id != run_id:
            self.protocol_error = "BACKEND_PROGRESS_INVALID"
            return
        self.lease = self.repository.start_run(self.lease, run_id, self.clock())
        self.started.add(run_id)

    def trial_finished(self, run_id: str) -> None:
        if run_id in self.ended:
            return
        expected = self._next_signal()
        if expected is None or expected.run_id != run_id or run_id not in self.started:
            self.protocol_error = "BACKEND_PROGRESS_INVALID"
            return
        self.lease = self.repository.finish_run_execution(
            self.lease, run_id, self.clock()
        )
        self.ended.add(run_id)

    def reconcile(self, trials: tuple[ExecutionTrialResult, ...]) -> str | None:
        returned: dict[str, ExecutionTrialResult] = {}
        expected = {run.run_id for run in self.runs}
        if any(
            warning in _INCOMPLETE_BATCH_WARNINGS
            for trial in trials
            for warning in trial.warnings
        ):
            self.protocol_error = (
                self.protocol_error or "BACKEND_RESULT_IDENTITY_INVALID"
            )
        for trial in trials:
            if trial.run_id in returned or trial.run_id not in expected:
                self.protocol_error = "BACKEND_RESULT_IDENTITY_INVALID"
            else:
                returned[trial.run_id] = trial
        if returned.keys() != expected or self.ended != expected:
            self.protocol_error = (
                self.protocol_error or "BACKEND_RESULT_IDENTITY_INVALID"
            )
        for run in self.runs:
            result = returned.get(run.run_id)
            if result is None:
                self._fail(
                    run.run_id, self.protocol_error or "BACKEND_RESULT_IDENTITY_INVALID"
                )
            elif (
                run.run_id not in self.ended
                and result.termination_reason is TerminationReason.COMPLETED
            ):
                self._fail(
                    run.run_id, self.protocol_error or "BACKEND_RESULT_IDENTITY_INVALID"
                )
            else:
                self._handle(run, result)
            self.closed.add(run.run_id)
        return self.protocol_error

    def abort_remaining(self, code: str) -> None:
        for run in self.runs:
            if run.run_id in self.closed:
                continue
            self._fail(run.run_id, code)
            self.closed.add(run.run_id)

    def finalize(self, failure_code: str | None = None) -> bool:
        self.lease = self.repository.start_finalizing(self.lease, self.clock())
        self.repository.finish(self.lease, self.clock(), failure_code)
        return failure_code is None and not self.had_run_failure

    def _next_signal(self) -> EvaluationRun | None:
        return next((run for run in self.runs if run.run_id not in self.ended), None)

    def _handle(self, run: EvaluationRun, trial: ExecutionTrialResult) -> None:
        try:
            self._process(run, trial)
        except JobError as error:
            self._fail(run.run_id, getattr(error, "code", "EVIDENCE_UNAVAILABLE"))
        except (ArtifactUnavailable, EvaluationError, PatchValidationError) as error:
            self._fail(run.run_id, getattr(error, "code", "EVIDENCE_UNAVAILABLE"))
        except (KeyError, OSError, RuntimeError, TypeError, ValueError):
            self._fail(run.run_id, "EXECUTION_PIPELINE_INVALID")

    def _process(self, run: EvaluationRun, trial: ExecutionTrialResult) -> None:
        if not trial.backend_job_ref:
            self._fail(run.run_id, "BACKEND_RESULT_IDENTITY_INVALID")
            return
        if trial.termination_reason is not TerminationReason.COMPLETED:
            code = "EXECUTION_" + trial.termination_reason.value.upper()
            self._fail(run.run_id, code, trial)
            return
        if not trial.backend_trial_ref:
            self._fail(run.run_id, "BACKEND_RESULT_IDENTITY_INVALID", trial)
            return
        if trial.patch_ref is None:
            self._fail(run.run_id, "PATCH_MISSING", trial)
            return
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
        self.lease = self.repository.start_verifying(self.lease, trial, self.clock())
        bundle = self.bundles[run.run_id]
        result = self.evaluator.evaluate(
            EvaluationRequest(
                run.run_id,
                bundle.evaluator,
                patch,
                run.agent.agent_configuration_id,
            )
        )
        self.lease = self.repository.complete(
            self.lease, self.completions.build(run, trial, result)
        )

    def _fail(
        self, run_id: str, code: str, trial: ExecutionTrialResult | None = None
    ) -> None:
        self.lease = self.repository.fail(
            self.lease,
            run_id,
            str(code),
            "运行未形成可信结果。",
            self.clock(),
            trial,
        )
        self.had_run_failure = True
