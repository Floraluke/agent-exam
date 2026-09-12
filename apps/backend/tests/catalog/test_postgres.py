from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import UTC, datetime
from hashlib import sha256
from threading import Barrier
from uuid import uuid4

import pytest

from catalog.conftest import task_bundle
from eval_platform.adapters.persistence.catalog import initialize_schema
from eval_platform.adapters.persistence.catalog.tasks import PostgresTaskRepository
from eval_platform.domain.catalog import (
    CatalogConflict,
    CatalogTask,
    CatalogUnavailable,
)
from eval_platform.domain.result import ArtifactRef

pytestmark = pytest.mark.integration


def record(instance_id="example__repo-1"):
    bundle = task_bundle(instance_id)
    now = datetime.now(UTC)
    return CatalogTask(
        str(uuid4()),
        bundle.public,
        str(uuid4()),
        ArtifactRef(
            "tasks/" + instance_id,
            "task_source_snapshot",
            len(bundle.raw_record_json),
            sha256(bundle.raw_record_json).hexdigest(),
            "application/json",
            "long_term",
            created_at=now,
        ),
        now,
    )


def test_concurrent_publication_reuses_one_complete_task(postgres_sandbox):
    initialize_schema(postgres_sandbox.dsn)
    repository = PostgresTaskRepository(postgres_sandbox.dsn)
    barrier = Barrier(2, timeout=10)

    def publish(_):
        candidate = record()
        barrier.wait()
        return repository.publish(candidate)

    with ThreadPoolExecutor(max_workers=2) as pool:
        first, second = pool.map(publish, range(2))
    assert first == second
    restored = PostgresTaskRepository(postgres_sandbox.dsn).get(first.task_id)
    assert restored == first
    assert repository.list({}, None, 20) == [first]
    changed = replace(record(), task=replace(first.task, repo="changed/repo"))
    with pytest.raises(CatalogConflict):
        repository.publish(changed)
    assert repository.get(first.task_id) == first


def test_agent_registration_survives_recreation_and_preserves_disabled_history(
    postgres_sandbox,
):
    from identity.conftest import WRITE_HEADERS

    from catalog.conftest import catalog_api
    from eval_platform.adapters.persistence.catalog.agents import (
        PostgresAgentRepository,
    )

    initialize_schema(postgres_sandbox.dsn)
    with catalog_api(agents=PostgresAgentRepository(postgres_sandbox.dsn)) as api:
        api.login()
        first = api.client.post(
            "/api/v1/agent-configurations",
            json={"preset_id": "verified-codex"},
            headers=WRITE_HEADERS,
        ).json()
    with catalog_api(agents=PostgresAgentRepository(postgres_sandbox.dsn)) as api:
        api.login()
        resource = "/api/v1/agent-configurations/" + first["agent_configuration_id"]
        assert api.client.get(resource).json() == first
        assert (
            api.client.post(
                resource + "/disable", json={}, headers=WRITE_HEADERS
            ).status_code
            == 204
        )
        disabled = api.client.get(resource).json()
        assert disabled["enabled"] is False
        assert (
            api.client.post(
                "/api/v1/agent-configurations",
                json={"preset_id": "verified-codex"},
                headers=WRITE_HEADERS,
            ).json()
            == disabled
        )


def test_real_task_pagination_and_exact_filters(postgres_sandbox):
    from identity.conftest import WRITE_HEADERS

    from catalog.conftest import catalog_api
    from catalog.memory import FixedSource

    initialize_schema(postgres_sandbox.dsn)
    source = FixedSource(task_bundle())
    source.bundles["example__repo-2"] = task_bundle(
        "example__repo-2", repo="second/repo"
    )
    with catalog_api(
        PostgresTaskRepository(postgres_sandbox.dsn),
        source=source,
        presets={"first": "example__repo-1", "second": "example__repo-2"},
    ) as api:
        api.login()
        for preset in ("first", "second"):
            assert (
                api.client.post(
                    "/api/v1/tasks/register",
                    json={"preset_id": preset},
                    headers=WRITE_HEADERS,
                ).status_code
                == 201
            )
        first = api.client.get("/api/v1/tasks?limit=1").json()
        assert len(first["items"]) == 1
        second = api.client.get(
            "/api/v1/tasks?limit=1&cursor=" + first["next_cursor"]
        ).json()
        assert len(second["items"]) == 1 and second["next_cursor"] is None
        assert {
            first["items"][0]["instance_id"],
            second["items"][0]["instance_id"],
        } == {
            "example__repo-1",
            "example__repo-2",
        }
        filtered = api.client.get("/api/v1/tasks?repo=second/repo").json()
        assert [item["instance_id"] for item in filtered["items"]] == [
            "example__repo-2"
        ]


def test_failed_artifact_index_rolls_back_task_publication(postgres_sandbox):
    initialize_schema(postgres_sandbox.dsn)
    repository = PostgresTaskRepository(postgres_sandbox.dsn)
    first = repository.publish(record())
    # The deliberately duplicated immutable object key fails the real index write.
    broken = replace(record("example__repo-2"), source=first.source)
    with pytest.raises(CatalogConflict):
        repository.publish(broken)
    assert repository.list({}, None, 20) == [first]


def test_explicit_upgrade_is_not_destructive_or_automatic(postgres_sandbox):
    repository = PostgresTaskRepository(postgres_sandbox.dsn)
    with pytest.raises(CatalogUnavailable):
        repository.list({}, None, 20)
    initialize_schema(postgres_sandbox.dsn)
    first = repository.publish(record())
    with pytest.raises(CatalogUnavailable):
        initialize_schema(postgres_sandbox.dsn)
    assert repository.get(first.task_id) == first
