import type { JobDetail } from "../../../lib/contracts";
import type { ComparisonMatrix } from "../../../lib/reporting/comparison-shape";

function isDifferent(values: Array<string | null>) {
  const known = values.filter((value): value is string => value !== null);
  return known.length > 1 && new Set(known).size > 1;
}

export default function ConfigurationComparison({
  matrix, details,
}: {
  matrix: ComparisonMatrix; details: Map<string, JobDetail>;
}) {
  const agents = matrix.columns.map((column) => details.get(column.job_id)?.agent_snapshots
    .find((agent) => agent.agent_configuration_id === column.agent_configuration_id));
  const models = agents.map((agent) => agent ? `${agent.model_provider}/${agent.model}` : null);
  const modelPolicies = agents.map((agent, index) => agent ?
    `${models[index]}/${agent.reasoning_effort}` : null);
  const versions = agents.map((agent) => agent?.agent_version ?? null);
  const limits = matrix.columns.map((column) => {
    const job = details.get(column.job_id);
    return job ? JSON.stringify(job.limit_snapshot) : null;
  });
  const networks = matrix.columns.map((column) => {
    const job = details.get(column.job_id);
    return job ? `${job.network_policy_id}/${JSON.stringify(job.network_policy_snapshot)}` : null;
  });
  const tools = matrix.columns.map((column) => {
    const job = details.get(column.job_id);
    return job ? `${job.tool_profile_id}/${JSON.stringify(job.tool_profile_snapshot)}` : null;
  });
  const revisions = matrix.columns.map((column) => {
    const job = details.get(column.job_id);
    return job ? `${job.harbor_revision}/${job.swe_gym_revision}/${job.swe_bench_fork_revision}` : null;
  });
  const differences = {
    model: isDifferent(modelPolicies), version: isDifferent(versions), limit: isDifferent(limits),
    network: isDifferent(networks), tool: isDifferent(tools),
    revision: isDifferent(revisions),
  };
  const hasUnknown = matrix.columns.some((column, index) =>
    !details.has(column.job_id) || !agents[index]);
  return <section aria-label="冻结配置差异" className="comparison-block">
    <h3>冻结配置</h3>
    <p className="muted small">均读取自提交时冻结的 Job 快照；“差异”只作提示，不参与排序。</p>
    {hasUnknown && <p className="muted small">
      部分快照未知，因此未知列不参与差异判断，也不会被标成真实差异。</p>}
    <div className="configuration-grid">{matrix.columns.map((column, index) => {
      const job = details.get(column.job_id); const agent = agents[index];
      return <article key={`${column.job_id}-${column.agent_configuration_id}`}>
        <h4>{column.agent_display_name}</h4>
        {!job || !agent ? <p>配置快照未知。</p> : <>
          <p>{differences.model && <b>差异 · </b>}模型：{models[index]}；推理 {agent.reasoning_effort}</p>
          <p>{differences.version && <b>差异 · </b>}Agent 版本：{agent.agent_version}</p>
          <p>{differences.limit && <b>差异 · </b>}限制 {job.limit_profile_id}：Agent
            {job.limit_snapshot.agent_wall_timeout_sec} 秒 / {job.limit_snapshot.agent_cpus} CPU /
            {job.limit_snapshot.agent_memory_mb} MiB；并发 {job.limit_snapshot.concurrency}；
            重试 {job.limit_snapshot.max_retries}</p>
          <p>{differences.network && <b>差异 · </b>}网络 {job.network_policy_id}：
            {job.network_policy_snapshot.mode}；搜索 {job.network_policy_snapshot.web_search}；任意主机
            {job.network_policy_snapshot.arbitrary_hosts ? "允许" : "禁止"}</p>
          <p>{differences.tool && <b>差异 · </b>}工具 {job.tool_profile_id}：搜索
            {job.tool_profile_snapshot.web_search}；任意命令
            {job.tool_profile_snapshot.arbitrary_commands ? "允许" : "禁止"}</p>
          <p>{differences.revision && <b>差异 · </b>}冻结版本：Harbor {job.harbor_revision}；SWE-Gym {job.swe_gym_revision}；
            SWE-bench fork {job.swe_bench_fork_revision}</p>
          <details><summary>完整限制快照</summary>
            <pre>{JSON.stringify(job.limit_snapshot, null, 2)}</pre></details>
          <details><summary>技术标识</summary><code>{agent.configuration_fingerprint}</code><br />
            <code>{column.job_id}</code></details>
        </>}
      </article>;
    })}</div>
  </section>;
}
