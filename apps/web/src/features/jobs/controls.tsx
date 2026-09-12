import type {
  BatchPreset, CatalogAgent, CatalogTask, LimitProfile,
} from "../../lib/contracts";

type Props = {
  tasks: CatalogTask[]; agents: CatalogAgent[]; batches: BatchPreset[];
  limits: LimitProfile[]; selectedTasks: string[]; selectedAgents: string[];
  batch: string; limit: string; busy: boolean;
  selectTask: (id: string, checked: boolean) => void;
  selectAgent: (id: string, checked: boolean) => void;
  setBatch: (id: string) => void; setLimit: (id: string) => void;
};

export default function JobControls(props: Props) {
  const count = props.selectedTasks.length * props.selectedAgents.length;
  return <>
    <fieldset disabled={props.busy}>
      <legend>已登记任务</legend>
      {props.tasks.length === 0 && <p>暂无可提交任务</p>}
      {props.tasks.map((task) => <label key={task.task_id}>
        <input type="checkbox" aria-label={`任务 ${task.instance_id}`}
          checked={props.selectedTasks.includes(task.task_id)}
          onChange={(event) => props.selectTask(
            task.task_id, event.target.checked)} />
        {task.instance_id}
      </label>)}
    </fieldset>
    <fieldset disabled={props.busy}>
      <legend>启用的 Codex 配置</legend>
      {props.agents.length === 0 && <p>暂无可提交配置</p>}
      {props.agents.map((agent) => <label key={agent.agent_configuration_id}>
        <input type="checkbox" aria-label={`配置 ${agent.display_name}`}
          checked={props.selectedAgents.includes(agent.agent_configuration_id)}
          onChange={(event) => props.selectAgent(
            agent.agent_configuration_id, event.target.checked)} />
        {agent.display_name}
      </label>)}
    </fieldset>
    <label>批次规模<select aria-label="批次规模" value={props.batch}
      disabled={props.busy} onChange={(event) => props.setBatch(event.target.value)}>
      {props.batches.map((item) => <option key={item.batch_preset}
        value={item.batch_preset}>
        {item.batch_preset}（{item.minimum_tasks}–{item.maximum_tasks} 题）
      </option>)}
    </select></label>
    <label>评测赛道<select aria-label="评测赛道" value="closed_book" disabled>
      <option value="closed_book">闭卷</option>
    </select></label>
    <label>资源限制<select aria-label="资源限制" value={props.limit}
      disabled={props.busy} onChange={(event) => props.setLimit(event.target.value)}>
      {props.limits.map((item) => <option key={item.limit_profile_id}
        value={item.limit_profile_id}>{item.limit_profile_id}</option>)}
    </select></label>
    <p>组合数量：{count}</p>
  </>;
}
