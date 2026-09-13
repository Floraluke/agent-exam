import type { JobDetail } from "../contracts";
import { bool, number, object, text } from "./shapes";

export type NetworkPolicySnapshot = JobDetail["network_policy_snapshot"];
export type ToolProfileSnapshot = JobDetail["tool_profile_snapshot"];
export type LimitSnapshot = JobDetail["limit_snapshot"];

export function networkSnapshot(value: unknown): NetworkPolicySnapshot {
  const item = object(value);
  return {
    mode: text(item, "mode"),
    web_search: text(item, "web_search"),
    arbitrary_hosts: bool(item, "arbitrary_hosts"),
  };
}

export function toolSnapshot(value: unknown): ToolProfileSnapshot {
  const item = object(value);
  return {
    agent_type: text(item, "agent_type"),
    web_search: text(item, "web_search"),
    arbitrary_commands: bool(item, "arbitrary_commands"),
  };
}

export function limitSnapshot(value: unknown): LimitSnapshot {
  const item = object(value);
  const keys = [
    "agent_wall_timeout_sec", "agent_cpus", "agent_memory_mb", "agent_storage_mb",
    "evaluator_wall_timeout_sec", "evaluator_cpus", "evaluator_memory_mb", "pids_limit",
    "patch_warning_bytes", "patch_max_bytes", "raw_artifact_max_bytes", "raw_run_max_bytes",
    "concurrency", "max_retries",
  ];
  return Object.fromEntries(keys.map((key) => [key, number(item, key)])) as LimitSnapshot;
}
