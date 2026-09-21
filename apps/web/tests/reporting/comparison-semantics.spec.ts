import { expect, test } from "@playwright/test";
import { loginOwner, navigation } from "../support/workbench";

const jobs = ["00000000-0000-4000-8000-000000000041", "00000000-0000-4000-8000-000000000042"];
const runs = ["00000000-0000-4000-8000-000000000051", "00000000-0000-4000-8000-000000000052"];

function summary(jobId: string, runId: string) {
  return {
    job_id: jobId, status: "COMPLETED", evaluation_track: "closed_book",
    result_scope: "internal_test", batch_preset: "demo", limit_profile_id: "tiny",
    trial_count: 1, run_ids: [runId], estimated_finish_at: null,
    created_at: "2026-09-21T00:00:00Z", owner_decided_by: "owner-id",
    owner_decided_at: "2026-09-21T00:00:01Z", owner_decision_reason: null,
    cancel_requested_by: null, cancel_requested_at: null, cancel_reason: null,
    failure_code: null, failure_summary: null, rerun_of_job_id: null,
  };
}

function report(index: number) {
  return {
    run: {
      run_id: runs[index], job_id: jobs[index], status: "COMPLETED", stage: "finished",
      task_instance_id: `last-choice-${index + 1}`, agent_configuration_id: `agent-${index + 1}`,
      backend_job_ref: null, backend_trial_ref: null, failure_code: null,
      failure_summary: null, started_at: null, finished_at: null, warnings: [],
    },
    deterministic_result: null,
    process_metrics: {
      usage: { n_input_tokens: index === 0 ? 1 : 10, n_cache_tokens: null,
        n_output_tokens: index === 0 ? 2 : 20, cost_usd: index === 0 ? 0 : null },
      resources: { wall_time_sec: index === 0 ? 3 : 30,
        cpu_time_sec: index === 0 ? 4 : 40, peak_memory_bytes: null },
    },
    judge_analyses: [], human_review: null, quality_tiebreak: null,
    review_status: "NOT_REQUIRED", artifact_links: [],
  };
}

function agent(index: number) {
  return { agent_configuration_id: `agent-${index}`, display_name: `方案 ${index}`,
    agent_type: "codex", agent_version: `${index}`, model_provider: "openai", model: "fixed",
    reasoning_effort: "medium", configuration_fingerprint: `fixture-${index}` };
}

function detail(agents = [agent(1)]) {
  return {
    ...summary(jobs[0], runs[0]), lease_expires_at: null, task_snapshots: [],
    agent_snapshots: agents,
    limit_snapshot: {
      agent_wall_timeout_sec: 1, agent_cpus: 1, agent_memory_mb: 1, agent_storage_mb: 1,
      evaluator_wall_timeout_sec: 1, evaluator_cpus: 1, evaluator_memory_mb: 1,
      pids_limit: 1, patch_warning_bytes: 1, patch_max_bytes: 1,
      raw_artifact_max_bytes: 1, raw_run_max_bytes: 1, concurrency: 1, max_retries: 0,
    },
    network_policy_id: "closed", network_policy_snapshot: {
      mode: "closed", web_search: "disabled", arbitrary_hosts: false,
    },
    tool_profile_id: "safe", tool_profile_snapshot: {
      agent_type: "codex", web_search: "disabled", arbitrary_commands: false,
    },
    harbor_revision: "h", swe_gym_revision: "g", swe_bench_fork_revision: "b",
    job_state_events: [], runs: [],
  };
}

