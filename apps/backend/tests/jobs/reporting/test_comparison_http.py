"""任务 03 对比报告端点的 HTTP 契约测试（成功形状、权限、400 族、无泄漏）。"""

from datetime import UTC, datetime

from identity.conftest import WRITE_HEADERS
from jobs.execution.support import fakes
from jobs.test_http import submission, submit
from jobs.test_security import invite

from eval_platform.application.execute_job import JobExecutor
from eval_platform.delivery.worker.main import WorkerShell

PATCH = b"diff --git a/a.py b/a.py\n--- a/a.py\n+++ b/a.py\n@@ -1 +1 @@\n-bug\n+fix\n"


def _run_worker(jobs_api):
    artifacts = jobs_api.run_artifacts
    now = datetime(2026, 9, 20, 15, 0, tzinfo=UTC)
    executor = JobExecutor(
        jobs_api.repository,
        artifacts,
        fakes.Backend(artifacts, PATCH),
        fakes.Evaluator(artifacts),
        jobs_api.jobs.tasks.source,
        lambda: now,
    )
    assert WorkerShell(jobs_api.repository, executor, lambda: now).run_once(
        "comparison-worker"
    )


def _approve(jobs_api, job_id, key):
    response = jobs_api.client.post(
        f"/api/v1/jobs/{job_id}/approve",
        json={},
        headers={**WRITE_HEADERS, "Idempotency-Key": key},
    )
    assert response.status_code == 200


def _comparison(jobs_api, ids):
    return jobs_api.client.get(
        "/api/v1/reports/comparisons", params={"job_ids": ",".join(ids)}
    )


def test_comparison_endpoint_returns_matrix_with_missing_semantics(
    internal_reports_api,
):
    api = internal_reports_api
    api.login()
    first, agent = api.register_catalogs()
    second = api.register_task("verified-task-2")
    other_agent = api.register_agent("verified-codex-2")

    body = submission(first["task_id"], agent["agent_configuration_id"])
    body["task_ids"] = [first["task_id"], second["task_id"]]
    job_a = submit(api, body, "comparison-http-a-0001").json()
    _approve(api, job_a["job_id"], "comparison-approve-a-0001")
    _run_worker(api)

    job_b = submit(
        api,
        submission(first["task_id"], other_agent["agent_configuration_id"]),
        "comparison-http-b-0001",
    ).json()
    _approve(api, job_b["job_id"], "comparison-approve-b-0001")
    _run_worker(api)

    response = _comparison(api, [job_a["job_id"], job_b["job_id"]])
    assert response.status_code == 200
    body = response.json()
    assert [column["agent_display_name"] for column in body["columns"]] == [
        "Synthetic Codex 1",
        "Synthetic Codex 2",
    ]
    assert len(body["rows"]) == 2
    assert body["totals"][0]["resolved"] == 2
    assert body["totals"][0]["decided"] == 2 and body["totals"][0]["total"] == 2
    assert body["totals"][1]["resolved"] == 1 and body["totals"][1]["missing"] == 1
    assert body["totals"][1]["decided"] == 1 and body["totals"][1]["total"] == 2
    missing = [
        cell
        for row in body["rows"]
        for cell in row["cells"]
        if cell["outcome"] == "missing"
    ]
    assert len(missing) == 1
    assert missing[0]["resolved"] is None and missing[0]["report_path"] is None
    assert "object_key" not in response.text


def test_comparison_requires_session_and_hides_unknown_or_foreign_jobs(
    internal_reports_api,
):
    api = internal_reports_api
    assert _comparison(api, ["00000000-0000-0000-0000-000000000001"]).status_code == 401
    api.login()
    assert _comparison(api, ["00000000-0000-0000-0000-000000000001"]).status_code == 404

    task, agent = api.register_catalogs()
    owner_job = submit(
        api,
        submission(task["task_id"], agent["agent_configuration_id"]),
        "comparison-owner-0001",
    ).json()
    invite(api, "comparison_other")
    api.login("comparison_other", "synthetic teammate password")
    response = _comparison(api, [owner_job["job_id"]])
    assert response.status_code == 404


def test_comparison_rejects_empty_bad_and_oversized_selections(internal_reports_api):
    api = internal_reports_api
    api.login()
    empty = api.client.get("/api/v1/reports/comparisons", params={"job_ids": ""})
    assert empty.status_code == 400
    assert empty.json()["error"]["code"] == "EMPTY_COMPARISON_SELECTION"

    bad = _comparison(api, ["not-a-uuid"])
    assert bad.status_code == 400
    assert bad.json()["error"]["code"] == "INVALID_REQUEST"

    many = [f"00000000-0000-0000-0000-{index:012x}" for index in range(21)]
    oversized = _comparison(api, many)
    assert oversized.status_code == 400
    assert oversized.json()["error"]["code"] == "COMPARISON_LIMIT_EXCEEDED"

    unknown = api.client.get(
        "/api/v1/reports/comparisons",
        params={"job_ids": many[0], "unexpected": "1"},
    )
    assert unknown.status_code == 400
    assert unknown.json()["error"]["code"] == "INVALID_REQUEST"

    duplicate = api.client.get(
        "/api/v1/reports/comparisons",
        params=[("job_ids", many[0]), ("job_ids", many[1])],
    )
    assert duplicate.status_code == 400
    assert duplicate.json()["error"]["code"] == "INVALID_REQUEST"


def test_comparison_normalizes_uuid_before_deduplicating(internal_reports_api):
    api = internal_reports_api
    api.login()
    task, agent = api.register_catalogs()
    created = submit(
        api,
        submission(task["task_id"], agent["agent_configuration_id"]),
        "comparison-normalized-uuid-0001",
    ).json()

    job_id = created["job_id"]
    response = _comparison(api, [job_id.lower(), job_id.upper()])

    assert response.status_code == 200
    assert [column["job_id"] for column in response.json()["columns"]] == [job_id]
