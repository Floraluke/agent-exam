import { ApiError } from "./api-client";
import type {
  BatchPreset,
  JobDetail,
  JobOptions,
  JobSummary,
  LimitProfile,
  Page,
  StateEvent,
} from "./contracts";
import { RUN_STATUSES } from "./contracts";
import {
  nullableText, number, object, parseJobSummary, text,
} from "./jobs/shapes";
import {
  limitSnapshot, networkSnapshot, toolSnapshot,
} from "./jobs/snapshots";

export { parseJobSummary } from "./jobs/shapes";

function stateEvent(value: unknown): StateEvent {
  const item = object(value);
  return {
    sequence: number(item, "sequence"),
    from_status: nullableText(item, "from_status"),
    to_status: text(item, "to_status"),
    reason_code: text(item, "reason_code"),
    occurred_at: text(item, "occurred_at"),
    actor_user_id: nullableText(item, "actor_user_id"),
    note: nullableText(item, "note"),
  };
}

function runDetail(value: unknown): JobDetail["runs"][number] {
  const item = object(value);
  if (!RUN_STATUSES.includes(String(item.status) as typeof RUN_STATUSES[number]) ||
      !Array.isArray(item.state_events)) throw new ApiError("UNAVAILABLE");
  const failureCode = nullableText(item, "failure_code");
  const failureSummary = nullableText(item, "failure_summary");
  if ((failureCode === null) !== (failureSummary === null) ||
      (item.status === "FAILED") !== (failureCode !== null)) {
    throw new ApiError("UNAVAILABLE");
  }
  return {
    run_id: text(item, "run_id"), task_id: text(item, "task_id"),
    agent_configuration_id: text(item, "agent_configuration_id"),
    status: item.status as JobDetail["runs"][number]["status"],
    backend_kind: text(item, "backend_kind"),
    backend_revision: text(item, "backend_revision"),
    execution_contract_version: text(item, "execution_contract_version"),
    stage: nullableText(item, "stage"), failure_code: failureCode,
    failure_summary: failureSummary, state_events: item.state_events.map(stateEvent),
  };
}

export function parseJobDetail(value: unknown): JobDetail {
  const item = object(value);
  if (!Array.isArray(item.task_snapshots) || !Array.isArray(item.agent_snapshots) ||
      !Array.isArray(item.job_state_events) || !Array.isArray(item.runs)) {
    throw new ApiError("UNAVAILABLE");
  }
  return {
    ...parseJobSummary(item),
    lease_expires_at: nullableText(item, "lease_expires_at"),
    task_snapshots: item.task_snapshots.map((value) => {
      const task = object(value);
      return {
        task_id: text(task, "task_id"),
        instance_id: text(task, "instance_id"),
        problem_statement: text(task, "problem_statement"),
        // 冻结的比较条件：响应本就有，排行榜预填靠它们，不在前端拼接或猜测。
        dataset_id: text(task, "dataset_id"),
        dataset_revision: text(task, "dataset_revision"),
        split: text(task, "split"),
        repo: text(task, "repo"),
      };
    }),
    agent_snapshots: item.agent_snapshots.map((value) => {
      const agent = object(value);
      return {
        agent_configuration_id: text(agent, "agent_configuration_id"),
        display_name: text(agent, "display_name"),
        agent_type: text(agent, "agent_type"),
        agent_version: text(agent, "agent_version"),
        model_provider: text(agent, "model_provider"),
        model: text(agent, "model"),
        reasoning_effort: text(agent, "reasoning_effort"),
        configuration_fingerprint: text(agent, "configuration_fingerprint"),
      };
    }),
    limit_snapshot: limitSnapshot(item.limit_snapshot),
    network_policy_id: text(item, "network_policy_id"),
    network_policy_snapshot: networkSnapshot(item.network_policy_snapshot),
    tool_profile_id: text(item, "tool_profile_id"),
    tool_profile_snapshot: toolSnapshot(item.tool_profile_snapshot),
    harbor_revision: text(item, "harbor_revision"),
    swe_gym_revision: text(item, "swe_gym_revision"),
    swe_bench_fork_revision: text(item, "swe_bench_fork_revision"),
    job_state_events: item.job_state_events.map(stateEvent),
    runs: item.runs.map(runDetail),
  };
}

function batchPreset(value: unknown): BatchPreset {
  const item = object(value);
  const minimum = number(item, "minimum_tasks");
  const maximum = number(item, "maximum_tasks");
  if (minimum < 1 || maximum < minimum) throw new ApiError("UNAVAILABLE");
  return {
    batch_preset: text(item, "batch_preset"),
    minimum_tasks: minimum,
    maximum_tasks: maximum,
  };
}

function limitProfile(value: unknown): LimitProfile {
  const item = object(value);
  return { limit_profile_id: text(item, "limit_profile_id"), ...limitSnapshot(item) };
}

export function parseJobOptions(value: unknown): JobOptions {
  const item = object(value);
  if (
    !Array.isArray(item.batch_presets) || !Array.isArray(item.limit_profiles) ||
    !Array.isArray(item.evaluation_tracks) || item.evaluation_tracks.length !== 1 ||
    item.evaluation_tracks[0] !== "closed_book"
  ) throw new ApiError("UNAVAILABLE");
  const maximumAgents = number(item, "maximum_agent_configurations");
  const maximumRuns = number(item, "maximum_runs");
  if (maximumAgents < 1 || maximumRuns < 1) throw new ApiError("UNAVAILABLE");
  return {
    batch_presets: item.batch_presets.map(batchPreset),
    evaluation_tracks: ["closed_book"],
    limit_profiles: item.limit_profiles.map(limitProfile),
    maximum_agent_configurations: maximumAgents,
    maximum_runs: maximumRuns,
  };
}

export function parseJobPage(value: unknown): Page<JobSummary> {
  const item = object(value);
  if (!Array.isArray(item.items) ||
      (item.next_cursor !== null && typeof item.next_cursor !== "string")) {
    throw new ApiError("UNAVAILABLE");
  }
  return { items: item.items.map(parseJobSummary), next_cursor: item.next_cursor };
}
