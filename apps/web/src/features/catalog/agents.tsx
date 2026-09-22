"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { ApiError } from "../../lib/api-client";
import { agentDetail, agents, disableAgent, registerAgent } from "../../lib/catalog-client";
import type { CatalogAgent, Page } from "../../lib/contracts";

export default function AgentsPanel({ owner }: { owner: boolean }) {
  const [data, setData] = useState<Page<CatalogAgent> | null>(null);
  const [detail, setDetail] = useState<CatalogAgent | null>(null);
  const [enabled, setEnabled] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const generation = useRef(0);
  const filter = useRef("");

  const explain = useCallback((value: unknown) => {
    setError(value instanceof ApiError ? value.message : "暂时无法读取配置目录。");
  }, []);
  const load = useCallback(async (cursor?: string) => {
    const revision = ++generation.current;
    setBusy(true); setError(""); setDetail(null);
    const query = new URLSearchParams({ limit: "20", agent_type: "codex" });
    if (filter.current) query.set("enabled", filter.current);
    if (cursor) query.set("cursor", cursor);
    try {
      const result = await agents(query);
      if (revision === generation.current) setData(result);
    } catch (value) {
      if (revision === generation.current) { setData(null); explain(value); }
    } finally { if (revision === generation.current) setBusy(false); }
  }, [explain]);
  useEffect(() => {
    void load();
    return () => { generation.current = -1; };
  }, [load]);

  async function inspect(id: string) {
    const revision = ++generation.current;
    setBusy(true); setError(""); setDetail(null);
    try {
      const result = await agentDetail(id);
      if (revision === generation.current) setDetail(result);
    } catch (value) { if (revision === generation.current) explain(value); }
    finally { if (revision === generation.current) setBusy(false); }
  }
  async function manage(id?: string) {
    const revision = ++generation.current;
    setBusy(true); setError(""); setDetail(null);
    try {
      if (id) await disableAgent(id); else await registerAgent();
      if (revision === generation.current) await load();
    } catch (value) { if (revision === generation.current) { explain(value); setBusy(false); } }
  }

  return <section aria-label="Codex 配置目录">
    <h2>Codex 配置目录</h2>
    <p className="muted">固定配置是评测身份；禁用后仍保留历史，不会自动恢复启用。</p>
    {owner && <button disabled={busy} onClick={() => manage()}>登记固定 Codex 配置</button>}
    <label>配置状态<select value={enabled} disabled={busy} onChange={(event) => {
      setEnabled(event.target.value); filter.current = event.target.value; void load();
    }}>
      <option value="">全部（含已禁用）</option>
      <option value="true">仅启用</option><option value="false">仅禁用</option>
    </select></label>
    {busy && <p role="status">正在读取配置…</p>}
    {error && <p role="alert">{error}</p>}
    {data?.items.length === 0 && <p>暂无匹配配置</p>}
    {data?.items.map((item) => <article key={item.agent_configuration_id}>
      <h3>{item.display_name}</h3>
      <p>{item.agent_version} · {item.model_provider} · {item.model}</p>
      <p>{item.enabled ? "已启用" : "已禁用（保留历史）"}</p>
      <p style={{ overflowWrap: "anywhere" }}>配置指纹：{item.configuration_fingerprint}</p>
      <button disabled={busy} onClick={() => inspect(item.agent_configuration_id)}>
        查看 {item.display_name}
      </button>
      {owner && item.enabled && <button disabled={busy}
        onClick={() => manage(item.agent_configuration_id)}>禁用 {item.display_name}</button>}
    </article>)}
    <button disabled={busy} onClick={() => load()}>刷新配置</button>
    {data?.next_cursor && <button disabled={busy}
      onClick={() => load(data.next_cursor ?? undefined)}>下一页配置</button>}
    {detail && <article aria-label="配置详情">
      <h3>{detail.display_name}</h3>
      <p>推理强度：{detail.public_options?.reasoning_effort}</p>
      <p>默认限制：{detail.limit_profile_id ?? "尚未绑定（等待限制模板任务）"}</p>
    </article>}
  </section>;
}
