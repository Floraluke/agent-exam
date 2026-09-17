"""Verify the public owner initialization command against an isolated database."""

import os
from collections.abc import Iterator
from uuid import uuid4

import psycopg
import pytest
from eval_platform.delivery import owner as owner_cli
from psycopg import sql
from psycopg.conninfo import conninfo_to_dict, make_conninfo

EXPECTED_TABLES = {
    "accounts",
    "agent_configurations",
    "artifact_records",
    "deterministic_results",
    "evaluation_jobs",
    "evaluation_runs",
    "evaluation_tasks",
    "invitations",
    "job_state_events",
    "run_state_events",
    "sessions",
}


@pytest.fixture
def empty_database() -> Iterator[str]:
    if os.environ.get("AGENTEXAM_RUN_INIT_POSTGRES") != "1":
        pytest.skip("专属初始化 PostgreSQL 测试未显式启用")
    admin_dsn = os.environ.get("AGENTEXAM_INIT_POSTGRES_ADMIN_DSN", "")
    try:
        settings = conninfo_to_dict(admin_dsn)
    except psycopg.Error:
        pytest.fail("无效的专属初始化测试数据库配置", pytrace=False)
    if (
        settings.get("host") != "127.0.0.1"
        or settings.get("dbname") != "agentexam_init_test"
        or settings.get("user") != "agentexam_init_test"
        or settings.get("port") in {None, "5432"}
    ):
        pytest.fail("拒绝非专属回环初始化测试数据库", pytrace=False)
    database = "init_" + uuid4().hex
    with psycopg.connect(admin_dsn, autocommit=True, connect_timeout=3) as connection:
        connection.execute(
            sql.SQL("CREATE DATABASE {}").format(sql.Identifier(database))
        )
        try:
            yield make_conninfo(admin_dsn, dbname=database)
        finally:
            connection.execute(
                "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                "WHERE datname = %s AND pid <> pg_backend_pid()",
                (database,),
            )
            connection.execute(
                sql.SQL("DROP DATABASE {}").format(sql.Identifier(database))
            )


def public_tables(dsn: str) -> set[str]:
    with psycopg.connect(dsn, connect_timeout=3) as connection:
        rows = connection.execute(
            "SELECT tablename FROM pg_catalog.pg_tables WHERE schemaname = 'public'"
        ).fetchall()
    return {str(row[0]) for row in rows}


@pytest.mark.integration
def test_owner_init_db_builds_the_complete_platform_schema(empty_database, monkeypatch):
    monkeypatch.setenv("AGENTEXAM_DATABASE_URL", empty_database)

    assert owner_cli.main(["init-db"]) == 0
    assert public_tables(empty_database) == EXPECTED_TABLES


@pytest.mark.integration
def test_owner_init_db_refuses_nonempty_database_without_changing_it(
    empty_database, monkeypatch
):
    with psycopg.connect(empty_database) as connection:
        connection.execute("CREATE TABLE existing_data (value text NOT NULL)")
        connection.execute("INSERT INTO existing_data VALUES ('keep me')")
    monkeypatch.setenv("AGENTEXAM_DATABASE_URL", empty_database)

    assert owner_cli.main(["init-db"]) == 2
    with psycopg.connect(empty_database) as connection:
        value = connection.execute("SELECT value FROM existing_data").fetchone()
    assert value == ("keep me",)
    assert public_tables(empty_database) == {"existing_data"}
