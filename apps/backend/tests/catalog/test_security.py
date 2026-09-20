from uuid import uuid4

import pytest
from identity.conftest import PASSWORD, WRITE_HEADERS
from jobs.conftest import job_api
from jobs.test_http import submission, submit
from membership.conftest import invite, redeem


@pytest.mark.parametrize("path", ["/tasks", "/agent-configurations"])
def test_catalog_requires_authentication(identity_api, path):
    response = identity_api.client.get("/api/v1" + path)
    assert response.status_code == 401


def test_collaborator_can_browse_but_cannot_manage_catalog(identity_api):
    token = invite(identity_api)["invitation_token"]
    assert redeem(identity_api, token).status_code == 201
    identity_api.client.post("/api/v1/auth/logout", headers=WRITE_HEADERS)
    assert (
        identity_api.client.post(
            "/api/v1/auth/login",
            json={"username": "teammate", "password": PASSWORD},
            headers=WRITE_HEADERS,
        ).status_code
        == 200
    )
    for path in ("tasks", "agent-configurations"):
        assert identity_api.client.get("/api/v1/" + path).status_code == 200
    for path, body in (
        ("tasks/register", {"preset_id": "verified-task"}),
        ("agent-configurations", {"preset_id": "verified-codex"}),
        (f"agent-configurations/{uuid4()}/disable", {}),
    ):
        response = identity_api.client.post(
            "/api/v1/" + path,
            json=body,
            headers=WRITE_HEADERS,
        )
        assert response.status_code == 403
        assert response.json()["error"]["code"] == "FORBIDDEN"


@pytest.mark.parametrize(
    "extra",
    [
        {"role": "owner"},
        {"command": "unsafe-command"},
        {"model": "other"},
        {"source_url": "https://untrusted.invalid"},
        {"public_options": {"secret": "LEAK"}},
    ],
)
@pytest.mark.parametrize(
    "path,preset",
    [
        ("tasks/register", "verified-task"),
        ("agent-configurations", "verified-codex"),
    ],
)
def test_registration_rejects_client_overrides(identity_api, extra, path, preset):
    assert identity_api.login().status_code == 200
    response = identity_api.client.post(
        "/api/v1/" + path,
        json={"preset_id": preset, **extra},
        headers=WRITE_HEADERS,
    )
    assert response.status_code == 422
    assert response.json()["error"]["details"] == {}
    assert "LEAK" not in response.text


@pytest.mark.parametrize(
    "query",
    [
        "limit=0",
        "limit=101",
        "cursor=bad",
        "dataset_id=",
        "split=",
        "repo=",
        "hidden_tests=true",
        "limit=1&limit=2",
    ],
)
def test_invalid_task_filters_have_explicit_feedback(identity_api, query):
    assert identity_api.login().status_code == 200
    response = identity_api.client.get("/api/v1/tasks?" + query)
    assert response.status_code in {400, 422}


def test_public_config_omits_credential_reference(identity_api):
    assert identity_api.login().status_code == 200
    response = identity_api.client.post(
        "/api/v1/agent-configurations",
        json={"preset_id": "verified-codex"},
        headers=WRITE_HEADERS,
    )
    assert response.status_code == 201
    public = response.json()
    assert set(public) == {
        "agent_configuration_id",
        "display_name",
        "agent_type",
        "agent_version",
        "model_provider",
        "model",
        "configuration_fingerprint",
        "enabled",
        "public_options",
        "limit_profile_id",
    }
    assert "private-test-reference" not in response.text


HIDDEN_SENTINELS = (
    "HIDDEN_ANSWER",  # gold_patch / test_patch 与原始记录里的 patch 字段
    "hidden_test",  # fail_to_pass 名单
    "hidden_pass",  # pass_to_pass 名单
    "private-test-reference",  # 凭据逻辑引用
)


@pytest.fixture
def job_flow_api():
    with job_api(scope_visible=lambda scope: scope == "internal_test") as api:
        yield api


def test_hidden_evaluation_fields_never_reach_public_surfaces(job_flow_api):
    """登记并提交后逐条扫描公开读取面：隐藏答案、判卷名单与凭据引用一处都不能出现。"""
    api = job_flow_api
    assert api.login().status_code == 200
    task = api.register_task("verified-task")
    agent = api.register_agent("verified-codex")
    body = submission(task["task_id"], agent["agent_configuration_id"])
    body["batch_preset"] = "continuous"
    created = submit(api, body, "hidden-surface-0001").json()
    job_id = created["job_id"]
    run_id = created["run_ids"][0]

    surfaces = {
        "tasks": "/api/v1/tasks",
        "task": "/api/v1/tasks/" + task["task_id"],
        "agents": "/api/v1/agent-configurations",
        "agent": "/api/v1/agent-configurations/" + agent["agent_configuration_id"],
        "options": "/api/v1/job-options",
        "jobs": "/api/v1/jobs",
        "job": "/api/v1/jobs/" + job_id,
        "job_report": "/api/v1/reports/jobs/" + job_id,
        "run_report": "/api/v1/reports/runs/" + run_id,
        "comparison": "/api/v1/reports/comparisons?job_ids=" + job_id,
        "artifacts": f"/api/v1/runs/{run_id}/artifacts",
        "trajectory": f"/api/v1/runs/{run_id}/trajectory",
    }
    responses = {name: api.client.get(path) for name, path in surfaces.items()}
    refused = {}
    for name, response in responses.items():
        if response.status_code != 200:
            refused[name] = response.status_code
        for sentinel in HIDDEN_SENTINELS:
            assert sentinel not in response.text, (name, sentinel)
    # 内容尚未产出的端点可以按契约拒绝（未执行 Run 的轨迹即如此）；
    # 此处如实记录拒绝集合，不把 409 当作通过
    assert set(refused) <= {"trajectory"}, refused

    # 对照：公开题面仍然在读回结果里，说明上面的断言不是因为响应为空而通过
    assert "Fix the visible bug." in responses["task"].text
    assert "Fix the visible bug." in responses["job"].text
