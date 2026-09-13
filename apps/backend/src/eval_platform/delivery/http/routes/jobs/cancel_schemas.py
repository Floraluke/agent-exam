"""Strict Job cancellation HTTP input."""

from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, field_validator

from eval_platform.domain.jobs.cancellation import normalize_cancel_reason
from eval_platform.domain.jobs.models import JobInputError


class CancelRequest(BaseModel):
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
            return normalize_cancel_reason(value)
        except JobInputError:
            raise ValueError("Cancellation reason is invalid") from None
