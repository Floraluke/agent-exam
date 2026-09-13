"""Approved duplicate, denominator, classification and tie policy."""

from dataclasses import replace
from datetime import datetime
from typing import cast

from eval_platform.domain.leaderboard.models import (
    AgentIdentity,
    Classification,
    ComparisonScope,
    LeaderboardAttempt,
    LeaderboardRow,
    LeaderboardSource,
    LeaderboardTask,
    MetricSummary,
)

_TERMINAL_JOBS = {"COMPLETED", "COMPLETED_WITH_ERRORS", "FAILED", "CANCELED"}


def build_rows(
    tasks: tuple[LeaderboardTask, ...],
    attempts: tuple[LeaderboardAttempt, ...],
    generated_at: datetime,
    visible_scope: str = "official",
) -> tuple[LeaderboardRow, ...]:
    known_tasks = {task.task_id: task for task in tasks}
    eligible = tuple(
        item
        for item in attempts
        if item.result_scope == visible_scope
        and item.job_status in _TERMINAL_JOBS
        and item.task_id in known_tasks
        and known_tasks[item.task_id].repo == item.scope.repo
    )
    grouped: dict[tuple[ComparisonScope, AgentIdentity], list[LeaderboardAttempt]] = {}
    for item in eligible:
        grouped.setdefault((item.scope, item.agent), []).append(item)
    rows = [
        _row(key, values, known_tasks, generated_at) for key, values in grouped.items()
    ]
    rows.sort(
        key=lambda item: (
            _scope_key(item.scope),
            -item.resolved_count,
            _agent_key(item.agent),
        )
    )
    ranked: list[LeaderboardRow] = []
    previous_scope: ComparisonScope | None = None
    previous_score = -1
    scope_position = 0
    rank = 0
    for row in rows:
        scope_position = scope_position + 1 if row.scope == previous_scope else 1
        if row.scope != previous_scope:
            rank, previous_score = 1, row.resolved_count
        elif row.resolved_count != previous_score:
            rank, previous_score = scope_position, row.resolved_count
        ranked.append(replace(row, rank=rank))
        previous_scope = row.scope
    return tuple(ranked)


def _row(
    key: tuple[ComparisonScope, AgentIdentity],
    attempts: list[LeaderboardAttempt],
    tasks: dict[str, LeaderboardTask],
    generated_at: datetime,
) -> LeaderboardRow:
    scope, agent = key
    denominator = sorted(
        (task for task in tasks.values() if task.repo == scope.repo),
        key=lambda item: item.task_id,
    )
    selected: list[LeaderboardAttempt] = []
    counts: dict[Classification, int] = {
        "resolved": 0,
        "unresolved": 0,
        "infrastructure_error": 0,
        "unknown": 0,
    }
    sources: list[LeaderboardSource] = []
    for task in denominator:
        candidates = [item for item in attempts if item.task_id == task.task_id]
        results = [item for item in candidates if item.resolved is not None]
        choice = (
            min(results, key=_earliest)
            if results
            else max(candidates, key=_latest)
            if candidates
            else None
        )
        classification = _classification(choice)
        counts[classification] += 1
        if choice is not None:
            selected.append(choice)
            sources.append(
                LeaderboardSource(
                    task.task_id,
                    task.instance_id,
                    choice.job_id,
                    choice.run_id,
                    choice.rerun_of_job_id,
                    classification,
                )
            )
    return LeaderboardRow(
        0,
        scope,
        agent,
        len(denominator),
        counts["resolved"] + counts["unresolved"],
        counts["resolved"],
        counts["unresolved"],
        counts["infrastructure_error"],
        counts["unknown"],
        _metrics(selected),
        tuple(sources),
        generated_at,
    )


def _classification(item: LeaderboardAttempt | None) -> Classification:
    if item is None:
        return "unknown"
    if item.resolved is not None:
        return "resolved" if item.resolved else "unresolved"
    return "infrastructure_error" if item.run_status == "FAILED" else "unknown"


def _metrics(items: list[LeaderboardAttempt]) -> MetricSummary:
    def aggregate(name: str, maximum: bool = False) -> tuple[int | float | None, int]:
        present = [
            getattr(item.metrics, name)
            for item in items
            if getattr(item.metrics, name) is not None
        ]
        value = (
            None
            if len(present) != len(items)
            else (max(present) if maximum else sum(present))
        )
        return value, len(present)

    input_tokens = aggregate("n_input_tokens")
    cache_tokens = aggregate("n_cache_tokens")
    output_tokens = aggregate("n_output_tokens")
    cost = aggregate("cost_usd")
    wall = aggregate("wall_time_sec")
    cpu = aggregate("cpu_time_sec")
    memory = aggregate("peak_memory_bytes", maximum=True)
    return MetricSummary(
        len(items),
        cast(int | None, input_tokens[0]),
        input_tokens[1],
        cast(int | None, cache_tokens[0]),
        cache_tokens[1],
        cast(int | None, output_tokens[0]),
        output_tokens[1],
        cost[0],
        cost[1],
        wall[0],
        wall[1],
        cpu[0],
        cpu[1],
        cast(int | None, memory[0]),
        memory[1],
    )


def _earliest(item: LeaderboardAttempt) -> tuple[datetime, datetime, str]:
    assert item.result_created_at is not None
    return item.result_created_at, item.job_created_at, item.run_id


def _latest(item: LeaderboardAttempt) -> tuple[datetime, datetime, str]:
    return item.finished_at, item.job_created_at, item.run_id


def _scope_key(scope: ComparisonScope) -> tuple[str, ...]:
    fields = ComparisonScope.__dataclass_fields__
    return tuple(str(getattr(scope, name)) for name in fields)


def _agent_key(agent: AgentIdentity) -> tuple[str, ...]:
    fields = AgentIdentity.__dataclass_fields__
    return tuple(str(getattr(agent, name)) for name in fields)
