"use client";

import { useEffect, useState } from "react";
import { ApiError } from "../../lib/api-client";
import { agents as loadAgents, tasks as loadTasks } from "../../lib/catalog-client";
import type {
  CatalogAgent, CatalogTask, JobDetail, JobOptions,
} from "../../lib/contracts";
import { jobDetail, jobOptions, jobs, submitJob } from "../../lib/job-client";
import JobControls from "./controls";
import JobDetails from "./details";

export default function JobsPanel() {
  const [options, setOptions] = useState<JobOptions | null>(null);
  const [tasks, setTasks] = useState<CatalogTask[]>([]);
  const [agents, setAgents] = useState<CatalogAgent[]>([]);
  const [selectedTasks, setSelectedTasks] = useState<string[]>([]);
  const [selectedAgents, setSelectedAgents] = useState<string[]>([]);
  const [batch, setBatch] = useState("demo");
  const [limit, setLimit] = useState("default-single-host-v1");
  const [current, setCurrent] = useState<JobDetail | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  function explain(value: unknown) {
    setError(value instanceof ApiError ? value.message : "暂时无法读取评测批次。");
  }
  async function load() {
    setBusy(true); setError("");
    try {
      const [taskPage, agentPage, serverOptions, jobPage] = await Promise.all([
        loadTasks(new URLSearchParams({ limit: "100" })),
        loadAgents(new URLSearchParams({
          limit: "100", agent_type: "codex", enabled: "true",
        })),
        jobOptions(), jobs(),
      ]);
      setTasks(taskPage.items); setAgents(agentPage.items); setOptions(serverOptions);
      const taskIds = new Set(taskPage.items.map((item) => item.task_id));
      const agentIds = new Set(
        agentPage.items.map((item) => item.agent_configuration_id),
      );
      setSelectedTasks((current) => current.filter((id) => taskIds.has(id)));
      setSelectedAgents((current) => current.filter((id) => agentIds.has(id)));
      setBatch(serverOptions.batch_presets[0]?.batch_preset ?? "");
      setLimit(serverOptions.limit_profiles[0]?.limit_profile_id ?? "");
      if (jobPage.items[0]) setCurrent(await jobDetail(jobPage.items[0].job_id));
    } catch (value) { explain(value); }
    finally { setBusy(false); }
  }
  useEffect(() => { void load(); }, []);

  function toggle(current: string[], id: string, checked: boolean) {
    return checked
      ? [...new Set([...current, id])]
      : current.filter((item) => item !== id);
  }
  async function submit() {
    setBusy(true); setError("");
    try {
      const created = await submitJob({
        task_ids: selectedTasks,
        agent_configuration_ids: selectedAgents,
        evaluation_track: "closed_book",
        batch_preset: batch,
        limit_profile_id: limit,
      }, crypto.randomUUID());
      setCurrent(await jobDetail(created.job_id));
    } catch (value) { explain(value); }
    finally { setBusy(false); }
  }
  async function refresh() {
    if (!current) return;
    setBusy(true); setError("");
    try { setCurrent(await jobDetail(current.job_id)); }
    catch (value) { explain(value); }
    finally { setBusy(false); }
  }
  const count = selectedTasks.length * selectedAgents.length;
  return <section aria-label="提交评测">
    <h2>提交评测</h2>
    <p className="muted">提交只冻结选择并等待所有者批准，不会立即运行 Agent。</p>
    {error && <p role="alert">{error}</p>}
    {options && <JobControls tasks={tasks} agents={agents}
      batches={options.batch_presets} limits={options.limit_profiles}
      selectedTasks={selectedTasks} selectedAgents={selectedAgents}
      batch={batch} limit={limit} busy={busy}
      selectTask={(id, checked) => setSelectedTasks(
        toggle(selectedTasks, id, checked))}
      selectAgent={(id, checked) => setSelectedAgents(
        toggle(selectedAgents, id, checked))}
      setBatch={setBatch} setLimit={setLimit} />}
    <button disabled={busy} onClick={load}>刷新可提交选项</button>
    <button disabled={busy || count === 0} onClick={submit}>提交等待批准</button>
    {current && <>
      <JobDetails job={current} />
      <button disabled={busy} onClick={refresh}>刷新当前批次</button>
    </>}
  </section>;
}
