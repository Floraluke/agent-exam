"use client";

import { useState } from "react";
import { ApiError } from "../../lib/api-client";
import type { RunReport, TrajectoryPage } from "../../lib/contracts";
import { runTrajectory } from "../../lib/job-client";

const names = {
  agent_patch: "最终补丁",
  public_test_summary: "测试摘要",
  public_trajectory: "安全轨迹",
};
const filenames = {
  agent_patch: "agent.patch",
  public_test_summary: "test-summary.json",
  public_trajectory: "trajectory.jsonl",
};

const publicTypes = new Set(["agent_patch", "public_test_summary", "public_trajectory"]);

export default function EvidenceView({
  runId, artifacts,
}: {
  runId: string; artifacts: RunReport["artifact_links"];
}) {
  const [trajectory, setTrajectory] = useState<TrajectoryPage | null>(null);
  const [error, setError] = useState("");
  const published = artifacts.filter((item) => publicTypes.has(item.artifact_type));
  const raw = artifacts.filter((item) => item.retention_class === "raw_30d");
  const waiting = raw.filter((item) => item.content_status === "not_ready");
  const deleted = raw.filter((item) => item.content_status === "deleted");
  const truncated = raw.filter((item) => item.truncated);

  async function loadTrajectory(after = 0) {
    setError("");
    try {
      const page = await runTrajectory(runId, after);
      setTrajectory((current) => after === 0 || current === null ? page : {
        ...page, items: [...current.items, ...page.items],
      });
    }
    catch (value) {
      setError(value instanceof ApiError ? value.message : "安全轨迹暂不可用。");
    }
  }

  return <section aria-label="安全证据">
    <h4>安全证据</h4>
    <ul>{published.map((item) => <li key={item.artifact_id}>
      {names[item.artifact_type as keyof typeof names]} · {item.size_bytes} 字节 · SHA-256 {item.sha256}
      {item.warnings.includes("PATCH_SIZE_WARNING") ? " · 补丁超过 256 KiB" : ""}
      {item.artifact_type !== "public_trajectory" && <a
        href={`/api/v1/artifacts/${encodeURIComponent(item.artifact_id)}/content`}
        download={filenames[item.artifact_type as keyof typeof filenames]}>
        下载{names[item.artifact_type as keyof typeof names]}</a>}
    </li>)}</ul>
    {raw.length > 0 && <p>受限原始制品：{waiting.length} 个，等待到期维护；
      已按保留策略清理：{deleted.length} 个；审计仍保留。
      {truncated.length > 0 ? `其中 ${truncated.length} 个已显式截断。` : ""}</p>}
    {raw.length > 0 && <ul aria-label="原始制品元数据">{raw.map((item) =>
      <li key={item.artifact_id}>
        {item.artifact_type} · 保留 {item.size_bytes}/{item.original_size_bytes} 字节 ·
        SHA-256 {item.sha256} · 创建 {item.created_at ?? "未知"} ·
        {item.content_status === "deleted"
          ? ` 已删除 ${item.deleted_at ?? "未知"} · 清理者 ${item.deleted_by ?? "未知"} · 原因 ${item.deletion_reason ?? "未知"}`
          : ` 到期 ${item.expires_at ?? "未知"} · 正文不公开`}
      </li>)}</ul>}
    {published.some((item) => item.artifact_type === "public_trajectory") &&
      trajectory === null &&
      <button onClick={() => void loadTrajectory()}>查看安全轨迹</button>}
    {error && <p role="alert">{error}</p>}
    {trajectory && <ol>{trajectory.items.map((event) => <li key={event.sequence}>
      {event.sequence}. {event.summary}
    </li>)}</ol>}
    {trajectory && !trajectory.complete && <button onClick={() =>
      void loadTrajectory(trajectory.next_after_sequence)}>加载更多轨迹</button>}
    <p className="muted">轨迹只含可观察事件；消息正文、工具参数和私密思维链不公开。</p>
  </section>;
}
