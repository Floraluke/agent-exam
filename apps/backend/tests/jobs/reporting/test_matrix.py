from dataclasses import replace
from datetime import UTC, datetime
from uuid import uuid4

from jobs.execution.support.fixtures import queued_batch

from eval_platform.application.reporting.matrix import (
    MatrixColumnTotals,
    build_matrix,
)
from eval_platform.domain.jobs.execution import (
    JobReport,
    ProcessMetrics,
    RunReport,
    StoredDeterministicResult,
)
from eval_platform.domain.result import ResourceSummary, UsageSummary

NOW = datetime(2026, 9, 19, 12, 0, tzinfo=UTC)


def _completed(run, resolved: bool):
    return replace(
        run, status="COMPLETED", stage="completed", resolved_summary=resolved
    )


def _run_report(job, run, resolved: bool) -> RunReport:
    return RunReport(
        created_by=job.created_by,
        result_scope="official",
        run=run,
        deterministic_result=StoredDeterministicResult(
            run_id=run.run_id,
            patch_exists=True,
            patch_successfully_applied=True,
            resolved=resolved,
            tests_status_summary={"FAIL_TO_PASS": {"success": 1, "failure": 0}},
            harness_revision="a" * 40,
            report_artifact_id=str(uuid4()),
            test_output_artifact_id=None,
            duration_ms=None,
            created_at=NOW,
        ),
        process_metrics=ProcessMetrics(UsageSummary(), ResourceSummary()),
        artifacts=(),
        warnings=(),
    )


def _two_configuration_inputs():
    """两个 Job：A 为原始配置，B 为另一配置且缺第三题、首题报告缺失。"""
    job_a, _ = queued_batch(NOW, size=3)
    first, second, third = job_a.runs
    job_a = replace(
        job_a,
        runs=(
            _completed(first, True),
            replace(
                second,
                status="FAILED",
                stage="failed",
                failure_code="BATCH_FAILED",
                failure_summary="执行租约过期，批次已安全收束。",
            ),
            third,
        ),
    )
    report_a = JobReport(
        created_by=job_a.created_by,
        job=job_a,
        run_reports=(_run_report(job_a, job_a.runs[0], True),),
    )

    config = replace(
        first.agent,
        agent_configuration_id="cfg-second",
        display_name="Synthetic Second Configuration",
    )
    job_b = replace(
        job_a,
        job_id=str(uuid4()),
        runs=(
            replace(_completed(first, True), agent=config),
            replace(_completed(second, False), agent=config),
        ),
    )
    report_b = JobReport(
        created_by=job_b.created_by,
        job=job_b,
        run_reports=(_run_report(job_b, job_b.runs[1], False),),
    )
    return job_a, job_b, report_a, report_b


def _cells(matrix):
    return {
        (row.task_instance_id, index): row.cells[index]
        for row in matrix.rows
        for index in range(len(matrix.columns))
    }


def test_matrix_classifies_cross_configuration_outcomes():
    job_a, job_b, report_a, report_b = _two_configuration_inputs()
    matrix = build_matrix([report_a, report_b])

    assert [column.job_id for column in matrix.columns] == [job_a.job_id, job_b.job_id]
    assert matrix.columns[1].agent_display_name == "Synthetic Second Configuration"

    ids = [run.task.instance_id for run in job_a.runs]
    cells = _cells(matrix)
    assert [cells[(ids[0], index)].outcome for index in range(2)] == [
        "resolved",
        "missing",
    ]
    assert [cells[(ids[1], index)].outcome for index in range(2)] == [
        "infrastructure_error",
        "unresolved",
    ]
    assert [cells[(ids[2], index)].outcome for index in range(2)] == [
        "incomplete",
        "missing",
    ]
    assert matrix.totals[0] == MatrixColumnTotals(1, 0, 1, 1, 0)
    assert matrix.totals[1] == MatrixColumnTotals(0, 1, 0, 0, 2)
    assert matrix.totals[0].decided == 3
    assert matrix.totals[0].total == 3
    assert matrix.totals[1].decided == 1
    assert matrix.totals[1].total == 3


def test_missing_cells_never_carry_false_or_zero():
    _, _, report_a, report_b = _two_configuration_inputs()
    matrix = build_matrix([report_a, report_b])

    missing = [
        cell for row in matrix.rows for cell in row.cells if cell.outcome == "missing"
    ]
    assert len(missing) == 2
    assert all(cell.resolved is None and cell.failure_code is None for cell in missing)
    # 一档来自"没有 Run"，一档来自"已完成但没有报告"；两者都不算 unresolved。
    assert sum(cell.run_id is None for cell in missing) == 1
    assert sum(cell.report_path is None for cell in missing) == 2


def test_rows_are_ordered_and_empty_input_is_safe():
    _, _, report_a, report_b = _two_configuration_inputs()
    matrix = build_matrix([report_a, report_b])

    keys = [(row.repo, row.task_instance_id) for row in matrix.rows]
    assert keys == sorted(keys)

    empty = build_matrix([])
    assert empty.columns == () and empty.rows == () and empty.totals == ()


def test_same_instance_id_in_different_repositories_stays_in_separate_rows():
    job_a, _ = queued_batch(NOW, size=2)
    run_a = _completed(job_a.runs[0], True)
    job_a = replace(job_a, runs=(run_a,))
    report_a = JobReport(
        created_by=job_a.created_by,
        job=job_a,
        run_reports=(_run_report(job_a, run_a, True),),
    )

    task_b = replace(run_a.task, repo="another/repository")
    run_b = replace(
        run_a,
        run_id=str(uuid4()),
        job_id=str(uuid4()),
        task=task_b,
    )
    job_b = replace(job_a, job_id=run_b.job_id, runs=(run_b,))
    report_b = JobReport(
        created_by=job_b.created_by,
        job=job_b,
        run_reports=(_run_report(job_b, run_b, True),),
    )

    matrix = build_matrix([report_a, report_b])

    assert [(row.repo, row.task_instance_id) for row in matrix.rows] == [
        ("another/repository", run_b.task.instance_id),
        (run_a.task.repo, run_a.task.instance_id),
    ]
    assert [[cell.outcome for cell in row.cells] for row in matrix.rows] == [
        ["missing", "resolved"],
        ["resolved", "missing"],
    ]
