import pytest
from identity.conftest import PASSWORD, WRITE_HEADERS

from membership.conftest import invite, redeem


@pytest.mark.parametrize("condition", ["unknown", "expired", "redeemed"])
def test_unavailable_invitation_has_safe_error(identity_api, condition, caplog):
    token = invite(identity_api)["invitation_token"]
    if condition == "unknown":
        token = "synthetic unavailable invitation"
    elif condition == "expired":
        identity_api.clock.advance(86400)
    else:
        assert redeem(identity_api, token).status_code == 201
    response = redeem(identity_api, token, "someone_else")
    assert response.status_code == 410
    assert response.json()["error"]["code"] == "INVITATION_UNAVAILABLE"
    assert token not in response.text + caplog.text
    assert PASSWORD not in response.text + caplog.text
    assert "set-cookie" not in response.headers


def test_collaborator_cannot_invite_and_body_cannot_assign_owner(identity_api):
    token = invite(identity_api)["invitation_token"]
    assert redeem(identity_api, token, role="owner").status_code == 422
    assert redeem(identity_api, token).status_code == 201
    login = identity_api.client.post(
        "/api/v1/auth/login",
        json={
            "username": "teammate",
            "password": PASSWORD,
        },
        headers=WRITE_HEADERS,
    )
    assert login.status_code == 200
    response = identity_api.client.post(
        "/api/v1/invitations", json={}, headers=WRITE_HEADERS
    )
    assert response.status_code == 403


def test_name_conflict_does_not_consume_invitation(identity_api):
    token = invite(identity_api)["invitation_token"]
    assert redeem(identity_api, token, "owner").status_code == 409
    assert redeem(identity_api, token, "teammate").status_code == 201


def test_runtime_schema_registers_membership_without_connecting_to_database(
    monkeypatch,
):
    from fastapi.testclient import TestClient

    from eval_platform.delivery.http.app import create_runtime_app

    monkeypatch.setenv(
        "AGENTEXAM_DATABASE_URL", "postgresql://synthetic@127.0.0.1:1/synthetic"
    )
    monkeypatch.setenv("AGENTEXAM_PUBLIC_ORIGIN", "https://testserver")
    with TestClient(create_runtime_app(), base_url="https://testserver") as client:
        paths = client.get("/openapi.json").json()["paths"]
    assert "/api/v1/invitations/redeem" in paths
    assert "/api/v1/members/{user_id}/disable" in paths


def test_redeem_attempt_budget_does_not_consume_owner_login_budget(identity_api):
    for _ in range(10):
        assert redeem(identity_api, "synthetic-invalid-code").status_code == 410
    response = redeem(identity_api, "another-invalid-code")
    assert response.status_code == 429
    assert response.json()["error"]["code"] == "RATE_LIMITED"
    assert response.headers["retry-after"] == "60"
    assert identity_api.login().status_code == 200


def test_membership_openapi_declares_public_failures_and_empty_write_responses(
    identity_api,
):
    schema = identity_api.client.get("/openapi.json").json()
    paths = schema["paths"]
    disable = paths["/api/v1/members/{user_id}/disable"]["post"]["responses"]
    assert disable["404"]["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/ApiError"
    }
    redeem_responses = paths["/api/v1/invitations/redeem"]["post"]["responses"]
    assert "429" in redeem_responses
    assert "content" not in disable["204"]
    assert "HTTPValidationError" not in schema["components"]["schemas"]
    status = schema["components"]["schemas"]["InvitationResponse"]["properties"][
        "status"
    ]
    if "$ref" in status:
        status = schema["components"]["schemas"][status["$ref"].rsplit("/", 1)[-1]]
    assert status["enum"] == ["pending", "expired", "revoked", "redeemed"]
