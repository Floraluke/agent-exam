from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest
from identity.conftest import PASSWORD, WRITE_HEADERS, IdentityAPI

from membership.conftest import invite, postgres_client, redeem

pytestmark = pytest.mark.integration


def test_concurrent_redeem_creates_one_persistent_collaborator(
    postgres_sandbox, postgres_api
):
    invitation = invite(postgres_api)
    barrier = Barrier(2, timeout=10)

    def join(index):
        with postgres_client(postgres_sandbox) as client:
            api = IdentityAPI(client, postgres_api.service, postgres_api.clock)
            barrier.wait()
            return redeem(api, invitation["invitation_token"], f"member{index}")

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(join, range(2)))
    assert sorted(result.status_code for result in results) == [201, 410]
    actor = next(result.json() for result in results if result.status_code == 201)
    with postgres_client(postgres_sandbox) as client:
        assert (
            client.post(
                "/api/v1/auth/login",
                json={"username": actor["username"], "password": PASSWORD},
                headers=WRITE_HEADERS,
            ).json()
            == actor
        )
        assert client.get("/api/v1/auth/me").json() == actor
    assert postgres_api.client.get("/api/v1/members").json()["items"] == [
        {"user_id": actor["user_id"], "username": actor["username"], "active": True}
    ]
    status = postgres_api.client.get("/api/v1/invitations").json()["items"][0]
    assert status["status"] == "redeemed"
    assert status["redeemed_by"] == actor["user_id"]


def test_revoke_and_redeem_are_one_atomic_choice(postgres_sandbox, postgres_api):
    invitation = invite(postgres_api)
    barrier = Barrier(2, timeout=10)

    def join():
        with postgres_client(postgres_sandbox) as client:
            api = IdentityAPI(client, postgres_api.service, postgres_api.clock)
            barrier.wait()
            return redeem(api, invitation["invitation_token"]).status_code

    def revoke():
        barrier.wait()
        return postgres_api.client.post(
            f"/api/v1/invitations/{invitation['invitation_id']}/revoke",
            json={},
            headers=WRITE_HEADERS,
        ).status_code

    with ThreadPoolExecutor(max_workers=2) as pool:
        joined, revoked = pool.submit(join), pool.submit(revoke)
        outcomes = (joined.result(timeout=15), revoked.result(timeout=15))
    assert outcomes in {(201, 409), (410, 204)}
    state = postgres_api.client.get("/api/v1/invitations").json()["items"][0]
    assert state["status"] == ("redeemed" if outcomes[0] == 201 else "revoked")


@pytest.mark.parametrize("attempt", range(3))
def test_member_login_cannot_keep_access_after_disable(
    postgres_sandbox, postgres_api, attempt
):
    token = invite(postgres_api)["invitation_token"]
    actor = redeem(postgres_api, token).json()
    barrier = Barrier(2, timeout=10)

    def login():
        with postgres_client(postgres_sandbox) as client:
            barrier.wait()
            response = client.post(
                "/api/v1/auth/login",
                json={"username": "teammate", "password": PASSWORD},
                headers=WRITE_HEADERS,
            )
            assert response.status_code in {200, 401}
            return client.cookies.get("__Host-agentexam_session")

    def disable():
        barrier.wait()
        return postgres_api.client.post(
            f"/api/v1/members/{actor['user_id']}/disable",
            json={},
            headers=WRITE_HEADERS,
        ).status_code

    with ThreadPoolExecutor(max_workers=2) as pool:
        pending_login, pending_disable = pool.submit(login), pool.submit(disable)
        assert pending_disable.result(timeout=15) == 204
        old_token = pending_login.result(timeout=15)
    with postgres_client(postgres_sandbox) as client:
        if old_token:
            assert (
                client.get(
                    "/api/v1/auth/me",
                    headers={"Cookie": f"__Host-agentexam_session={old_token}"},
                ).status_code
                == 401
            )
        assert (
            client.post(
                "/api/v1/auth/login",
                json={"username": "teammate", "password": PASSWORD},
                headers=WRITE_HEADERS,
            ).status_code
            == 401
        )
    assert postgres_api.client.get("/api/v1/members").json()["items"] == [
        {"user_id": actor["user_id"], "username": "teammate", "active": False}
    ]
