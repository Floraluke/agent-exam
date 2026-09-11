import os
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import psycopg
import pytest
from fastapi.testclient import TestClient
from psycopg import sql
from psycopg.conninfo import conninfo_to_dict, make_conninfo

from eval_platform.adapters.identity.passwords import Argon2Passwords
from eval_platform.adapters.persistence.identity import PostgresIdentityRepository
from eval_platform.application.identity import IdentityService
from eval_platform.delivery.http.app import create_app
from eval_platform.delivery.http.config import HttpConfig
from identity.memory import MemoryIdentityRepository

ORIGIN = "https://testserver"
WRITE_HEADERS = {"Origin": ORIGIN, "X-AgentExam-Request": "1"}
PASSWORD = "synthetic owner password"


class Clock:
    def __init__(self):
        self.value = datetime(2026, 9, 11, tzinfo=UTC)

    def __call__(self):
        return self.value

    def advance(self, seconds):
        self.value += timedelta(seconds=seconds)


@dataclass
class IdentityAPI:
    client: TestClient
    service: IdentityService
    clock: Clock

    def login(self, password=PASSWORD, **extra):
        return self.client.post(
            "/api/v1/auth/login",
            json={"username": "owner", "password": password, **extra},
            headers=WRITE_HEADERS,
        )


@pytest.fixture
def identity_api():
    clock = Clock()
    service = IdentityService(MemoryIdentityRepository(), Argon2Passwords(), clock)
    service.bootstrap_owner("owner", PASSWORD)
    app = create_app(service, HttpConfig(public_origin=ORIGIN))
    with TestClient(app, base_url=ORIGIN, raise_server_exceptions=False) as client:
        yield IdentityAPI(client, service, clock)


@dataclass
class PostgresSandbox:
    repository: PostgresIdentityRepository
    dsn: str


@pytest.fixture
def postgres_sandbox():
    if os.environ.get("AGENTEXAM_RUN_IDENTITY_POSTGRES") != "1":
        pytest.skip("专属 PostgreSQL 测试未显式启用")
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
    database = "identity_" + uuid4().hex
    with psycopg.connect(dsn, autocommit=True, connect_timeout=3) as connection:
        connection.execute(
            sql.SQL("CREATE DATABASE {}").format(sql.Identifier(database))
        )
        try:
            isolated_dsn = make_conninfo(dsn, dbname=database)
            repository = PostgresIdentityRepository(isolated_dsn)
            repository.initialize_schema()
            yield PostgresSandbox(repository, isolated_dsn)
        finally:
            connection.execute(
                sql.SQL("DROP DATABASE {}").format(sql.Identifier(database))
            )
