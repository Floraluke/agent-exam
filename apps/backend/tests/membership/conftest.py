from contextlib import contextmanager
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient
from identity.conftest import (
    ORIGIN,
    PASSWORD,
    Clock,
    IdentityAPI,
    postgres_sandbox,  # noqa: F401
)

from eval_platform.adapters.identity.passwords import Argon2Passwords
from eval_platform.adapters.persistence.membership import PostgresMembershipRepository
from eval_platform.application.identity import IdentityService
from eval_platform.application.membership import MembershipService
from eval_platform.delivery.http.app import create_app
from eval_platform.delivery.http.config import HttpConfig
from membership.memory import MemoryMembershipRepository


def invite(api):
    assert api.login().status_code == 200
    response = api.client.post(
        "/api/v1/invitations",
        json={},
        headers={
            "Origin": ORIGIN,
            "X-AgentExam-Request": "1",
        },
    )
    assert response.status_code == 201
    return response.json()


def redeem(api, token, username="teammate", **extra):
    return api.client.post(
        "/api/v1/invitations/redeem",
        json={
            "invitation_token": token,
            "username": username,
            "password": PASSWORD,
            **extra,
        },
        headers={"Origin": ORIGIN, "X-AgentExam-Request": "1"},
    )


@pytest.fixture
def identity_api():
    clock = Clock()
    repository = MemoryMembershipRepository()
    passwords = Argon2Passwords()
    service = IdentityService(repository, passwords, clock)
    service.bootstrap_owner("owner", PASSWORD)
    membership = MembershipService(repository, passwords, clock)
    app = create_app(service, HttpConfig(public_origin=ORIGIN), membership)
    with TestClient(app, base_url=ORIGIN, raise_server_exceptions=False) as client:
        yield IdentityAPI(client, service, clock)


@contextmanager
def postgres_client(sandbox):
    passwords = Argon2Passwords()
    app = create_app(
        IdentityService(sandbox.repository, passwords),
        HttpConfig(public_origin=ORIGIN),
        MembershipService(PostgresMembershipRepository(sandbox.dsn), passwords),
    )
    with TestClient(app, base_url=ORIGIN, raise_server_exceptions=False) as client:
        yield client


@pytest.fixture
def postgres_api(postgres_sandbox):  # noqa: F811 - pytest injects the imported fixture
    clock = Clock()
    clock.value = datetime.now(UTC)
    service = IdentityService(postgres_sandbox.repository, Argon2Passwords(), clock)
    service.bootstrap_owner("owner", PASSWORD)
    with postgres_client(postgres_sandbox) as client:
        yield IdentityAPI(client, service, clock)
