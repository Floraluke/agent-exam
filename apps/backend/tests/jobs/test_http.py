from identity.conftest import WRITE_HEADERS


def submission(task_id, configuration_id):
    return {
        "task_ids": [task_id],
        "agent_configuration_ids": [configuration_id],
        "evaluation_track": "closed_book",
        "batch_preset": "demo",
        "limit_profile_id": "default-single-host-v1",
    }


def submit(api, body, key="browser-request-0001"):
    return api.client.post(
        "/api/v1/jobs",
        json=body,
        headers={**WRITE_HEADERS, "Idempotency-Key": key},
    )


def test_authenticated_options_are_server_owned_and_exact(jobs_api):
    assert jobs_api.client.get("/api/v1/job-options").status_code == 401
    assert jobs_api.login().status_code == 200
    response = jobs_api.client.get("/api/v1/job-options")
    assert response.status_code == 200
    assert response.json() == {
        "batch_presets": [
            {"batch_preset": "demo", "minimum_tasks": 1, "maximum_tasks": 3},
            {"batch_preset": "quick", "minimum_tasks": 5, "maximum_tasks": 5},
            {"batch_preset": "standard", "minimum_tasks": 10, "maximum_tasks": 20},
            {"batch_preset": "continuous", "minimum_tasks": 1, "maximum_tasks": 20},
        ],
        "evaluation_tracks": ["closed_book"],
        "limit_profiles": [
            {
                "limit_profile_id": "default-single-host-v1",
                "agent_wall_timeout_sec": 900,
                "agent_cpus": 1,
                "agent_memory_mb": 4096,
                "agent_storage_mb": 8192,
                "evaluator_wall_timeout_sec": 300,
                "evaluator_cpus": 1,
                "evaluator_memory_mb": 4096,
                "pids_limit": 64,
                "patch_warning_bytes": 262144,
                "patch_max_bytes": 1048576,
                "raw_artifact_max_bytes": 52428800,
                "raw_run_max_bytes": 209715200,
                "concurrency": 1,
                "max_retries": 0,
            }
        ],
        "maximum_agent_configurations": 3,
        "maximum_runs": 60,
    }


def test_submit_returns_frozen_waiting_job_and_refreshes(jobs_api):
    jobs_api.login()
    task, agent = jobs_api.register_catalogs()
    body = submission(task["task_id"], agent["agent_configuration_id"])
    response = submit(jobs_api, body)
    assert response.status_code == 202
    created = response.json()
    assert created["status"] == "AWAITING_OWNER_APPROVAL"
    assert created["trial_count"] == 1
    assert created["result_scope"] == "internal_test"
    assert len(created["run_ids"]) == 1
    detail = jobs_api.client.get("/api/v1/jobs/" + created["job_id"])
    assert detail.status_code == 200
    frozen = detail.json()
    assert frozen["task_snapshots"][0]["problem_statement"] == "Fix the visible bug."
    assert (
        frozen["agent_snapshots"][0]["configuration_fingerprint"]
        == (agent["configuration_fingerprint"])
    )
    assert "private-test-reference" not in detail.text
    assert frozen["job_state_events"][0]["reason_code"] == "JOB_SUBMITTED"
    assert frozen["runs"][0]["state_events"][0]["reason_code"] == "JOB_SUBMITTED"
    page = jobs_api.client.get("/api/v1/jobs").json()
    assert [item["job_id"] for item in page["items"]] == [created["job_id"]]


def test_submit_rejects_malformed_catalog_ids_before_repository_access(jobs_api):
    jobs_api.login()
    task, agent = jobs_api.register_catalogs()
    body = submission(task["task_id"], agent["agent_configuration_id"])
    for field in ("task_ids", "agent_configuration_ids"):
        response = submit(
            jobs_api,
            {**body, field: ["not-a-uuid"]},
            key=f"malformed-{field}-0001",
        )
        assert response.status_code == 422
