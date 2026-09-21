from eval_platform.domain.jobs.execution import initial_events_valid, pending_run_valid
from eval_platform.domain.jobs.models import EvaluationJob

TERMINAL_RUN_STATUSES = frozenset({"COMPLETED", "FAILED", "CANCELED"})
ACTIVE_RUN_STATUSES = (
    frozenset({"PENDING", "PREPARING", "RUNNING_AGENT", "VERIFYING"})
    | TERMINAL_RUN_STATUSES
)


def stored_job_valid(record: EvaluationJob) -> bool:
    if not initial_events_valid(record.state_events) or not _failure_valid(record):
        return False
    decided = _paired(record.owner_decided_by, record.owner_decided_at)
    cancel_requested = _paired(record.cancel_requested_by, record.cancel_requested_at)
    if record.status == "AWAITING_OWNER_APPROVAL":
        return not decided and not cancel_requested and _pending_runs(record)
    if record.state_events[-1].to_status != record.status:
        return False
    if record.status == "CANCELED":
        return cancel_requested and _statuses(record) <= TERMINAL_RUN_STATUSES
    if not decided:
        return False
    if record.status == "QUEUED":
        return len(record.state_events) == 2 and _pending_runs(record)
    if record.status == "REJECTED":
        return all(run.status == "CANCELED" for run in record.runs)
    if not record.claimed_by or record.lease_expires_at is None:
        return False
    if not _run_events_valid(record):
        return False
    return _claimed_status_valid(record, cancel_requested)


def _failure_valid(record: EvaluationJob) -> bool:
    has_failure = record.failure_code is not None and record.failure_summary is not None
    complete_pair = (record.failure_code is None) == (record.failure_summary is None)
    return complete_pair and (
        (record.status in {"FAILED", "COMPLETED_WITH_ERRORS"}) == has_failure
    )


def _paired(first: object | None, second: object | None) -> bool:
    return first is not None and second is not None


def _pending_runs(record: EvaluationJob) -> bool:
    return all(pending_run_valid(run) for run in record.runs)


def _statuses(record: EvaluationJob) -> set[str]:
    return {run.status for run in record.runs}


def _run_events_valid(record: EvaluationJob) -> bool:
    return all(
        initial_events_valid(run.state_events)
        and run.state_events[-1].to_status == run.status
        for run in record.runs
    )


def _claimed_status_valid(record: EvaluationJob, cancel_requested: bool) -> bool:
    statuses = _statuses(record)
    if record.status == "PREPARING":
        return (
            statuses <= {"PENDING", "PREPARING"}
            and sum(run.status == "PREPARING" for run in record.runs) == 1
        )
    if record.status == "EXECUTING":
        return statuses <= ACTIVE_RUN_STATUSES
    if record.status == "CANCEL_REQUESTED":
        return cancel_requested and statuses <= ACTIVE_RUN_STATUSES
    if record.status == "FINALIZING":
        return statuses <= TERMINAL_RUN_STATUSES
    if record.status == "COMPLETED":
        return statuses == {"COMPLETED"}
    if record.status == "COMPLETED_WITH_ERRORS":
        return "COMPLETED" in statuses and statuses <= TERMINAL_RUN_STATUSES
    return (
        record.status == "FAILED"
        and "COMPLETED" not in statuses
        and statuses <= TERMINAL_RUN_STATUSES
    )
