import { ApiError } from "./api-client";
import type {
  BatchPreset,
  JobDetail,
  JobOptions,
  JobSummary,
  LimitProfile,
  Page,
} from "./contracts";
import { bool, number, object, parseJobSummary, text } from "./jobs/shapes";

export { parseJobSummary } from "./jobs/shapes";

function networkPolicy(value: unknown): JobDetail["network_policy_snapshot"] {
  const item = object(value);
  return {
    mode: text(item, "mode"),
    web_search: text(item, "web_search"),
    arbitrary_hosts: bool(item, "arbitrary_hosts"),
  };
}

function toolPolicy(value: unknown): JobDetail["tool_profile_snapshot"] {
  const item = object(value);
  return {
    agent_type: text(item, "agent_type"),
    web_search: text(item, "web_search"),
    arbitrary_commands: bool(item, "arbitrary_commands"),
  };
}

function limitSnapshot(value: unknown): JobDetail["limit_snapshot"] {
  const item = object(value);
  const keys = [
    "agent_wall_timeout_sec", "agent_cpus", "agent_memory_mb", "agent_storage_mb",
    "evaluator_wall_timeout_sec", "evaluator_cpus", "evaluator_memory_mb", "pids_limit",
    "patch_warning_bytes", "patch_max_bytes", "raw_artifact_max_bytes", "raw_run_max_bytes",
    "concurrency", "max_retries",
  ];
  return Object.fromEntries(keys.map((key) => [key, number(item, key)])) as
    JobDetail["limit_snapshot"];
}

export function parseJobDetail(value: unknown): JobDetail {
  const item = object(value);
  if (!Array.isArray(item.task_snapshots) || !Array.isArray(item.agent_snapshots)) {
    throw new ApiError("UNAVAILABLE");
  }
  return {
    ...parseJobSummary(item),
    task_snapshots: item.task_snapshots.map((value) => {
      const task = object(value);
      return {
        task_id: text(task, "task_id"),
        instance_id: text(task, "instance_id"),
        problem_statement: text(task, "problem_statement"),
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
    network_policy_snapshot: networkPolicy(item.network_policy_snapshot),
    tool_profile_id: text(item, "tool_profile_id"),
    tool_profile_snapshot: toolPolicy(item.tool_profile_snapshot),
    harbor_revision: text(item, "harbor_revision"),
    swe_gym_revision: text(item, "swe_gym_revision"),
    swe_bench_fork_revision: text(item, "swe_bench_fork_revision"),
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
