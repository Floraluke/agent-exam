"""Explicitly gated synthetic HTTP server for browser wiring tests only."""

import os
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path
from threading import Event, Thread
from time import sleep

from catalog.conftest import task_bundle
from catalog.memory import (
    FixedSource,
    MemoryAgents,
    MemoryTasks,
)
from catalog.memory import (
    MemoryArtifacts as CatalogArtifacts,
)
from jobs.execution.support.fakes import Backend, Evaluator, FailedBackend
from jobs.execution.support.fakes import MemoryArtifacts as RunArtifacts
from jobs.execution.support.memory import ExecutableMemoryJobs
from leaderboard.browser_repository import BrowserLeaderboardRepository
from membership.memory import MemoryMembershipRepository

from eval_platform.adapters.identity.passwords import Argon2Passwords
from eval_platform.application.agent_registry import AgentRegistry
from eval_platform.application.execute_job import JobExecutor
from eval_platform.application.identity import IdentityService
from eval_platform.application.job_lifecycle.cancellation import JobCancellation
from eval_platform.application.job_lifecycle.recovery import JobRecovery
from eval_platform.application.job_lifecycle.retention import ArtifactRetention
from eval_platform.application.job_submission import JobSubmission
from eval_platform.application.membership import MembershipService
from eval_platform.application.owner_approval import OwnerApproval
from eval_platform.application.reporting import JobReporting, LeaderboardReporting
from eval_platform.application.task_catalog import TaskCatalog
from eval_platform.delivery.http.app import create_app
from eval_platform.delivery.http.config import HttpConfig
from eval_platform.delivery.job_presets import submission_policy
from eval_platform.delivery.worker.main import WorkerShell
from eval_platform.domain.agent import AgentConfiguration

if os.environ.get("AGENTEXAM_IDENTITY_BROWSER_TEST") != "1":
    raise RuntimeError("Synthetic identity server requires the browser-test gate")


class BrowserBackend(Backend):
    def execute(self, request, progress=None):
        # 故障注入：下一条真正执行的 Run 以失败收束，码与文案由控制端点给定。
        if forced_failure:
            return FailedBackend.execute(self, request, progress)
        results = super().execute(request, progress)
        return tuple(
            replace(item, usage=replace(item.usage, n_cache_tokens=None))
            if item.usage is not None
            else item
            for item in results
        )


def browser_clock():
    clock_file = (
        Path(__file__).resolve().parents[4] / "runtime/tests/identity-browser-clock.txt"
    )
    try:
        offset = int(clock_file.read_text(encoding="ascii"))
    except FileNotFoundError:
        offset = 0
    if not 0 <= offset <= 28800:
        raise ValueError("Browser-test clock offset is outside the test boundary")
    return datetime.now(UTC) + timedelta(seconds=offset)


repository = MemoryMembershipRepository()
passwords = Argon2Passwords()
service = IdentityService(repository, passwords, browser_clock)
browser_owner = service.bootstrap_owner("owner", "synthetic browser password")
task_source = FixedSource(task_bundle())
# 任务 04：夹具扩到六题与两个配置；这些 preset 只有被 spec 显式登记后才进入
# 目录，因此不会改变既有 spec 看到的数量。
for _index in range(2, 7):
    task_source.bundles[f"example__repo-{_index}"] = task_bundle(
        f"example__repo-{_index}"
    )
task_repository = MemoryTasks()
tasks = TaskCatalog(
    task_repository,
    CatalogArtifacts(),
    task_source,
    {
        "swe-gym-lite-mypy-15413": "example__repo-1",
        "swe-gym-lite-example-2": "example__repo-2",
        "swe-gym-lite-example-3": "example__repo-3",
        "swe-gym-lite-example-4": "example__repo-4",
        "swe-gym-lite-example-5": "example__repo-5",
        "swe-gym-lite-example-6": "example__repo-6",
    },
)


