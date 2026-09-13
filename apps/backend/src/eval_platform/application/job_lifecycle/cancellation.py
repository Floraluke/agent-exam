"""Authorize and persist cancellation without impersonation or eager stopping."""

import hashlib
import re
from collections.abc import Callable
from datetime import UTC, datetime

from eval_platform.application.ports.repositories import JobRepository
from eval_platform.domain.identity import AuthenticatedActor
from eval_platform.domain.jobs.cancellation import (
    CancellationRequest,
    CancellationResult,
    cancel_request_sha,
    normalize_cancel_reason,
)
from eval_platform.domain.jobs.models import JobInputError, JobNotFound

_KEY = re.compile(r"[A-Za-z0-9._~-]{8,128}")


class JobCancellation:
    def __init__(
        self,
        repository: JobRepository,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self.repository = repository
        self.clock = clock

    def cancel(
        self,
        actor: AuthenticatedActor,
        job_id: str,
        reason: str | None,
        idempotency_key: str,
    ) -> CancellationResult:
        if not _KEY.fullmatch(idempotency_key):
            raise JobInputError("IDEMPOTENCY_KEY_INVALID")
        record = self.repository.get(job_id)
        if actor.role != "owner" and record.created_by != actor.user_id:
            raise JobNotFound
        reason = normalize_cancel_reason(reason)
        return self.repository.cancel(
            CancellationRequest(
                job_id,
                actor.user_id,
                reason,
                self.clock(),
                hashlib.sha256(idempotency_key.encode()).hexdigest(),
                cancel_request_sha(reason),
            )
        )
