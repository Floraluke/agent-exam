import type { ComparisonMatrix, ComparisonOutcome } from "../../../lib/reporting/comparison-shape";

const names: Record<ComparisonOutcome, string> = {
  resolved: "已解决", unresolved: "未解决",
  infrastructure_error: "基础设施错误", incomplete: "未完成", missing: "缺失",
};

function explanation(outcome: ComparisonOutcome) {
  if (outcome === "infrastructure_error") return "运行环境未能形成可判定结果。";
  if (outcome === "incomplete") return "运行尚未形成确定性成绩。";
  if (outcome === "missing") return "无运行或报告缺失；不计为未通过或零。";
  return outcome === "resolved" ? "固定判卷已通过。" : "固定判卷已完成但未通过。";
}

export default function ComparisonMatrixView({
  matrix, openRun, openJob,
}: {
  matrix: ComparisonMatrix; openRun: (runId: string) => void;
  openJob: (jobId: string) => void;
}) {
  return <section aria-label="题目配置对比矩阵" className="comparison-block">
    <h3>题目 × 配置矩阵</h3>
    <p className="muted small">结论来自服务端批次报告；缺失独立统计，不折算为未通过。</p>
    <div className="comparison-scroll comparison-matrix" tabIndex={0}>
      <table className="comparison-table">
      <caption>题目 × 配置矩阵；列序与所选批次一致，行按仓库与题目排序。</caption>
      <thead><tr><th scope="col">题目</th>{matrix.columns.map((column, index) =>
        <th scope="col" key={`${column.job_id}-${column.agent_configuration_id}`}>
          <button onClick={() => openJob(column.job_id)}>{column.agent_display_name}</button>
          <small>配置 {index + 1} · {column.job_id}</small>
        </th>)}</tr></thead>
      <tbody>{matrix.rows.map((row) => <tr key={`${row.repo}-${row.task_instance_id}`}>
        <th scope="row">{row.task_instance_id}<small>{row.repo}</small></th>
        {row.cells.map((cell, index) => <td key={index} data-outcome={cell.outcome}>
          {cell.run_id && cell.report_path ? <button
            aria-label={`查看 ${row.task_instance_id} 运行报告 / 查看单次证据：配置 ${index + 1}，${names[cell.outcome]}`}
            onClick={() => openRun(cell.run_id as string)}>{names[cell.outcome]}</button> :
            <strong>{names[cell.outcome]}</strong>}
          <span>{explanation(cell.outcome)}</span>
          {cell.failure_code && <details><summary>技术错误码</summary>
            <code>{cell.failure_code}</code></details>}
        </td>)}</tr>)}</tbody>
      <tfoot><tr><th scope="row">汇总 · 有结论 / 总数</th>
        {matrix.totals.map((total, index) => <td key={index}>
        <span>通过 {total.resolved} · 未通过 {total.unresolved}</span>
        <span>故障 {total.infrastructure_error} · 未完成 {total.incomplete}</span>
        <strong>缺失 {total.missing}（{total.decided}/{total.total}）</strong>
      </td>)}</tr></tfoot>
    </table></div>
  </section>;
}
