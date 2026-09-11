"""Opt-in tests against an explicitly isolated, disposable PostgreSQL database."""

import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from threading import Barrier

import psycopg
import pytest
from fastapi.testclient import TestClient

from eval_platform.adapters.identity.passwords import Argon2Passwords
from eval_platform.application.identity import IdentityService
from eval_platform.delivery.http.app import create_app
from eval_platform.delivery.http.config import HttpConfig
from eval_platform.domain.identity import (
    AuthenticationRequired,
    IdentityConflict,
    IdentityUnavailable,
)
from identity.conftest import PASSWORD, WRITE_HEADERS, Clock

pytestmark = pytest.mark.integration


def test_postgres_owner_survives_new_application_and_concurrent_bootstrap(
    postgres_sandbox,
):
    passwords = Argon2Passwords()
    service = IdentityService(postgres_sandbox.repository, passwords)

    def bootstrap():
        try:
            return service.bootstrap_owner("owner", PASSWORD)
        except IdentityConflict:
            return None

    with ThreadPoolExecutor(max_workers=2) as pool:
        created = list(pool.map(lambda _: bootstrap(), range(2)))
    owners = [owner for owner in created if owner is not None]
    assert len(owners) == 1
    with pytest.raises(IdentityConflict):
        service.bootstrap_owner("second_owner", PASSWORD)
    restarted = IdentityService(postgres_sandbox.repository, passwords)
    app = create_app(restarted, HttpConfig(public_origin="https://testserver"))
    with TestClient(app, base_url="https://testserver") as client:
        response = client.post(
            "/api/v1/auth/login",
            json={"username": "owner", "password": PASSWORD},
            headers=WRITE_HEADERS,
        )
        assert response.status_code == 200
        assert client.get("/api/v1/auth/me").json()["user_id"] == owners[0].user_id
        before_recovery_cookie = client.cookies.get("__Host-agentexam_session")
        recovered = restarted.recover_owner("owner", "new synthetic postgres password")
        assert recovered.user_id == owners[0].user_id
        assert client.get("/api/v1/auth/me").status_code == 401
        old_login = client.post(
            "/api/v1/auth/login",
            json={"username": "owner", "password": PASSWORD},
            headers=WRITE_HEADERS,
        )
        assert old_login.status_code == 401
        current = client.post(
            "/api/v1/auth/login",
            json={"username": "owner", "password": "new synthetic postgres password"},
            headers=WRITE_HEADERS,
        )
        assert current.json()["user_id"] == owners[0].user_id
        assert (
            client.get(
                "/api/v1/auth/me",
                headers={
                    "Cookie": f"__Host-agentexam_session={before_recovery_cookie}"
                },
            ).status_code
            == 401
        )


def test_failed_recovery_rolls_back_password_and_keeps_existing_session(
    postgres_sandbox,
):
    service = IdentityService(postgres_sandbox.repository, Argon2Passwords())
    owner = service.bootstrap_owner("owner", PASSWORD)
    previous = service.login("owner", PASSWORD)
    with psycopg.connect(postgres_sandbox.dsn) as connection:
        connection.execute("""
            CREATE FUNCTION reject_session_delete() RETURNS trigger
            LANGUAGE plpgsql AS $$ BEGIN
                RAISE EXCEPTION 'synthetic recovery failure';
            END $$;
            CREATE TRIGGER fail_recovery BEFORE DELETE ON sessions
            FOR EACH STATEMENT EXECUTE FUNCTION reject_session_delete();
        """)
    with pytest.raises(IdentityUnavailable):
        service.recover_owner("owner", "new synthetic postgres password")
    assert service.current_actor(previous.token) == owner
    assert service.login("owner", PASSWORD).actor == owner


@pytest.mark.parametrize("attempt", range(3))
def test_concurrent_login_cannot_preserve_old_access_after_recovery(
    postgres_sandbox, attempt
):
    service = IdentityService(postgres_sandbox.repository, Argon2Passwords())
    owner = service.bootstrap_owner("owner", PASSWORD)
    barrier = Barrier(2, timeout=10)

    def login():
        barrier.wait()
        try:
            return service.login("owner", PASSWORD)
        except AuthenticationRequired:
            return None

    def recover():
        barrier.wait()
        return service.recover_owner("owner", "new synthetic postgres password")

    with ThreadPoolExecutor(max_workers=2) as pool:
        pending_login = pool.submit(login)
        pending_recovery = pool.submit(recover)
        assert pending_recovery.result(timeout=15) == owner
        previous = pending_login.result(timeout=15)
    if previous is not None:
        with pytest.raises(AuthenticationRequired):
            service.current_actor(previous.token)
    with pytest.raises(AuthenticationRequired):
        service.login("owner", PASSWORD)
    assert service.login("owner", "new synthetic postgres password").actor == owner


def test_session_survives_another_process_but_not_expiry_or_logout(postgres_sandbox):
    clock = Clock()
    clock.value = datetime.now(UTC)
    service = IdentityService(postgres_sandbox.repository, Argon2Passwords(), clock)
    owner = service.bootstrap_owner("owner", PASSWORD)
    previous = service.login("owner", PASSWORD)
    program = """
import os
from fastapi.testclient import TestClient
from eval_platform.delivery.http.app import create_runtime_app
with TestClient(create_runtime_app(), base_url='https://testserver') as client:
    response = client.get('/api/v1/auth/me', headers={
        'Cookie': '__Host-agentexam_session=' + os.environ['TEST_SESSION']})
    assert response.status_code == 200
    print(response.json()['user_id'])
"""
    result = subprocess.run(
        [sys.executable, "-c", program],
        env=dict(
            os.environ,
            AGENTEXAM_DATABASE_URL=postgres_sandbox.dsn,
            AGENTEXAM_PUBLIC_ORIGIN="https://testserver",
            TEST_SESSION=previous.token,
        ),
        capture_output=True,
        text=True,
        timeout=15,
    )
    assert result.returncode == 0
    assert result.stdout.strip() == owner.user_id
    clock.advance(8 * 60 * 60)
    with pytest.raises(AuthenticationRequired):
        service.current_actor(previous.token)
    current = service.login("owner", PASSWORD)
    service.logout(current.token)
    with pytest.raises(AuthenticationRequired):
        service.current_actor(current.token)
