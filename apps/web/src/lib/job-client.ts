import { ApiError, request } from "./api-client";
import type { JobDetail, JobOptions, JobSummary, Page } from "./contracts";

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
export async function jobOptions(): Promise<JobOptions> {
  const value = object(await request("job-options"));
  if (!Array.isArray(value.batch_presets) ||
      !Array.isArray(value.limit_profiles) ||
      !Array.isArray(value.evaluation_tracks) ||
      value.evaluation_tracks.length !== 1 ||
      value.evaluation_tracks[0] !== "closed_book") {
    throw new ApiError("UNAVAILABLE");
  }
  return value as JobOptions;
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
