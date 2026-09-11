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
