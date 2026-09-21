"use client";

import { useEffect, useRef, useState } from "react";
import { ApiError } from "../../../lib/api-client";
import type { JobDetail, JobSummary, RunReport } from "../../../lib/contracts";
import { jobs, runReport } from "../../../lib/job-client";
import {
  comparison, comparisonDetails, comparisonReports,
} from "../../../lib/reporting/comparison-client";
import type { ComparisonMatrix } from "../../../lib/reporting/comparison-shape";
import { COMPARISON_LIMIT } from "../../../lib/reporting/comparison-shapes";
import RunReportView from "../report";
import { JOB_STATUS_NAMES } from "../listing/labels";
import ConfigurationComparison from "./configuration";
import ComparisonMatrixView from "./matrix";
import MetricsComparison from "./metrics";

export default function ComparisonWorkspace({
  ids, toggle, clearAll, openJob,
}: {
  ids: string[]; toggle: (id: string) => void; clearAll: () => void;
  openJob: (id: string) => void;
}) {
  const [available, setAvailable] = useState<JobSummary[] | null>(null);
  const [matrix, setMatrix] = useState<ComparisonMatrix | null>(null);
  const [details, setDetails] = useState(new Map<string, JobDetail>());
  const [reports, setReports] = useState(new Map<string, RunReport>());
  const [opened, setOpened] = useState<RunReport | null>(null);
  const [busy, setBusy] = useState(false); const [metricsBusy, setMetricsBusy] = useState(false);
  const [metricsLoaded, setMetricsLoaded] = useState(false); const [failed, setFailed] = useState(0);
  const [error, setError] = useState("");
  const openRequest = useRef(0); const metricsRequest = useRef(0);

  async function loadJobs(reconcile = false) {
    setError("");
    try {
      const next = (await jobs()).items;
      setAvailable(next);
      if (reconcile) {
        const visible = new Set(next.map((job) => job.job_id));
        ids.filter((id) => !visible.has(id)).forEach(toggle);
        resetResult();
      }
    }
    catch (value) {
      setAvailable(null);
      setError(value instanceof ApiError ? value.message : "暂时无法读取评测列表。");
    }
  }
  useEffect(() => { void loadJobs(); }, []);

  function resetResult() {
    openRequest.current += 1; metricsRequest.current += 1;
    setMatrix(null); setDetails(new Map()); setReports(new Map()); setOpened(null);
    setMetricsLoaded(false); setMetricsBusy(false); setFailed(0); setError("");
  }

  function changeSelection(id: string) {
    toggle(id); resetResult();
  }

  function resetSelection() {
    clearAll(); resetResult();
  }

  async function compare() {
    if (ids.length === 0) return;
    resetResult(); setBusy(true);
    try {
      const next = await comparison(ids);
      setMatrix(next);
      const result = await comparisonDetails(next.columns.map((column) => column.job_id));
      setDetails(result.values);
      if (result.failed.length > 0) {
        setError(`${result.failed.length} 个冻结配置快照读取失败，相关字段显示未知。`);
      }
    } catch (value) {
      setError(value instanceof ApiError ? value.message : "暂时无法生成对比报告。");
    } finally { setBusy(false); }
  }

  async function loadMetrics() {
    if (!matrix) return;
    const request = ++metricsRequest.current;
    setMetricsBusy(true); setFailed(0);
    const runIds = matrix.rows.flatMap((row) => row.cells)
      .filter((cell) => cell.run_id !== null && cell.report_path !== null)
      .map((cell) => cell.run_id as string);
    const result = await comparisonReports(runIds);
    if (request === metricsRequest.current) {
      setReports(result.values); setFailed(result.failed.length);
      setMetricsLoaded(true); setMetricsBusy(false);
    }
  }

  async function openRun(id: string) {
    const request = ++openRequest.current;
    setError(""); setOpened(null);
    if (reports.has(id)) { setOpened(reports.get(id) as RunReport); return; }
    try {
      const report = await runReport(id);
      if (request === openRequest.current) setOpened(report);
    } catch (value) {
      if (request === openRequest.current) {
        setError(value instanceof ApiError ? value.message : "暂时无法读取单次报告。");
      }
    }
  }

  return <section aria-label="对比报告工作区">
    <section aria-label="跨批次对比报告">
      <div className="section-heading"><div><span className="eyebrow">服务端只读聚合</span>
        <h2>对比报告</h2><p>选择已登记的评测批次进行对比；缺失不当作未通过或零。</p></div>
        <div className="heading-actions"><button disabled={busy} onClick={() => void loadJobs(true)}>
          刷新可见批次</button><button onClick={resetSelection}>清空选择</button></div>
      </div>
      <fieldset className="comparison-picker"><legend>
        当前可见首屏批次（最多 {COMPARISON_LIMIT} 个，不代表按创建时间排序）</legend>
        {available === null && !error && <p role="status">正在读取可见批次…</p>}
        {available?.length === 0 && <p>暂无可对比的评测批次。</p>}
        {available?.map((job) => <label key={job.job_id}>
          <input type="checkbox" checked={ids.includes(job.job_id)} disabled={busy ||
            (!ids.includes(job.job_id) && ids.length >= COMPARISON_LIMIT)}
            onChange={() => changeSelection(job.job_id)} />
          <span><strong>{JOB_STATUS_NAMES[job.status]}</strong> · {job.trial_count} 个 Run ·
            {new Date(job.created_at).toLocaleString("zh-CN")}<small>{job.job_id}</small></span>
        </label>)}
      </fieldset>
      {ids.length === 0 ? <div className="empty-state"><h3>还没有选择要对比的批次</h3>
        <p>可在评测列表或本页勾选 1–{COMPARISON_LIMIT} 个批次。</p></div> : <>
        <ul className="comparison-selection" aria-label="已选批次">
          {ids.map((id) => <li key={id}><code>{id}</code>
            <button aria-label={`移除 ${id}`} disabled={busy}
              onClick={() => changeSelection(id)}>移除</button></li>)}
        </ul>
        <button disabled={busy} onClick={() => void compare()}>
          {busy ? "正在生成…" : `应用对比 · 生成对比（${ids.length}）`}</button>
      </>}
      {error && <p role="alert" className="error">{error}</p>}
      {matrix && <>
        <ComparisonMatrixView matrix={matrix} openRun={(id) => void openRun(id)} openJob={openJob} />
        <MetricsComparison matrix={matrix} reports={reports} loaded={metricsLoaded}
          busy={metricsBusy} failed={failed} load={() => void loadMetrics()} />
        <ConfigurationComparison matrix={matrix} details={details} />
      </>}
      {opened && <section className="comparison-block" aria-label="对比中的单次运行报告">
        <div role="region" aria-label="选中的单次证据">
          <div className="section-heading"><h3>单次证据</h3>
            <button onClick={() => setOpened(null)}>返回对比矩阵</button></div>
          <RunReportView report={opened} />
        </div>
      </section>}
    </section>
  </section>;
}
