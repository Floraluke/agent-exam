from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, SecretStr


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    username: str = Field(
        min_length=3, max_length=64, pattern=r"^[a-z0-9][a-z0-9_.-]+$"
    )
    password: SecretStr = Field(min_length=1, max_length=128)


class ActorResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    user_id: str
    username: str
    role: Literal["owner", "collaborator"]


class EmptyRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ErrorDetails(BaseModel):
    model_config = ConfigDict(extra="forbid")
    code: str
    message: str
    details: dict[str, object]
    request_id: str


class ApiError(BaseModel):
    model_config = ConfigDict(extra="forbid")
    error: ErrorDetails


def error_responses(*statuses: int) -> dict[int | str, dict[str, object]]:
    responses: dict[int | str, dict[str, object]] = {
        status: {"model": ApiError, "description": "统一安全错误"}
        for status in statuses
    }
    if 429 in responses:
        responses[429]["headers"] = {
            "Retry-After": {"schema": {"type": "string"}, "description": "等待秒数"}
        }
    return responses