def _codex(display: str, preset: str, model: str, effort: str, reference: str):
    return display, AgentConfiguration(
        preset,
        "codex",
        "test-version",
        "openai_chatgpt",
        model,
        "chatgpt_auth_json",
        reference,
        {"reasoning_effort": effort},
    )


agents = AgentRegistry(
    MemoryAgents(),
    {
        "codex-0153-terra-medium": _codex(
            "Synthetic Codex",
            "test-preset",
            "test-model",
            "medium",
            "private-test-reference",
        ),
        # 第二个配置的显示名刻意不含 "Synthetic Codex"：既有助手的子串
        # 匹配会因此变成歧义定位。
        "codex-0153-terra-low": _codex(
            "Synthetic Terra",
            "test-preset-2",
            "test-model-2",
            "low",
            "private-test-reference-2",
        ),
    },
)
job_repository = ExecutableMemoryJobs()
jobs = JobSubmission(
    tasks,
    agents,
    job_repository,
    submission_policy("internal_test"),
    browser_clock,
)
run_artifacts = RunArtifacts()
worker = WorkerShell(
    job_repository,
    JobExecutor(
        job_repository,
        run_artifacts,
        BrowserBackend(
            run_artifacts,
            b"diff --git a/a.py b/a.py\n--- a/a.py\n+++ b/a.py\n",
            trial_delay_sec=0.75,
        ),
        Evaluator(run_artifacts),
        tasks.source,
        browser_clock,
    ),
    browser_clock,
)
app = create_app(
    service,
    HttpConfig(public_origin="https://127.0.0.1:3100"),
    MembershipService(repository, passwords, browser_clock),
    tasks,
    agents,
    jobs,
    OwnerApproval(job_repository, browser_clock),
    JobReporting(
        job_repository,
        run_artifacts,
        lambda scope: scope == "internal_test",
    ),
    JobCancellation(job_repository, browser_clock),
    JobRecovery(job_repository, jobs, browser_clock),
    LeaderboardReporting(
        BrowserLeaderboardRepository(task_repository, job_repository, browser_clock)
    ),
)

worker_enabled = Event()
worker_enabled.set()


@app.post("/__test__/worker/pause")
def pause_worker():
    worker_enabled.clear()
    return {"paused": True}


@app.post("/__test__/worker/resume")
def resume_worker():
    worker_enabled.set()
    return {"paused": False}


@app.post("/__test__/jobs/interrupt-next")
def interrupt_next_job():
    claimed = job_repository.claim("internal-browser-interrupted", browser_clock())
    if claimed is None:
        return {"job_id": None}
    with job_repository.lock:
        job_repository.records[claimed.job.job_id] = replace(
            claimed.job, lease_expires_at=browser_clock()
        )
    return {"job_id": claimed.job.job_id}


@app.post("/__test__/artifacts/expire-and-clean")
def expire_and_clean_artifacts():
    result = ArtifactRetention(job_repository, run_artifacts).cleanup(
        browser_owner,
        browser_clock() + timedelta(days=31),
    )
    return {
        "scanned": result.scanned,
        "deleted": result.deleted,
        "recovered": result.recovered,
    }


forced_failure: list[tuple[str, str]] = []
submitted_fail = job_repository.fail


def injected_fail(lease, run_id, code, summary, now, trial=None):
    # Run 失败码与失败文案的唯一落库点；注入只对下一次失败生效，取走即清空。
    code, summary = forced_failure.pop() if forced_failure else (code, summary)
    return submitted_fail(lease, run_id, code, summary, now, trial)


job_repository.fail = injected_fail


@app.post("/__test__/jobs/fail-next-run")
def fail_next_run(payload: dict[str, str]):
    forced_failure.append((payload["failure_code"], payload["failure_summary"]))
    return {"forced": True}


def run_synthetic_worker() -> None:
    while True:
        worker_enabled.wait()
        if not worker.run_once("internal-browser-worker"):
            sleep(0.05)


Thread(target=run_synthetic_worker, daemon=True).start()
