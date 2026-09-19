"""Read-only task × configuration matrix over existing Job reports.

任务 03/08 要求的"缺失"语义在此先行落地为原型：没有 Run，或 Run 已完成但报告
缺失时，单元格记为 missing；既不并入 unresolved，也不写成 0 或 false。
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal

from eval_platform.domain.jobs.execution import JobReport
from eval_platform.domain.jobs.models import EvaluationRun, run_order_key

MatrixCell = Literal[
    "resolved",
    "unresolved",
    "infrastructure_error",
    "incomplete",
    "missing",
]


@dataclass(frozen=True, slots=True)
class MatrixColumn:
    """One Job × Agent configuration pair occupying a matrix column."""

    job_id: str
    agent_configuration_id: str
    agent_display_name: str


@dataclass(frozen=True, slots=True)
class MatrixCellValue:
    outcome: MatrixCell
    run_id: str | None
    resolved: bool | None
    failure_code: str | None
    report_path: str | None


@dataclass(frozen=True, slots=True)
class MatrixRow:
    task_instance_id: str
    repo: str
    cells: tuple[MatrixCellValue, ...]


@dataclass(frozen=True, slots=True)
class MatrixColumnTotals:
    resolved: int
    unresolved: int
    infrastructure_error: int
    incomplete: int
    missing: int


@dataclass(frozen=True, slots=True)
class ReportMatrix:
    columns: tuple[MatrixColumn, ...]
    rows: tuple[MatrixRow, ...]
    totals: tuple[MatrixColumnTotals, ...]


def build_matrix(reports: Sequence[JobReport]) -> ReportMatrix:
    """Aggregate job reports into one task × configuration matrix."""
    columns: list[MatrixColumn] = []
    runs_by_task: list[dict[str, EvaluationRun]] = []
    reported_runs: list[frozenset[str]] = []
    tasks: dict[str, str] = {}

    for report in reports:
        reported = frozenset(item.run.run_id for item in report.run_reports)
        grouped: dict[str, list[EvaluationRun]] = {}
        for run in sorted(report.job.runs, key=run_order_key):
            grouped.setdefault(run.agent.agent_configuration_id, []).append(run)
        for runs in grouped.values():
            columns.append(
                MatrixColumn(
                    report.job.job_id,
                    runs[0].agent.agent_configuration_id,
                    runs[0].agent.display_name,
                )
            )
            runs_by_task.append({run.task.instance_id: run for run in runs})
            reported_runs.append(reported)
            for run in runs:
                tasks.setdefault(run.task.instance_id, run.task.repo)

    rows: list[MatrixRow] = []
    counts: list[Counter[str]] = [Counter() for _ in columns]
    for instance_id, repo in sorted(tasks.items(), key=lambda item: (item[1], item[0])):
        cells: list[MatrixCellValue] = []
        for index, index_by_task in enumerate(runs_by_task):
            candidate = index_by_task.get(instance_id)
            reported = reported_runs[index]
            available = candidate is not None and candidate.run_id in reported
            value = _cell(candidate, available)
            counts[index][value.outcome] += 1
            cells.append(value)
        rows.append(MatrixRow(instance_id, repo, tuple(cells)))

    return ReportMatrix(
        columns=tuple(columns),
        rows=tuple(rows),
        totals=tuple(_totals(count) for count in counts),
    )


def _cell(run: EvaluationRun | None, report_available: bool) -> MatrixCellValue:
    if run is None:
        return MatrixCellValue("missing", None, None, None, None)
    if run.status == "COMPLETED" and not report_available:
        return MatrixCellValue("missing", run.run_id, None, None, None)
    return MatrixCellValue(
        _outcome(run),
        run.run_id,
        run.resolved_summary,
        run.failure_code,
        f"/api/v1/reports/runs/{run.run_id}",
    )


def _outcome(run: EvaluationRun) -> MatrixCell:
    if run.status == "COMPLETED":
        return "resolved" if run.resolved_summary else "unresolved"
    if run.status == "FAILED":
        return "infrastructure_error"
    return "incomplete"


def _totals(counts: Counter[str]) -> MatrixColumnTotals:
    return MatrixColumnTotals(
        resolved=counts["resolved"],
        unresolved=counts["unresolved"],
        infrastructure_error=counts["infrastructure_error"],
        incomplete=counts["incomplete"],
        missing=counts["missing"],
    )
