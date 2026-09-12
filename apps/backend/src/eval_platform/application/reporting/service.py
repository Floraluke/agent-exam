from collections.abc import Callable

from eval_platform.application.ports.artifacts import ArtifactReader
from eval_platform.application.ports.repositories import JobRepository
from eval_platform.domain.catalog import ArtifactUnavailable
from eval_platform.domain.identity import AuthenticatedActor
from eval_platform.domain.jobs.execution import JobReport, RunReport
from eval_platform.domain.jobs.models import JobNotFound, ResultScope


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
        self.artifacts = artifacts
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
            self.artifacts.read_verified(item.reference)

    @staticmethod
    def _authorize(actor: AuthenticatedActor, created_by: str) -> None:
        if actor.role != "owner" and actor.user_id != created_by:
            raise JobNotFound
