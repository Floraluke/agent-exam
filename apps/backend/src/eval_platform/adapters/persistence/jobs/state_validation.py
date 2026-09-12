from eval_platform.domain.jobs.execution import initial_events_valid, pending_run_valid
from eval_platform.domain.jobs.models import EvaluationJob


def stored_job_valid(record: EvaluationJob) -> bool:
    if not initial_events_valid(record.state_events):
        return False
    has_failure = record.failure_code is not None and record.failure_summary is not None
    if (record.failure_code is None) != (record.failure_summary is None):
        return False
    if (record.status in {"FAILED", "COMPLETED_WITH_ERRORS"}) != has_failure:
        return False
    decided = (
        record.owner_decided_by is not None and record.owner_decided_at is not None
    )
    if record.status == "AWAITING_OWNER_APPROVAL":
        return not decided and all(pending_run_valid(run) for run in record.runs)
    if not decided or record.state_events[-1].to_status != record.status:
        return False
    if record.status == "QUEUED":
        return len(record.state_events) == 2 and all(
            pending_run_valid(run) for run in record.runs
        )
    if record.status == "REJECTED":
        return all(run.status == "CANCELED" for run in record.runs)
    if not record.claimed_by or record.lease_expires_at is None:
        return False
    if not all(
        initial_events_valid(run.state_events)
        and run.state_events[-1].to_status == run.status
        for run in record.runs
    ):
        return False
    statuses = {run.status for run in record.runs}
    terminal = {"COMPLETED", "FAILED", "CANCELED"}
    if record.status == "PREPARING":
        return (
            statuses <= {"PENDING", "PREPARING"}
            and sum(run.status == "PREPARING" for run in record.runs) == 1
        )
    if record.status == "EXECUTING":
        return statuses <= {
            "PENDING",
            "PREPARING",
            "RUNNING_AGENT",
            "VERIFYING",
            *terminal,
        }
    if record.status == "FINALIZING":
        return statuses <= terminal
    if record.status == "COMPLETED":
        return statuses == {"COMPLETED"}
    if record.status == "COMPLETED_WITH_ERRORS":
        return "COMPLETED" in statuses and statuses <= terminal
    return (
        record.status == "FAILED"
        and "COMPLETED" not in statuses
        and statuses <= terminal
    )
