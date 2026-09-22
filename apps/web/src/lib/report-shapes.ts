import { ApiError } from "./api-client";
import { RUN_STATUSES } from "./contracts";
import type {
  RunReport, RunStatus, TrajectoryPage,
} from "./contracts";
import { parseArtifact } from "./reporting/artifact-shape";

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

function flag(value: Record<string, unknown>, key: string): boolean {
  if (typeof value[key] !== "boolean") throw new ApiError("UNAVAILABLE");
  return value[key];
}

function texts(value: Record<string, unknown>, key: string): string[] {
  const item = value[key];
  if (!Array.isArray(item) || item.some((entry) => typeof entry !== "string")) {
    throw new ApiError("UNAVAILABLE");
  }
  return item;
}

function nullableNumber(value: Record<string, unknown>, key: string): number | null {
  const item = value[key];
  if (item !== null && (typeof item !== "number" || !Number.isFinite(item) || item < 0)) {
    throw new ApiError("UNAVAILABLE");
  }
  return item as number | null;
}

function natural(value: Record<string, unknown>, key: string): number {
  const item = nullableNumber(value, key);
  if (item === null || !Number.isInteger(item)) throw new ApiError("UNAVAILABLE");
  return item;
}

function runIdentity(value: unknown): RunReport["run"] {
  const item = record(value);
  if (!RUN_STATUSES.includes(String(item.status) as RunStatus)) {
    throw new ApiError("UNAVAILABLE");
  }
  return {
    run_id: text(item, "run_id"), job_id: text(item, "job_id"),
    status: item.status as RunStatus, stage: nullableText(item, "stage"),
    task_instance_id: text(item, "task_instance_id"),
    agent_configuration_id: text(item, "agent_configuration_id"),
    backend_job_ref: nullableText(item, "backend_job_ref"),
    backend_trial_ref: nullableText(item, "backend_trial_ref"),
    failure_code: nullableText(item, "failure_code"),
    failure_summary: nullableText(item, "failure_summary"),
    started_at: nullableText(item, "started_at"),
    finished_at: nullableText(item, "finished_at"),
    warnings: texts(item, "warnings"),
  };
}

function result(value: unknown): RunReport["deterministic_result"] {
  if (value === null) return null;
  const item = record(value);
  const summary = record(item.tests_status_summary);
  return {
    patch_exists: flag(item, "patch_exists"),
    patch_successfully_applied: flag(item, "patch_successfully_applied"),
    resolved: flag(item, "resolved"), tests_status_summary: summary,
    harness_revision: text(item, "harness_revision"),
    duration_ms: nullableNumber(item, "duration_ms"),
  };
}

function metrics(value: unknown): RunReport["process_metrics"] {
  const item = record(value); const usage = record(item.usage);
  const resources = record(item.resources);
  return {
    usage: {
      n_input_tokens: nullableNumber(usage, "n_input_tokens"),
      n_cache_tokens: nullableNumber(usage, "n_cache_tokens"),
      n_output_tokens: nullableNumber(usage, "n_output_tokens"),
      cost_usd: nullableNumber(usage, "cost_usd"),
    },
    resources: {
      wall_time_sec: nullableNumber(resources, "wall_time_sec"),
      cpu_time_sec: nullableNumber(resources, "cpu_time_sec"),
      peak_memory_bytes: nullableNumber(resources, "peak_memory_bytes"),
    },
  };
}

export function parseRunReport(value: unknown): RunReport {
  const item = record(value);
  if (!Array.isArray(item.judge_analyses) || item.judge_analyses.length !== 0 ||
      item.human_review !== null || item.quality_tiebreak !== null ||
      item.review_status !== "NOT_REQUIRED" || !Array.isArray(item.artifact_links)) {
    throw new ApiError("UNAVAILABLE");
  }
  return {
    run: runIdentity(item.run), deterministic_result: result(item.deterministic_result),
    process_metrics: metrics(item.process_metrics), judge_analyses: [],
    human_review: null, quality_tiebreak: null, review_status: "NOT_REQUIRED",
    artifact_links: item.artifact_links.map(parseArtifact),
  };
}

export function parseTrajectoryPage(value: unknown): TrajectoryPage {
  const item = record(value);
  if (!Array.isArray(item.items) || typeof item.complete !== "boolean") {
    throw new ApiError("UNAVAILABLE");
  }
  const next = natural(item, "next_after_sequence");
  const events = item.items.map((value) => {
    const event = record(value); const payload = record(event.payload);
    if (Object.keys(payload).length !== 0) throw new ApiError("UNAVAILABLE");
    return {
      sequence: natural(event, "sequence"),
      occurred_at: text(event, "occurred_at"), source: text(event, "source"),
      type: text(event, "type"), summary: text(event, "summary"), payload: {},
    };
  });
  if (events.some((event, index) => index > 0 &&
      event.sequence <= events[index - 1].sequence) ||
      events.some((event) => event.sequence > next)) {
    throw new ApiError("UNAVAILABLE");
  }
  return { items: events, next_after_sequence: next, complete: item.complete };
}
