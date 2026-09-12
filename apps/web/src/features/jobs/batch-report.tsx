import type { JobReport } from "../../lib/contracts";

const outcomes = {
  resolved: "已解决",
  unresolved: "未解决",
  infrastructure_error: "基础设施错误",
  incomplete: "未完成",
};

export default function BatchReportView({
  report, openRun,
}: {
  report: JobReport; openRun: (runId: string) => void;
}) {
  return <section aria-label="批次进度">
    <h3>批次进度</h3>
    <p role="status">{report.stage_message}</p>
    <p>已完成 {report.completed_runs} · 基础设施错误 {report.failed_runs} ·
      未完成 {report.pending_runs}</p>
    <p>已解决 {report.resolved_runs} · 未解决 {report.unresolved_runs}</p>
    {report.failure_code && <p>批次错误：{report.failure_code}</p>}
    <ul>{report.runs.map((run) => <li key={run.run_id}>
      <strong>{run.task_instance_id}</strong> × {run.agent_display_name}：
      {outcomes[run.outcome]}。{run.stage_message}
      {run.failure_code && <> 错误码：{run.failure_code}。</>}
      {(run.status === "COMPLETED" || run.status === "FAILED") &&
      <button onClick={() => openRun(run.run_id)}>
        查看 {run.task_instance_id} / {run.agent_display_name} 运行报告
      </button>}
    </li>)}</ul>
    <p className="muted">阶段来自受控状态事件，不展示 Harbor 进程日志或凭据。</p>
  </section>;
}
