"""Owner command control; production composition stays in runtime.py."""

import argparse
import json
import sys
from collections.abc import Callable
from pathlib import Path
from time import sleep

from eval_platform.delivery.worker.main import WorkerShell


def run_command(
    argv: list[str] | None,
    worker_factory: Callable[[], WorkerShell],
    *,
    wait: Callable[[float], None] = sleep,
) -> int:
    parser = argparse.ArgumentParser(description="AgentExam 本机正式 Worker")
    parser.add_argument("worker_id")
    parser.add_argument("--loop", action="store_true")
    parser.add_argument("--stop-file", type=Path)
    arguments = parser.parse_args(argv)
    stop_file: Path | None = arguments.stop_file
    if arguments.loop:
        if stop_file is None or not stop_file.is_absolute():
            parser.error("--loop requires an absolute --stop-file")
    elif stop_file is not None:
        parser.error("--stop-file requires --loop")
    try:
        if stop_file is not None and _stop_requested(stop_file):
            print(json.dumps({"status": "worker_stopped", "completed_cycles": 0}))
            return 0
        worker = worker_factory()
        completed_cycles = 0
        while True:
            if stop_file is not None and _stop_requested(stop_file):
                print(
                    json.dumps(
                        {
                            "status": "worker_stopped",
                            "completed_cycles": completed_cycles,
                        }
                    )
                )
                return 0
            worked = worker.run_once(arguments.worker_id)
            if not arguments.loop:
                print(
                    json.dumps({"status": "worker_cycle_finished", "claimed": worked})
                )
                return 0
            completed_cycles += int(worked)
            if not worked:
                wait(1.0)
    except Exception:
        print(json.dumps({"status": "worker_cycle_unavailable"}), file=sys.stderr)
        return 2


def _stop_requested(path: Path) -> bool:
    try:
        path.lstat()
    except FileNotFoundError:
        if not path.parent.is_dir():
            raise ValueError("WORKER_STOP_DIRECTORY_UNAVAILABLE") from None
        return False
    return True
