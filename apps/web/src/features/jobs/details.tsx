import type { JobDetail } from "../../lib/contracts";

export default function JobDetails({ job }: { job: JobDetail }) {
  const title = {
    AWAITING_OWNER_APPROVAL: "等待所有者批准",
    QUEUED: "已批准，等待执行",
    REJECTED: "已拒绝",
  }[job.status];
  return <article aria-label="评测批次详情">
    <h3>{title}</h3>
    <p>冻结运行数：{job.trial_count}</p>
    <p>批次：{job.batch_preset} · 赛道：闭卷</p>
    <p>限制：{job.limit_profile_id}</p>
    <p>任务：{job.task_snapshots.map((item) => item.instance_id).join("、")}</p>
    <p>配置：{job.agent_snapshots.map((item) => item.display_name).join("、")}</p>
    {job.owner_decided_at && <>
      <p>决定时间：{new Date(job.owner_decided_at).toLocaleString("zh-CN")}</p>
      {job.owner_decision_reason && <p>决定说明：{job.owner_decision_reason}</p>}
    </>}
  </article>;
}
