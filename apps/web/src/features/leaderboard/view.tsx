"use client";

import { useState, type FormEvent } from "react";
import { ApiError } from "../../lib/api-client";
import {
  filtersFromQuery, leaderboard, type LeaderboardFilters,
} from "../../lib/leaderboard/client";
import type { LeaderboardRow, MetricValue } from "../../lib/leaderboard/shapes";

const empty: LeaderboardFilters = {
  datasetId: "", datasetRevision: "", split: "", repo: "", toolProfileId: "",
};

// 预填只读 URL 参数：这是默认值，不是授权，也不自动发起查询。
function initialFilters(): LeaderboardFilters {
  if (typeof window === "undefined") return empty;
  return filtersFromQuery(new URL(window.location.href).searchParams);
}

function metric(label: string, item: MetricValue, selected: number, suffix = "") {
  const value = item.value === null ? "unknown" : `${item.value}${suffix}`;
  return <li>{label}：{value}（覆盖 {item.coverage}/{selected}）</li>;
}

function Result({ row }: { row: LeaderboardRow }) {
  const scope = row.comparison_scope; const metrics = row.process_metrics;
  const network = scope.network_policy_snapshot;
  const tools = scope.tool_profile_snapshot;
  const limits = scope.limit_snapshot;
  const yesNo = (value: boolean) => value ? "是" : "否";
  return <article className="leaderboard-row">
    <h3>并列第 {row.rank} 名 · {row.agent.display_name}</h3>
    <p>{row.agent.agent_type} {row.agent.agent_version} · {row.agent.model_provider}
      / {row.agent.model} · reasoning {row.agent.reasoning_effort}</p>
    <p className="small">配置 ID：{row.agent.agent_configuration_id}<br />
      配置 fingerprint：{row.agent.configuration_fingerprint}</p>
    <p><strong>{row.resolved_count} / {row.total_tasks}{" · "}
      {(row.resolved_rate * 100).toFixed(1)}%</strong></p>
    <p>确定性结果 {row.deterministic_count} · 未解决 {row.unresolved_count} ·
      基础设施错误 {row.infrastructure_error_count} · 未知 {row.unknown_count}</p>
    <details>
      <summary>完整比较条件</summary>
      <p>{scope.dataset_id} / {scope.dataset_revision} / {scope.split} / {scope.repo}</p>
      <p>赛道 {scope.evaluation_track} · 网络策略 {scope.network_policy_id} ·
        工具策略 {scope.tool_profile_id} · 资源模板 {scope.limit_profile_id}</p>
      <p>网络 {network.mode} · Web 搜索 {network.web_search} ·
        任意主机 {yesNo(network.arbitrary_hosts)}</p>
      <p>工具 {tools.agent_type} · Web 搜索 {tools.web_search} ·
        任意命令 {yesNo(tools.arbitrary_commands)}</p>
      <p>Agent {limits.agent_wall_timeout_sec} 秒 / {limits.agent_cpus} CPU /
        {" "}{limits.agent_memory_mb} MB / {limits.agent_storage_mb} MB 存储</p>
      <p>评测器 {limits.evaluator_wall_timeout_sec} 秒 /
        {" "}{limits.evaluator_cpus} CPU / {limits.evaluator_memory_mb} MB ·
        PID 上限 {limits.pids_limit}</p>
      <p>补丁提醒/上限 {limits.patch_warning_bytes}/{limits.patch_max_bytes} bytes ·
        原始产物/运行上限 {limits.raw_artifact_max_bytes}/{limits.raw_run_max_bytes} bytes</p>
      <p>并发 {limits.concurrency} / 自动重试 {limits.max_retries}</p>
      <p className="small">Harbor {scope.harbor_revision}<br />
        SWE-Gym {scope.swe_gym_revision}<br />
        SWE-Bench Fork {scope.swe_bench_fork_revision}<br />
        执行契约 {scope.execution_contract_version}</p>
    </details>
    <details>
      <summary>过程指标（不参与排名）</summary>
      <ul>
        {metric("输入 token", metrics.n_input_tokens, metrics.selected_runs)}
        {metric("缓存 token", metrics.n_cache_tokens, metrics.selected_runs)}
        {metric("输出 token", metrics.n_output_tokens, metrics.selected_runs)}
        {metric("成本", metrics.cost_usd, metrics.selected_runs, " USD")}
        {metric("墙钟时间", metrics.wall_time_sec, metrics.selected_runs, " 秒")}
        {metric("CPU 时间", metrics.cpu_time_sec, metrics.selected_runs, " 秒")}
        {metric("峰值内存", metrics.peak_memory_bytes, metrics.selected_runs, " bytes")}
      </ul>
    </details>
    <details>
      <summary>纳入来源</summary>
      <ul>{row.sources.map((source) => <li key={source.task_id}>
        {source.instance_id} · {source.classification} ·
        <a href={`/?view=jobs&job=${source.job_id}`}>查看批次</a> ·
        <a href={`/api/v1/reports/runs/${source.run_id}`}>查看运行报告</a>
      </li>)}</ul>
    </details>
    <p className="muted small">质量评分未启用；确定性成绩相同保持并列。</p>
  </article>;
}

export default function LeaderboardView() {
  const [filters, setFilters] = useState(initialFilters);
  const [applied, setApplied] = useState(empty);
  const [rows, setRows] = useState<LeaderboardRow[]>([]);
  const [next, setNext] = useState<string | null>(null);
  const [searched, setSearched] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  function field(key: keyof LeaderboardFilters, value: string) {
    setFilters((current) => ({ ...current, [key]: value }));
  }
  async function load(current: LeaderboardFilters, cursor?: string) {
    if (!cursor) {
      setRows([]); setNext(null); setSearched(false);
    }
    setBusy(true); setError("");
    try {
      const page = await leaderboard(current, cursor);
      setRows((items) => cursor ? [...items, ...page.items] : page.items);
      setNext(page.next_cursor); setSearched(true); setApplied(current);
    } catch (value) {
      setError(value instanceof ApiError ? value.message : "暂时无法读取排行榜。");
    } finally { setBusy(false); }
  }
  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); void load(filters);
  }
  return <section aria-label="基础排行榜">
    <h2>基础排行榜</h2>
    <p className="muted">只比较相同冻结条件；分母包含范围内全部题目。</p>
    <form onSubmit={submit}>
      <label>数据集 ID<input required maxLength={128} value={filters.datasetId}
        onChange={(event) => field("datasetId", event.target.value)} /></label>
      <label>数据集 revision<input required maxLength={64}
        value={filters.datasetRevision}
        onChange={(event) => field("datasetRevision", event.target.value)} /></label>
      <label>数据集 split<input required maxLength={64} value={filters.split}
        onChange={(event) => field("split", event.target.value)} /></label>
      <label>代码仓库（可选）<input maxLength={128} value={filters.repo}
        onChange={(event) => field("repo", event.target.value)} /></label>
      <label>工具策略（可选）<input maxLength={128} value={filters.toolProfileId}
        onChange={(event) => field("toolProfileId", event.target.value)} /></label>
      <button disabled={busy}>{busy ? "正在查询…" : "查询排行榜"}</button>
    </form>
    {error && <p role="alert" className="error">{error}</p>}
    {searched && !error && rows.length === 0 && <p>没有符合条件的正式结果。</p>}
    {rows.map((row) => <Result key={
      `${row.agent.configuration_fingerprint}:${JSON.stringify(row.comparison_scope)}`
    } row={row} />)}
    {next && <button disabled={busy} onClick={() => void load(applied, next)}>
      加载下一页
    </button>}
  </section>;
}
