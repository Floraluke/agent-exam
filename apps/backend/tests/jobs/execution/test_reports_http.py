from datetime import UTC, datetime

from identity.conftest import WRITE_HEADERS

from eval_platform.application.execute_job import JobExecutor
from eval_platform.delivery.worker.main import WorkerShell
from jobs.execution.support.fakes import Backend, Evaluator, FailingEvaluator
from jobs.test_http import submission, submit
from jobs.test_security import invite


def test_http_submission_approval_worker_and_layered_reports(internal_reports_api):
    jobs_api = internal_reports_api
    assert jobs_api.login().status_code == 200
    task, agent = jobs_api.register_catalogs()
    created = submit(
        jobs_api,
        submission(task["task_id"], agent["agent_configuration_id"]),
        "report-http-source-0001",
    ).json()
    approved = jobs_api.client.post(
        f"/api/v1/jobs/{created['job_id']}/approve",
        json={},
        headers={**WRITE_HEADERS, "Idempotency-Key": "report-http-approve-0001"},
    )
    assert approved.status_code == 200
    artifacts = jobs_api.run_artifacts
    backend = Backend(artifacts, b"diff --git a/a.py b/a.py\n--- a/a.py\n+++ b/a.py\n")
    evaluator = Evaluator(artifacts)
    now = datetime(2026, 9, 12, 12, 0, tzinfo=UTC)
    executor = JobExecutor(
        jobs_api.repository,
        artifacts,
        backend,
        evaluator,
        jobs_api.jobs.tasks.source,
        lambda: now,
    )
    assert WorkerShell(jobs_api.repository, executor, lambda: now).run_once(
        "http-worker"
    )

    job = jobs_api.client.get(f"/api/v1/reports/jobs/{created['job_id']}")
    run_id = created["run_ids"][0]
    run = jobs_api.client.get(f"/api/v1/reports/runs/{run_id}")
    assert job.status_code == run.status_code == 200
    assert job.json()["runs"][0]["report_path"].endswith(run_id)
    body = run.json()
    assert body["deterministic_result"]["resolved"] is True
    assert body["judge_analyses"] == []
    assert body["human_review"] is None
    assert body["quality_tiebreak"] is None
    assert body["review_status"] == "NOT_REQUIRED"
    assert {item["artifact_type"] for item in body["artifact_links"]} == {
        "agent_patch",
        "harness_report",
        "harness_test_output",
    }
    assert all("object_key" not in item for item in body["artifact_links"])
    report_schema = jobs_api.client.get("/openapi.json").json()["components"][
        "schemas"
    ]["RunReportResponse"]
    assert report_schema["properties"]["process_metrics"]["$ref"].endswith(
        "ProcessMetricsResponse"
    )
    assert "object_key" not in jobs_api.client.get("/openapi.json").text
    missing_key = next(iter(artifacts.content))
    artifacts.content.pop(missing_key)
    unavailable = jobs_api.client.get(f"/api/v1/reports/runs/{run_id}")
    assert unavailable.status_code == 503
    assert unavailable.json()["error"]["code"] == "DEPENDENCY_UNAVAILABLE"


def test_report_requires_identity_and_hides_unknown_run(jobs_api):
    missing = "00000000-0000-4000-8000-000000000001"
    response = jobs_api.client.get(f"/api/v1/reports/runs/{missing}")
    assert response.status_code == 401
    assert jobs_api.login().status_code == 200
    response = jobs_api.client.get(f"/api/v1/reports/runs/{missing}")
    assert response.status_code == 404


