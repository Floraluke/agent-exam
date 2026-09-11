from identity.conftest import PASSWORD, WRITE_HEADERS

from membership.conftest import invite, redeem


def test_owner_invites_and_guest_joins_as_collaborator(identity_api):
    assert identity_api.login().status_code == 200
    invited = identity_api.client.post(
        "/api/v1/invitations", json={}, headers=WRITE_HEADERS
    )
    assert invited.status_code == 201
    token = invited.json()["invitation_token"]
    identity_api.client.post("/api/v1/auth/logout", json={}, headers=WRITE_HEADERS)
    joined = identity_api.client.post(
        "/api/v1/invitations/redeem",
        json={"invitation_token": token, "username": "teammate", "password": PASSWORD},
        headers=WRITE_HEADERS,
    )
    assert joined.status_code == 201
    assert joined.json()["role"] == "collaborator"
    login = identity_api.client.post(
        "/api/v1/auth/login",
        json={"username": "teammate", "password": PASSWORD},
        headers=WRITE_HEADERS,
    )
    assert login.status_code == 200
    assert identity_api.client.get("/api/v1/auth/me").json() == joined.json()


def test_invitation_list_is_paginated_and_never_repeats_the_token(identity_api):
    created = [invite(identity_api) for _ in range(3)]
    page = identity_api.client.get("/api/v1/invitations?limit=2")
    assert page.status_code == 200
    assert len(page.json()["items"]) == 2
    cursor = page.json()["next_cursor"]
    last = identity_api.client.get(
        "/api/v1/invitations", params={"cursor": cursor, "limit": 2}
    )
    items = page.json()["items"] + last.json()["items"]
    assert {item["invitation_id"] for item in items} == {
        item["invitation_id"] for item in created
    }
    assert last.json()["next_cursor"] is None
    assert all(item["status"] == "pending" for item in items)
    for invitation in created:
        assert invitation["invitation_token"] not in page.text + last.text
    assert all(
        "invitation_token" not in item and "token_hash" not in item for item in items
    )


def test_revoked_invitation_cannot_be_used(identity_api):
    invitation = invite(identity_api)
    path = f"/api/v1/invitations/{invitation['invitation_id']}/revoke"
    assert (
        identity_api.client.post(path, json={}, headers=WRITE_HEADERS).status_code
        == 204
    )
    assert (
        identity_api.client.post(path, json={}, headers=WRITE_HEADERS).status_code
        == 204
    )
    assert redeem(identity_api, invitation["invitation_token"]).status_code == 410
    items = identity_api.client.get("/api/v1/invitations").json()["items"]
    assert items[0]["status"] == "revoked"


def test_owner_disables_member_and_old_access_stops_without_deleting_identity(
    identity_api,
):
    invitation = invite(identity_api)
    member = redeem(identity_api, invitation["invitation_token"]).json()
    previous = identity_api.service.login("teammate", PASSWORD)
    path = f"/api/v1/members/{member['user_id']}/disable"
    assert (
        identity_api.client.post(path, json={}, headers=WRITE_HEADERS).status_code
        == 204
    )
    assert (
        identity_api.client.post(path, json={}, headers=WRITE_HEADERS).status_code
        == 204
    )
    response = identity_api.client.get(
        "/api/v1/auth/me",
        headers={
            "Cookie": f"__Host-agentexam_session={previous.token}",
        },
    )
    assert response.status_code == 401
    members = identity_api.client.get("/api/v1/members").json()["items"]
    assert len(members) == 1
    assert members[0]["user_id"] == member["user_id"]
    assert members[0]["active"] is False
    login = identity_api.client.post(
        "/api/v1/auth/login",
        json={
            "username": "teammate",
            "password": PASSWORD,
        },
        headers=WRITE_HEADERS,
    )
    assert login.status_code == 401
