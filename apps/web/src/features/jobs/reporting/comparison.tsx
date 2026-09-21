"use client";

import { useState } from "react";
import { ApiError } from "../../../lib/api-client";
import { comparisons, runReport } from "../../../lib/job-client";
import type { RunReport } from "../../../lib/contracts";
import {
  COMPARISON_OUTCOME_NAMES,
  type ComparisonCell,
  type ComparisonMatrix,
} from "../../../lib/reporting/comparison-shapes";
import RunReportView from "../report";

function cellText(cell: ComparisonCell) {
  if (cell.outcome !== "missing") return COMPARISON_OUTCOME_NAMES[cell.outcome];
  return cell.run_id === null ? "无运行" : "报告缺失";
}

function coverage(totals: ComparisonMatrix["totals"][number]) {
  return totals.total === 0 ? "0/0" : `${totals.decided}/${totals.total}`;
}

export default function ComparisonView({
  ids,
  remove,
  clearAll,
  openJob,
}: {
  ids: string[];
  remove: (id: string) => void;
  clearAll: () => void;
  openJob: (id: string) => void;
}) {
  const [matrix, setMatrix] = useState<ComparisonMatrix | null>(null);
  const [report, setReport] = useState<RunReport | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function load() {
    if (ids.length === 0) return;
    setBusy(true); setError("");
    try { setMatrix(await comparisons(ids)); }
    catch (value) {
      // 保留旧矩阵，只提示失败——404 收敛或 503 时不清空已经看到的内容。
      setError(value instanceof ApiError ? value.message : "暂时无法读取对比矩阵。");
    } finally { setBusy(false); }
  }

  async function openRun(runId: string) {
    setBusy(true); setError("");
    try { setReport(await runReport(runId)); }
    catch (value) {
      setError(value instanceof ApiError ? value.message : "暂时无法读取运行报告。");
    } finally { setBusy(false); }
  }

  if (report) return <section aria-label="对比中的单次运行报告">
    <div className="section-heading">
      <div><span className="eyebrow">对比钻取</span><h2>单题运行报告</h2></div>
      <button onClick={() => setReport(null)}>返回对比矩阵</button>
    </div>
    <RunReportView report={report} />
  </section>;

  return <section aria-label="跨批次对比报告">
    <div className="section-heading">
      <div><span className="eyebrow">只读聚合</span><h2>跨批次对比报告</h2></div>
      <button onClick={clearAll}>清空选择</button>
    </div>
    <p className="muted">每题一行、每个批次（配置）一列；缺失只表示没有结果，不当作未解决或零。</p>
    {ids.length === 0
      ? <div className="empty-state">
        <h3>还没有选择要对比的批次</h3>
        <p>到评测列表勾选 1–20 个批次，再点「对比所选」。</p>
      </div>
      : <>
        <ul aria-label="已选批次">{ids.map((id) => <li key={id}>
          <code>{id}</code>
          <button disabled={busy} onClick={() => remove(id)}>移除 {id}</button>
        </li>)}</ul>
        <button disabled={busy || ids.length === 0} onClick={() => void load()}>
          {busy ? "正在读取…" : "应用对比"}
        </button>
      </>}
    {error && <p role="alert" className="error">{error}</p>}
    {matrix && <div className="comparison-matrix" tabIndex={0}>
      <table>
        <caption>题目 × 配置矩阵；列序与所选批次一致，行按仓库与题目排序。</caption>
        <thead><tr><th scope="col">题目</th>
          {matrix.columns.map((column) => <th key={column.job_id} scope="col">
            <button onClick={() => openJob(column.job_id)}>
              {column.agent_display_name}
            </button>
            <span className="small">{column.job_id}</span>
          </th>)}</tr></thead>
        <tbody>{matrix.rows.map((row) => <tr key={`${row.repo}:${row.task_instance_id}`}>
          <th scope="row">{row.repo} / {row.task_instance_id}</th>
          {row.cells.map((cell, index) => <td key={matrix.columns[index].job_id}
            data-outcome={cell.outcome}>
            <span>{cellText(cell)}</span>
            {cell.run_id !== null && <button disabled={busy}
              onClick={() => void openRun(cell.run_id as string)}>
              查看 {row.task_instance_id} 运行报告
            </button>}
          </td>)}
        </tr>)}</tbody>
        <tfoot><tr><th scope="row">有结论 / 总数</th>
          {matrix.totals.map((total, index) => <td key={matrix.columns[index].job_id}>
            已解决 {total.resolved} · 未解决 {total.unresolved} ·
            基础设施错误 {total.infrastructure_error} · 未完成 {total.incomplete} ·
            缺失 {total.missing}（{coverage(total)}）
          </td>)}</tr></tfoot>
      </table>
    </div>}
  </section>;
}
