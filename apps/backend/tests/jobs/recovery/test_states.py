from dataclasses import replace

from identity.conftest import WRITE_HEADERS
from jobs.test_http import submission, submit


def _batch(api, count, key):
    api.login()
    tasks = [api.register_task("verified-task")]
    tasks.extend(
        api.register_task(f"verified-task-{index}")
        for index in range(2, count + 1)
    )
    agent = api.register_agent("verified-codex")
    body = submission(tasks[0]["task_id"], agent["agent_configuration_id"])
    body["task_ids"] = [task["task_id"] for task in tasks]
    created = submit(api, body, key).json()
    approved = api.client.post(
        f"/api/v1/jobs/{created['job_id']}/approve",
        json={},
        headers={**WRITE_HEADERS, "Idempotency-Key": f"approve-{key}"},
    )
    assert approved.status_code == 200
    claimed = api.repository.claim("recovery-state-worker", api.clock())
    assert claimed is not None
    return created, claimed


def _recover(api, job_id):
    return api.client.post(
        f"/api/v1/jobs/{job_id}/recover", json={}, headers=WRITE_HEADERS
    )


def test_mixed_run_recovery_preserves_complete_and_closes_the_rest(jobs_api):
    created, claimed = _batch(jobs_api, 3, "recovery-mixed-source-0001")
    first, second, third = sorted(claimed.job.runs, key=lambda run: run.task.task_id)
    completed = replace(
        first,
        status="COMPLETED",
        stage="completed",
        resolved_summary=True,
        row_version=first.row_version + 1,
        finished_at=jobs_api.clock(),
    )
    running = replace(
        second,
        status="RUNNING_AGENT",
        stage="running_agent",
        row_version=second.row_version + 1,
        started_at=jobs_api.clock(),
    )
    stored = jobs_api.repository.get(created["job_id"])
    jobs_api.repository.records[stored.job_id] = replace(
        stored,
        status="EXECUTING",
        runs=(completed, running, third),
        row_version=stored.row_version + 1,
    )
    jobs_api.clock.value = claimed.lease.lease_expires_at

    response = _recover(jobs_api, created["job_id"])

    assert response.status_code == 200
    assert response.json()["status"] == "COMPLETED_WITH_ERRORS"
    recovered = jobs_api.repository.get(created["job_id"])
    assert recovered.runs[0] == completed
    assert [run.status for run in recovered.runs] == [
        "COMPLETED",
        "FAILED",
        "CANCELED",
    ]
    assert recovered.runs[1].failure_code == "INFRASTRUCTURE_INTERRUPTED"
    assert recovered.runs[2].failure_code is None


def test_cancel_request_wins_while_run_keeps_interruption_evidence(jobs_api):
    created, claimed = _batch(jobs_api, 2, "recovery-cancel-source-0001")
    lease = jobs_api.repository.start_execution(claimed.lease, jobs_api.clock())
    ordered = sorted(claimed.job.runs, key=lambda run: run.task.task_id)
    started = jobs_api.repository.start_run(lease, ordered[0].run_id, jobs_api.clock())
    assert started.started
    canceled = jobs_api.client.post(
        f"/api/v1/jobs/{created['job_id']}/cancel",
        json={"reason": "中断后停止"},
        headers={**WRITE_HEADERS, "Idempotency-Key": "recovery-cancel-0001"},
    )
    assert canceled.status_code == 202
    jobs_api.clock.value = jobs_api.repository.get(
        created["job_id"]
    ).lease_expires_at

    first = _recover(jobs_api, created["job_id"])
    replay = _recover(jobs_api, created["job_id"])

    assert first.status_code == 200 and replay.json() == first.json()
    assert first.json()["status"] == "CANCELED"
    assert first.json()["failure_code"] is None
    detail = jobs_api.client.get(f"/api/v1/jobs/{created['job_id']}").json()
    assert [run["status"] for run in detail["runs"]] == ["FAILED", "CANCELED"]
    assert detail["runs"][0]["failure_code"] == "INFRASTRUCTURE_INTERRUPTED"
    assert detail["runs"][1]["failure_code"] is None
