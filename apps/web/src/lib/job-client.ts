import { ApiError, request } from "./api-client";
import type {
  BatchPreset, JobDetail, JobOptions, JobSummary, LimitProfile, Page,
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
function summary(value: unknown): JobSummary {
  const item = object(value);
  if (item.status !== "AWAITING_OWNER_APPROVAL" ||
      item.evaluation_track !== "closed_book" ||
      !["official", "internal_test"].includes(String(item.result_scope)) ||
      !Array.isArray(item.run_ids) ||
      item.run_ids.some((id) => typeof id !== "string") ||
      item.estimated_finish_at !== null) throw new ApiError("UNAVAILABLE");
  return {
    job_id: text(item, "job_id"), status: "AWAITING_OWNER_APPROVAL",
    evaluation_track: "closed_book",
    result_scope: item.result_scope === "official" ? "official" : "internal_test",
    batch_preset: text(item, "batch_preset"),
    limit_profile_id: text(item, "limit_profile_id"),
    trial_count: number(item, "trial_count"), run_ids: item.run_ids,
    estimated_finish_at: null, created_at: text(item, "created_at"),
  };
}
function detail(value: unknown): JobDetail {
  const item = object(value);
  if (!Array.isArray(item.task_snapshots) || !Array.isArray(item.agent_snapshots)) {
    throw new ApiError("UNAVAILABLE");
  }
  return {
    ...summary(item),
    task_snapshots: item.task_snapshots.map((value) => {
      const task = object(value);
      return {
        task_id: text(task, "task_id"), instance_id: text(task, "instance_id"),
        problem_statement: text(task, "problem_statement"),
      };
    }),
    agent_snapshots: item.agent_snapshots.map((value) => {
      const agent = object(value);
      return {
        agent_configuration_id: text(agent, "agent_configuration_id"),
        display_name: text(agent, "display_name"),
        configuration_fingerprint: text(agent, "configuration_fingerprint"),
      };
    }),
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
  return {
    limit_profile_id: text(item, "limit_profile_id"),
    agent_wall_timeout_sec: number(item, "agent_wall_timeout_sec"),
    agent_cpus: number(item, "agent_cpus"),
    agent_memory_mb: number(item, "agent_memory_mb"),
    agent_storage_mb: number(item, "agent_storage_mb"),
    evaluator_wall_timeout_sec: number(item, "evaluator_wall_timeout_sec"),
    evaluator_cpus: number(item, "evaluator_cpus"),
    evaluator_memory_mb: number(item, "evaluator_memory_mb"),
    pids_limit: number(item, "pids_limit"),
    patch_warning_bytes: number(item, "patch_warning_bytes"),
    patch_max_bytes: number(item, "patch_max_bytes"),
    raw_artifact_max_bytes: number(item, "raw_artifact_max_bytes"),
    raw_run_max_bytes: number(item, "raw_run_max_bytes"),
    concurrency: number(item, "concurrency"),
    max_retries: number(item, "max_retries"),
  };
}
export async function jobOptions(): Promise<JobOptions> {
  const value = object(await request("job-options"));
  if (!Array.isArray(value.batch_presets) ||
      !Array.isArray(value.limit_profiles) ||
      !Array.isArray(value.evaluation_tracks) ||
      value.evaluation_tracks.length !== 1 ||
      value.evaluation_tracks[0] !== "closed_book") {
    throw new ApiError("UNAVAILABLE");
  }
  const maximumAgents = number(value, "maximum_agent_configurations");
  const maximumRuns = number(value, "maximum_runs");
  if (maximumAgents < 1 || maximumRuns < 1) throw new ApiError("UNAVAILABLE");
  return {
    batch_presets: value.batch_presets.map(batchPreset),
    evaluation_tracks: ["closed_book"],
    limit_profiles: value.limit_profiles.map(limitProfile),
    maximum_agent_configurations: maximumAgents,
    maximum_runs: maximumRuns,
  };
}
export async function submitJob(body: object, key: string): Promise<JobSummary> {
  return summary(await request("jobs", body, { "Idempotency-Key": key }));
}
export async function jobDetail(id: string): Promise<JobDetail> {
  return detail(await request("jobs/" + encodeURIComponent(id)));
}
export async function jobs(): Promise<Page<JobSummary>> {
  const value = object(await request("jobs?limit=20"));
  if (!Array.isArray(value.items) ||
      (value.next_cursor !== null && typeof value.next_cursor !== "string")) {
    throw new ApiError("UNAVAILABLE");
  }
  return { items: value.items.map(summary), next_cursor: value.next_cursor };
}
