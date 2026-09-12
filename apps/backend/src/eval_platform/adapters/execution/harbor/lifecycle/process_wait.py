import subprocess
import time
from collections.abc import Callable

_POLL_INTERVAL_SEC = 0.1


def wait_bounded(
    process: subprocess.Popen[bytes],
    timeout_sec: int | float,
    on_poll: Callable[[], None] | None,
) -> bool:
    deadline = time.monotonic() + timeout_sec
    while process.poll() is None:
        if on_poll is not None:
            on_poll()
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            return True
        try:
            process.wait(timeout=min(_POLL_INTERVAL_SEC, remaining))
        except subprocess.TimeoutExpired:
            continue
    if on_poll is not None:
        on_poll()
    return False
