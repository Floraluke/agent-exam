import type { RunReport } from "../../../lib/contracts";
import type { ComparisonMatrix } from "../../../lib/reporting/comparison-shape";

type Metric = { label: string; values: Array<number | null>; suffix?: string };

function displayNumber(value: number) {
  return Number(value.toPrecision(15)).toString();
}

function summary(metric: Metric) {
  const known = metric.values.filter((value): value is number => value !== null);
  if (known.length === 0) return `未知（0/${metric.values.length} 个单元格有值）`;
  const total = known.reduce((sum, value) => sum + value, 0);
  const value = `${displayNumber(total)}${metric.suffix ?? ""}`;
  return known.length === metric.values.length ? `总量：${value}` :
    `部分：${value}（${known.length}/${metric.values.length} 个单元格有值）`;
}

export default function MetricsComparison({
  matrix, reports, loaded, busy, failed, load,
}: {
  matrix: ComparisonMatrix; reports: Map<string, RunReport>; loaded: boolean;
  busy: boolean; failed: number; load: () => void;
}) {
  function metrics(column: number): Metric[] {
    const cells = matrix.rows.map((row) => row.cells[column]);
    const value = (pick: (report: RunReport) => number | null) => cells.map((cell) =>
      cell.run_id && reports.has(cell.run_id) ? pick(reports.get(cell.run_id) as RunReport) : null);
    return [
      { label: "输入 tokens", values: value((report) => report.process_metrics.usage.n_input_tokens) },
      { label: "缓存 tokens", values: value((report) => report.process_metrics.usage.n_cache_tokens) },
      { label: "输出 tokens", values: value((report) => report.process_metrics.usage.n_output_tokens) },
      { label: "费用", values: value((report) => report.process_metrics.usage.cost_usd), suffix: " USD" },
      { label: "各 Run 墙钟耗时之和", values: value((report) => report.process_metrics.resources.wall_time_sec), suffix: " 秒" },
      { label: "各 Run CPU 用时之和", values: value((report) => report.process_metrics.resources.cpu_time_sec), suffix: " 秒" },
    ];
  }
  return <section aria-label="用量与资源汇总" className="comparison-block">
    <div className="section-heading"><div><h3>用量与资源</h3>
      <p className="muted small">按需读取单次 Run 报告，最多同时请求 3 个。</p></div>
      <button disabled={busy} onClick={load}>{busy ? "正在加载…" :
        loaded ? "重新加载用量与资源" : "加载用量与资源"}</button></div>
    {!loaded ? <p>尚未加载；当前值为未知，不显示为 0。</p> : <>
      {failed > 0 && <p role="alert">{failed} 个 Run 报告读取失败，对应指标保持未知。</p>}
      <div className="metric-configurations">{matrix.columns.map((column, index) => {
        const total = matrix.totals[index];
        return <article key={`${column.job_id}-${column.agent_configuration_id}`}
          aria-label={`${column.agent_display_name} 配置 ${index + 1} 指标`}>
          <h4>{column.agent_display_name} · 配置 {index + 1}</h4>
          <p>确定性通过 {total.resolved} / {total.total}；未通过 {total.unresolved}；
            故障 {total.infrastructure_error}；未完成 {total.incomplete}；缺失 {total.missing}</p>
          <dl className="metric-grid">{metrics(index).map((metric) => <div key={metric.label}>
            <dt>{metric.label}</dt><dd>{summary(metric)}</dd>
          </div>)}</dl>
        </article>;
      })}</div>
      <p className="muted small">墙钟耗时是各 Run 用时之和，不是整批从开始到结束的墙钟耗时。
        费用仅显示报告中的 USD 原币值；不把人民币预算当作实际账单。</p>
    </>}
  </section>;
}
