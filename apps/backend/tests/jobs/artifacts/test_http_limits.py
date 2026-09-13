from datetime import UTC, datetime

from identity.conftest import WRITE_HEADERS

from eval_platform.application.execute_job import JobExecutor
from eval_platform.delivery.worker.main import WorkerShell
from eval_platform.domain.result import (
    DeterministicResult,
    ExecutionTrialResult,
    TerminationReason,
)
from jobs.execution.support.fakes import artifact
from jobs.test_http import submission, submit


class LimitBackend:
    def __init__(self, store, content):
        self.store, self.content = store, content

    def execute(self, request, progress=None):
        run_id = request.runs[0].run_id
        assert progress is not None and progress.trial_started(run_id)
        patch = artifact(
            self.store,
            run_id,
            "agent_patch",
            b"diff --git a/a b/a\n",
            "text/x-diff",
        )
        config = artifact(
            self.store, run_id, "harbor_trial_config", self.content, "application/json"
        )
        result = artifact(
            self.store, run_id, "harbor_trial_result", self.content, "application/json"
        )
        progress.trial_finished(run_id)
        return (
            ExecutionTrialResult(
                run_id,
                "harbor-job-limit",
                "harbor-trial-limit",
                TerminationReason.COMPLETED,
                patch,
                None,
                config,
                result,
            ),
        )


class LimitEvaluator:
    def __init__(self, store, content):
        self.store, self.content = store, content

    def evaluate(self, request):
        run_id = request.run_id
        report = artifact(
            self.store, run_id, "harness_report", self.content, "application/json"
        )
        output = artifact(
            self.store, run_id, "harness_test_output", self.content, "text/plain"
        )
        extra = artifact(self.store, run_id, "harness_log", self.content, "text/plain")
        return DeterministicResult(
            run_id,
            True,
            True,
            report,
            (output, extra),
            {"FAIL_TO_PASS": {"success": 0, "failure": 1}},
        )


class OversizedTrajectoryBackend:
    def __init__(self, store, trajectory):
        self.store, self.trajectory = store, trajectory

    def execute(self, request, progress=None):
        run_id = request.runs[0].run_id
        assert progress is not None and progress.trial_started(run_id)
        patch = artifact(
            self.store,
            run_id,
            "agent_patch",
            b"diff --git a/a b/a\n",
            "text/x-diff",
        )
        trajectory = artifact(
            self.store,
            run_id,
            "agent_trajectory",
            self.trajectory,
            "application/json",
        )
        progress.trial_finished(run_id)
        return (
            ExecutionTrialResult(
                run_id,
                "harbor-job-large-trajectory",
                "harbor-trial-large-trajectory",
                TerminationReason.COMPLETED,
                patch,
                trajectory,
            ),
        )


def test_raw_run_over_limit_is_visible_without_losing_core_result(
    internal_reports_api,
):
    api = internal_reports_api
    api.login()
    task, agent = api.register_catalogs()
    created = submit(
        api,
        submission(task["task_id"], agent["agent_configuration_id"]),
        "artifact-limit-source-0001",
    ).json()
    api.client.post(
        f"/api/v1/jobs/{created['job_id']}/approve",
        json={},
        headers={**WRITE_HEADERS, "Idempotency-Key": "artifact-limit-approve-0001"},
    )
    content = b"x" * (50 * 1024 * 1024)
    now = datetime(2026, 9, 13, 9, 0, tzinfo=UTC)
    executor = JobExecutor(
        api.repository,
        api.run_artifacts,
        LimitBackend(api.run_artifacts, content),
        LimitEvaluator(api.run_artifacts, content),
        api.jobs.tasks.source,
        lambda: now,
    )
    assert WorkerShell(api.repository, executor, lambda: now).run_once(
        "artifact-limit-worker"
    )

    response = api.client.get(f"/api/v1/reports/runs/{created['run_ids'][0]}")

    assert response.status_code == 200
    body = response.json()
    assert body["deterministic_result"]["resolved"] is True
    assert body["run"]["warnings"] == ["RAW_ARTIFACT_RUN_LIMIT_EXCEEDED"]
    raw = [
        item for item in body["artifact_links"] if item["retention_class"] == "raw_30d"
    ]
    assert sum(item["size_bytes"] for item in raw) == 200 * 1024 * 1024
    assert "harness_log_raw" not in {item["artifact_type"] for item in raw}


def test_oversized_trajectory_is_truncated_without_failing_core_result(
    internal_reports_api,
):
    api = internal_reports_api
    api.login()
    task, agent = api.register_catalogs()
    created = submit(
        api,
        submission(task["task_id"], agent["agent_configuration_id"]),
        "artifact-large-trajectory-source-0001",
    ).json()
    api.client.post(
        f"/api/v1/jobs/{created['job_id']}/approve",
        json={},
        headers={
            **WRITE_HEADERS,
            "Idempotency-Key": "artifact-large-trajectory-approve-0001",
        },
    )
    trajectory = b"x" * (50 * 1024 * 1024 + 1)
    now = datetime(2026, 9, 13, 10, 0, tzinfo=UTC)
    executor = JobExecutor(
        api.repository,
        api.run_artifacts,
        OversizedTrajectoryBackend(api.run_artifacts, trajectory),
        LimitEvaluator(api.run_artifacts, b"{}"),
        api.jobs.tasks.source,
        lambda: now,
    )

    assert WorkerShell(api.repository, executor, lambda: now).run_once(
        "artifact-large-trajectory-worker"
    )
    response = api.client.get(f"/api/v1/reports/runs/{created['run_ids'][0]}")

    assert response.status_code == 200
    body = response.json()
    assert body["deterministic_result"]["resolved"] is True
    assert "PUBLIC_TRAJECTORY_RAW_LIMIT_EXCEEDED" in body["run"]["warnings"]
    artifacts = body["artifact_links"]
    raw = next(
        item for item in artifacts if item["artifact_type"] == "agent_trajectory"
    )
    assert raw["truncated"] is True
    assert raw["size_bytes"] == 50 * 1024 * 1024
    assert raw["original_size_bytes"] == len(trajectory)
    assert "public_trajectory" not in {item["artifact_type"] for item in artifacts}
