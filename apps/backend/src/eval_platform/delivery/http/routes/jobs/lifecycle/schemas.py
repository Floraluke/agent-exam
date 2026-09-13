from pydantic import BaseModel, ConfigDict


class EmptyLifecycleRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
