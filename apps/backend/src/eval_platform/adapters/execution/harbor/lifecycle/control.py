"""Private per-execution files for cooperative Harbor Trial admission."""

import asyncio
import importlib
from pathlib import Path
from typing import Any


def ready_path(root: Path, index: int) -> Path:
    return root / f"ready-{index:04d}"


def permit_path(root: Path, index: int) -> Path:
    return root / f"permit-{index:04d}"


def stop_path(root: Path) -> Path:
    return root / "stop"


def signal(path: Path) -> None:
    path.touch(mode=0o600, exist_ok=False)


async def run_controlled_trials(
    job: Any,
    root: Path,
    loading_progress: Any,
    loading_progress_task: Any,
    _running_progress: Any = None,
) -> list[Any]:
    """Submit fixed single-concurrency Trials only after platform admission."""

    results: list[Any] = []
    for index, config in enumerate(job._remaining_trial_configs):
        signal(ready_path(root, index))
        while not permit_path(root, index).is_file():
            if stop_path(root).is_file():
                return results
            await asyncio.sleep(0.05)
        results.append(await job._trial_queue.submit(config))
        loading_progress.advance(loading_progress_task)
    return results


def install_controlled_runner(root: Path) -> None:
    async def run(job: Any, loading: Any, task: Any, running: Any = None) -> list[Any]:
        return await run_controlled_trials(job, root, loading, task, running)

    job_type = importlib.import_module("harbor.job").Job
    job_type._run_trials_with_queue = run
