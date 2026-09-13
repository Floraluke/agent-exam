from dataclasses import replace
from datetime import UTC, datetime, timedelta

from identity.conftest import WRITE_HEADERS
from jobs.test_http import submission, submit

from eval_platform.domain.jobs.policy import (
    recovery_is_due,
    recovery_job_outcome,
    recovery_run_outcome,
)


def _batch(api, count, key):
    api.login()
    tasks = [api.register_task("verified-task")]
    tasks.extend(
        api.register_task(f"verified-task-{index}") for index in range(2, count + 1)
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


def test_recovery_policy_classifies_only_expired_active_work():
    now = datetime(2026, 9, 13, tzinfo=UTC)

    assert recovery_is_due("EXECUTING", now, now)
    assert not recovery_is_due("EXECUTING", now + timedelta(seconds=1), now)
    assert not recovery_is_due("COMPLETED", now - timedelta(seconds=1), now)

    pending = recovery_run_outcome("PENDING", None)
    running = recovery_run_outcome("RUNNING_AGENT", "running_agent")
    assert pending == ("CANCELED", "canceled", None, None)
    assert running == (
        "FAILED",
        "interrupted",
        "INFRASTRUCTURE_INTERRUPTED",
        "运行在 running_agent 阶段中断。",
    )
    assert recovery_run_outcome("COMPLETED", "completed") is None

    assert recovery_job_outcome(False, ["COMPLETED", "FAILED"], True) == (
        "COMPLETED_WITH_ERRORS",
        "INFRASTRUCTURE_INTERRUPTED",
        "执行租约过期，批次已安全收束。",
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
    replay = _recover(jobs_api, created["job_id"])

    assert response.status_code == 200
    assert replay.status_code == 200 and replay.json() == response.json()
    assert response.json()["status"] == "COMPLETED_WITH_ERRORS"
    recovered = jobs_api.repository.get(created["job_id"])
    assert (
        sum(
            event.reason_code == "INTERRUPTION_RECOVERED"
            for event in recovered.state_events
        )
        == 1
    )
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
    jobs_api.clock.value = jobs_api.repository.get(created["job_id"]).lease_expires_at

    first = _recover(jobs_api, created["job_id"])
    replay = _recover(jobs_api, created["job_id"])

    assert first.status_code == 200 and replay.json() == first.json()
    assert first.json()["status"] == "CANCELED"
    assert first.json()["failure_code"] is None
    detail = jobs_api.client.get(f"/api/v1/jobs/{created['job_id']}").json()
    assert [run["status"] for run in detail["runs"]] == ["FAILED", "CANCELED"]
    assert detail["runs"][0]["failure_code"] == "INFRASTRUCTURE_INTERRUPTED"
    assert detail["runs"][1]["failure_code"] is None


def test_cancel_request_remains_authoritative_after_finalizing_transition(jobs_api):
    created, claimed = _batch(jobs_api, 1, "recovery-finalizing-cancel-source-0001")
    jobs_api.repository.start_execution(claimed.lease, jobs_api.clock())
    canceled = jobs_api.client.post(
        f"/api/v1/jobs/{created['job_id']}/cancel",
        json={"reason": "最终收束前停止"},
        headers={**WRITE_HEADERS, "Idempotency-Key": "recovery-finalizing-cancel-0001"},
    )
    assert canceled.status_code == 202
    stored = jobs_api.repository.get(created["job_id"])
    jobs_api.repository.records[stored.job_id] = replace(
        stored,
        status="FINALIZING",
        row_version=stored.row_version + 1,
    )
    jobs_api.clock.value = stored.lease_expires_at

    recovered = _recover(jobs_api, created["job_id"])

    assert recovered.status_code == 200
    assert recovered.json()["status"] == "CANCELED"
    assert recovered.json()["failure_code"] is None
