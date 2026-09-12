"""Thread-safe synthetic adapter for the JobRepository port."""

from threading import Lock

from eval_platform.domain.jobs.models import JobIdempotencyConflict, JobNotFound


class MemoryJobs:
    def __init__(self):
        self.records = {}
        self.keys = {}
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
