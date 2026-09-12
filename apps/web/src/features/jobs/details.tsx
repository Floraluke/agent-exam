import type { JobDetail } from "../../lib/contracts";

export default function JobDetails({ job }: { job: JobDetail }) {
  const title = {
    AWAITING_OWNER_APPROVAL: "等待所有者批准",
    QUEUED: "已批准，等待执行",
    PREPARING: "正在准备运行",
    EXECUTING: "Agent 正在执行",
    FINALIZING: "正在核验并保存结果",
    COMPLETED: "执行完成",
    FAILED: "运行失败",
    REJECTED: "已拒绝",
  }[job.status];
  return <article aria-label="评测批次详情">
    <h3>{title}</h3>
    <p>冻结运行数：{job.trial_count}</p>
    {job.trial_count > 1 && <p>开发期限制：任务 07 接通前，多组合批次不会被部分领取。</p>}
    <p>批次：{job.batch_preset} · 赛道：闭卷</p>
    <p>结果范围：{job.result_scope === "official" ? "正式" : "内部测试"}</p>
    <p>限制：{job.limit_profile_id}；Agent {job.limit_snapshot.agent_wall_timeout_sec} 秒 /
      {job.limit_snapshot.agent_cpus} CPU / {job.limit_snapshot.agent_memory_mb} MiB 内存 /
      {job.limit_snapshot.agent_storage_mb} MiB 存储；判卷 {job.limit_snapshot.evaluator_wall_timeout_sec} 秒 /
      {job.limit_snapshot.evaluator_cpus} CPU / {job.limit_snapshot.evaluator_memory_mb} MiB 内存；
      PID {job.limit_snapshot.pids_limit}；并发 {job.limit_snapshot.concurrency}；重试 {job.limit_snapshot.max_retries}</p>
    <p>制品限制：补丁警告 {job.limit_snapshot.patch_warning_bytes} 字节 / 上限
      {job.limit_snapshot.patch_max_bytes} 字节；单原始制品 {job.limit_snapshot.raw_artifact_max_bytes} 字节；
      单 Run 原始制品 {job.limit_snapshot.raw_run_max_bytes} 字节</p>
    <p>任务：{job.task_snapshots.map((item) => item.instance_id).join("、")}</p>
    <p>配置：{job.agent_snapshots.map((item) => item.display_name).join("、")}</p>
    {job.agent_snapshots.map((item) => <p key={item.agent_configuration_id}>
      Agent 版本：{item.agent_type} / {item.agent_version}；模型：{item.model_provider} / {item.model}；
      推理配置：{item.reasoning_effort}；配置指纹：{item.configuration_fingerprint}
    </p>)}
    <p>网络策略：{job.network_policy_id}（{job.network_policy_snapshot.mode}；
      web search {job.network_policy_snapshot.web_search}；任意主机
      {job.network_policy_snapshot.arbitrary_hosts ? "允许" : "禁止"}）</p>
    <p>工具策略：{job.tool_profile_id}（{job.tool_profile_snapshot.agent_type}；
      web search {job.tool_profile_snapshot.web_search}；任意命令
      {job.tool_profile_snapshot.arbitrary_commands ? "允许" : "禁止"}）</p>
    <p>冻结版本：Harbor {job.harbor_revision}；SWE-Gym {job.swe_gym_revision}；
      SWE-Bench-Fork {job.swe_bench_fork_revision}</p>
    {job.owner_decided_at && <>
      <p>决定者：{job.owner_decided_by}</p>
      <p>决定时间：{new Date(job.owner_decided_at).toLocaleString("zh-CN")}</p>
      {job.owner_decision_reason && <p>决定说明：{job.owner_decision_reason}</p>}
    </>}
  </article>;
}
