from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from eval_platform.adapters.execution.codex.install import prepare_codex_bundle
from eval_platform.adapters.execution.harbor.config_mapper import (
    HarborJobPlan,
    build_job_plan,
    process_timeout_sec,
    validate_job_id,
)
from eval_platform.adapters.execution.harbor.lifecycle.cleanup import (
    cleanup_timed_out_projects,
)
from eval_platform.adapters.execution.harbor.lifecycle.monitor import (
    HarborProgressMonitor,
)
from eval_platform.adapters.execution.harbor.process_runner import run_bounded_process
from eval_platform.adapters.execution.harbor.result_mapper import map_job_results
from eval_platform.adapters.execution.harbor.result_values import process_start_failure
from eval_platform.adapters.execution.harbor_entry import (
    harbor_command,
    harbor_environment,
)
from eval_platform.adapters.execution.network import validate_hosts
from eval_platform.adapters.tasks.swe_gym import render_harbor_task
from eval_platform.application.ports.execution import (
    ExecutionJobRequest,
    ExecutionProgressObserver,
    RunLimits,
)
from eval_platform.domain.result import ExecutionTrialResult, TerminationReason
from eval_platform.domain.task import EvaluationTask

TaskRenderer = Callable[[EvaluationTask, Path, RunLimits], Path]


@dataclass(frozen=True, slots=True)
class HarborExecutionAdapter:
    harbor_executable: Path
    evidence_root: Path
    project_root: Path
    task_renderer: TaskRenderer = render_harbor_task
    network_hosts: tuple[str, ...] = ()
    codex_archive: Path | None = field(default=None, repr=False)
    codex_auth_path: Path | None = field(default=None, repr=False)

    def __post_init__(self) -> None:
        validate_hosts(self.network_hosts)
        if (self.codex_archive is None) != (self.codex_auth_path is None):
            raise ValueError("CODEX_RUNTIME_BINDING_INCOMPLETE")
        if not self.harbor_executable.is_file() or self.harbor_executable.is_symlink():
            raise FileNotFoundError("The fixed Harbor executable is unavailable")
        if not self.project_root.is_dir():
            raise NotADirectoryError("The Harbor project root is unavailable")

    def execute(
        self,
        request: ExecutionJobRequest,
        progress: ExecutionProgressObserver | None = None,
    ) -> tuple[ExecutionTrialResult, ...]:
        validate_job_id(request.job_id)
        run_root = self.evidence_root.resolve() / request.job_id
        if run_root.exists():
            raise FileExistsError(
                f"Refusing to overwrite execution evidence: {run_root}"
            )
        run_root.mkdir(parents=True, mode=0o700)
        bundle_root = None
        if self.codex_archive is not None:
            bundle_root = run_root / "codex-input"
            prepare_codex_bundle(self.codex_archive, bundle_root)
        task_dirs = self._render_tasks(request, run_root / "tasks")
        plan = build_job_plan(
            request,
            jobs_dir=run_root / "jobs",
            task_dirs=task_dirs,
            network_hosts=self.network_hosts,
        )
        config_path = run_root / "harbor-config.json"
        config_path.write_text(
            json.dumps(plan.config, indent=2, sort_keys=True),
            encoding="utf-8",
            newline="\n",
        )
        return self._run(plan, request, run_root, config_path, bundle_root, progress)

    def _render_tasks(
        self,
        request: ExecutionJobRequest,
        root: Path,
    ) -> dict[str, Path]:
        tasks: dict[str, EvaluationTask] = {}
        rendered: dict[str, Path] = {}
        for run in request.runs:
            previous = tasks.get(run.task.instance_id)
            if previous is not None and previous != run.task:
                raise ValueError("A task identity maps to conflicting snapshots")
            if previous is None:
                tasks[run.task.instance_id] = run.task
                rendered[run.task.instance_id] = self.task_renderer(
                    run.task, root, request.limits
                )
        return rendered

    def _run(
        self,
        plan: HarborJobPlan,
        request: ExecutionJobRequest,
        run_root: Path,
        config_path: Path,
        bundle_root: Path | None,
        progress: ExecutionProgressObserver | None,
    ) -> tuple[ExecutionTrialResult, ...]:
        env = harbor_environment(
            auth_path=self.codex_auth_path, bundle_root=bundle_root
        )
        command = harbor_command(self.harbor_executable, config_path)
        job_dir = _job_dir(plan, request.job_id)
        monitor = HarborProgressMonitor(plan, job_dir, progress)
        try:
            outcome = run_bounded_process(
                command,
                cwd=self.project_root.resolve(),
                env=env,
                timeout_sec=process_timeout_sec(request),
                evidence_root=run_root,
                on_poll=monitor.scan,
            )
            monitor.scan()
        except Exception:
            cleanup_timed_out_projects(job_dir)
            raise
        if outcome.start_error is not None:
            return process_start_failure(request, outcome.start_error, outcome.warnings)
        process_warnings = outcome.warnings
        if outcome.timed_out:
            process_warnings += cleanup_timed_out_projects(job_dir)
        return map_job_results(
            plan,
            job_dir,
            process_returncode=outcome.returncode,
            process_failure_reason=(
                TerminationReason.TIMED_OUT if outcome.timed_out else None
            ),
            process_warnings=process_warnings,
        )


def _job_dir(plan: HarborJobPlan, job_id: str) -> Path:
    return Path(str(plan.config["jobs_dir"])) / job_id
