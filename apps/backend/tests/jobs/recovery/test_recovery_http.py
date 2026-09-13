from datetime import timedelta

import pytest
from identity.conftest import WRITE_HEADERS
from jobs.test_http import submission, submit
from jobs.test_security import invite

from eval_platform.domain.jobs.execution import JobLeaseConflict


def _claimed_job(api):
    api.login()
    task, agent = api.register_catalogs()
    created = submit(
        api,
        submission(task["task_id"], agent["agent_configuration_id"]),
        "recovery-source-0001",
    ).json()
    approved = api.client.post(
        f"/api/v1/jobs/{created['job_id']}/approve",
        json={},
        headers={**WRITE_HEADERS, "Idempotency-Key": "recovery-approve-0001"},
    )
    assert approved.status_code == 200
    claimed = api.repository.claim("interrupted-worker", api.clock())
    assert claimed is not None
    return created, claimed


def _recover(api, job_id, body=None):
    return api.client.post(
        f"/api/v1/jobs/{job_id}/recover",
        json={} if body is None else body,
        headers=WRITE_HEADERS,
    )


def test_owner_recovers_expired_preparing_job_without_restarting_it(jobs_api):
    created, claimed = _claimed_job(jobs_api)
    jobs_api.clock.value = claimed.lease.lease_expires_at

    response = _recover(jobs_api, created["job_id"])

    assert response.status_code == 200
    assert response.json()["status"] == "FAILED"
    assert response.json()["failure_code"] == "INFRASTRUCTURE_INTERRUPTED"
    detail = jobs_api.client.get(f"/api/v1/jobs/{created['job_id']}").json()
    assert detail["job_state_events"][-1]["reason_code"] == "INTERRUPTION_RECOVERED"
    assert detail["runs"][0]["status"] == "FAILED"
    assert detail["runs"][0]["failure_code"] == "INFRASTRUCTURE_INTERRUPTED"
    with pytest.raises(JobLeaseConflict):
        jobs_api.repository.start_execution(
            claimed.lease, claimed.lease.lease_expires_at - timedelta(seconds=1)
        )


def test_recovery_waits_for_expiry_and_replays_without_new_events(jobs_api):
    created, claimed = _claimed_job(jobs_api)
    active = _recover(jobs_api, created["job_id"])
    assert active.status_code == 409
    assert active.json()["error"]["code"] == "JOB_STATE_CONFLICT"

    jobs_api.clock.value = claimed.lease.lease_expires_at
    first = _recover(jobs_api, created["job_id"])
    jobs_api.clock.advance(60)
    replay = _recover(jobs_api, created["job_id"])

    assert replay.status_code == 200
    assert replay.json() == first.json()
    assert len(jobs_api.repository.get(created["job_id"]).state_events) == 4


def test_recovery_is_owner_only_and_rejects_forged_control_fields(jobs_api):
    created, claimed = _claimed_job(jobs_api)
    jobs_api.clock.value = claimed.lease.lease_expires_at
    forged = _recover(
        jobs_api,
        created["job_id"],
        {"worker_id": "forged", "status": "COMPLETED"},
    )
    assert forged.status_code == 422

    jobs_api.login()
    invite(jobs_api, "recovery_member")
    jobs_api.login("recovery_member", "synthetic teammate password")
    denied = _recover(jobs_api, created["job_id"])
    assert denied.status_code == 403
    assert denied.json()["error"]["code"] == "OWNER_APPROVAL_REQUIRED"
    assert jobs_api.repository.get(created["job_id"]).status == "PREPARING"
