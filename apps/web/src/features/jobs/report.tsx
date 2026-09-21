import type { RunReport } from "../../lib/contracts";
import EvidenceView from "./evidence";

function shown(value: number | null, suffix = "") {
  return value === null ? "未知" : `${value}${suffix}`;
}

export default function RunReportView({ report }: { report: RunReport }) {
  const result = report.deterministic_result;
  const usage = report.process_metrics.usage;
  const resources = report.process_metrics.resources;
  return <section aria-label="单题运行报告">
    <h3>单题运行报告</h3>
    <p>Run：{report.run.run_id}</p>
    {result ? <>
      <p>确定性结果：{result.resolved ? "已解决" : "未解决"}</p>
      <p>补丁：{result.patch_exists ? "已产生" : "空补丁"}；
        {result.patch_successfully_applied ? "成功应用" : "未成功应用"}</p>
      <p>固定判卷版本：{result.harness_revision}</p>
    </> : <>
      <p role="status">本次没有形成确定性成绩，可能是执行环境故障、取消或尚未完成。</p>
      <details><summary>技术详情</summary>
        <p>错误码：<code>{report.run.failure_code ?? "无"}</code></p>
        {report.run.failure_summary && <p>{report.run.failure_summary}</p>}
      </details>
    </>}
    <p>用量：输入 {shown(usage.n_input_tokens)} / 缓存 {shown(usage.n_cache_tokens)} /
      输出 {shown(usage.n_output_tokens)} tokens；成本 {shown(usage.cost_usd, " USD")}</p>
    <p>资源：墙钟 {shown(resources.wall_time_sec, " 秒")}；CPU
      {shown(resources.cpu_time_sec, " 秒")}；峰值内存
      {shown(resources.peak_memory_bytes, " 字节")}</p>
    <p>Judge 分析：未启用（0）；人工复核：无；质量决胜：无；复核状态：无需复核</p>
    {report.run.warnings.includes("RAW_ARTIFACT_RUN_LIMIT_EXCEEDED") &&
      <p role="alert">单 Run 原始制品达到 200 MiB 上限；超出制品已明确拒绝。</p>}
    <EvidenceView runId={report.run.run_id} artifacts={report.artifact_links} />
  </section>;
}
