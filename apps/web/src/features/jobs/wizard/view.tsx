"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { ApiError } from "../../../lib/api-client";
import { agents as loadAgents, tasks as loadTasks } from "../../../lib/catalog-client";
import type { CatalogAgent, CatalogTask, JobDetail, JobOptions } from "../../../lib/contracts";
import { jobDetail, jobOptions, submitJob } from "../../../lib/job-client";
import JobControls from "../controls";

type Attempt = { fingerprint: string; key: string };

export default function JobWizard({
  onCreated,
  onCancel,
}: {
  onCreated: (job: JobDetail) => void;
  onCancel?: () => void;
}) {
  const [options, setOptions] = useState<JobOptions | null>(null);
  const [tasks, setTasks] = useState<CatalogTask[]>([]);
  const [agents, setAgents] = useState<CatalogAgent[]>([]);
  const [selectedTasks, setSelectedTasks] = useState<string[]>([]);
  const [selectedAgents, setSelectedAgents] = useState<string[]>([]);
  const [batch, setBatch] = useState("");
  const [limit, setLimit] = useState("");
  const [step, setStep] = useState(1);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const attempt = useRef<Attempt | null>(null);

  const explain = useCallback((value: unknown) => {
    setError(value instanceof ApiError ? value.message : "暂时无法读取可提交选项。");
  }, []);
  const load = useCallback(async () => {
    setBusy(true); setError("");
    setOptions(null); setTasks([]); setAgents([]);
    try {
      const [taskPage, agentPage, serverOptions] = await Promise.all([
        loadTasks(new URLSearchParams({ limit: "100" })),
        loadAgents(new URLSearchParams({
          limit: "100", agent_type: "codex", enabled: "true",
        })),
        jobOptions(),
      ]);
      setTasks(taskPage.items); setAgents(agentPage.items); setOptions(serverOptions);
      const taskIds = new Set(taskPage.items.map((item) => item.task_id));
      const agentIds = new Set(agentPage.items.map((item) => item.agent_configuration_id));
      setSelectedTasks((items) => items.filter((id) => taskIds.has(id)));
      setSelectedAgents((items) => items.filter((id) => agentIds.has(id)));
      setBatch((current) => serverOptions.batch_presets.some(
        (item) => item.batch_preset === current,
      ) ? current : serverOptions.batch_presets[0]?.batch_preset ?? "");
      setLimit((current) => serverOptions.limit_profiles.some(
        (item) => item.limit_profile_id === current,
      ) ? current : serverOptions.limit_profiles[0]?.limit_profile_id ?? "");
    } catch (value) { explain(value); }
    finally { setBusy(false); }
  }, [explain]);
  useEffect(() => { void load(); }, [load]);

  function toggle(items: string[], id: string, checked: boolean) {
    return checked ? [...new Set([...items, id])] : items.filter((item) => item !== id);
  }
  async function submit() {
    const body = {
      task_ids: selectedTasks, agent_configuration_ids: selectedAgents,
      evaluation_track: "closed_book", batch_preset: batch, limit_profile_id: limit,
    };
    const fingerprint = JSON.stringify(body);
    if (attempt.current?.fingerprint !== fingerprint) {
      attempt.current = { fingerprint, key: crypto.randomUUID() };
    }
    setBusy(true); setError("");
    try {
      const created = await submitJob(body, attempt.current.key);
      onCreated(await jobDetail(created.job_id));
      attempt.current = null;
    } catch (value) { explain(value); }
    finally { setBusy(false); }
  }

  const count = selectedTasks.length * selectedAgents.length;
  const canContinue = step === 1 ? selectedTasks.length > 0 : selectedAgents.length > 0;
  return <section aria-label="新建评测向导" className="wizard">
    <ol className="wizard-steps" aria-label="提交步骤">
      {["选题", "选配置", "核对提交"].map((label, index) => <li
        key={label} aria-current={step === index + 1 ? "step" : undefined}>
        {index + 1}. {label}
      </li>)}
    </ol>
    {error && <p role="alert" className="error">{error}</p>}
    {options && <JobControls step={step} tasks={tasks} agents={agents}
      batches={options.batch_presets} limits={options.limit_profiles}
      selectedTasks={selectedTasks} selectedAgents={selectedAgents}
      batch={batch} limit={limit} busy={busy}
      selectTask={(id, checked) => setSelectedTasks(toggle(selectedTasks, id, checked))}
      selectAgent={(id, checked) => setSelectedAgents(toggle(selectedAgents, id, checked))}
      setBatch={setBatch} setLimit={setLimit} />}
    <div className="wizard-actions">
      {onCancel && <button disabled={busy} onClick={onCancel}>取消新建</button>}
      <button disabled={busy || step === 1} onClick={() => setStep(step - 1)}>上一步</button>
      {step < 3 ? <button disabled={busy || !canContinue}
        onClick={() => setStep(step + 1)}>下一步</button> :
        <button disabled={busy || count === 0} onClick={() => void submit()}>
          提交并等待批准
        </button>}
      <button disabled={busy} onClick={() => void load()}>刷新可选项</button>
    </div>
  </section>;
}
