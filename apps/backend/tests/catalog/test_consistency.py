import pytest
from identity.conftest import WRITE_HEADERS
from psycopg.conninfo import make_conninfo

from catalog.conftest import catalog_api, task_bundle
from catalog.memory import FixedSource
from eval_platform.adapters.artifacts.minio import MinioArtifactStore
from eval_platform.adapters.persistence.catalog import initialize_schema
from eval_platform.adapters.persistence.catalog.tasks import PostgresTaskRepository


def register(api):
    return api.client.post(
        "/api/v1/tasks/register",
        json={"preset_id": "verified-task"},
        headers=WRITE_HEADERS,
    )


@pytest.mark.integration
def test_real_object_failure_does_not_publish_half_a_task(
    postgres_sandbox, minio_sandbox
):
    initialize_schema(postgres_sandbox.dsn)
    repository = PostgresTaskRepository(postgres_sandbox.dsn)
    store, service, bucket = minio_sandbox
    unavailable = MinioArtifactStore(service, bucket + "-missing")
    with catalog_api(repository, unavailable) as api:
        assert api.login().status_code == 200
        response = register(api)
        assert response.status_code == 503
        assert response.json()["error"]["details"] == {}
        assert api.client.get("/api/v1/tasks").json()["items"] == []
    with catalog_api(PostgresTaskRepository(postgres_sandbox.dsn), store) as api:
        api.login()
        assert register(api).status_code == 201


@pytest.mark.integration
def test_database_failure_then_reentry_uses_verified_snapshot(
    postgres_sandbox, minio_sandbox
):
    initialize_schema(postgres_sandbox.dsn)
    store, _, _ = minio_sandbox
    broken = PostgresTaskRepository(make_conninfo(postgres_sandbox.dsn, port="59998"))
    with catalog_api(broken, store) as api:
        api.login()
        response = register(api)
        assert response.status_code == 503
        assert "password" not in response.text.lower()
    repository = PostgresTaskRepository(postgres_sandbox.dsn)
    with catalog_api(repository, store) as api:
        api.login()
        assert api.client.get("/api/v1/tasks").json()["items"] == []
        first = register(api)
        assert first.status_code == 201
        assert register(api).json() == first.json()


@pytest.mark.integration
def test_real_content_drift_keeps_original_identity(postgres_sandbox, minio_sandbox):
    initialize_schema(postgres_sandbox.dsn)
    store, _, _ = minio_sandbox
    source = FixedSource(task_bundle())
    with catalog_api(
        PostgresTaskRepository(postgres_sandbox.dsn), store, source
    ) as api:
        api.login()
        first = register(api).json()
        source.bundles["example__repo-1"] = task_bundle(repo="changed/repo")
        response = register(api)
        assert response.status_code == 409
        assert response.json()["error"]["code"] == "CATALOG_CONFLICT"
        assert api.client.get("/api/v1/tasks/" + first["task_id"]).json() == first


@pytest.mark.integration
def test_missing_published_snapshot_is_not_presented_as_complete(
    postgres_sandbox, minio_sandbox
):
    initialize_schema(postgres_sandbox.dsn)
    store, service, bucket = minio_sandbox
    repository = PostgresTaskRepository(postgres_sandbox.dsn)
    with catalog_api(repository, store) as api:
        api.login()
        task = register(api).json()
        source = repository.get(task["task_id"]).source
        service.delete_object(Bucket=bucket, Key=source.object_key)
        for path in ("/api/v1/tasks", "/api/v1/tasks/" + task["task_id"]):
            response = api.client.get(path)
            assert response.status_code == 503
            assert "HIDDEN_ANSWER" not in response.text
            assert source.object_key not in response.text
