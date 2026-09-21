from jobs.reporting.test_matrix import _two_configuration_inputs

from eval_platform.application.reporting.matrix import build_matrix
from eval_platform.application.reporting.matrix_markdown import render_matrix_markdown


def _task_lines(text: str) -> list[str]:
    return [line for line in text.splitlines() if line.startswith("| example__")]


def test_markdown_renders_task_rows_with_chinese_labels():
    _, _, report_a, report_b = _two_configuration_inputs()
    text = render_matrix_markdown(build_matrix([report_a, report_b]))

    assert text.startswith("| 题目 |")
    task_lines = _task_lines(text)
    assert len(task_lines) == 3
    joined = "\n".join(task_lines)
    assert "通过" in joined and "基础设施失败" in joined and "未完成" in joined
    # 两格缺失：一档"没有 Run"，一档"已完成但没有报告"；都不写成 0 或未通过。
    assert joined.count("缺失") == 2


def test_markdown_summary_reports_coverage_instead_of_zero():
    _, _, report_a, report_b = _two_configuration_inputs()
    lines = render_matrix_markdown(build_matrix([report_a, report_b])).splitlines()

    assert any(line.endswith("| 3/3 |") for line in lines)
    assert any(line.endswith("| 1/3 |") for line in lines)


def test_empty_matrix_still_renders_a_header():
    text = render_matrix_markdown(build_matrix([]))
    assert text.splitlines()[0] == "| 题目 |"
