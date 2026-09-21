"""Render a report matrix as a reviewable Markdown comparison table.

任务 08 要交付"可复查的对比报告"；这里把 matrix.py 的只读矩阵渲染成表格文本，
供验收报告直接粘贴。缺失格渲染为"缺失"，不显示为 0 或"未解决"。
五档中文文案与 Web 界面共用同一套词（已解决/未解决/基础设施错误/未完成/缺失），
术语表见 docs/architecture/modules/evidence-and-reporting/ARCHITECTURE.md。
"""

from __future__ import annotations

from eval_platform.application.reporting.matrix import ReportMatrix

_CELL_LABELS = {
    "resolved": "已解决",
    "unresolved": "未解决",
    "infrastructure_error": "基础设施错误",
    "incomplete": "未完成",
    "missing": "缺失",
}


def render_matrix_markdown(matrix: ReportMatrix) -> str:
    """Return one matrix table plus a per-column coverage summary."""
    header = ["题目"] + [
        f"{column.agent_display_name}（{column.job_id[:8]}）"
        for column in matrix.columns
    ]
    lines = [
        "| " + " | ".join(header) + " |",
        "|" + "---|" * len(header),
    ]
    for row in matrix.rows:
        labels = [_CELL_LABELS[cell.outcome] for cell in row.cells]
        lines.append("| " + " | ".join([row.task_instance_id, *labels]) + " |")

    lines.extend(
        [
            "",
            "| 配置 | 已解决 | 未解决 | 基础设施错误 "
            "| 未完成 | 缺失 | 有结论 | 覆盖率 |",
            "|---|---|---|---|---|---|---|---|",
        ]
    )
    for column, total in zip(matrix.columns, matrix.totals, strict=True):
        coverage = f"{total.decided}/{total.total}" if total.total else "0/0"
        lines.append(
            f"| {column.agent_display_name} | {total.resolved} | {total.unresolved} "
            f"| {total.infrastructure_error} | {total.incomplete} | {total.missing} "
            f"| {total.decided} | {coverage} |"
        )
    return "\n".join(lines)
