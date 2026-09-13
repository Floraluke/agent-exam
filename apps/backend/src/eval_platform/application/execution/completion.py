from collections.abc import Callable
from datetime import datetime
from uuid import uuid4

from eval_platform.application.execution.evidence import EvidencePublication
from eval_platform.application.ports.artifacts import ArtifactStore
from eval_platform.domain.jobs.execution import (
    ProcessMetrics,
    RunArtifact,
    RunCompletion,
    StoredDeterministicResult,
)
from eval_platform.domain.jobs.models import EvaluationJob, EvaluationRun
from eval_platform.domain.result import (
    ArtifactRef,
    DeterministicResult,
    ExecutionTrialResult,
    ResourceSummary,
    UsageSummary,
)


class CompletionFactory:
    """Publish and verify all evidence before constructing an atomic Run result."""

    def __init__(
        self,
        job: EvaluationJob,
        artifacts: ArtifactStore,
        evidence: EvidencePublication,
        clock: Callable[[], datetime],
    ) -> None:
        self.job, self.artifacts = job, artifacts
        self.evidence, self.clock = evidence, clock

    def build(
        self,
        run: EvaluationRun,
        trial: ExecutionTrialResult,
        result: DeterministicResult,
    ) -> RunCompletion:
        if result.run_id != run.run_id or result.tests_status_summary is None:
            raise ValueError("Evaluator result identity is incomplete")
        patch_ref = trial.patch_ref
        if patch_ref is None:
            raise ValueError("Patch reference disappeared")
        patch_exists = patch_ref.size_bytes > 0
        if result.patch_applied != patch_exists or (
            result.resolved and not patch_exists
        ):
            raise ValueError("Evaluator result contradicts patch evidence")
        public_summary = self.evidence.publish_test_summary(
            run.run_id, result.tests_status_summary
        )
        trajectory_time = self.clock()
        if trial.trajectory_ref is not None and trial.trajectory_ref.created_at:
            trajectory_time = trial.trajectory_ref.created_at
        public_trajectory = self.evidence.publish_trajectory(
            run.run_id,
            trial.trajectory_ref,
            run.agent.agent_type,
            trajectory_time,
        )
        raw_sources = tuple(
            item
            for item in (
                trial.raw_config_ref,
                trial.raw_result_ref,
                trial.trajectory_ref,
                result.report_ref,
                *result.log_refs,
            )
            if item is not None
        )
        raw, raw_warnings = self.evidence.publish_raw(
            run.run_id,
            raw_sources,
            self.job.limit_snapshot.raw_artifact_max_bytes,
            self.job.limit_snapshot.raw_run_max_bytes,
        )
        references = (
            patch_ref,
            *self.evidence.publish_evaluation(run.run_id, result),
            public_summary,
            *((public_trajectory,) if public_trajectory is not None else ()),
            *raw,
        )
        verified = tuple(self._artifact(run.run_id, item) for item in references)
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
        if len(outputs) > 1 or (patch_exists and len(outputs) != 1):
            raise ValueError("Evaluator test output identity is incomplete")
        now = self.clock()
        stored = StoredDeterministicResult(
            run.run_id,
            patch_exists,
            result.patch_applied,
            result.resolved,
            result.tests_status_summary,
            self.job.swe_bench_fork_revision,
            report.artifact_id,
            outputs[0].artifact_id if outputs else None,
            result.duration_ms,
            now,
        )
        metrics = ProcessMetrics(
            trial.usage or UsageSummary(), trial.resource_summary or ResourceSummary()
        )
        return RunCompletion(
            stored,
            verified,
            metrics,
            trial.backend_job_ref,
            trial.backend_trial_ref,
            tuple(dict.fromkeys((*trial.warnings, *raw_warnings))),
            now,
        )

    def _artifact(self, run_id: str, reference: ArtifactRef) -> RunArtifact:
        prefix = f"runs/{run_id}/{reference.artifact_type}/"
        if not reference.object_key.startswith(prefix):
            raise ValueError("Artifact owner identity mismatch")
        self.artifacts.read_verified(reference)
        redaction = (
            "redacted"
            if reference.artifact_type in {"public_test_summary", "public_trajectory"}
            else "blocked"
            if reference.artifact_type
            not in {"agent_patch", "public_test_summary", "public_trajectory"}
            else "not_required"
        )
        return RunArtifact(str(uuid4()), run_id, reference, redaction)
