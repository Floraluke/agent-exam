from collections.abc import Callable, Sequence

from eval_platform.application.ports.artifacts import ArtifactReader
from eval_platform.application.ports.repositories import JobRepository
from eval_platform.application.reporting.evidence import (
    ArtifactPage,
    EvidenceContent,
    TrajectoryPage,
    artifact,
    artifact_page,
    content,
    trajectory_page,
)
from eval_platform.application.reporting.matrix import ReportMatrix, build_matrix
from eval_platform.domain.catalog import ArtifactUnavailable
from eval_platform.domain.identity import AuthenticatedActor
from eval_platform.domain.jobs.execution import JobReport, RunReport
from eval_platform.domain.jobs.models import (
    EvidenceNotFound,
    EvidenceNotReady,
    JobInputError,
    JobNotFound,
    ResultScope,
)

MAX_COMPARISON_JOBS = 20


def _official(scope: ResultScope) -> bool:
    return scope == "official"


class JobReporting:
    def __init__(
        self,
        repository: JobRepository,
        artifacts: ArtifactReader,
        scope_visible: Callable[[ResultScope], bool] = _official,
    ) -> None:
        self.repository = repository
        self.artifact_reader = artifacts
        self.scope_visible = scope_visible

    def run(self, actor: AuthenticatedActor, run_id: str) -> RunReport:
        report = self.repository.get_run_report(run_id)
        self._publishable(report.result_scope)
        self._authorize(actor, report.created_by)
        self._verify(report)
        return report

    def job(self, actor: AuthenticatedActor, job_id: str) -> JobReport:
        report = self.repository.get_job_report(job_id)
        self._publishable(report.job.result_scope)
        self._authorize(actor, report.created_by)
        for run in report.run_reports:
            self._verify(run)
        return report

    def compare(
        self, actor: AuthenticatedActor, job_ids: Sequence[str]
    ) -> ReportMatrix:
        """Aggregate several job reports into one task × configuration matrix.

        Authorization and evidence verification reuse `job`; any hidden or
        unreadable job fails the whole comparison without revealing which one.
        """
        unique = tuple(dict.fromkeys(job_ids))
        if not unique:
            raise JobInputError("EMPTY_COMPARISON_SELECTION")
        if len(unique) > MAX_COMPARISON_JOBS:
            raise JobInputError("COMPARISON_LIMIT_EXCEEDED")
        return build_matrix([self.job(actor, job_id) for job_id in unique])

    def artifacts(
        self,
        actor: AuthenticatedActor,
        run_id: str,
        kind: str | None,
        cursor: str | None,
        limit: int,
    ) -> ArtifactPage:
        return artifact_page(self.run(actor, run_id), kind, cursor, limit)

    def content(self, actor: AuthenticatedActor, artifact_id: str) -> EvidenceContent:
        try:
            report = self.repository.get_artifact_report(artifact_id)
            self._publishable(report.result_scope)
            self._authorize(actor, report.created_by)
        except JobNotFound:
            raise EvidenceNotFound from None
        self._verify(report)
        item = artifact(report, artifact_id)
        return content(item, self.artifact_reader.read_verified(item.reference))

    def trajectory(
        self,
        actor: AuthenticatedActor,
        run_id: str,
        after_sequence: int,
        limit: int,
        kind: str | None,
    ) -> TrajectoryPage:
        report = self.run(actor, run_id)
        item = next(
            (
                item
                for item in report.artifacts
                if item.reference.artifact_type == "public_trajectory"
            ),
            None,
        )
        if item is None:
            raise EvidenceNotReady
        body = self.artifact_reader.read_verified(item.reference)
        return trajectory_page(report, body, after_sequence, limit, kind)

    def _publishable(self, scope: ResultScope) -> None:
        if not self.scope_visible(scope):
            raise JobNotFound

    def _verify(self, report: RunReport) -> None:
        result = report.deterministic_result
        if result is None:
            return
        indexed = {item.artifact_id: item for item in report.artifacts}
        required = {result.report_artifact_id}
        if result.patch_exists:
            if result.test_output_artifact_id is None:
                raise ArtifactUnavailable
            required.add(result.test_output_artifact_id)
        elif result.test_output_artifact_id is not None:
            raise ArtifactUnavailable
        patches = [
            item
            for item in report.artifacts
            if item.reference.artifact_type == "agent_patch"
        ]
        report_type = "harness_report" if result.patch_exists else "harness_summary"
        if (
            not required <= indexed.keys()
            or len(patches) != 1
            or indexed[result.report_artifact_id].reference.artifact_type != report_type
            or (
                result.test_output_artifact_id is not None
                and indexed[result.test_output_artifact_id].reference.artifact_type
                != "harness_test_output"
            )
        ):
            raise ArtifactUnavailable
        for item in report.artifacts:
            prefix = f"runs/{report.run.run_id}/{item.reference.artifact_type}/"
            if (
                item.run_id != report.run.run_id
                or not item.reference.object_key.startswith(prefix)
            ):
                raise ArtifactUnavailable
            if item.reference.deleted_at is None:
                self.artifact_reader.read_verified(item.reference)

    @staticmethod
    def _authorize(actor: AuthenticatedActor, created_by: str) -> None:
        if actor.role != "owner" and actor.user_id != created_by:
            raise JobNotFound
