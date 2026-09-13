"""Read-only report views for the executable memory adapter."""

from eval_platform.domain.jobs.execution import JobReport, ProcessMetrics, RunReport
from eval_platform.domain.jobs.models import JobNotFound
from eval_platform.domain.result import ResourceSummary, UsageSummary


def get_run_report(repository, run_id):
    try:
        return repository.reports[run_id]
    except KeyError:
        for job in repository.records.values():
            run = next((item for item in job.runs if item.run_id == run_id), None)
            if run is not None:
                return RunReport(
                    job.created_by,
                    job.result_scope,
                    run,
                    None,
                    ProcessMetrics(UsageSummary(), ResourceSummary()),
                    (),
                )
        raise JobNotFound from None


def get_job_report(repository, job_id):
    job = repository.get(job_id)
    reports = tuple(get_run_report(repository, run.run_id) for run in job.runs)
    return JobReport(job.created_by, job, reports)


def get_artifact_report(repository, artifact_id):
    for job in repository.records.values():
        for run in job.runs:
            report = get_run_report(repository, run.run_id)
            if any(item.artifact_id == artifact_id for item in report.artifacts):
                return report
    raise JobNotFound
