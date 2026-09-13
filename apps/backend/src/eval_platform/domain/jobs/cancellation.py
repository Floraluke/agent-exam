"""Trusted cancellation values and safe request normalization."""

import hashlib
import json
import unicodedata
from dataclasses import dataclass
from datetime import datetime

from eval_platform.domain.jobs.models import JobInputError


def normalize_cancel_reason(reason: str | None) -> str | None:
    if reason is None:
        return None
    if any(unicodedata.category(character) == "Cc" for character in reason):
        raise JobInputError("CANCEL_REASON_INVALID")
    normalized = reason.strip()
    if not 1 <= len(normalized) <= 500:
        raise JobInputError("CANCEL_REASON_INVALID")
    return normalized


def cancel_request_sha(reason: str | None) -> str:
    body = json.dumps(
        {"reason": reason}, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    )
    return hashlib.sha256(body.encode()).hexdigest()


@dataclass(frozen=True, slots=True)
class CancellationRequest:
    job_id: str
    actor_user_id: str
    reason: str | None
    requested_at: datetime
    idempotency_key_hash: str
    request_sha256: str
