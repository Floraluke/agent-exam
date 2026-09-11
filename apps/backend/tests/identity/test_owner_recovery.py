import os
import subprocess
import sys
from types import SimpleNamespace

import pytest

from eval_platform.adapters.identity.passwords import Argon2Passwords
from eval_platform.application.identity import IdentityService
from eval_platform.delivery import owner as owner_cli
from eval_platform.domain.identity import AuthenticationRequired, IdentityConflict
from identity.conftest import PASSWORD


def test_local_recovery_preserves_owner_and_revokes_all_previous_sessions(identity_api):
    first_login = identity_api.login()
    owner_id = first_login.json()["user_id"]
    old_cookie = identity_api.client.cookies.get("__Host-agentexam_session")
    identity_api.login()
    recovered = identity_api.service.recover_owner("owner", "new synthetic password")
    assert recovered.user_id == owner_id
    assert identity_api.client.get("/api/v1/auth/me").status_code == 401
    assert (
        identity_api.client.get(
            "/api/v1/auth/me",
            headers={"Cookie": f"__Host-agentexam_session={old_cookie}"},
        ).status_code
        == 401
    )
    assert identity_api.login(password=PASSWORD).status_code == 401
    response = identity_api.login(password="new synthetic password")
    assert response.status_code == 200
    assert response.json()["user_id"] == owner_id


def test_second_owner_bootstrap_does_not_replace_the_existing_login(identity_api):
    original = identity_api.login().json()
    with pytest.raises(IdentityConflict):
        identity_api.service.bootstrap_owner("second", "synthetic second password")
    assert identity_api.login().json() == original


def test_invalid_recovery_leaves_the_existing_session_usable(identity_api):
    original = identity_api.login().json()
    with pytest.raises(ValueError):
        identity_api.service.recover_owner("owner", "short")
    with pytest.raises(IdentityConflict):
        identity_api.service.recover_owner("missing", "synthetic new password")
    assert identity_api.client.get("/api/v1/auth/me").json() == original


def test_local_cli_refuses_password_pipes_before_connecting_to_a_database():
    environment = dict(os.environ)
    environment.pop("AGENTEXAM_DATABASE_URL", None)
    result = subprocess.run(
        [sys.executable, "-m", "eval_platform.delivery.owner", "bootstrap", "owner"],
        input="synthetic piped password\n",
        text=True,
        capture_output=True,
        env=environment,
        timeout=10,
    )
    assert result.returncode == 2
    assert "synthetic piped password" not in result.stdout + result.stderr


@pytest.mark.integration
def test_local_cli_bootstrap_and_recovery_with_real_persistence(
    postgres_sandbox, monkeypatch, capsys
):
    # Only the terminal device is replaced; CLI, use cases and database are real.
    monkeypatch.setenv("AGENTEXAM_DATABASE_URL", postgres_sandbox.dsn)
    monkeypatch.setattr(owner_cli.sys, "stdin", SimpleNamespace(isatty=lambda: True))
    entered = iter([PASSWORD, PASSWORD])
    monkeypatch.setattr(owner_cli.getpass, "getpass", lambda _: next(entered))
    assert owner_cli.main(["bootstrap", "owner"]) == 0
    service = IdentityService(postgres_sandbox.repository, Argon2Passwords())
    previous = service.login("owner", PASSWORD)
    entered = iter(["new synthetic CLI password", "new synthetic CLI password"])
    assert owner_cli.main(["recover", "owner"]) == 0
    with pytest.raises(AuthenticationRequired):
        service.current_actor(previous.token)
    current = service.login("owner", "new synthetic CLI password")
    assert current.actor == previous.actor
    # Explicit initialization refuses an existing schema without erasing identity.
    assert owner_cli.main(["init-db"]) == 2
    assert service.current_actor(current.token) == previous.actor
    captured = capsys.readouterr()
    assert PASSWORD not in captured.out + captured.err
    assert "new synthetic CLI password" not in captured.out + captured.err
