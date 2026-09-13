import json
from pathlib import Path

from eval_platform.adapters.execution.harbor.config_mapper import HarborJobPlan
from eval_platform.adapters.execution.harbor.lifecycle.control import (
    permit_path,
    ready_path,
    signal,
    stop_path,
)
from eval_platform.adapters.execution.harbor.result_mapper import trial_key
from eval_platform.adapters.execution.harbor.result_values import read_json
from eval_platform.application.ports.execution import ExecutionProgressObserver


class HarborProgressMonitor:
    """Translate trusted per-Trial files into ordered platform identities."""

    def __init__(
        self,
        plan: HarborJobPlan,
        job_dir: Path,
        observer: ExecutionProgressObserver | None,
        control_dir: Path | None = None,
    ) -> None:
        self.plan, self.job_dir, self.observer = plan, job_dir, observer
        self.control_dir = control_dir
        self.started: set[str] = set()
        self.finished: set[str] = set()
        self.requested: set[str] = set()

    def scan(self) -> None:
        if self.observer is None:
            return
        discovered: dict[tuple[str, str], Path] = {}
        duplicates: set[tuple[str, str]] = set()
        for config_path in self.job_dir.glob("*/config.json"):
            try:
                key = trial_key({"config": read_json(config_path)})
            except (OSError, ValueError, json.JSONDecodeError):
                continue
            if key in discovered:
                duplicates.add(key)
            else:
                discovered[key] = config_path.parent
        for binding in self.plan.bindings:
            key = (binding.task_path_key, binding.agent_key)
            trial_dir = discovered.get(key)
            if trial_dir is None or key in duplicates:
                continue
            if binding.run_id not in self.started and self.control_dir is None:
                if not self.observer.trial_started(binding.run_id):
                    continue
                self.started.add(binding.run_id)
            if binding.run_id not in self.started:
                continue
            if binding.run_id in self.finished:
                continue
            try:
                result = read_json(trial_dir / "result.json")
                if trial_key(result) != key or not isinstance(result.get("id"), str):
                    continue
            except (OSError, ValueError, json.JSONDecodeError):
                continue
            self.observer.trial_finished(binding.run_id)
            self.finished.add(binding.run_id)
        if self.control_dir is not None:
            self._admit_ready_trials()

    def _admit_ready_trials(self) -> None:
        assert self.observer is not None and self.control_dir is not None
        for index, binding in enumerate(self.plan.bindings):
            if binding.run_id in self.requested:
                continue
            if not ready_path(self.control_dir, index).is_file():
                return
            allowed = self.observer.trial_started(binding.run_id)
            self.requested.add(binding.run_id)
            if allowed:
                self.started.add(binding.run_id)
                signal(permit_path(self.control_dir, index))
                continue
            signal(stop_path(self.control_dir))
            return
