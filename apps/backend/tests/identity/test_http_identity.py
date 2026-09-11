import pytest
from fastapi.testclient import TestClient

from eval_platform.adapters.identity.passwords import Argon2Passwords
from eval_platform.application.identity import IdentityService
from eval_platform.delivery.http.app import create_app
from eval_platform.delivery.http.config import HttpConfig
from identity.conftest import WRITE_HEADERS
from identity.memory import MemoryIdentityRepository


def test_owner_can_login_and_read_their_identity():
    service = IdentityService(MemoryIdentityRepository(), Argon2Passwords())
    owner = service.bootstrap_owner("owner", "synthetic owner password")
    app = create_app(service, HttpConfig(public_origin="https://testserver"))
    with TestClient(app, base_url="https://testserver") as client:
        response = client.post(
            "/api/v1/auth/login",
            json={"username": "owner", "password": "synthetic owner password"},
            headers={"Origin": "https://testserver", "X-AgentExam-Request": "1"},
        )
        assert response.status_code == 200
        assert client.get("/api/v1/auth/me").json() == {
            "user_id": owner.user_id,
            "username": "owner",
            "role": "owner",
        }


def test_logout_revokes_the_old_cookie_even_if_replayed(identity_api):
    assert identity_api.login().status_code == 200
    old_cookie = identity_api.client.cookies.get("__Host-agentexam_session")
    response = identity_api.client.post("/api/v1/auth/logout", headers=WRITE_HEADERS)
    assert response.status_code == 204
    replay = identity_api.client.get(
        "/api/v1/auth/me", headers={"Cookie": f"__Host-agentexam_session={old_cookie}"}
    )
    assert replay.status_code == 401
    assert replay.json()["error"]["code"] == "AUTHENTICATION_REQUIRED"


def test_authenticated_responses_are_not_cacheable(identity_api):
    login = identity_api.login()
    for flag in ("HttpOnly", "Secure", "SameSite=strict", "Path=/", "Max-Age=28800"):
        assert flag in login.headers["set-cookie"]
    assert "Domain=" not in login.headers["set-cookie"]
    assert "token" not in login.json()
    assert login.headers["cache-control"] == "no-store"
    assert (
        identity_api.client.get("/api/v1/auth/me").headers["cache-control"]
        == "no-store"
    )


def test_session_expires_at_eight_hours(identity_api):
    assert identity_api.login().status_code == 200
    identity_api.clock.advance(28799)
    assert identity_api.client.get("/api/v1/auth/me").status_code == 200
    identity_api.clock.advance(1)
    assert identity_api.client.get("/api/v1/auth/me").status_code == 401


def test_explicit_loopback_development_can_use_http_cookies():
    service = IdentityService(MemoryIdentityRepository(), Argon2Passwords())
    service.bootstrap_owner("owner", "synthetic owner password")
    config = HttpConfig(
        public_origin="http://127.0.0.1:3000", allow_insecure_loopback=True
    )
    with TestClient(
        create_app(service, config), base_url=config.public_origin
    ) as client:
        response = client.post(
            "/api/v1/auth/login",
            json={"username": "owner", "password": "synthetic owner password"},
            headers={"Origin": config.public_origin, "X-AgentExam-Request": "1"},
        )
        assert response.status_code == 200
        assert "HttpOnly" in response.headers["set-cookie"]
        assert "Secure" not in response.headers["set-cookie"]
        assert client.get("/api/v1/auth/me").status_code == 200


@pytest.mark.parametrize("token", [None, "synthetic-invalid-session", "x" * 129])
def test_missing_or_invalid_session_is_rejected(identity_api, token):
    headers = {} if token is None else {"Cookie": f"__Host-agentexam_session={token}"}
    response = identity_api.client.get("/api/v1/auth/me", headers=headers)
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "AUTHENTICATION_REQUIRED"


def test_http_surface_contains_only_the_three_approved_identity_endpoints(identity_api):
    schema = identity_api.client.get("/openapi.json").json()
    assert set(schema["paths"]) == {
        "/api/v1/auth/login",
        "/api/v1/auth/logout",
        "/api/v1/auth/me",
    }
    assert (
        schema["components"]["schemas"]["LoginRequest"]["additionalProperties"] is False
    )
    assert set(schema["components"]["schemas"]["ActorResponse"]["properties"]) == {
        "user_id",
        "username",
        "role",
    }