def test_batch_report_exposes_safe_identity_stage_and_partial_matrix(
    internal_reports_api,
):
    jobs_api = internal_reports_api
    jobs_api.login()
    first, agent = jobs_api.register_catalogs()
    second = jobs_api.register_task("verified-task-2")
    other_agent = jobs_api.register_agent("verified-codex-2")
    body = submission(first["task_id"], agent["agent_configuration_id"])
    body["task_ids"] = [first["task_id"], second["task_id"]]
    body["agent_configuration_ids"] = [
        agent["agent_configuration_id"],
        other_agent["agent_configuration_id"],
    ]
    created = submit(jobs_api, body, "batch-report-source-0001").json()
    jobs_api.client.post(
        f"/api/v1/jobs/{created['job_id']}/approve",
        json={},
        headers={**WRITE_HEADERS, "Idempotency-Key": "batch-report-approve-0001"},
    )
    frozen = jobs_api.repository.get(created["job_id"])
    failed = min(run.run_id for run in frozen.runs)
    artifacts = jobs_api.run_artifacts
    now = datetime(2026, 9, 12, 13, 30, tzinfo=UTC)
    executor = JobExecutor(
        jobs_api.repository,
        artifacts,
        Backend(artifacts, b"diff --git a/a b/a\n"),
        FailingEvaluator(artifacts, {failed}),
        jobs_api.jobs.tasks.source,
        lambda: now,
    )
    assert WorkerShell(jobs_api.repository, executor, lambda: now).run_once(
        "batch-http-worker"
    )

    response = jobs_api.client.get(f"/api/v1/reports/jobs/{created['job_id']}")
    assert response.status_code == 200
    report = response.json()
    assert report["status"] == "COMPLETED_WITH_ERRORS"
    assert report["failure_code"] == "BATCH_PARTIAL_FAILURE"
    assert report["completed_runs"] == 3
    assert report["failed_runs"] == 1
    assert {run["outcome"] for run in report["runs"]} == {
        "resolved",
        "infrastructure_error",
    }
    assert {run["task_instance_id"] for run in report["runs"]} == {
        "example__repo-1",
        "example__repo-2",
    }
    expected = [
        (run.task.instance_id, run.agent.agent_configuration_id)
        for run in sorted(
            frozen.runs,
            key=lambda run: (
                run.task.task_id,
                run.agent.agent_configuration_id,
                run.run_id,
            ),
        )
    ]
    assert [
        (run["task_instance_id"], run["agent_configuration_id"])
        for run in report["runs"]
    ] == expected
    assert all("log" not in run["stage_message"].lower() for run in report["runs"])


def test_run_report_uses_the_same_owner_or_creator_scope(internal_reports_api):
    jobs_api = internal_reports_api
    jobs_api.login()
    task, agent = jobs_api.register_catalogs()
    invite(jobs_api, "report_creator")
    jobs_api.login("report_creator", "synthetic teammate password")
    created = submit(
        jobs_api,
        submission(task["task_id"], agent["agent_configuration_id"]),
        "report-scope-source-0001",
    ).json()
    jobs_api.client.post("/api/v1/auth/logout", json={}, headers=WRITE_HEADERS)
    jobs_api.login()
    approved = jobs_api.client.post(
        f"/api/v1/jobs/{created['job_id']}/approve",
        json={},
        headers={**WRITE_HEADERS, "Idempotency-Key": "report-scope-approve-0001"},
    )
    assert approved.status_code == 200
    artifacts = jobs_api.run_artifacts
    now = datetime(2026, 9, 12, 13, 0, tzinfo=UTC)
    executor = JobExecutor(
        jobs_api.repository,
        artifacts,
        Backend(artifacts, b"diff --git a/a b/a\n"),
        Evaluator(artifacts),
        jobs_api.jobs.tasks.source,
        lambda: now,
    )
    assert WorkerShell(jobs_api.repository, executor, lambda: now).run_once(
        "scope-worker"
    )
    run_path = f"/api/v1/reports/runs/{created['run_ids'][0]}"
    assert jobs_api.client.get(run_path).status_code == 200

    invite(jobs_api, "report_other")
    jobs_api.login("report_other", "synthetic teammate password")
    assert jobs_api.client.get(run_path).status_code == 404
    jobs_api.client.post("/api/v1/auth/logout", json={}, headers=WRITE_HEADERS)
    jobs_api.login("report_creator", "synthetic teammate password")
    assert jobs_api.client.get(run_path).status_code == 200
