import pytest
from identity.conftest import WRITE_HEADERS
from jobs.test_http import submission, submit
from jobs.test_postgres import login, postgres_api
from jobs.test_security import invite

from eval_platform.domain.jobs.execution import JobLeaseConflict


def _cancel(api, job_id, key="cancel-request-0001", reason="不再需要"):
    body = {} if reason is None else {"reason": reason}
    return api.client.post(
        f"/api/v1/jobs/{job_id}/cancel",
        json=body,
        headers={**WRITE_HEADERS, "Idempotency-Key": key},
    )


def test_collaborator_cancels_own_waiting_job_with_trusted_audit(jobs_api):
    jobs_api.login()
    task, agent = jobs_api.register_catalogs()
    invite(jobs_api, "cancel_teammate")
    jobs_api.login("cancel_teammate", "synthetic teammate password")
    actor = jobs_api.client.get("/api/v1/auth/me").json()
    created = submit(
        jobs_api,
        submission(task["task_id"], agent["agent_configuration_id"]),
        "cancel-waiting-source-0001",
    ).json()
    jobs_api.clock.advance(15)

    response = _cancel(jobs_api, created["job_id"], reason="  不再需要  ")

    assert response.status_code == 202
    assert response.json() == {
        **created,
        "status": "CANCELED",
        "cancel_requested_by": actor["user_id"],
        "cancel_requested_at": "2026-09-11T00:00:15Z",
        "cancel_reason": "不再需要",
    }
    detail = jobs_api.client.get(f"/api/v1/jobs/{created['job_id']}").json()
    assert detail["job_state_events"][-1] == {
        "sequence": 2,
        "from_status": "AWAITING_OWNER_APPROVAL",
        "to_status": "CANCELED",
        "reason_code": "JOB_CANCELED",
        "actor_user_id": actor["user_id"],
        "note": "不再需要",
        "occurred_at": "2026-09-11T00:00:15Z",
    }
    assert {run["status"] for run in detail["runs"]} == {"CANCELED"}
    assert {run["state_events"][-1]["reason_code"] for run in detail["runs"]} == {
        "JOB_CANCELED"
    }


def test_cancel_claimed_job_before_trial_starts_invalidates_worker_lease(jobs_api):
    jobs_api.login()
    task, agent = jobs_api.register_catalogs()
    created = submit(
        jobs_api,
        submission(task["task_id"], agent["agent_configuration_id"]),
        "cancel-preparing-source-0001",
    ).json()
    jobs_api.client.post(
        f"/api/v1/jobs/{created['job_id']}/approve",
        json={},
        headers={**WRITE_HEADERS, "Idempotency-Key": "approve-before-cancel-0001"},
    )
    claimed = jobs_api.repository.claim("worker-one", jobs_api.clock())
    assert claimed is not None and claimed.job.status == "PREPARING"

    response = _cancel(jobs_api, created["job_id"], "cancel-preparing-0001")

    assert response.status_code == 202
    assert response.json()["status"] == "CANCELED"
    detail = jobs_api.client.get(f"/api/v1/jobs/{created['job_id']}").json()
    assert {run["status"] for run in detail["runs"]} == {"CANCELED"}
    try:
        jobs_api.repository.start_execution(claimed.lease, jobs_api.clock())
    except JobLeaseConflict:
        pass
    else:
        raise AssertionError("canceled PREPARING lease remained executable")


def test_owner_cancels_any_job_but_collaborator_cannot_cancel_another(jobs_api):
    jobs_api.login()
    task, agent = jobs_api.register_catalogs()
    invite(jobs_api, "first_cancel_member")
    jobs_api.login()
    invite(jobs_api, "second_cancel_member")
    jobs_api.login("first_cancel_member", "synthetic teammate password")
    created = submit(
        jobs_api,
        submission(task["task_id"], agent["agent_configuration_id"]),
        "cancel-other-source-0001",
    ).json()
    jobs_api.login("second_cancel_member", "synthetic teammate password")
    hidden = _cancel(jobs_api, created["job_id"], "cancel-other-0001")
    assert hidden.status_code == 404

    jobs_api.login()
    approved = jobs_api.client.post(
        f"/api/v1/jobs/{created['job_id']}/approve",
        json={},
        headers={**WRITE_HEADERS, "Idempotency-Key": "approve-any-cancel-0001"},
    )
    assert approved.status_code == 200 and approved.json()["status"] == "QUEUED"
    canceled = _cancel(jobs_api, created["job_id"], "cancel-any-0001")
    assert canceled.status_code == 202
    assert canceled.json()["status"] == "CANCELED"


def test_cancel_replay_and_conflicts_preserve_the_first_request(jobs_api):
    jobs_api.login()
    task, agent = jobs_api.register_catalogs()
    created = submit(
        jobs_api,
        submission(task["task_id"], agent["agent_configuration_id"]),
        "cancel-replay-source-0001",
    ).json()
    first = _cancel(jobs_api, created["job_id"], "same-cancel-0001", "撤回")
    jobs_api.clock.advance(60)
    replay = _cancel(jobs_api, created["job_id"], "same-cancel-0001", "撤回")
    assert replay.status_code == 202
    assert replay.json() == first.json()

    changed = _cancel(jobs_api, created["job_id"], "same-cancel-0001", "改写")
    assert changed.status_code == 409
    assert changed.json()["error"]["code"] == "IDEMPOTENCY_CONFLICT"
    second = _cancel(jobs_api, created["job_id"], "second-cancel-0001", "撤回")
    assert second.status_code == 409
    assert second.json()["error"]["code"] == "JOB_STATE_CONFLICT"
    assert len(jobs_api.repository.get(created["job_id"]).state_events) == 2


def test_cancel_rejects_forged_identity_and_invalid_reason(jobs_api):
    jobs_api.login()
    missing = "00000000-0000-0000-0000-000000000099"
    forged = jobs_api.client.post(
        f"/api/v1/jobs/{missing}/cancel",
        json={"reason": "撤回", "actor_user_id": missing, "role": "owner"},
        headers={**WRITE_HEADERS, "Idempotency-Key": "forged-cancel-0001"},
    )
    assert forged.status_code == 422
    for index, reason in enumerate(("   ", "line\nbreak", "x" * 501)):
        invalid = _cancel(jobs_api, missing, f"invalid-cancel-{index:04d}", reason)
        assert invalid.status_code == 422


@pytest.mark.integration
def test_postgres_cancel_is_atomic_and_restores_audited_state(postgres_sandbox):
    with postgres_api(postgres_sandbox) as (client, jobs, repository, owner):
        login(client)
        task = jobs.tasks.register(owner, "verified-task")
        agent = jobs.agents.register(owner, "verified-codex")
        created = jobs.submit(
            owner,
            [task.task_id],
            [agent.configuration.configuration_id],
            "closed_book",
            "demo",
            "default-single-host-v1",
            "postgres-cancel-source-0001",
        )
        response = client.post(
            f"/api/v1/jobs/{created.job_id}/cancel",
            json={"reason": "撤回 PostgreSQL 任务"},
            headers={**WRITE_HEADERS, "Idempotency-Key": "postgres-cancel-0001"},
        )

        assert response.status_code == 202
        restored = repository.get(created.job_id)
        assert restored.status == "CANCELED"
        assert restored.cancel_requested_by == owner.user_id
        assert restored.cancel_reason == "撤回 PostgreSQL 任务"
        assert restored.state_events[-1].reason_code == "JOB_CANCELED"
        assert {run.status for run in restored.runs} == {"CANCELED"}
        assert {run.state_events[-1].reason_code for run in restored.runs} == {
            "JOB_CANCELED"
        }
