"""Thread-safe synthetic adapter for the JobRepository port."""

from dataclasses import replace
from threading import Lock
from uuid import uuid4

from eval_platform.domain.jobs.decisions import JobStateConflict
from eval_platform.domain.jobs.models import (
    JobIdempotencyConflict,
    JobNotFound,
    StateEvent,
)
from jobs.support.cancellation import cancel as cancel_job
from jobs.support.recovery import recover as recover_job


class MemoryJobs:
    def __init__(self):
        self.records = {}
        self.keys = {}
        self.decisions = {}
        self.cancellations = {}
        self.lock = Lock()

    def resolve_idempotency(self, created_by, key_hash, request_sha256):
        with self.lock:
            value = self.keys.get((created_by, key_hash))
            if value is None:
                return None
            original_sha, job_id = value
            if original_sha != request_sha256:
                raise JobIdempotencyConflict
            return self.records[job_id]

    def create(self, record, key_hash, request_sha256):
        with self.lock:
            scope = (record.created_by, key_hash)
            value = self.keys.get(scope)
            if value is not None:
                original_sha, job_id = value
                if original_sha != request_sha256:
                    raise JobIdempotencyConflict
                return self.records[job_id]
            self.records[record.job_id] = record
            self.keys[scope] = (request_sha256, record.job_id)
            return record

    def get(self, job_id):
        try:
            return self.records[job_id]
        except KeyError:
            raise JobNotFound from None

    def list(self, created_by, filters, cursor, limit):
        return [
            record
            for key, record in sorted(self.records.items())
            if (created_by is None or record.created_by == created_by)
            and (cursor is None or key > cursor)
            and all(getattr(record, field) == value for field, value in filters.items())
        ][:limit]

    def decide(self, decision):
        with self.lock:
            record = self.get(decision.job_id)
            previous = self.decisions.get(decision.job_id)
            if previous is not None:
                key_hash, request_sha = previous
                if key_hash == decision.idempotency_key_hash:
                    if request_sha != decision.request_sha256:
                        raise JobIdempotencyConflict
                    return record
                raise JobStateConflict
            if record.status != "AWAITING_OWNER_APPROVAL":
                raise JobStateConflict
            event = StateEvent(
                str(uuid4()),
                2,
                "AWAITING_OWNER_APPROVAL",
                decision.target_status,
                decision.reason_code,
                decision.decided_at,
                decision.actor_user_id,
                decision.reason,
            )
            runs = record.runs
            if decision.cancels_runs:
                runs = tuple(
                    replace(
                        run,
                        status="CANCELED",
                        state_events=run.state_events
                        + (
                            StateEvent(
                                str(uuid4()),
                                2,
                                "PENDING",
                                "CANCELED",
                                "JOB_REJECTED",
                                decision.decided_at,
                            ),
                        ),
                    )
                    for run in runs
                )
            decided = replace(
                record,
                status=decision.target_status,
                row_version=record.row_version + 1,
                runs=runs,
                state_events=record.state_events + (event,),
                owner_decided_by=decision.actor_user_id,
                owner_decided_at=decision.decided_at,
                owner_decision_reason=decision.reason,
            )
            self.records[record.job_id] = decided
            self.decisions[record.job_id] = (
                decision.idempotency_key_hash,
                decision.request_sha256,
            )
            return decided

    def cancel(self, request):
        return cancel_job(self, request)

    def recover(self, request):
        return recover_job(self, request)
