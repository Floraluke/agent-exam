from uuid import uuid4

import pytest
from identity.conftest import PASSWORD, WRITE_HEADERS
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
