"use client";

import { useEffect, useState } from "react";
import { ApiError } from "../../lib/api-client";
import type { JobSummary } from "../../lib/contracts";
import { jobs } from "../../lib/job-client";
import { JOB_STATUS_NAMES } from "../jobs/listing/labels";

const ACTIVE_STATUSES = [
  "QUEUED", "PREPARING", "EXECUTING", "FINALIZING", "CANCEL_REQUESTED",
] as const;
const ABNORMAL_STATUSES = ["COMPLETED_WITH_ERRORS", "FAILED"] as const;

async function jobsByStatus(statuses: readonly string[]) {
  const pages = await Promise.all(statuses.map((status) => jobs(new URLSearchParams({
    limit: "5", status,
  }))));
  return pages.flatMap((page) => page.items);
}

function JobCards({
  items,
  openJob,
  empty,
}: {
  items: JobSummary[];
  openJob: (id: string) => void;
  empty: string;
}) {
  if (items.length === 0) return <p className="muted">{empty}</p>;
  return <div className="dashboard-jobs">{items.map((job) => <article key={job.job_id}>
    <strong>{JOB_STATUS_NAMES[job.status]}</strong>
    <span>{job.trial_count} 个 Run</span>
    <code>{job.job_id}</code>
    <button onClick={() => openJob(job.job_id)}>打开评测 {job.job_id}</button>
  </article>)}</div>;
}

export default function Dashboard({
  owner,
  newJob,
  allJobs,
  openJob,
}: {
  owner: boolean;
  newJob: () => void;
  allJobs: () => void;
  openJob: (id: string) => void;
}) {
  const [visible, setVisible] = useState<JobSummary[]>([]);
  const [pending, setPending] = useState<JobSummary[]>([]);
  const [active, setActive] = useState<JobSummary[]>([]);
  const [abnormal, setAbnormal] = useState<JobSummary[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function load() {
    setBusy(true); setError("");
    try {
      const [visiblePage, pendingJobs, activeJobs, abnormalJobs] = await Promise.all([
        jobs(new URLSearchParams({ limit: "5" })),
        owner ? jobsByStatus(["AWAITING_OWNER_APPROVAL"]) : Promise.resolve([]),
        owner ? jobsByStatus(ACTIVE_STATUSES) : Promise.resolve([]),
        owner ? jobsByStatus(ABNORMAL_STATUSES) : Promise.resolve([]),
      ]);
      setVisible(visiblePage.items); setPending(pendingJobs);
      setActive(activeJobs); setAbnormal(abnormalJobs);
    } catch (value) {
      setVisible([]); setPending([]); setActive([]); setAbnormal([]);
      setError(value instanceof ApiError ? value.message : "暂时无法读取工作台。");
    } finally { setBusy(false); }
  }
  useEffect(() => { void load(); }, []);

  return <section aria-label={owner ? "所有者工作台" : "协作者工作台"}>
    <div className="section-heading">
      <div><span className="eyebrow">{owner ? "所有者视图" : "协作者视图"}</span>
        <h2>{owner ? "所有者工作台" : "协作者工作台"}</h2></div>
      <div className="heading-actions">
        <button disabled={busy} onClick={() => void load()}>刷新工作台</button>
        <button onClick={allJobs}>查看全部评测</button>
        <button onClick={newJob}>新建评测</button>
      </div>
    </div>
    {busy && <p role="status">正在读取工作台…</p>}
    {error && <p role="alert" className="error">{error}</p>}
    {!busy && !error && owner && <section aria-label="待处理审批" className="dashboard-panel">
      <h3>待处理审批</h3>
      <JobCards items={pending} openJob={openJob} empty="当前没有待处理审批。" />
      <p className="muted small">最多显示服务器返回的 5 条待批准评测。</p>
    </section>}
    {!busy && !error && owner && <section aria-label="执行队列" className="dashboard-panel">
      <h3>执行队列</h3>
      <JobCards items={active} openJob={openJob} empty="当前各执行状态都没有评测。" />
      <p className="muted small">每个执行状态最多显示服务器返回的 5 条。</p>
    </section>}
    {!busy && !error && owner && <section aria-label="异常评测" className="dashboard-panel">
      <h3>异常评测</h3>
      <JobCards items={abnormal} openJob={openJob} empty="当前没有失败或部分出错的评测。" />
      <p className="muted small">每个异常状态最多显示服务器返回的 5 条。</p>
    </section>}
    {!busy && !error && <section aria-label="当前可见评测" className="dashboard-panel">
      <h3>当前可见评测</h3>
      <JobCards items={visible} openJob={openJob} empty="当前还没有可见评测。" />
      <p className="muted small">这里只显示服务器返回的当前一页；接口未承诺按创建时间排序，也不代表全部数量。</p>
    </section>}
  </section>;
}
