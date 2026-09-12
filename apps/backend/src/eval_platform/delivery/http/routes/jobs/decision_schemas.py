"""Strict owner-decision HTTP input."""

from pydantic import BaseModel, ConfigDict, field_validator

from eval_platform.domain.jobs.decisions import normalize_decision_reason
from eval_platform.domain.jobs.models import JobInputError


class OwnerDecisionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    reason: str | None = None

    @field_validator("reason")
    @classmethod
    def reject_control_characters(cls, value: str | None) -> str | None:
        try:
            return normalize_decision_reason(value)
        except JobInputError:
            raise ValueError("Decision reason is invalid") from None
