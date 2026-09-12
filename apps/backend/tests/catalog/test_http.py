from identity.conftest import WRITE_HEADERS


def test_owner_registers_and_reads_fixed_task_without_hidden_answers(identity_api):
    assert identity_api.login().status_code == 200
    response = identity_api.client.post(
        "/api/v1/tasks/register",
        json={"preset_id": "verified-task"},
        headers=WRITE_HEADERS,
    )
    assert response.status_code == 201
    task = response.json()
    assert task["instance_id"] == "example__repo-1"
    assert task["problem_statement"] == "Fix the visible bug."
    page = identity_api.client.get("/api/v1/tasks").json()
    assert [item["task_id"] for item in page["items"]] == [task["task_id"]]
    detail = identity_api.client.get(f"/api/v1/tasks/{task['task_id']}")
    assert detail.json() == task
    assert "HIDDEN_ANSWER" not in response.text + detail.text + str(page)
    assert set(task) == {
        "task_id",
        "instance_id",
        "dataset_id",
        "dataset_revision",
        "split",
        "repo",
        "base_commit",
        "problem_statement_preview",
        "problem_statement",
    }


def test_fixed_configuration_reentry_and_disable_preserve_identity(identity_api):
    assert identity_api.login().status_code == 200
    endpoint = "/api/v1/agent-configurations"

    def register():
        return identity_api.client.post(
            endpoint,
            json={"preset_id": "verified-codex"},
            headers=WRITE_HEADERS,
        )

    response = register()
    assert response.status_code == 201
    configuration = response.json()
    assert configuration["agent_type"] == "codex"
    assert configuration["public_options"] == {"reasoning_effort": "medium"}
    assert configuration["limit_profile_id"] is None
    assert len(configuration["configuration_fingerprint"]) == 64
    assert register().json() == configuration
    resource = f"{endpoint}/{configuration['agent_configuration_id']}"
    assert (
        identity_api.client.post(
            resource + "/disable",
            json={},
            headers=WRITE_HEADERS,
        ).status_code
        == 204
    )
    disabled = identity_api.client.get(resource).json()
    assert disabled["enabled"] is False
    assert (
        disabled["configuration_fingerprint"]
        == configuration["configuration_fingerprint"]
    )
    assert register().json() == disabled
    assert identity_api.client.get(endpoint + "?enabled=true").json()["items"] == []
