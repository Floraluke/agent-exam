import { ApiError } from "../api-client";

export type MetricValue = { value: number | null; coverage: number };
export type LeaderboardScope = {
  dataset_id: string; dataset_revision: string; split: string; repo: string;
  evaluation_track: string; network_policy_id: string;
  network_policy_snapshot: Record<string, unknown>; tool_profile_id: string;
  tool_profile_snapshot: Record<string, unknown>; limit_profile_id: string;
  limit_snapshot: Record<string, unknown>; harbor_revision: string;
  swe_gym_revision: string; swe_bench_fork_revision: string;
  execution_contract_version: string;
};
export type LeaderboardAgent = {
  agent_configuration_id: string; display_name: string; agent_type: string;
  agent_version: string; model_provider: string; model: string;
  reasoning_effort: string; configuration_fingerprint: string;
};
export type LeaderboardSource = {
  task_id: string; instance_id: string; job_id: string; run_id: string;
  rerun_of_job_id: string | null;
  classification: "resolved" | "unresolved" | "infrastructure_error" | "unknown";
};
export type LeaderboardMetrics = {
  selected_runs: number; n_input_tokens: MetricValue; n_cache_tokens: MetricValue;
  n_output_tokens: MetricValue; cost_usd: MetricValue; wall_time_sec: MetricValue;
  cpu_time_sec: MetricValue; peak_memory_bytes: MetricValue;
};
export type LeaderboardRow = {
  rank: number; comparison_scope: LeaderboardScope; agent: LeaderboardAgent;
  total_tasks: number; deterministic_count: number; resolved_count: number;
  unresolved_count: number; infrastructure_error_count: number;
  unknown_count: number; resolved_rate: number; process_metrics: LeaderboardMetrics;
  sources: LeaderboardSource[]; quality_tiebreak: null; generated_at: string;
};
export type LeaderboardPage = {
  items: LeaderboardRow[]; next_cursor: string | null;
};

function record(value: unknown): Record<string, unknown> {
  if (typeof value !== "object" || value === null || Array.isArray(value)) {
    throw new ApiError("UNAVAILABLE");
  }
  return value as Record<string, unknown>;
}
function text(item: Record<string, unknown>, key: string): string {
  if (typeof item[key] !== "string") throw new ApiError("UNAVAILABLE");
  return item[key];
}
function count(item: Record<string, unknown>, key: string): number {
  const value = item[key];
  if (typeof value !== "number" || !Number.isFinite(value) || value < 0) {
    throw new ApiError("UNAVAILABLE");
  }
  return value;
}
function metric(value: unknown): MetricValue {
  const item = record(value);
  const amount = item.value;
  if ((amount !== null && (typeof amount !== "number" || !Number.isFinite(amount))) ||
      typeof item.coverage !== "number" || item.coverage < 0) {
    throw new ApiError("UNAVAILABLE");
  }
  return { value: amount as number | null, coverage: item.coverage };
}
function scope(value: unknown): LeaderboardScope {
  const item = record(value);
  const names = [
    "dataset_id", "dataset_revision", "split", "repo", "evaluation_track",
    "network_policy_id", "tool_profile_id", "limit_profile_id", "harbor_revision",
    "swe_gym_revision", "swe_bench_fork_revision", "execution_contract_version",
  ] as const;
  const result = Object.fromEntries(names.map((name) => [name, text(item, name)]));
  return {
    ...result,
    network_policy_snapshot: record(item.network_policy_snapshot),
    tool_profile_snapshot: record(item.tool_profile_snapshot),
    limit_snapshot: record(item.limit_snapshot),
  } as LeaderboardScope;
}
function agent(value: unknown): LeaderboardAgent {
  const item = record(value);
  return {
    agent_configuration_id: text(item, "agent_configuration_id"),
    display_name: text(item, "display_name"), agent_type: text(item, "agent_type"),
    agent_version: text(item, "agent_version"),
    model_provider: text(item, "model_provider"), model: text(item, "model"),
    reasoning_effort: text(item, "reasoning_effort"),
    configuration_fingerprint: text(item, "configuration_fingerprint"),
  };
}
function source(value: unknown): LeaderboardSource {
  const item = record(value);
  const classification = text(item, "classification");
  if (!["resolved", "unresolved", "infrastructure_error", "unknown"]
    .includes(classification) || (item.rerun_of_job_id !== null &&
      typeof item.rerun_of_job_id !== "string")) throw new ApiError("UNAVAILABLE");
  return {
    task_id: text(item, "task_id"), instance_id: text(item, "instance_id"),
    job_id: text(item, "job_id"), run_id: text(item, "run_id"),
    rerun_of_job_id: item.rerun_of_job_id,
    classification: classification as LeaderboardSource["classification"],
  };
}
function row(value: unknown): LeaderboardRow {
  const item = record(value); const metrics = record(item.process_metrics);
  if (!Array.isArray(item.sources) || item.quality_tiebreak !== null) {
    throw new ApiError("UNAVAILABLE");
  }
  return {
    rank: count(item, "rank"), comparison_scope: scope(item.comparison_scope),
    agent: agent(item.agent), total_tasks: count(item, "total_tasks"),
    deterministic_count: count(item, "deterministic_count"),
    resolved_count: count(item, "resolved_count"),
    unresolved_count: count(item, "unresolved_count"),
    infrastructure_error_count: count(item, "infrastructure_error_count"),
    unknown_count: count(item, "unknown_count"),
    resolved_rate: count(item, "resolved_rate"),
    process_metrics: {
      selected_runs: count(metrics, "selected_runs"),
      n_input_tokens: metric(metrics.n_input_tokens),
      n_cache_tokens: metric(metrics.n_cache_tokens),
      n_output_tokens: metric(metrics.n_output_tokens), cost_usd: metric(metrics.cost_usd),
      wall_time_sec: metric(metrics.wall_time_sec), cpu_time_sec: metric(metrics.cpu_time_sec),
      peak_memory_bytes: metric(metrics.peak_memory_bytes),
    },
    sources: item.sources.map(source), quality_tiebreak: null,
    generated_at: text(item, "generated_at"),
  };
}
export function leaderboardPage(value: unknown): LeaderboardPage {
  const item = record(value);
  if (!Array.isArray(item.items) ||
      (item.next_cursor !== null && typeof item.next_cursor !== "string")) {
    throw new ApiError("UNAVAILABLE");
  }
  return { items: item.items.map(row), next_cursor: item.next_cursor };
}
