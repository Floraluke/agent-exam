from collections.abc import Callable
from datetime import datetime

from eval_platform.application.execution.evidence import EvidencePublication
from eval_platform.application.execution.run_results import RunResultProcessor
from eval_platform.application.ports.artifacts import ArtifactStore
from eval_platform.application.ports.evaluator import PatchEvaluator
from eval_platform.application.ports.repositories import JobRepository
from eval_platform.domain.jobs.execution import JobLease
from eval_platform.domain.jobs.models import (
    EvaluationJob,
    EvaluationRun,
    run_order_key,
)
from eval_platform.domain.result import ExecutionTrialResult, TerminationReason
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
        self.repository, self.job, self.lease = repository, job, lease
        self.clock = clock
        self.processor = RunResultProcessor(
            repository, artifacts, evaluator, evidence, job, bundles, clock
        )
        self.runs = tuple(sorted(job.runs, key=run_order_key))
        self.started: set[str] = set()
        self.ended: set[str] = set()
        self.closed: set[str] = set()
        self.had_run_failure = False
        self.protocol_error: str | None = None

    def trial_started(self, run_id: str) -> bool:
        if run_id in self.started:
            return True
        expected = self._next_signal()
        if expected is None or expected.run_id != run_id:
            self.protocol_error = "BACKEND_PROGRESS_INVALID"
            return False
        decision = self.repository.start_run(self.lease, run_id, self.clock())
        self.lease = decision.lease
        if not decision.started:
            return False
        self.started.add(run_id)
        return True

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
        canceling = self.repository.get(self.job.job_id).status == "CANCEL_REQUESTED"
        expected_results = self.ended if canceling else expected
        if returned.keys() != expected_results or self.ended != expected_results:
            self.protocol_error = (
                self.protocol_error or "BACKEND_RESULT_IDENTITY_INVALID"
            )
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
        self.lease, failed = self.processor.handle(self.lease, run, trial)
        self.had_run_failure = self.had_run_failure or failed

    def _fail(
        self, run_id: str, code: str, trial: ExecutionTrialResult | None = None
    ) -> None:
        current = self.repository.get(self.job.job_id)
        run = next(item for item in current.runs if item.run_id == run_id)
        if run.status == "CANCELED":
            return
        self.lease, failed = self.processor.fail(self.lease, run_id, str(code), trial)
        self.had_run_failure = self.had_run_failure or failed
