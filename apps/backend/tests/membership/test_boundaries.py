from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from identity.conftest import ORIGIN, PASSWORD, WRITE_HEADERS

from eval_platform.adapters.identity.passwords import Argon2Passwords
from eval_platform.application.identity import IdentityService
from eval_platform.application.membership import MembershipService
from eval_platform.delivery.http.app import create_app
from eval_platform.delivery.http.config import HttpConfig
from eval_platform.domain.identity import IdentityUnavailable
from membership.conftest import invite, redeem
from membership.memory import MemoryMembershipRepository


@pytest.mark.parametrize("role", ["anonymous", "collaborator"])
def test_management_requires_owner_at_every_http_entry(identity_api, role):
    invitation = invite(identity_api)
    actor = redeem(identity_api, invitation["invitation_token"]).json()
    identity_api.client.cookies.clear()
    if role == "collaborator":
        login = identity_api.client.post(
            "/api/v1/auth/login",
            json={"username": "teammate", "password": PASSWORD},
            headers=WRITE_HEADERS,
        )
        assert login.status_code == 200
    expected = 401 if role == "anonymous" else 403
    for path in ("/api/v1/invitations", "/api/v1/members"):
        assert identity_api.client.get(path).status_code == expected
    for path in (
        "/api/v1/invitations",
        f"/api/v1/invitations/{invitation['invitation_id']}/revoke",
        f"/api/v1/members/{actor['user_id']}/disable",
    ):
        response = identity_api.client.post(path, json={}, headers=WRITE_HEADERS)
        assert response.status_code == expected
        assert response.json()["error"]["details"] == {}


def test_owner_cannot_disable_self_or_revoke_a_consumed_invitation(identity_api):
    invitation = invite(identity_api)
    owner = identity_api.client.get("/api/v1/auth/me").json()
    assert redeem(identity_api, invitation["invitation_token"]).status_code == 201
    for path, expected in (
        (f"members/{owner['user_id']}/disable", 403),
        (f"members/{uuid4()}/disable", 404),
        (f"invitations/{uuid4()}/revoke", 410),
        (f"invitations/{invitation['invitation_id']}/revoke", 409),
    ):
        response = identity_api.client.post(
            f"/api/v1/{path}", json={}, headers=WRITE_HEADERS
        )
        assert response.status_code == expected
    assert identity_api.client.get("/api/v1/auth/me").json() == owner
    assert identity_api.client.get("/api/v1/members").json()["items"][0]["active"]


def test_lists_validate_cursors_and_limits_and_derive_expiry(identity_api):
    invite(identity_api)
    for query in ("limit=0", "limit=101", "cursor=not-a-uuid"):
        for path in ("invitations", "members"):
            response = identity_api.client.get(f"/api/v1/{path}?{query}")
            assert response.status_code == 422
    identity_api.clock.advance(86400)
    assert identity_api.login().status_code == 200
    assert (
        identity_api.client.get("/api/v1/invitations").json()["items"][0]["status"]
        == "expired"
    )


def test_members_are_paginated_without_credentials(identity_api):
    actors = []
    for index in range(3):
        token = invite(identity_api)["invitation_token"]
        actors.append(redeem(identity_api, token, f"member{index}").json())
    first = identity_api.client.get("/api/v1/members?limit=2").json()
    last = identity_api.client.get(
        "/api/v1/members", params={"limit": 2, "cursor": first["next_cursor"]}
    ).json()
    assert len(first["items"]) == 2
    assert len(last["items"]) == 1
    assert last["next_cursor"] is None
    items = first["items"] + last["items"]
    assert {item["user_id"] for item in items} == {a["user_id"] for a in actors}
    assert all(set(item) == {"user_id", "username", "active"} for item in items)


def test_membership_dependency_failure_is_safe_and_not_wrong_password(caplog):
    class UnavailableDatabase(MemoryMembershipRepository):
        def redeem_invitation(self, token_hash, account, now):
            raise IdentityUnavailable("synthetic connection secret")

    repository = UnavailableDatabase()
    passwords = Argon2Passwords()
    app = create_app(
        IdentityService(repository, passwords),
        HttpConfig(public_origin=ORIGIN),
        MembershipService(repository, passwords),
    )
    with TestClient(app, base_url=ORIGIN, raise_server_exceptions=False) as client:
        response = client.post(
            "/api/v1/invitations/redeem",
            json={
                "invitation_token": "synthetic secret invitation",
                "username": "teammate",
                "password": PASSWORD,
            },
            headers=WRITE_HEADERS,
        )
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "DEPENDENCY_UNAVAILABLE"
    assert "synthetic connection secret" not in response.text + caplog.text
    assert PASSWORD not in response.text + caplog.text


def test_redeem_requires_same_origin_and_rejects_public_registration(identity_api):
    token = invite(identity_api)["invitation_token"]
    response = identity_api.client.post(
        "/api/v1/invitations/redeem",
        json={"invitation_token": token, "username": "teammate", "password": PASSWORD},
    )
    assert response.status_code == 403
    assert redeem(identity_api, token).status_code == 201
    assert (
        identity_api.client.post(
            "/api/v1/auth/register", json={}, headers=WRITE_HEADERS
        ).status_code
        == 404
    )
