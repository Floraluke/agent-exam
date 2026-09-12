from typing import Protocol

from eval_platform.domain.task import TaskBundle


class TaskSource(Protocol):
    """Load only fixed, verified source data; hidden fields remain separate."""

    def load(self, instance_id: str) -> TaskBundle: ...
