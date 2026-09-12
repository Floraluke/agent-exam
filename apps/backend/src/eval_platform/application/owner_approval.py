"""Authorize and record an owner decision without starting execution."""

import hashlib
import re
from collections.abc import Callable
from datetime import UTC, datetime

from eval_platform.application.ports.repositories import JobRepository
from eval_platform.domain.identity import AuthenticatedActor
from eval_platform.domain.jobs.decisions import (
    DecisionKind,
    OwnerApprovalRequired,
    OwnerDecision,
    decision_request_sha,
    normalize_decision_reason,
)
from eval_platform.domain.jobs.models import EvaluationJob, JobInputError

_KEY = re.compile(r"[A-Za-z0-9._~-]{8,128}")


class OwnerApproval:
    def __init__(
        self,
        repository: JobRepository,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self.repository = repository
        self.clock = clock

    def decide(
        self,
        actor: AuthenticatedActor,
        job_id: str,
        kind: DecisionKind,
        reason: str | None,
        idempotency_key: str,
    ) -> EvaluationJob:
        if actor.role != "owner":
            raise OwnerApprovalRequired
        if not _KEY.fullmatch(idempotency_key):
            raise JobInputError("IDEMPOTENCY_KEY_INVALID")
        reason = normalize_decision_reason(reason)
        return self.repository.decide(
            OwnerDecision(
                job_id,
                actor.user_id,
                kind,
                reason,
                self.clock(),
                hashlib.sha256(idempotency_key.encode()).hexdigest(),
                decision_request_sha(kind, reason),
            )
        )
