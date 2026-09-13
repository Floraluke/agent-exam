from identity.conftest import WRITE_HEADERS
from jobs.test_http import submission, submit


def test_executing_cancel_returns_request_state_without_canceling_current_run(jobs_api):
    jobs_api.login()
    first = jobs_api.register_task("verified-task")
    second = jobs_api.register_task("verified-task-2")
    agent = jobs_api.register_agent("verified-codex")
    body = submission(first["task_id"], agent["agent_configuration_id"])
    body["task_ids"] = [first["task_id"], second["task_id"]]
    created = submit(jobs_api, body, "cancel-executing-source-0001").json()
    jobs_api.client.post(
        f"/api/v1/jobs/{created['job_id']}/approve",
        json={},
        headers={**WRITE_HEADERS, "Idempotency-Key": "approve-executing-0001"},
    )
    claimed = jobs_api.repository.claim("http-cancel-worker", jobs_api.clock())
    assert claimed is not None
    lease = jobs_api.repository.start_execution(claimed.lease, jobs_api.clock())
    ordered = sorted(claimed.job.runs, key=lambda run: run.task.task_id)
    start = jobs_api.repository.start_run(lease, ordered[0].run_id, jobs_api.clock())
    assert start.started

    response = jobs_api.client.post(
        f"/api/v1/jobs/{created['job_id']}/cancel",
        json={"reason": "当前项结束后停止"},
        headers={**WRITE_HEADERS, "Idempotency-Key": "http-executing-cancel-0001"},
    )

    assert response.status_code == 202
    assert response.json()["status"] == "CANCEL_REQUESTED"
    assert response.json()["cancel_reason"] == "当前项结束后停止"
    detail = jobs_api.client.get(f"/api/v1/jobs/{created['job_id']}").json()
    assert [run["status"] for run in detail["runs"]].count("RUNNING_AGENT") == 1
    assert [run["status"] for run in detail["runs"]].count("PENDING") == 1
    assert detail["job_state_events"][-1]["reason_code"] == "CANCEL_REQUESTED"


def test_executing_cancel_replay_keeps_the_original_accepted_status(jobs_api):
    jobs_api.login()
    first = jobs_api.register_task("verified-task")
    second = jobs_api.register_task("verified-task-2")
    agent = jobs_api.register_agent("verified-codex")
    body = submission(first["task_id"], agent["agent_configuration_id"])
    body["task_ids"] = [first["task_id"], second["task_id"]]
    created = submit(jobs_api, body, "cancel-replay-executing-source-0001").json()
    jobs_api.client.post(
        f"/api/v1/jobs/{created['job_id']}/approve",
        json={},
        headers={**WRITE_HEADERS, "Idempotency-Key": "approve-replay-cancel-0001"},
    )
    claimed = jobs_api.repository.claim("replay-cancel-worker", jobs_api.clock())
    assert claimed is not None
    lease = jobs_api.repository.start_execution(claimed.lease, jobs_api.clock())
    ordered = sorted(claimed.job.runs, key=lambda run: run.task.task_id)
    started = jobs_api.repository.start_run(lease, ordered[0].run_id, jobs_api.clock())
    assert started.started

    first_response = jobs_api.client.post(
        f"/api/v1/jobs/{created['job_id']}/cancel",
        json={"reason": "当前项结束后停止"},
        headers={**WRITE_HEADERS, "Idempotency-Key": "replay-executing-cancel-0001"},
    )
    assert first_response.status_code == 202
    assert first_response.json()["status"] == "CANCEL_REQUESTED"
    lease = jobs_api.repository.fail(
        started.lease,
        ordered[0].run_id,
        "EXECUTION_PROCESS_ERROR",
        "受控失败。",
        jobs_api.clock(),
    )
    stopped = jobs_api.repository.start_run(lease, ordered[1].run_id, jobs_api.clock())
    assert not stopped.started
    lease = jobs_api.repository.start_finalizing(stopped.lease, jobs_api.clock())
    jobs_api.repository.finish(lease, jobs_api.clock())
    assert jobs_api.repository.get(created["job_id"]).status == "CANCELED"

    replay = jobs_api.client.post(
        f"/api/v1/jobs/{created['job_id']}/cancel",
        json={"reason": "当前项结束后停止"},
        headers={**WRITE_HEADERS, "Idempotency-Key": "replay-executing-cancel-0001"},
    )

    assert replay.status_code == 202
    assert replay.json() == first_response.json()
