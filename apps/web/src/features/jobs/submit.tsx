"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { ApiError } from "../../lib/api-client";
import type { JobDetail, JobReport, RunReport } from "../../lib/contracts";
import { cancelJob, decideJob, jobDetail, jobReport, runReport } from "../../lib/job-client";
import OwnerApprovalPanel from "./approval";
import BatchReportView from "./batch-report";
import CancellationPanel from "./cancellation";
import JobDetails from "./details";
import RecoveryPanel from "./lifecycle/recovery";
import RunReportView from "./report";
import JobWizard from "./wizard/view";

export default function JobsPanel({
  owner,
  showWizard = true,
  onCreated,
  onCancel,
}: {
  owner: boolean;
  showWizard?: boolean;
  onCreated?: (job: JobDetail) => void;
  onCancel?: () => void;
}) {
  const [current, setCurrent] = useState<JobDetail | null>(null);
  const [report, setReport] = useState<RunReport | null>(null);
  const [batchReport, setBatchReport] = useState<JobReport | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const decisionAttempt = useRef<{
    job: string; kind: "approve" | "reject"; reason: string; key: string;
  } | null>(null);
  const cancelAttempt = useRef<{ job: string; reason: string; key: string } | null>(null);

  const explain = useCallback((value: unknown) => {
    setError(value instanceof ApiError ? value.message : "暂时无法读取评测批次。");
  }, []);
  // 动作已被服务端受理，但随后的重读失败：页面只能停在旧状态，必须显式说明，
  // 不能让用户以为操作没生效、也不能声称一个页面并未确认成功的结果。
  // 返回错误值本身，让调用方照常显示出既有的重读失败文案，不吞掉原错误。
  async function rereadAfterAction(jobId: string): Promise<unknown | null> {
    try { setCurrent(await jobDetail(jobId)); return null; }
    catch (value) {
      setNotice("刷新失败，当前显示的可能不是最新状态，请手动刷新。");
      return value;
    }
  }
  const restore = useCallback(async () => {
    setBusy(true); setError("");
    try {
      const requested = showWizard ? null :
        new URL(window.location.href).searchParams.get("job");
      setCurrent(requested ? await jobDetail(requested) : null);
      setReport(null); setBatchReport(null);
    } catch (value) { explain(value); }
    finally { setBusy(false); }
  }, [explain, showWizard]);
  useEffect(() => { void restore(); }, [restore]);

  async function refresh() {
    if (!current) return;
    setBusy(true); setError("");
    try {
      setCurrent(await jobDetail(current.job_id));
      // 成功重读后，"可能不是最新状态"的提示必须消失，否则它会一直误导用户。
      setNotice("");
      if (batchReport) setBatchReport(await jobReport(current.job_id));
      setReport(null);
    } catch (value) { explain(value); }
    finally { setBusy(false); }
  }
  async function openReport(runId?: string) {
    if (!current) return;
    const id = runId ?? (current.run_ids.length === 1 ? current.run_ids[0] : null);
    if (!id) return;
    setBusy(true); setError("");
    try { setReport(await runReport(id)); }
    catch (value) { explain(value); }
    finally { setBusy(false); }
  }
  async function openBatchReport() {
    if (!current) return;
    setBusy(true); setError("");
    try { setBatchReport(await jobReport(current.job_id)); setReport(null); }
    catch (value) { explain(value); }
    finally { setBusy(false); }
  }
  async function decide(kind: "approve" | "reject", reason: string) {
    if (!current) return;
    setBusy(true); setError(""); setNotice("");
    const previous = decisionAttempt.current;
    const attempt = previous && previous.job === current.job_id &&
      previous.kind === kind && previous.reason === reason ? previous :
      { job: current.job_id, kind, reason, key: crypto.randomUUID() };
    decisionAttempt.current = attempt;
    try {
      await decideJob(current.job_id, kind, reason, attempt.key);
      const failed = await rereadAfterAction(current.job_id);
      if (failed === null) decisionAttempt.current = null; else explain(failed);
    } catch (value) {
      if (value instanceof ApiError && value.code === "JOB_STATE_CONFLICT") {
        // 冲突后重读服务器事实；重读也失败时保留冲突文案，另加过期提示。
        await rereadAfterAction(current.job_id);
      }
      explain(value);
    } finally { setBusy(false); }
  }
  async function cancel(reason: string) {
    if (!current) return;
    setBusy(true); setError(""); setNotice("");
    const previous = cancelAttempt.current;
    const attempt = previous && previous.job === current.job_id && previous.reason === reason
      ? previous : { job: current.job_id, reason, key: crypto.randomUUID() };
    cancelAttempt.current = attempt;
    try {
      await cancelJob(current.job_id, reason, attempt.key);
      const failed = await rereadAfterAction(current.job_id);
      if (failed === null) cancelAttempt.current = null; else explain(failed);
    } catch (value) {
      if (value instanceof ApiError && value.code === "JOB_STATE_CONFLICT") {
        // 冲突后重读服务器事实；重读也失败时保留冲突文案，另加过期提示。
        await rereadAfterAction(current.job_id);
      }
      explain(value);
    } finally { setBusy(false); }
  }

  return <section aria-label="提交评测">
    {showWizard && <JobWizard onCancel={onCancel} onCreated={(job) => {
      setCurrent(job); setReport(null); setBatchReport(null); onCreated?.(job);
    }} />}
    {error && <p role="alert" className="error">{error}</p>}
    {notice && <p role="status" className="error">{notice}</p>}
    {current && <>
      <JobDetails job={current} />
      <RecoveryPanel job={current} owner={owner} onChanged={setCurrent} />
      {owner && current.status === "AWAITING_OWNER_APPROVAL" &&
        <OwnerApprovalPanel busy={busy} decide={decide} />}
      {["AWAITING_OWNER_APPROVAL", "QUEUED", "PREPARING", "EXECUTING"]
        .includes(current.status) && <CancellationPanel busy={busy} cancel={cancel} />}
      <button disabled={busy} onClick={refresh}>刷新当前批次</button>
      <button disabled={busy} onClick={openBatchReport}>查看批次进度</button>
      {["COMPLETED", "COMPLETED_WITH_ERRORS", "FAILED"].includes(current.status) &&
        current.run_ids.length === 1 &&
        <button disabled={busy} onClick={() => openReport()}>查看单题运行报告</button>}
      {batchReport && <BatchReportView report={batchReport}
        openRun={(runId) => void openReport(runId)} />}
      {report && <RunReportView report={report} />}
    </>}
  </section>;
}
