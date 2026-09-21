"use client";

import { useEffect, useRef, useState } from "react";
import { ApiError } from "../../../lib/api-client";
import type { JobDetail, JobSummary, RunReport } from "../../../lib/contracts";
import { jobs, runReport } from "../../../lib/job-client";
import {
  comparison, comparisonDetails, comparisonReports,
} from "../../../lib/reporting/comparison-client";
import type { ComparisonMatrix } from "../../../lib/reporting/comparison-shape";
import RunReportView from "../report";
import { JOB_STATUS_NAMES } from "../listing/labels";
import ConfigurationComparison from "./configuration";
import ComparisonMatrixView from "./matrix";
import MetricsComparison from "./metrics";

export default function ComparisonWorkspace() {
  const [available, setAvailable] = useState<JobSummary[] | null>(null);
  const [selected, setSelected] = useState<string[]>([]);
  const [matrix, setMatrix] = useState<ComparisonMatrix | null>(null);
  const [details, setDetails] = useState(new Map<string, JobDetail>());
  const [reports, setReports] = useState(new Map<string, RunReport>());
  const [opened, setOpened] = useState<RunReport | null>(null);
  const [busy, setBusy] = useState(false); const [metricsBusy, setMetricsBusy] = useState(false);
  const [metricsLoaded, setMetricsLoaded] = useState(false); const [failed, setFailed] = useState(0);
  const [error, setError] = useState("");
  const openRequest = useRef(0); const metricsRequest = useRef(0);

  async function loadJobs() {
    setError("");
    try {
      const next = (await jobs()).items;
      const visible = new Set(next.map((job) => job.job_id));
      setAvailable(next);
      setSelected((current) => current.filter((id) => visible.has(id)));
    }
    catch (value) {
      setAvailable(null); setSelected([]);
      setError(value instanceof ApiError ? value.message : "暂时无法读取评测列表。");
    }
  }
  useEffect(() => { void loadJobs(); }, []);

  function toggle(id: string, checked: boolean) {
    setSelected((current) => checked ? [...current, id] : current.filter((item) => item !== id));
  }

  async function compare() {
    openRequest.current += 1; metricsRequest.current += 1;
    setBusy(true); setMetricsBusy(false); setError(""); setOpened(null); setMatrix(null);
    setDetails(new Map()); setReports(new Map()); setMetricsLoaded(false); setFailed(0);
    try {
      const next = await comparison(selected);
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
    const ids = matrix.rows.flatMap((row) => row.cells)
      .filter((cell) => cell.run_id !== null && cell.report_path !== null)
      .map((cell) => cell.run_id as string);
    const result = await comparisonReports(ids);
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
    }
    catch (value) {
      if (request === openRequest.current) {
        setOpened(null);
        setError(value instanceof ApiError ? value.message : "暂时无法读取单次报告。");
      }
    }
  }

  return <section aria-label="对比报告工作区">
    <div className="section-heading"><div><span className="eyebrow">服务端报告</span>
      <h2>对比报告</h2><p>选择已登记的评测批次进行对比</p></div>
      <button disabled={busy} onClick={() => void loadJobs()}>刷新可见批次</button>
    </div>
    <fieldset className="comparison-picker"><legend>当前可见首屏批次（最多 20 个，不代表按创建时间排序）</legend>
      {available === null && !error && <p role="status">正在读取可见批次…</p>}
      {available?.length === 0 && <p>暂无可对比的评测批次。</p>}
      {available?.map((job) => <label key={job.job_id}>
        <input type="checkbox" checked={selected.includes(job.job_id)}
          disabled={busy} onChange={(event) => toggle(job.job_id, event.target.checked)} />
        <span><strong>{JOB_STATUS_NAMES[job.status]}</strong> · {job.trial_count} 个 Run ·
          {new Date(job.created_at).toLocaleString("zh-CN")}<small>{job.job_id}</small></span>
      </label>)}
    </fieldset>
    <div className="heading-actions">
      <button disabled={busy || selected.length === 0} onClick={() => void compare()}>
        {busy ? "正在生成…" : `生成对比（${selected.length}）`}</button>
    </div>
    {error && <p role="alert" className="error">{error}</p>}
    {matrix && <>
      <ComparisonMatrixView matrix={matrix} openRun={(id) => void openRun(id)} />
      <MetricsComparison matrix={matrix} reports={reports} loaded={metricsLoaded}
        busy={metricsBusy} failed={failed} load={() => void loadMetrics()} />
      <ConfigurationComparison matrix={matrix} details={details} />
    </>}
    {opened && <section className="comparison-block" aria-label="选中的单次证据">
      <div className="section-heading"><h3>单次证据</h3>
        <button onClick={() => setOpened(null)}>关闭单次证据</button></div>
      <RunReportView report={opened} />
    </section>}
  </section>;
}
