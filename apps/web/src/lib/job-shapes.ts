import { ApiError } from "./api-client";
import type {
  BatchPreset,
  JobDetail,
  JobOptions,
  JobSummary,
  LimitProfile,
  Page,
} from "./contracts";

function object(value: unknown): Record<string, unknown> {
  if (typeof value !== "object" || value === null || Array.isArray(value)) {
    throw new ApiError("UNAVAILABLE");
  }
  return value as Record<string, unknown>;
}

function text(value: Record<string, unknown>, key: string): string {
  if (typeof value[key] !== "string") throw new ApiError("UNAVAILABLE");
  return value[key];
}

function number(value: Record<string, unknown>, key: string): number {
  if (!Number.isInteger(value[key]) || Number(value[key]) < 0) {
    throw new ApiError("UNAVAILABLE");
  }
  return Number(value[key]);
}

function bool(value: Record<string, unknown>, key: string): boolean {
  if (typeof value[key] !== "boolean") throw new ApiError("UNAVAILABLE");
  return value[key];
}

function nullableText(value: Record<string, unknown>, key: string): string | null {
  if (value[key] !== null && typeof value[key] !== "string") {
    throw new ApiError("UNAVAILABLE");
  }
  return value[key] as string | null;
}

export function parseJobSummary(value: unknown): JobSummary {
  const item = object(value);
  if (
    ![
      "AWAITING_OWNER_APPROVAL", "QUEUED", "PREPARING", "EXECUTING",
      "FINALIZING", "COMPLETED", "FAILED", "REJECTED",
    ].includes(String(item.status)) ||
    item.evaluation_track !== "closed_book" ||
    !["official", "internal_test"].includes(String(item.result_scope)) ||
    !Array.isArray(item.run_ids) ||
    item.run_ids.some((id) => typeof id !== "string") ||
    item.estimated_finish_at !== null
  ) throw new ApiError("UNAVAILABLE");
  const decidedBy = nullableText(item, "owner_decided_by");
  const decidedAt = nullableText(item, "owner_decided_at");
  const reason = nullableText(item, "owner_decision_reason");
  if (
    reason !== null &&
    (reason !== reason.trim() || [...reason].length < 1 || [...reason].length > 500 ||
      /[\u0000-\u001f\u007f-\u009f]/u.test(reason))
  ) throw new ApiError("UNAVAILABLE");
  const awaiting = item.status === "AWAITING_OWNER_APPROVAL";
  if (
    (awaiting && (decidedBy !== null || decidedAt !== null || reason !== null)) ||
    (!awaiting && (decidedBy === null || decidedAt === null))
  ) throw new ApiError("UNAVAILABLE");
  return {
    job_id: text(item, "job_id"),
    status: item.status as JobSummary["status"],
    evaluation_track: "closed_book",
    result_scope: item.result_scope === "official" ? "official" : "internal_test",
    batch_preset: text(item, "batch_preset"),
    limit_profile_id: text(item, "limit_profile_id"),
    trial_count: number(item, "trial_count"),
    run_ids: item.run_ids,
    estimated_finish_at: null,
    created_at: text(item, "created_at"),
    owner_decided_by: decidedBy,
    owner_decided_at: decidedAt,
    owner_decision_reason: reason,
  };
}

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
