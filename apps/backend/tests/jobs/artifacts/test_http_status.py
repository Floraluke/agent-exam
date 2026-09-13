from datetime import UTC, datetime

from identity.conftest import WRITE_HEADERS

from eval_platform.application.execute_job import JobExecutor
from eval_platform.delivery.worker.main import WorkerShell
from jobs.execution.support.fakes import Backend, Evaluator
from jobs.test_http import submission, submit


def test_completed_run_reports_public_and_restricted_artifact_states(
    internal_reports_api,
):
    api = internal_reports_api
    api.login()
    task, agent = api.register_catalogs()
    created = submit(
        api,
        submission(task["task_id"], agent["agent_configuration_id"]),
        "artifact-state-source-0001",
    ).json()
    api.client.post(
        f"/api/v1/jobs/{created['job_id']}/approve",
        json={},
        headers={**WRITE_HEADERS, "Idempotency-Key": "artifact-state-approve-0001"},
    )
    now = datetime(2026, 9, 13, 8, 0, tzinfo=UTC)
    executor = JobExecutor(
        api.repository,
        api.run_artifacts,
        Backend(api.run_artifacts, b"diff --git a/a b/a\n"),
        Evaluator(api.run_artifacts),
        api.jobs.tasks.source,
        lambda: now,
    )
    assert WorkerShell(api.repository, executor, lambda: now).run_once(
        "artifact-state-worker"
    )

    run_id = created["run_ids"][0]
    response = api.client.get(f"/api/v1/reports/runs/{run_id}")

    assert response.status_code == 200
    items = response.json()["artifact_links"]
    assert {item["artifact_type"] for item in items} == {
        "agent_patch",
        "public_test_summary",
        "public_trajectory",
        "harness_report",
        "harness_test_output",
        "agent_trajectory",
        "harness_report_raw",
        "harness_test_output_raw",
    }
    restricted = [item for item in items if item["retention_class"] == "raw_30d"]
    assert all(item["content_status"] == "not_ready" for item in restricted)
    assert all(item["expires_at"] is not None for item in restricted)
    assert all(item["deleted_at"] is None for item in restricted)
    assert all(item["original_size_bytes"] == item["size_bytes"] for item in restricted)
    assert all(item["redaction_status"] == "blocked" for item in restricted)
    public = [
        item
        for item in items
        if item["artifact_type"]
        in {"agent_patch", "public_test_summary", "public_trajectory"}
    ]
    assert all(item["content_status"] == "available" for item in public)

    private_id = restricted[0]["artifact_id"]
    body = api.client.get(f"/api/v1/artifacts/{private_id}/content")
    assert body.status_code == 409
    assert body.json()["error"]["code"] == "ARTIFACT_NOT_READY"

    missing = api.client.get(
        "/api/v1/artifacts/00000000-0000-4000-8000-000000000099/content"
    )
    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "ARTIFACT_NOT_FOUND"

    openapi = api.client.get("/openapi.json").json()
    content_path = openapi["paths"]["/api/v1/artifacts/{artifact_id}/content"]
    assert "get" in content_path and "delete" not in content_path
    assert "410" in content_path["get"]["responses"]
