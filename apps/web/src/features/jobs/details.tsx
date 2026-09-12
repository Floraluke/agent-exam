import type { JobDetail } from "../../lib/contracts";

export default function JobDetails({ job }: { job: JobDetail }) {
  return <article aria-label="评测批次详情">
    <h3>等待所有者批准</h3>
    <p>冻结运行数：{job.trial_count}</p>
    <p>批次：{job.batch_preset} · 赛道：闭卷</p>
    <p>限制：{job.limit_profile_id}</p>
    <p>任务：{job.task_snapshots.map((item) => item.instance_id).join("、")}</p>
    <p>配置：{job.agent_snapshots.map((item) => item.display_name).join("、")}</p>
  </article>;
}
