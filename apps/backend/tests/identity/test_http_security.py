import logging

import pytest
from fastapi.testclient import TestClient

from eval_platform.adapters.identity.passwords import Argon2Passwords
from eval_platform.application.identity import IdentityService
from eval_platform.delivery.http.app import create_app
from eval_platform.delivery.http.config import HttpConfig
from eval_platform.domain.identity import IdentityUnavailable
from identity.conftest import PASSWORD, WRITE_HEADERS
from identity.memory import MemoryIdentityRepository


@pytest.mark.parametrize(
    "headers",
    [
        {},
        {"Origin": "https://attacker.invalid", "X-AgentExam-Request": "1"},
        {"Origin": "https://testserver"},
    ],
)
def test_login_requires_a_trusted_origin_and_non_simple_request(identity_api, headers):
    response = identity_api.client.post(
        "/api/v1/auth/login",
        json={"username": "owner", "password": PASSWORD},
        headers=headers,
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"
    assert "set-cookie" not in response.headers


def test_invalid_requests_never_echo_passwords_or_privilege_fields(identity_api):
    response = identity_api.login(role="owner", owner_id=PASSWORD)
    assert response.status_code == 422
    assert PASSWORD not in response.text
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"
    assert identity_api.client.get("/api/v1/auth/me").status_code == 401


def test_unavailable_database_is_a_safe_503_not_a_false_authentication_failure():
    class UnavailableDatabase(MemoryIdentityRepository):
        def find_account(self, username):
            raise IdentityUnavailable("synthetic connection secret")

    service = IdentityService(UnavailableDatabase(), Argon2Passwords())
    app = create_app(service, HttpConfig(public_origin="https://testserver"))
    with TestClient(
        app, base_url="https://testserver", raise_server_exceptions=False
    ) as client:
        response = client.post(
            "/api/v1/auth/login",
            json={"username": "owner", "password": PASSWORD},
            headers=WRITE_HEADERS,
        )
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "DEPENDENCY_UNAVAILABLE"
    assert "synthetic connection secret" not in response.text


def test_login_attempts_are_bounded_even_with_changing_usernames(identity_api):
    for index in range(10):
        response = identity_api.client.post(
            "/api/v1/auth/login",
            json={"username": f"unknown{index}", "password": PASSWORD},
            headers=WRITE_HEADERS,
        )
        assert response.status_code == 401
    response = identity_api.login()
    assert response.status_code == 429
    assert response.json()["error"]["code"] == "RATE_LIMITED"
    assert int(response.headers["retry-after"]) > 0


def test_logout_rejects_unexpected_body_fields(identity_api):
    assert identity_api.login().status_code == 200
    response = identity_api.client.post(
        "/api/v1/auth/logout", json={"owner_id": "forged"}, headers=WRITE_HEADERS
    )
    assert response.status_code == 422
    assert identity_api.client.get("/api/v1/auth/me").status_code == 200


@pytest.mark.parametrize(
    "body",
    [
        {"username": "owner", "password": "x" * 129},
        {"username": "owner", "password": 12345},
        {"username": "OWNER", "password": PASSWORD},
        {"username": "owner", "password": PASSWORD, "role": "owner"},
    ],
)
def test_malformed_login_inputs_do_not_authenticate_or_echo_secrets(identity_api, body):
    response = identity_api.client.post(
        "/api/v1/auth/login", json=body, headers=WRITE_HEADERS
    )
    assert response.status_code == 422
    assert response.json()["error"]["details"] == {}
    assert "input" not in response.text
    assert "set-cookie" not in response.headers


def test_wrong_password_and_unknown_account_have_the_same_public_error(identity_api):
    wrong = identity_api.login(password="incorrect synthetic password")
    unknown = identity_api.client.post(
        "/api/v1/auth/login",
        json={"username": "missing", "password": PASSWORD},
        headers=WRITE_HEADERS,
    )
    assert wrong.status_code == unknown.status_code == 401
    for key in ("code", "message", "details"):
        assert wrong.json()["error"][key] == unknown.json()["error"][key]


@pytest.mark.parametrize("origin", ["http://example.com", "http://127.0.0.1:3000/path"])
def test_insecure_or_path_bearing_public_origin_cannot_start_http(origin):
    with pytest.raises(ValueError):
        HttpConfig(public_origin=origin, allow_insecure_loopback=True)


def test_unexpected_dependency_failure_has_a_safe_structured_error(caplog):
    class BrokenDatabase(MemoryIdentityRepository):
        def find_account(self, username):
            raise RuntimeError("synthetic unexpected secret")

    service = IdentityService(BrokenDatabase(), Argon2Passwords())
    app = create_app(service, HttpConfig(public_origin="https://testserver"))
    with caplog.at_level(logging.ERROR, logger="eval_platform.http"):
        with TestClient(
            app, base_url="https://testserver", raise_server_exceptions=False
        ) as client:
            response = client.post(
                "/api/v1/auth/login",
                json={"username": "owner", "password": PASSWORD},
                headers=WRITE_HEADERS,
            )
    assert response.status_code == 500
    assert response.json()["error"]["code"] == "INTERNAL_ERROR"
    request_id = response.json()["error"]["request_id"]
    assert "synthetic unexpected secret" not in response.text + caplog.text
    record = next(
        record
        for record in caplog.records
        if getattr(record, "request_id", None) == request_id
    )
    assert record.method == "POST"
    assert record.path == "/api/v1/auth/login"
    assert record.exception_type == "RuntimeError"


@pytest.mark.parametrize(
    ("path", "status", "code"),
    [
        ("/api/v1/auth/login", 405, "METHOD_NOT_ALLOWED"),
        ("/api/v1/auth/unknown", 404, "RESOURCE_NOT_FOUND"),
    ],
)
def test_framework_http_errors_use_safe_api_errors(identity_api, path, status, code):
    response = identity_api.client.get(path)
    assert response.status_code == status
    assert set(response.json()) == {"error"}
    assert response.json()["error"]["code"] == code
    assert response.json()["error"]["details"] == {}
    assert response.json()["error"]["request_id"].startswith("req_")
    assert response.headers["cache-control"] == "no-store"
    if status == 405:
        assert response.headers["allow"] == "POST"
