from identity.conftest import WRITE_HEADERS

from jobs.test_http import submission, submit
from jobs.test_security import code, invite


def test_owner_approves_frozen_job_and_refreshes_auditable_queue_state(jobs_api):
    jobs_api.login()
    actor = jobs_api.client.get("/api/v1/auth/me").json()
    task, agent = jobs_api.register_catalogs()
    created = submit(
        jobs_api,
        submission(task["task_id"], agent["agent_configuration_id"]),
        "approval-source-0001",
    ).json()
    jobs_api.clock.advance(30)

    response = jobs_api.client.post(
        f"/api/v1/jobs/{created['job_id']}/approve",
        json={"reason": "  已核对冻结范围  "},
        headers={**WRITE_HEADERS, "Idempotency-Key": "approve-job-0001"},
    )

    assert response.status_code == 200
    assert response.json() == {
        **created,
        "status": "QUEUED",
        "owner_decided_by": actor["user_id"],
        "owner_decided_at": "2026-09-11T00:00:30Z",
        "owner_decision_reason": "已核对冻结范围",
    }
    detail = jobs_api.client.get(f"/api/v1/jobs/{created['job_id']}").json()
    assert detail["status"] == "QUEUED"
    assert detail["job_state_events"][-1] == {
        "sequence": 2,
        "from_status": "AWAITING_OWNER_APPROVAL",
        "to_status": "QUEUED",
        "reason_code": "OWNER_APPROVED",
        "actor_user_id": actor["user_id"],
        "note": "已核对冻结范围",
        "occurred_at": "2026-09-11T00:00:30Z",
    }
    assert {run["status"] for run in detail["runs"]} == {"PENDING"}
    queued = jobs_api.client.get("/api/v1/jobs?status=QUEUED")
    assert queued.status_code == 200
    assert [item["job_id"] for item in queued.json()["items"]] == [created["job_id"]]


def test_owner_rejects_job_and_cancels_every_pending_run(jobs_api):
    jobs_api.login()
    task, agent = jobs_api.register_catalogs()
    created = submit(
        jobs_api,
        submission(task["task_id"], agent["agent_configuration_id"]),
        "rejection-source-0001",
    ).json()

    response = jobs_api.client.post(
        f"/api/v1/jobs/{created['job_id']}/reject",
        json={},
        headers={**WRITE_HEADERS, "Idempotency-Key": "reject-job-0001"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "REJECTED"
    assert response.json()["owner_decision_reason"] is None
    detail = jobs_api.client.get(f"/api/v1/jobs/{created['job_id']}").json()
    assert detail["job_state_events"][-1]["reason_code"] == "OWNER_REJECTED"
    assert {run["status"] for run in detail["runs"]} == {"CANCELED"}
    assert {run["state_events"][-1]["reason_code"] for run in detail["runs"]} == {
        "JOB_REJECTED"
    }
    assert jobs_api.client.get("/api/v1/jobs?status=QUEUED").json()["items"] == []
    rejected = jobs_api.client.get("/api/v1/jobs?status=REJECTED").json()
    assert [item["job_id"] for item in rejected["items"]] == [created["job_id"]]


def test_collaborator_cannot_decide_even_own_job_or_forge_owner(jobs_api):
    jobs_api.login()
    task, agent = jobs_api.register_catalogs()
    invite(jobs_api, "approval_teammate")
    jobs_api.login("approval_teammate", "synthetic teammate password")
    created = submit(
        jobs_api,
        submission(task["task_id"], agent["agent_configuration_id"]),
        "teammate-approval-source-0001",
    ).json()
    endpoint = f"/api/v1/jobs/{created['job_id']}/approve"
    response = jobs_api.client.post(
        endpoint,
        json={"reason": "try", "owner_id": created["job_id"]},
        headers={**WRITE_HEADERS, "Idempotency-Key": "forged-owner-0001"},
    )
    assert response.status_code == 422
    response = jobs_api.client.post(
        endpoint,
        json={"reason": "try"},
        headers={**WRITE_HEADERS, "Idempotency-Key": "teammate-approve-0001"},
    )
    assert response.status_code == 403
    assert code(response) == "OWNER_APPROVAL_REQUIRED"


def test_decision_reason_and_missing_job_fail_closed(jobs_api):
    jobs_api.login()
    missing = "00000000-0000-0000-0000-000000000099"
    for index, reason in enumerate(("   ", "line\nbreak", "\ntrimmed text", "x" * 501)):
        response = jobs_api.client.post(
            f"/api/v1/jobs/{missing}/approve",
            json={"reason": reason},
            headers={**WRITE_HEADERS, "Idempotency-Key": f"invalid-note-{index:04d}"},
        )
        assert response.status_code == 422
    response = jobs_api.client.post(
        f"/api/v1/jobs/{missing}/approve",
        json={},
        headers={**WRITE_HEADERS, "Idempotency-Key": "missing-approval-0001"},
    )
    assert response.status_code == 404
    assert code(response) == "JOB_NOT_FOUND"


def test_decision_replay_and_conflicts_keep_one_final_state(jobs_api):
    jobs_api.login()
    task, agent = jobs_api.register_catalogs()
    created = submit(
        jobs_api,
        submission(task["task_id"], agent["agent_configuration_id"]),
        "decision-replay-source-0001",
    ).json()
    endpoint = f"/api/v1/jobs/{created['job_id']}"
    headers = {**WRITE_HEADERS, "Idempotency-Key": "stable-decision-0001"}
    original = jobs_api.client.post(
        endpoint + "/approve", json={"reason": "checked"}, headers=headers
    )
    jobs_api.clock.advance(60)
    replay = jobs_api.client.post(
        endpoint + "/approve", json={"reason": "checked"}, headers=headers
    )
    assert replay.status_code == 200
    assert replay.json() == original.json()
    changed = jobs_api.client.post(
        endpoint + "/reject", json={"reason": "changed"}, headers=headers
    )
    assert changed.status_code == 409 and code(changed) == "IDEMPOTENCY_CONFLICT"
    second_key = jobs_api.client.post(
        endpoint + "/approve",
        json={"reason": "checked"},
        headers={**WRITE_HEADERS, "Idempotency-Key": "another-decision-0001"},
    )
    assert second_key.status_code == 409
    assert code(second_key) == "JOB_STATE_CONFLICT"
    detail = jobs_api.client.get(endpoint).json()
    assert detail["status"] == "QUEUED"
    assert len(detail["job_state_events"]) == 2
