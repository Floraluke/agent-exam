from identity.conftest import WRITE_HEADERS

from jobs.test_http import submission, submit


def code(response):
    return response.json()["error"]["code"]


def invite(api, username):
    invitation = api.client.post(
        "/api/v1/invitations", json={}, headers=WRITE_HEADERS
    ).json()
    api.client.post("/api/v1/auth/logout", json={}, headers=WRITE_HEADERS)
    response = api.client.post(
        "/api/v1/invitations/redeem",
        json={
            "invitation_token": invitation["invitation_token"],
            "username": username,
            "password": "synthetic teammate password",
        },
        headers=WRITE_HEADERS,
    )
    assert response.status_code == 201


def test_rejects_untrusted_fields_and_all_controlled_selection_errors(jobs_api):
    jobs_api.login()
    task, agent = jobs_api.register_catalogs()
    body = submission(task["task_id"], agent["agent_configuration_id"])
    for field, value in (
        ("result_scope", "official"),
        ("command", "run anything"),
        ("model_base_url", "https://outside.example"),
        ("memory_mb", 999999),
        ("internal_test", False),
    ):
        response = submit(jobs_api, {**body, field: value}, key="field-test-0001")
        assert response.status_code == 422
    cases = (
        ({**body, "task_ids": []}, "EMPTY_JOB_SELECTION"),
        ({**body, "agent_configuration_ids": []}, "EMPTY_JOB_SELECTION"),
        (
            {**body, "evaluation_track": "open_book_experimental"},
            "EVALUATION_TRACK_NOT_ENABLED",
        ),
        ({**body, "limit_profile_id": "custom"}, "LIMIT_PROFILE_NOT_ALLOWED"),
        ({**body, "batch_preset": "quick"}, "BATCH_PRESET_EXCEEDED"),
    )
    for index, (candidate, expected) in enumerate(cases):
        response = submit(jobs_api, candidate, key=f"selection-test-{index:04d}")
        assert response.status_code == 400
        assert code(response) == expected
    missing = "00000000-0000-0000-0000-000000000099"
    response = submit(jobs_api, {**body, "task_ids": [missing]}, "missing-task-0001")
    assert response.status_code == 404 and code(response) == "TASK_NOT_FOUND"
    response = submit(
        jobs_api,
        {**body, "agent_configuration_ids": [missing]},
        "missing-agent-0001",
    )
    assert response.status_code == 404
    assert code(response) == "AGENT_CONFIGURATION_NOT_FOUND"


def test_deduplicates_then_enforces_three_config_and_sixty_run_limits(jobs_api):
    jobs_api.login()
    first_task, first_agent = jobs_api.register_catalogs()
    duplicate = submission(first_task["task_id"], first_agent["agent_configuration_id"])
    duplicate["task_ids"] *= 2
    duplicate["agent_configuration_ids"] *= 2
    assert submit(jobs_api, duplicate, "deduplicate-0001").json()["trial_count"] == 1
    agents = [first_agent] + [
        jobs_api.register_agent(f"verified-codex-{index}") for index in range(2, 5)
    ]
    too_many = submission(first_task["task_id"], agents[0]["agent_configuration_id"])
    too_many["agent_configuration_ids"] = [
        item["agent_configuration_id"] for item in agents
    ]
    response = submit(jobs_api, too_many, "too-many-agents-0001")
    assert response.status_code == 400 and code(response) == "BATCH_PRESET_EXCEEDED"
    tasks = [first_task] + [
        jobs_api.register_task(f"verified-task-{index}") for index in range(2, 21)
    ]
    standard = submission(tasks[0]["task_id"], agents[0]["agent_configuration_id"])
    standard["task_ids"] = [item["task_id"] for item in tasks]
    standard["agent_configuration_ids"] = [
        item["agent_configuration_id"] for item in agents[:3]
    ]
    standard["batch_preset"] = "standard"
    response = submit(jobs_api, standard, "sixty-runs-0001")
    assert response.status_code == 202 and response.json()["trial_count"] == 60


def test_idempotency_replays_after_disable_but_conflicts_on_changed_body(jobs_api):
    jobs_api.login()
    first, agent = jobs_api.register_catalogs()
    second = jobs_api.register_task("verified-task-2")
    body = submission(first["task_id"], agent["agent_configuration_id"])
    original = submit(jobs_api, body, "stable-replay-0001")
    resource = "/api/v1/agent-configurations/" + agent["agent_configuration_id"]
    disabled_response = jobs_api.client.post(
        resource + "/disable", json={}, headers=WRITE_HEADERS
    )
    assert disabled_response.status_code == 204
    assert submit(jobs_api, body, "stable-replay-0001").json() == original.json()
    disabled = submit(jobs_api, body, "new-after-disable-0001")
    assert disabled.status_code == 409
    assert code(disabled) == "AGENT_CONFIGURATION_DISABLED"
    changed = {**body, "task_ids": [second["task_id"]]}
    conflict = submit(jobs_api, changed, "stable-replay-0001")
    assert conflict.status_code == 409 and code(conflict) == "IDEMPOTENCY_CONFLICT"


def test_collaborator_sees_only_own_jobs_while_owner_sees_all(jobs_api):
    jobs_api.login()
    task, agent = jobs_api.register_catalogs()
    invite(jobs_api, "first_teammate")
    jobs_api.login("first_teammate", "synthetic teammate password")
    created = submit(
        jobs_api,
        submission(task["task_id"], agent["agent_configuration_id"]),
        "teammate-job-0001",
    ).json()
    jobs_api.client.post("/api/v1/auth/logout", json={}, headers=WRITE_HEADERS)
    jobs_api.login()
    invite(jobs_api, "second_teammate")
    jobs_api.login("second_teammate", "synthetic teammate password")
    assert jobs_api.client.get("/api/v1/jobs").json()["items"] == []
    hidden = jobs_api.client.get("/api/v1/jobs/" + created["job_id"])
    assert hidden.status_code == 404 and code(hidden) == "JOB_NOT_FOUND"
    jobs_api.client.post("/api/v1/auth/logout", json={}, headers=WRITE_HEADERS)
    jobs_api.login()
    assert jobs_api.client.get("/api/v1/jobs/" + created["job_id"]).status_code == 200


def test_unknown_or_repeated_job_query_is_rejected(jobs_api):
    jobs_api.login()
    for query in ("unknown=1", "limit=1&limit=2"):
        response = jobs_api.client.get("/api/v1/jobs?" + query)
        assert response.status_code == 400


def test_task_five_routes_are_not_prebuilt(jobs_api):
    jobs_api.login()
    missing = "00000000-0000-0000-0000-000000000099"
    for action in ("approve", "reject", "cancel"):
        response = jobs_api.client.post(
            f"/api/v1/jobs/{missing}/{action}", json={}, headers=WRITE_HEADERS
        )
        assert response.status_code == 404
