"""Strict owner-decision HTTP input."""

from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, field_validator

from eval_platform.domain.jobs.decisions import normalize_decision_reason
from eval_platform.domain.jobs.models import JobInputError


class OwnerDecisionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    reason: (
        Annotated[
            str,
            Field(
                description="Trimmed before validating normalized Unicode length.",
                json_schema_extra={
                    "x-normalization": "trim",
                    "x-normalizedMinLength": 1,
                    "x-normalizedMaxLength": 500,
                },
            ),
        ]
        | None
    ) = None

    @field_validator("reason", mode="before")
    @classmethod
    def reject_control_characters(cls, value: object) -> object:
        if not isinstance(value, str):
            return value
        try:
            return normalize_decision_reason(value)
        except JobInputError:
            raise ValueError("Decision reason is invalid") from None
