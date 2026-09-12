"""Owner decision values and safe conflict categories."""

import hashlib
import json
import unicodedata
from dataclasses import dataclass
from datetime import datetime
from typing import Literal

from eval_platform.domain.jobs.models import JobError, JobInputError

DecisionKind = Literal["approve", "reject"]


class OwnerApprovalRequired(JobError):
    pass


class JobStateConflict(JobError):
    pass


def normalize_decision_reason(reason: str | None) -> str | None:
    if reason is None:
        return None
    if any(unicodedata.category(character) == "Cc" for character in reason):
        raise JobInputError("DECISION_REASON_INVALID")
    normalized = reason.strip()
    if not 1 <= len(normalized) <= 500:
        raise JobInputError("DECISION_REASON_INVALID")
    return normalized


@dataclass(frozen=True, slots=True)
class OwnerDecision:
    job_id: str
    actor_user_id: str
    kind: DecisionKind
    reason: str | None
    decided_at: datetime
    idempotency_key_hash: str
    request_sha256: str


def decision_request_sha(kind: DecisionKind, reason: str | None) -> str:
    body = json.dumps(
        {"decision": kind, "reason": reason},
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    return hashlib.sha256(body.encode()).hexdigest()
