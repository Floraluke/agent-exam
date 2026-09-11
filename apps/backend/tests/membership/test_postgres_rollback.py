import psycopg
import pytest
from identity.conftest import PASSWORD, WRITE_HEADERS

from eval_platform.delivery.owner import main
from membership.conftest import invite, postgres_client, redeem

pytestmark = pytest.mark.integration


def test_failed_invitation_write_rolls_back_new_account_and_can_retry(
    postgres_sandbox, postgres_api
):
    token = invite(postgres_api)["invitation_token"]
    with psycopg.connect(postgres_sandbox.dsn) as connection:
        connection.execute("""
            CREATE FUNCTION reject_invitation_update() RETURNS trigger
            LANGUAGE plpgsql AS $$ BEGIN
                RAISE EXCEPTION 'synthetic invitation failure';
            END $$;
            CREATE TRIGGER reject_redeem BEFORE UPDATE ON invitations
            FOR EACH ROW EXECUTE FUNCTION reject_invitation_update();
        """)
    response = redeem(postgres_api, token)
    assert response.status_code == 503
    assert "synthetic invitation failure" not in response.text
    assert postgres_api.client.get("/api/v1/members").json()["items"] == []
    assert (
        postgres_api.client.get("/api/v1/invitations").json()["items"][0]["status"]
        == "pending"
    )
    with postgres_client(postgres_sandbox) as client:
        assert (
            client.post(
                "/api/v1/auth/login",
                json={"username": "teammate", "password": PASSWORD},
                headers=WRITE_HEADERS,
            ).status_code
            == 401
        )
    with psycopg.connect(postgres_sandbox.dsn) as connection:
        connection.execute("DROP TRIGGER reject_redeem ON invitations")
    assert redeem(postgres_api, token).status_code == 201


def test_account_name_conflict_does_not_consume_invitation(postgres_api):
    token = invite(postgres_api)["invitation_token"]
    assert redeem(postgres_api, token, "owner").status_code == 409
    assert redeem(postgres_api, token).status_code == 201


def test_failed_session_deletion_rolls_back_member_disable(
    postgres_sandbox, postgres_api
):
    token = invite(postgres_api)["invitation_token"]
    actor = redeem(postgres_api, token).json()
    with postgres_client(postgres_sandbox) as client:
        assert (
            client.post(
                "/api/v1/auth/login",
                json={"username": "teammate", "password": PASSWORD},
                headers=WRITE_HEADERS,
            ).status_code
            == 200
        )
        with psycopg.connect(postgres_sandbox.dsn) as connection:
            connection.execute("""
                CREATE FUNCTION reject_session_delete() RETURNS trigger
                LANGUAGE plpgsql AS $$ BEGIN
                    RAISE EXCEPTION 'synthetic member failure';
                END $$;
                CREATE TRIGGER reject_disable BEFORE DELETE ON sessions
                FOR EACH STATEMENT EXECUTE FUNCTION reject_session_delete();
            """)
        response = postgres_api.client.post(
            f"/api/v1/members/{actor['user_id']}/disable",
            json={},
            headers=WRITE_HEADERS,
        )
        assert response.status_code == 503
        assert client.get("/api/v1/auth/me").json() == actor
        assert postgres_api.client.get("/api/v1/members").json()["items"][0]["active"]
        with psycopg.connect(postgres_sandbox.dsn) as connection:
            connection.execute("DROP TRIGGER reject_disable ON sessions")
        assert (
            postgres_api.client.post(
                f"/api/v1/members/{actor['user_id']}/disable",
                json={},
                headers=WRITE_HEADERS,
            ).status_code
            == 204
        )
        assert client.get("/api/v1/auth/me").status_code == 401


def test_explicit_upgrade_preserves_existing_identity_and_never_resets_schema(
    postgres_sandbox, postgres_api, monkeypatch, capsys
):
    assert postgres_api.login().status_code == 200
    previous = postgres_api.client.get("/api/v1/auth/me").json()
    # Recreate the old task-01 schema in this disposable test database only.
    with psycopg.connect(postgres_sandbox.dsn) as connection:
        connection.execute("DROP TABLE invitations")
    monkeypatch.setenv("AGENTEXAM_DATABASE_URL", postgres_sandbox.dsn)
    assert main(["upgrade-members"]) == 0
    invitation = invite(postgres_api)
    assert main(["upgrade-members"]) == 2
    assert postgres_api.client.get("/api/v1/auth/me").json() == previous
    assert redeem(postgres_api, invitation["invitation_token"]).status_code == 201
    output = capsys.readouterr()
    assert postgres_sandbox.dsn not in output.out + output.err