test("metrics stay per configuration and the latest evidence click wins", async ({ page }) => {
  await loginOwner(page);
  let visibleJobs = jobs;
  await page.route("**/api/v1/jobs?limit=20", (route) => route.fulfill({ json: {
    items: visibleJobs.map((job) => summary(job, runs[jobs.indexOf(job)])), next_cursor: null,
  } }));
  await page.route("**/api/v1/reports/comparisons?*", (route) => route.fulfill({ json: {
    columns: jobs.map((job_id, index) => ({ job_id,
      agent_configuration_id: `agent-${index + 1}`, agent_display_name: `方案 ${index + 1}` })),
    rows: [{ task_instance_id: "task-1", repo: "fixture/repo", cells: runs.map((run_id) => ({
      outcome: "resolved", resolved: true, run_id, failure_code: null,
      report_path: `/api/v1/reports/runs/${run_id}`,
    })) }],
    totals: jobs.map(() => ({ resolved: 1, unresolved: 0, infrastructure_error: 0,
      incomplete: 0, missing: 0, decided: 1, total: 1 })),
  } }));
  await page.route("**/api/v1/jobs/*", (route) => route.request().url().endsWith(jobs[0]) ?
    route.fulfill({ json: detail() }) : route.fulfill({
      status: 503, json: { error: { code: "DEPENDENCY_UNAVAILABLE" } },
    }));
  await page.route("**/api/v1/reports/runs/*", async (route) => {
    const index = runs.indexOf(route.request().url().split("/").at(-1) as string);
    await new Promise((resolve) => setTimeout(resolve, index === 0 ? 120 : 10));
    await route.fulfill({ json: report(index) });
  });

  await navigation(page).getByRole("button", { name: "对比报告" }).click();
  const workspace = page.getByRole("region", { name: "对比报告工作区" });
  for (const choice of await workspace.getByRole("checkbox").all()) await choice.check();
  await workspace.getByRole("button", { name: "生成对比（2）" }).click();
  const configurations = workspace.getByRole("region", { name: "冻结配置差异" });
  await expect(configurations).toContainText("未知列不参与差异判断");
  await expect(configurations.getByText("差异 ·", { exact: true })).toHaveCount(0);
  await expect(configurations.getByText("完整限制快照")).toHaveCount(1);
  const cells = workspace.getByRole("button", { name: /查看单次证据/ });
  await cells.nth(0).click();
  await cells.nth(1).click();
  await expect(workspace.getByRole("region", { name: "选中的单次证据" }))
    .toContainText(runs[1]);
  await expect(workspace.getByRole("region", { name: "选中的单次证据" }))
    .not.toContainText(runs[0]);

  await workspace.getByRole("button", { name: "加载用量与资源" }).click();
  await expect(workspace.getByRole("article", { name: "方案 1 配置 1 指标" }))
    .toContainText("总量：1");
  await expect(workspace.getByRole("article", { name: "方案 2 配置 2 指标" }))
    .toContainText("总量：10");

  visibleJobs = [jobs[1]];
  await workspace.getByRole("button", { name: "刷新可见批次" }).click();
  await expect(workspace.getByRole("checkbox")).toHaveCount(1);
  await expect(workspace.getByRole("button", { name: "生成对比（1）" })).toBeVisible();
});

test("one job with multiple complete configurations is not reported as unknown", async ({ page }) => {
  await loginOwner(page);
  await page.route("**/api/v1/jobs?limit=20", (route) => route.fulfill({ json: {
    items: [summary(jobs[0], runs[0])], next_cursor: null,
  } }));
  await page.route("**/api/v1/reports/comparisons?*", (route) => route.fulfill({ json: {
    columns: [1, 2].map((index) => ({ job_id: jobs[0],
      agent_configuration_id: `agent-${index}`, agent_display_name: `方案 ${index}` })),
    rows: [{ task_instance_id: "task-1", repo: "fixture/repo", cells: runs.map((run_id) => ({
      outcome: "resolved", resolved: true, run_id, failure_code: null,
      report_path: `/api/v1/reports/runs/${run_id}`,
    })) }],
    totals: [1, 2].map(() => ({ resolved: 1, unresolved: 0, infrastructure_error: 0,
      incomplete: 0, missing: 0, decided: 1, total: 1 })),
  } }));
  await page.route(`**/api/v1/jobs/${jobs[0]}`, (route) => route.fulfill({
    json: detail([agent(1), agent(2)]),
  }));

  await navigation(page).getByRole("button", { name: "对比报告" }).click();
  const workspace = page.getByRole("region", { name: "对比报告工作区" });
  await workspace.getByRole("checkbox").check();
  await workspace.getByRole("button", { name: "生成对比（1）" }).click();
  const configurations = workspace.getByRole("region", { name: "冻结配置差异" });
  await expect(configurations).not.toContainText("部分快照未知");
  await expect(configurations.getByText("配置快照未知。")).toHaveCount(0);
  await expect(configurations.getByText("完整限制快照")).toHaveCount(2);
  await expect(configurations.getByText("差异 ·", { exact: true })).toHaveCount(2);
});
