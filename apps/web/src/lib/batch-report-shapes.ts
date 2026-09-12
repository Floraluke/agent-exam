import { ApiError } from "./api-client";
import { BATCH_OUTCOMES, JOB_STATUSES, RUN_STATUSES } from "./contracts";
import type { JobReport, JobRunReport } from "./contracts";

function record(value: unknown): Record<string, unknown> {
  if (typeof value !== "object" || value === null || Array.isArray(value)) {
    throw new ApiError("UNAVAILABLE");
  }
  return value as Record<string, unknown>;
}

function text(value: Record<string, unknown>, key: string): string {
  if (typeof value[key] !== "string") throw new ApiError("UNAVAILABLE");
  return value[key];
}

function nullableText(value: Record<string, unknown>, key: string): string | null {
  if (value[key] !== null && typeof value[key] !== "string") {
    throw new ApiError("UNAVAILABLE");
  }
  return value[key] as string | null;
}

function natural(value: Record<string, unknown>, key: string): number {
  const item = value[key];
  if (!Number.isInteger(item) || Number(item) < 0) throw new ApiError("UNAVAILABLE");
  return Number(item);
}

function run(value: unknown): JobRunReport {
  const item = record(value);
  if (
    !RUN_STATUSES.includes(String(item.status) as JobRunReport["status"]) ||
    !BATCH_OUTCOMES.includes(String(item.outcome) as JobRunReport["outcome"]) ||
    (item.resolved !== null && typeof item.resolved !== "boolean") ||
    !String(item.report_path).startsWith("/api/v1/reports/runs/")
  ) throw new ApiError("UNAVAILABLE");
  return {
    run_id: text(item, "run_id"),
    status: item.status as JobRunReport["status"],
    stage: nullableText(item, "stage"), stage_message: text(item, "stage_message"),
    task_instance_id: text(item, "task_instance_id"),
    agent_configuration_id: text(item, "agent_configuration_id"),
    agent_display_name: text(item, "agent_display_name"),
    outcome: item.outcome as JobRunReport["outcome"],
    resolved: item.resolved as boolean | null,
    failure_code: nullableText(item, "failure_code"),
    report_path: text(item, "report_path"),
  };
}

export function parseJobReport(value: unknown): JobReport {
  const item = record(value);
  if (
    !JOB_STATUSES.includes(String(item.status) as JobReport["status"]) ||
    !Array.isArray(item.runs)
  ) throw new ApiError("UNAVAILABLE");
  const runs = item.runs.map(run);
  const result = {
    job_id: text(item, "job_id"), status: item.status as JobReport["status"],
    stage_message: text(item, "stage_message"),
    failure_code: nullableText(item, "failure_code"),
    trial_count: natural(item, "trial_count"),
    completed_runs: natural(item, "completed_runs"),
    failed_runs: natural(item, "failed_runs"),
    pending_runs: natural(item, "pending_runs"),
    resolved_runs: natural(item, "resolved_runs"),
    unresolved_runs: natural(item, "unresolved_runs"), runs,
  };
  if (
    result.trial_count !== runs.length ||
    result.completed_runs + result.failed_runs + result.pending_runs > runs.length
  ) throw new ApiError("UNAVAILABLE");
  return result;
}
