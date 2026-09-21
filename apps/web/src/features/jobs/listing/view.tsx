"use client";

import { useEffect, useState, type FormEvent } from "react";
import { ApiError } from "../../../lib/api-client";
import type { Actor, JobSummary, Page } from "../../../lib/contracts";
import { JOB_STATUSES } from "../../../lib/contracts";
import { jobs } from "../../../lib/job-client";
import { COMPARISON_LIMIT } from "../../../lib/reporting/comparison-shapes";
import { JOB_STATUS_NAMES } from "./labels";

type Filters = { status: string; mine: boolean };

function filtersFromUrl(owner: boolean): Filters {
  if (typeof window === "undefined") return { status: "", mine: false };
  const query = new URL(window.location.href).searchParams;
  const candidate = query.get("job_status") ?? "";
  return {
    status: JOB_STATUSES.some((item) => item === candidate) ? candidate : "",
    mine: owner && query.get("job_mine") === "1",
  };
}

function storeFilters(filters: Filters) {
  const url = new URL(window.location.href);
  if (filters.status) url.searchParams.set("job_status", filters.status);
  else url.searchParams.delete("job_status");
  if (filters.mine) url.searchParams.set("job_mine", "1");
  else url.searchParams.delete("job_mine");
  window.history.replaceState(null, "", url);
}

export default function JobList({
  actor,
  openJob,
  newJob,
  selected,
  toggle,
  compare,
}: {
  actor: Actor;
  openJob: (id: string) => void;
  newJob: () => void;
  selected: string[];
  toggle: (id: string) => void;
  compare: () => void;
}) {
  const [initial] = useState(() => filtersFromUrl(actor.role === "owner"));
  const [data, setData] = useState<Page<JobSummary> | null>(null);
  const [status, setStatus] = useState(initial.status);
  const [mine, setMine] = useState(initial.mine);
  const [applied, setApplied] = useState<Filters>(initial);
  const [cursors, setCursors] = useState<(string | null)[]>([null]);
  const [page, setPage] = useState(0);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function load(filters: Filters, cursor: string | null = null) {
    setBusy(true); setError("");
    const query = new URLSearchParams({ limit: "20" });
    if (filters.status) query.set("status", filters.status);
    if (filters.mine) query.set("created_by", actor.user_id);
    if (cursor) query.set("cursor", cursor);
    try { setData(await jobs(query)); }
    catch (value) {
      setData(null);
      setError(value instanceof ApiError ? value.message : "暂时无法读取评测列表。");
    } finally { setBusy(false); }
  }
  useEffect(() => { void load(initial); }, []);

  function apply(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const filters = { status, mine };
    storeFilters(filters);
    setApplied(filters); setCursors([null]); setPage(0);
    void load(filters);
  }
  function clear() {
    setStatus(""); setMine(false);
    const filters = { status: "", mine: false };
    storeFilters(filters);
    setApplied(filters); setCursors([null]); setPage(0);
    void load(filters);
  }
  function next() {
    if (!data?.next_cursor) return;
    const nextPage = page + 1;
    setCursors((items) => [...items.slice(0, nextPage), data.next_cursor]);
    setPage(nextPage); void load(applied, data.next_cursor);
  }
  function previous() {
    if (page === 0) return;
    const previousPage = page - 1;
    setPage(previousPage); void load(applied, cursors[previousPage]);
  }

  return <section aria-label="评测列表">
    <div className="section-heading">
      <div><span className="eyebrow">服务器可见范围</span><h2>评测列表</h2></div>
      <div className="heading-actions">
        <button onClick={newJob}>新建评测</button>
        <button disabled={selected.length === 0} onClick={compare}>
          对比所选（{selected.length}/{COMPARISON_LIMIT}）
        </button>
      </div>
    </div>
    <form className="filter-bar" onSubmit={apply}>
      <label>状态筛选<select value={status} disabled={busy}
        onChange={(event) => setStatus(event.target.value)}>
        <option value="">全部状态</option>
        {JOB_STATUSES.map((item) => <option key={item} value={item}>
          {JOB_STATUS_NAMES[item]}
        </option>)}
      </select></label>
      {actor.role === "owner" && <label className="inline-check">
        <input type="checkbox" checked={mine} disabled={busy}
          onChange={(event) => setMine(event.target.checked)} />只看我提交的
      </label>}
      <button disabled={busy}>应用筛选</button>
      <button type="button" disabled={busy} onClick={clear}>清除筛选</button>
      <button type="button" disabled={busy}
        onClick={() => void load(applied, cursors[page])}>刷新列表</button>
    </form>
    {busy && <p role="status">正在读取评测列表…</p>}
    {error && <p role="alert" className="error">{error}</p>}
    {data?.items.length === 0 && <div className="empty-state">
      <h3>这里还没有评测</h3><p>调整筛选，或开始一次新评测。</p>
    </div>}
    <div className="job-list">{data?.items.map((job) => <article key={job.job_id}
      className="job-row">
      <label className="inline-check">
        <input type="checkbox" checked={selected.includes(job.job_id)}
          disabled={busy || (!selected.includes(job.job_id) &&
            selected.length >= COMPARISON_LIMIT)}
          onChange={() => toggle(job.job_id)} />
        选择对比
      </label>
      <div><strong>{JOB_STATUS_NAMES[job.status]}</strong>
        <span>{job.trial_count} 个 Run · {new Date(job.created_at).toLocaleString("zh-CN")}</span>
        <code>{job.job_id}</code></div>
      <button onClick={() => openJob(job.job_id)}>查看评测 {job.job_id}</button>
    </article>)}</div>
    {data && <div className="pagination">
      <button disabled={busy || page === 0} onClick={previous}>上一页</button>
      <span className="muted small">第 {page + 1} 页 · 当前 {data.items.length} 条；
        不代表全部评测数量。</span>
      <button disabled={busy || !data.next_cursor} onClick={next}>下一页</button>
    </div>}
  </section>;
}
