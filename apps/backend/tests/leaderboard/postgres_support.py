import os
from contextlib import contextmanager
from dataclasses import dataclass
from uuid import uuid4

import psycopg
import pytest
from psycopg import sql
from psycopg.conninfo import conninfo_to_dict, make_conninfo


@dataclass(frozen=True, slots=True)
class LeaderboardPostgres:
    dsn: str


@contextmanager
def isolated_postgres():
    if os.environ.get("AGENTEXAM_RUN_LEADERBOARD_POSTGRES") != "1":
        pytest.skip("专属排行榜 PostgreSQL 测试未显式启用")
    dsn = os.environ.get("AGENTEXAM_TEST_DATABASE_URL", "")
    try:
        settings = conninfo_to_dict(dsn)
    except psycopg.Error:
        pytest.fail("无效的专属测试数据库配置", pytrace=False)
    if (
        settings.get("host") != "127.0.0.1"
        or settings.get("dbname") != "agentexam_identity_test"
        or settings.get("user") != "agentexam_identity_test"
        or settings.get("port") in {None, "5432"}
    ):
        pytest.fail("拒绝非专属回环测试数据库", pytrace=False)
    database = "leaderboard_" + uuid4().hex
    with psycopg.connect(dsn, autocommit=True, connect_timeout=3) as connection:
        connection.execute(
            sql.SQL("CREATE DATABASE {}").format(sql.Identifier(database))
        )
        try:
            yield LeaderboardPostgres(make_conninfo(dsn, dbname=database))
        finally:
            connection.execute(
                sql.SQL("DROP DATABASE {}").format(sql.Identifier(database))
            )
