from collections import deque
from threading import Lock
from time import monotonic

from fastapi import Request

from eval_platform.delivery.http.config import HttpConfig


def trusted_write(request: Request, config: HttpConfig) -> bool:
    return (
        request.headers.get("origin") == config.public_origin
        and request.headers.get("x-agentexam-request") == "1"
    )


class LoginLimiter:
    """A bounded, per-process budget; not a distributed abuse-prevention system."""

    def __init__(self) -> None:
        self._attempts: deque[float] = deque()
        self._lock = Lock()

    def allow(self) -> bool:
        with self._lock:
            now = monotonic()
            while self._attempts and self._attempts[0] <= now - 60:
                self._attempts.popleft()
            if len(self._attempts) >= 10:
                return False
            self._attempts.append(now)
            return True
