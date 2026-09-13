from dataclasses import replace

LEADERBOARD_QUERY = {
    "evaluation_track": "closed_book",
    "dataset_id": "swe-bench",
    "dataset_revision": "rev-1",
    "split": "test",
}


def test_leaderboard_requires_an_application_session(leaderboard_api) -> None:
    response = leaderboard_api.client.get(
        "/api/v1/leaderboard", params=LEADERBOARD_QUERY
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "AUTHENTICATION_REQUIRED"


def test_leaderboard_exposes_conditions_counts_unknown_metrics_and_sources(
    leaderboard_api,
) -> None:
    assert leaderboard_api.login().status_code == 200

    response = leaderboard_api.client.get(
        "/api/v1/leaderboard", params=LEADERBOARD_QUERY
    )

    assert response.status_code == 200
    body = response.json()
    assert body["next_cursor"] is None
    row = body["items"][0]
    assert row["rank"] == 1
    assert row["comparison_scope"]["dataset_revision"] == "rev-1"
    assert row["comparison_scope"]["network_policy_id"] == "network-deny-v1"
    assert row["agent"]["model"] == "gpt-5"
    assert "credential_profile_id" not in str(row)
    assert row["total_tasks"] == 2
    assert row["deterministic_count"] == row["resolved_count"] == 1
    assert row["unknown_count"] == 1
    assert row["resolved_rate"] == 0.5
    assert row["quality_tiebreak"] is None
    metrics = row["process_metrics"]
    assert metrics["n_input_tokens"] == {"value": 10, "coverage": 1}
    assert metrics["n_cache_tokens"] == {"value": None, "coverage": 0}
    assert row["sources"][0]["run_id"] == "44444444-4444-4444-4444-444444444444"
    assert leaderboard_api.repository.queries[0].repo is None


def test_leaderboard_rejects_unknown_duplicate_and_disabled_track_queries(
    leaderboard_api,
) -> None:
    assert leaderboard_api.login().status_code == 200
    invalid = leaderboard_api.client.get(
        "/api/v1/leaderboard?evaluation_track=closed_book&dataset_id=swe-bench"
        "&dataset_revision=rev-1&split=test&split=test&unexpected=1"
    )
    disabled = leaderboard_api.client.get(
        "/api/v1/leaderboard",
        params={**LEADERBOARD_QUERY, "evaluation_track": "open_book"},
    )

    assert invalid.status_code == 400
    assert invalid.json()["error"]["code"] == "INVALID_REQUEST"
    assert disabled.status_code == 400
    assert disabled.json()["error"]["code"] == "EVALUATION_TRACK_NOT_ENABLED"


def test_leaderboard_paginates_with_an_opaque_non_scoring_cursor(
    leaderboard_api,
) -> None:
    first = leaderboard_api.repository.rows[0]
    second = replace(
        first,
        agent=replace(
            first.agent,
            agent_configuration_id="66666666-6666-6666-6666-666666666666",
            configuration_fingerprint="e" * 64,
        ),
    )
    leaderboard_api.repository.rows = (first, second)
    assert leaderboard_api.login().status_code == 200

    page = leaderboard_api.client.get(
        "/api/v1/leaderboard", params={**LEADERBOARD_QUERY, "limit": 1}
    ).json()
    following = leaderboard_api.client.get(
        "/api/v1/leaderboard",
        params={**LEADERBOARD_QUERY, "limit": 1, "cursor": page["next_cursor"]},
    )

    assert len(page["items"]) == 1 and page["next_cursor"] is not None
    assert following.status_code == 200
    configuration_id = following.json()["items"][0]["agent"]["agent_configuration_id"]
    assert configuration_id.startswith("66666666")
    assert following.json()["next_cursor"] is None


def test_leaderboard_empty_invalid_cursor_and_dependency_errors_are_explicit(
    leaderboard_api,
) -> None:
    assert leaderboard_api.login().status_code == 200
    leaderboard_api.repository.rows = ()
    empty = leaderboard_api.client.get("/api/v1/leaderboard", params=LEADERBOARD_QUERY)
    invalid = leaderboard_api.client.get(
        "/api/v1/leaderboard",
        params={**LEADERBOARD_QUERY, "cursor": "f" * 64},
    )
    leaderboard_api.repository.unavailable = True
    unavailable = leaderboard_api.client.get(
        "/api/v1/leaderboard", params=LEADERBOARD_QUERY
    )

    assert empty.json() == {"items": [], "next_cursor": None}
    assert invalid.status_code == 400
    assert invalid.json()["error"]["code"] == "INVALID_CURSOR"
    assert unavailable.status_code == 503
    assert unavailable.json()["error"]["code"] == "DEPENDENCY_UNAVAILABLE"
