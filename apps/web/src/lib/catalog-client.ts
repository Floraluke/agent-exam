import { ApiError, request } from "./api-client";
import type { CatalogAgent, CatalogTask, Page } from "./contracts";

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
function task(value: unknown, detail = false): CatalogTask {
  const item = object(value);
  return {
    task_id: text(item, "task_id"), instance_id: text(item, "instance_id"),
    dataset_id: text(item, "dataset_id"), dataset_revision: text(item, "dataset_revision"),
    split: text(item, "split"), repo: text(item, "repo"), base_commit: text(item, "base_commit"),
    problem_statement_preview: text(item, "problem_statement_preview"),
    ...(detail ? { problem_statement: text(item, "problem_statement") } : {}),
  };
}
function agent(value: unknown, detail = false): CatalogAgent {
  const item = object(value);
  if (item.agent_type !== "codex" || item.model_provider !== "openai_chatgpt" ||
      typeof item.enabled !== "boolean") throw new ApiError("UNAVAILABLE");
  const result: CatalogAgent = {
    agent_configuration_id: text(item, "agent_configuration_id"),
    display_name: text(item, "display_name"), agent_type: "codex",
    model_provider: "openai_chatgpt", agent_version: text(item, "agent_version"),
    model: text(item, "model"), configuration_fingerprint: text(item, "configuration_fingerprint"),
    enabled: item.enabled,
  };
  if (detail) {
    const effort = text(object(item.public_options), "reasoning_effort");
    if (!["low", "medium", "high", "xhigh"].includes(effort) ||
        (item.limit_profile_id !== null && typeof item.limit_profile_id !== "string")) {
      throw new ApiError("UNAVAILABLE");
    }
    result.public_options = { reasoning_effort: effort };
    result.limit_profile_id = item.limit_profile_id;
  }
  return result;
}
function page<T>(value: unknown, parse: (value: unknown) => T): Page<T> {
  const data = object(value);
  if (!Array.isArray(data.items) ||
      (data.next_cursor !== null && typeof data.next_cursor !== "string")) {
    throw new ApiError("UNAVAILABLE");
  }
  return { items: data.items.map((item) => parse(item)), next_cursor: data.next_cursor };
}
export async function tasks(query: URLSearchParams): Promise<Page<CatalogTask>> {
  return page(await request("tasks?" + query), task);
}
export async function taskDetail(id: string): Promise<CatalogTask> {
  return task(await request("tasks/" + encodeURIComponent(id)), true);
}
export async function registerTask(): Promise<CatalogTask> {
  return task(await request("tasks/register", { preset_id: "swe-gym-lite-mypy-15413" }), true);
}
export async function agents(query: URLSearchParams): Promise<Page<CatalogAgent>> {
  return page(await request("agent-configurations?" + query), agent);
}
export async function agentDetail(id: string): Promise<CatalogAgent> {
  return agent(await request("agent-configurations/" + encodeURIComponent(id)), true);
}
export async function registerAgent(): Promise<CatalogAgent> {
  return agent(await request("agent-configurations", { preset_id: "codex-0153-terra-medium" }), true);
}
export async function disableAgent(id: string): Promise<void> {
  await request("agent-configurations/" + encodeURIComponent(id) + "/disable", {});
}
