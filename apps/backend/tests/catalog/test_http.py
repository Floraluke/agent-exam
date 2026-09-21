from identity.conftest import WRITE_HEADERS

from catalog.conftest import catalog_api
from eval_platform.domain.agent import AgentConfiguration


def agent_preset(display_name, model_name):
    return (
        display_name,
        AgentConfiguration(
            "test-preset-" + model_name,
            "codex",
            "test-version",
            "openai_chatgpt",
            model_name,
            "chatgpt_auth_json",
            "private-test-reference",
            {"reasoning_effort": "medium"},
        ),
    )


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


def test_agent_list_paginates_and_filters_by_state():
    """配置列表的游标分页与启用状态筛选：三步向导"刷新可选项"真实调用的形状。"""
    presets = {
        "verified-codex": agent_preset("Synthetic Codex", "test-model"),
        "verified-codex-2": agent_preset("Synthetic Codex 2", "test-model-2"),
        "verified-codex-3": agent_preset("Synthetic Codex 3", "test-model-3"),
    }
    with catalog_api(agent_presets=presets) as api:
        assert api.login().status_code == 200
        endpoint = "/api/v1/agent-configurations"
        registered = [
            api.client.post(
                endpoint, json={"preset_id": preset}, headers=WRITE_HEADERS
            ).json()
            for preset in presets
        ]
        assert len({item["agent_configuration_id"] for item in registered}) == 3

        # 游标分页：两页取完，不重不漏，最后一页不带 next_cursor
        first = api.client.get(endpoint + "?limit=2").json()
        assert len(first["items"]) == 2
        assert first["next_cursor"] is not None
        second = api.client.get(
            endpoint + "?limit=2&cursor=" + first["next_cursor"]
        ).json()
        assert len(second["items"]) == 1
        assert second["next_cursor"] is None
        assert {
            item["agent_configuration_id"] for item in first["items"] + second["items"]
        } == {item["agent_configuration_id"] for item in registered}

        # 向导的真实调用形状：上限 100 加 agent_type；类型只允许 codex
        wizard = api.client.get(endpoint + "?limit=100&agent_type=codex").json()
        assert len(wizard["items"]) == 3
        assert api.client.get(endpoint + "?agent_type=other").status_code == 422

        # 状态筛选：停用一个之后，两个方向都只返回该状态下的条目
        disabled_id = registered[0]["agent_configuration_id"]
        assert (
            api.client.post(
                endpoint + "/" + disabled_id + "/disable",
                json={},
                headers=WRITE_HEADERS,
            ).status_code
            == 204
        )
        enabled = api.client.get(endpoint + "?enabled=true").json()["items"]
        stopped = api.client.get(endpoint + "?enabled=false").json()["items"]
        assert {item["agent_configuration_id"] for item in enabled} == {
            item["agent_configuration_id"] for item in registered[1:]
        }
        assert [item["agent_configuration_id"] for item in stopped] == [disabled_id]
