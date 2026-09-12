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

export default function EvidenceView({
  runId, artifacts,
}: {
  runId: string; artifacts: RunReport["artifact_links"];
}) {
  const [trajectory, setTrajectory] = useState<TrajectoryPage | null>(null);
  const [error, setError] = useState("");

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
    <ul>{artifacts.map((item) => <li key={item.artifact_id}>
      {names[item.artifact_type]} · {item.size_bytes} 字节 · SHA-256 {item.sha256}
      {item.warnings.includes("PATCH_SIZE_WARNING") ? " · 补丁超过 256 KiB" : ""}
      {item.artifact_type !== "public_trajectory" && <a
        href={`/api/v1/artifacts/${encodeURIComponent(item.artifact_id)}/content`}
        download={filenames[item.artifact_type]}>下载{names[item.artifact_type]}</a>}
    </li>)}</ul>
    {artifacts.some((item) => item.artifact_type === "public_trajectory") &&
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
