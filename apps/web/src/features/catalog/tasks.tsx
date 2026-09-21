"use client";

import { useCallback, useEffect, useRef, useState, type FormEvent } from "react";
import { ApiError } from "../../lib/api-client";
import { registerTask, taskDetail, tasks } from "../../lib/catalog-client";
import type { CatalogTask, Page } from "../../lib/contracts";

export default function TasksPanel({ owner }: { owner: boolean }) {
  const [data, setData] = useState<Page<CatalogTask> | null>(null);
  const [detail, setDetail] = useState<CatalogTask | null>(null);
  const [repo, setRepo] = useState("");
  const [dataset, setDataset] = useState("");
  const [split, setSplit] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const generation = useRef(0);
  const filters = useRef({ repo: "", dataset: "", split: "" });

  const explain = useCallback((value: unknown) => {
    setError(value instanceof ApiError ? value.message : "暂时无法读取任务目录。");
  }, []);
  const load = useCallback(async (cursor?: string) => {
    const revision = ++generation.current;
    setBusy(true); setError(""); setDetail(null);
    const query = new URLSearchParams({ limit: "20" });
    const current = filters.current;
    if (current.repo) query.set("repo", current.repo);
    if (current.dataset) query.set("dataset_id", current.dataset);
    if (current.split) query.set("split", current.split);
    if (cursor) query.set("cursor", cursor);
    try {
      const result = await tasks(query);
      if (generation.current === revision) setData(result);
    } catch (value) {
      if (generation.current === revision) { setData(null); explain(value); }
    } finally { if (generation.current === revision) setBusy(false); }
  }, [explain]);
  useEffect(() => {
    void load();
    return () => { generation.current = -1; };
  }, [load]);

  function filter(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    filters.current = { repo, dataset, split };
    void load();
  }
  async function inspect(id: string) {
    const revision = ++generation.current;
    setBusy(true); setError(""); setDetail(null);
    try {
      const result = await taskDetail(id);
      if (revision === generation.current) setDetail(result);
    } catch (value) { if (revision === generation.current) explain(value); }
    finally { if (revision === generation.current) setBusy(false); }
  }
  async function register() {
    const revision = ++generation.current;
    setBusy(true); setError("");
    try {
      await registerTask();
      if (revision === generation.current) {
        filters.current = { repo: "", dataset: "", split: "" };
        setRepo(""); setDataset(""); setSplit("");
        await load();
      }
    } catch (value) { if (revision === generation.current) { explain(value); setBusy(false); } }
  }

  return <section aria-label="任务目录">
    <h2>任务目录</h2>
    <p className="muted">这里只登记、查看固定题目；登记不会运行 Agent。</p>
    {owner && <button disabled={busy} onClick={register}>登记已核验题目</button>}
    <form onSubmit={filter}>
      <label>仓库筛选<input maxLength={128} value={repo}
        onChange={(event) => setRepo(event.target.value)} /></label>
      <label>数据集筛选<input maxLength={128} value={dataset}
        onChange={(event) => setDataset(event.target.value)} /></label>
      <label>数据划分筛选<input maxLength={64} value={split}
        onChange={(event) => setSplit(event.target.value)} /></label>
      <button disabled={busy}>筛选任务</button>
    </form>
    {busy && <p role="status">正在读取任务…</p>}
    {error && <p role="alert">{error}</p>}
    {data?.items.length === 0 && <p>暂无匹配任务</p>}
    {data?.items.map((item) => <article key={item.task_id}>
      <p>{item.instance_id} · {item.repo}</p>
      <button disabled={busy} onClick={() => inspect(item.task_id)}>查看 {item.instance_id}</button>
    </article>)}
    <button disabled={busy} onClick={() => load()}>刷新任务</button>
    {data?.next_cursor && <button disabled={busy}
      onClick={() => load(data.next_cursor ?? undefined)}>下一页任务</button>}
    {detail && <article aria-label="任务详情">
      <h3>{detail.instance_id}</h3>
      <p>数据集：{detail.dataset_id} / {detail.split}</p>
      <p>固定版本：{detail.dataset_revision}</p>
      <p>代码基线：{detail.base_commit}</p>
      <pre style={{ whiteSpace: "pre-wrap", overflowWrap: "anywhere" }}>{detail.problem_statement}</pre>
    </article>}
  </section>;
}
