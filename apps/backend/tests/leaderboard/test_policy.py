from dataclasses import replace
from datetime import UTC, datetime, timedelta

from eval_platform.domain.jobs.models import (
    LimitSnapshot,
    NetworkPolicySnapshot,
    ToolProfileSnapshot,
)
from eval_platform.domain.leaderboard import (
    AgentIdentity,
    AttemptMetrics,
    ComparisonScope,
    LeaderboardAttempt,
    LeaderboardTask,
    build_rows,
)

NOW = datetime(2026, 9, 13, tzinfo=UTC)


def scope() -> ComparisonScope:
    return ComparisonScope(
        "swe-bench",
        "rev-1",
        "test",
        "org/repo",
        "closed_book",
        "network-deny-v1",
        NetworkPolicySnapshot("deny", "disabled", False),
        "codex-basic-v1",
        ToolProfileSnapshot("codex", "disabled", True),
        "default-single-host-v1",
        LimitSnapshot(1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0),
        "a" * 40,
        "b" * 40,
        "c" * 40,
        "job-run-v1",
    )


def agent(configuration_id: str) -> AgentIdentity:
    return AgentIdentity(
        configuration_id,
        f"Agent {configuration_id}",
        "codex",
        "0.1.0",
        "openai_chatgpt",
        "gpt-5",
        "high",
        configuration_id[0] * 64,
    )


def attempt(
    configuration_id: str,
    task_id: str,
    minute: int,
    resolved: bool | None,
    *,
    failure_code: str | None = None,
    metrics: AttemptMetrics | None = None,
) -> LeaderboardAttempt:
    at = NOW + timedelta(minutes=minute)
    return LeaderboardAttempt(
        scope(),
        agent(configuration_id),
        task_id,
        f"instance-{task_id}",
        f"job-{configuration_id}-{task_id}-{minute}",
        None,
        f"run-{configuration_id}-{task_id}-{minute}",
        at,
        at,
        "COMPLETED" if resolved is not None else "FAILED",
        "COMPLETED" if resolved is not None else "FAILED",
        failure_code,
        resolved,
        at if resolved is not None else None,
        metrics or AttemptMetrics(),
        "official",
    )


def test_earliest_result_wins_and_retry_only_fills_an_unknown_task() -> None:
    tasks = (
        LeaderboardTask("task-1", "instance-task-1", "org/repo"),
        LeaderboardTask("task-2", "instance-task-2", "org/repo"),
        LeaderboardTask("task-3", "instance-task-3", "org/repo"),
    )
    rows = build_rows(
        tasks,
        (
            attempt("a", "task-1", 1, True),
            attempt("a", "task-1", 2, False),
            attempt("a", "task-2", 3, None, failure_code="AGENT_FAILED"),
            attempt("a", "task-2", 4, True),
        ),
        NOW,
    )

    row = rows[0]
    assert (row.total_tasks, row.deterministic_count, row.resolved_count) == (3, 2, 2)
    assert (
        row.unresolved_count,
        row.infrastructure_error_count,
        row.unknown_count,
    ) == (
        0,
        0,
        1,
    )
    assert [item.run_id for item in row.sources] == [
        "run-a-task-1-1",
        "run-a-task-2-4",
    ]


def test_full_denominator_infrastructure_unknown_metrics_and_ties_are_explicit() -> (
    None
):
    tasks = tuple(
        LeaderboardTask(f"task-{index}", f"instance-{index}", "org/repo")
        for index in range(1, 5)
    )
    complete = AttemptMetrics(10, 2, 4, 0.2, 3.0, 1.0, 256)
    missing = AttemptMetrics(5, None, 2, None, 2.0, None, 128)
    rows = build_rows(
        tasks,
        (
            attempt("a", "task-1", 1, True, metrics=complete),
            attempt(
                "a",
                "task-2",
                2,
                None,
                failure_code="INFRASTRUCTURE_INTERRUPTED",
                metrics=missing,
            ),
            attempt("b", "task-1", 1, True, metrics=complete),
            attempt("b", "task-2", 2, False, metrics=complete),
        ),
        NOW,
    )

    first, second = rows
    assert first.rank == second.rank == 1
    assert first.resolved_rate == second.resolved_rate == 0.25
    assert (first.infrastructure_error_count, first.unknown_count) == (1, 2)
    assert (second.unresolved_count, second.unknown_count) == (1, 2)
    assert first.metrics.n_input_tokens == 15
    assert first.metrics.n_cache_tokens is None
    assert first.metrics.n_cache_tokens_coverage == 1
    assert first.metrics.cost_usd is None
    assert first.metrics.peak_memory_bytes == 256
    assert second.metrics.cost_usd == 0.4


def test_incomparable_frozen_scopes_have_independent_denominators_and_ranks() -> None:
    tasks = (
        LeaderboardTask("task-1", "instance-1", "org/repo"),
        LeaderboardTask("task-2", "instance-2", "other/repo"),
    )
    first = attempt("a", "task-1", 1, True)
    second = replace(
        attempt("b", "task-2", 1, False),
        scope=replace(scope(), repo="other/repo", tool_profile_id="other-tool-v1"),
    )

    rows = build_rows(tasks, (first, second), NOW)

    assert [row.rank for row in rows] == [1, 1]
    assert [row.total_tasks for row in rows] == [1, 1]
    assert {row.scope.tool_profile_id for row in rows} == {
        "codex-basic-v1",
        "other-tool-v1",
    }
