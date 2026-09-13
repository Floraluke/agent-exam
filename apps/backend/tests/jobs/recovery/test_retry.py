from identity.conftest import WRITE_HEADERS
from jobs.test_http import submission, submit
from jobs.test_security import invite


def _retry(api, job_id, key="retry-request-0001", body=None):
    return api.client.post(
        f"/api/v1/jobs/{job_id}/retry",
        json={} if body is None else body,
        headers={**WRITE_HEADERS, "Idempotency-Key": key},
    )


def _interrupted(api, collaborator=False):
    api.login()
    task, agent = api.register_catalogs()
    creator = api.client.get("/api/v1/auth/me").json()["user_id"]
    if collaborator:
        invite(api, "retry_member")
        api.login("retry_member", "synthetic teammate password")
        creator = api.client.get("/api/v1/auth/me").json()["user_id"]
    created = submit(
        api,
        submission(task["task_id"], agent["agent_configuration_id"]),
        "retry-source-0001",
    ).json()
    api.login()
    approved = api.client.post(
        f"/api/v1/jobs/{created['job_id']}/approve",
        json={},
        headers={**WRITE_HEADERS, "Idempotency-Key": "retry-approve-0001"},
    )
    assert approved.status_code == 200
    claimed = api.repository.claim("retry-interrupted-worker", api.clock())
    assert claimed is not None
    api.clock.value = claimed.lease.lease_expires_at
    recovered = api.client.post(
        f"/api/v1/jobs/{created['job_id']}/recover",
        json={},
        headers=WRITE_HEADERS,
    )
    assert recovered.status_code == 200
    return created, creator, agent


def test_owner_retry_creates_new_pending_job_for_original_submitter(jobs_api):
    source, creator, _agent = _interrupted(jobs_api, collaborator=True)

    response = _retry(jobs_api, source["job_id"])

    assert response.status_code == 202
    retried = response.json()
    assert retried["job_id"] != source["job_id"]
    assert retried["status"] == "AWAITING_OWNER_APPROVAL"
    assert retried["rerun_of_job_id"] == source["job_id"]
    assert set(retried["run_ids"]).isdisjoint(source["run_ids"])
    record = jobs_api.repository.get(retried["job_id"])
    assert record.created_by == creator
    assert record.state_events[0].actor_user_id != creator
    assert jobs_api.repository.get(source["job_id"]).status == "FAILED"
    assert jobs_api.repository.claim("unexpected-worker", jobs_api.clock()) is None

    jobs_api.login("retry_member", "synthetic teammate password")
    visible = jobs_api.client.get(f"/api/v1/jobs/{retried['job_id']}")
    assert visible.status_code == 200


def test_retry_is_idempotent_and_cannot_be_forged_or_skip_recovery(jobs_api):
    source, _creator, _agent = _interrupted(jobs_api)
    first = _retry(jobs_api, source["job_id"], "same-retry-key-0001")
    replay = _retry(jobs_api, source["job_id"], "same-retry-key-0001")
    assert replay.status_code == 202
    assert replay.json() == first.json()

    forged = _retry(
        jobs_api,
        source["job_id"],
        "forged-retry-key-0001",
        {"created_by": "00000000-0000-0000-0000-000000000099"},
    )
    assert forged.status_code == 422
    assert len(jobs_api.repository.records) == 2

    waiting_task = jobs_api.register_task("verified-task-2")
    waiting_agent = jobs_api.register_agent("verified-codex-2")
    waiting = submit(
        jobs_api,
        submission(waiting_task["task_id"], waiting_agent["agent_configuration_id"]),
        "not-recovered-source-0001",
    ).json()
    assert (
        _retry(jobs_api, waiting["job_id"], "early-retry-key-0001").status_code == 409
    )


def test_retry_revalidates_enabled_configuration_and_remains_owner_only(jobs_api):
    source, _creator, agent = _interrupted(jobs_api)
    jobs_api.client.post(
        f"/api/v1/agent-configurations/{agent['agent_configuration_id']}/disable",
        json={},
        headers=WRITE_HEADERS,
    )
    disabled = _retry(jobs_api, source["job_id"], "disabled-retry-key-0001")
    assert disabled.status_code == 409
    assert disabled.json()["error"]["code"] == "AGENT_CONFIGURATION_DISABLED"

    invite(jobs_api, "denied_retry_member")
    jobs_api.login("denied_retry_member", "synthetic teammate password")
    denied = _retry(jobs_api, source["job_id"], "denied-retry-key-0001")
    assert denied.status_code == 403
    assert len(jobs_api.repository.records) == 1
