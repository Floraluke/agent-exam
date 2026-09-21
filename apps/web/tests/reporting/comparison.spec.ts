import { expect, test } from "@playwright/test";
import {
  loginOwner, navigation, openWizard, registerCatalog, reviewSelection,
} from "../support/workbench";

async function completeJob(page: import("@playwright/test").Page, tasks: string[]) {
  const wizard = await openWizard(page);
  await reviewSelection(wizard, tasks);
  await wizard.getByRole("button", { name: "提交并等待批准" }).click();
  await wizard.getByRole("button", { name: "批准并排队" }).click();
  const refresh = wizard.getByRole("button", { name: "刷新当前批次" });
  await expect.poll(async () => {
    await refresh.click();
    return wizard.getByText("执行完成", { exact: true }).count();
  }).toBe(1);
}

test("owner can open the server-backed comparison workspace", async ({ page }) => {
  await loginOwner(page);
  await navigation(page).getByRole("button", { name: "对比报告" }).click();
  await expect(page.getByRole("heading", { name: "对比报告" })).toBeVisible();
  await expect(page.getByText("选择已登记的评测批次进行对比")).toBeVisible();
});

test("real batches compare, summarize honestly, and drill into evidence on mobile", async ({ page }) => {
  await loginOwner(page);
  await registerCatalog(page, true);
  await completeJob(page, ["example__repo-1", "example__repo-2"]);
  await completeJob(page, ["example__repo-1"]);
  await navigation(page).getByRole("button", { name: "对比报告" }).click();
  const workspace = page.getByRole("region", { name: "对比报告工作区" });
  const choices = workspace.getByRole("checkbox");
  await expect(choices).toHaveCount(2);
  for (const choice of await choices.all()) await choice.check();
  await workspace.getByRole("button", { name: "生成对比（2）" }).click();

  const matrix = workspace.getByRole("region", { name: "题目配置对比矩阵" });
  await expect(matrix).toContainText("缺失 1");
  await expect(matrix).toContainText("不折算为未通过");
  await workspace.getByRole("button", { name: "加载用量与资源" }).click();
  const metrics = workspace.getByRole("region", { name: "用量与资源汇总" });
  await expect(metrics).toContainText("部分：11（1/2 个单元格有值）");
  await expect(metrics).toContainText("总量：22");
  await expect(metrics).toContainText("未知（0/2 个单元格有值）");
  await expect(metrics).toContainText("不是整批从开始到结束的墙钟耗时");

  await page.setViewportSize({ width: 375, height: 780 });
  expect(await page.locator(".comparison-scroll").evaluate((node) =>
    node.scrollWidth > node.clientWidth)).toBe(true);
  await matrix.getByRole("button", { name: /查看单次证据/ }).first().click();
  const evidence = workspace.getByRole("region", { name: "安全证据" });
  await expect(evidence).toContainText("最终补丁");
  await evidence.getByRole("button", { name: "查看安全轨迹" }).click();
  await expect(evidence).toContainText("调用工具 Read");
  const download = page.waitForEvent("download");
  await evidence.getByRole("link", { name: "下载最终补丁" }).click();
  await expect((await download).suggestedFilename()).toBe("agent.patch");
});

test("mixed outcomes keep zero distinct from unknown and cap report concurrency", async ({ page }) => {
  await loginOwner(page);
  const jobId = "00000000-0000-4000-8000-000000000031";
  const runIds = [1, 2, 3, 4].map((value) =>
    `00000000-0000-4000-8000-${String(value).padStart(12, "0")}`);
  await page.route("**/api/v1/jobs?limit=20", (route) => route.fulfill({ json: {
    items: [{
      job_id: jobId, status: "COMPLETED", evaluation_track: "closed_book",
      result_scope: "internal_test", batch_preset: "demo", limit_profile_id: "tiny",
      trial_count: 5, run_ids: runIds, estimated_finish_at: null,
      created_at: "2026-09-21T00:00:00Z", owner_decided_by: "owner-id",
      owner_decided_at: "2026-09-21T00:00:01Z", owner_decision_reason: null,
      cancel_requested_by: null, cancel_requested_at: null, cancel_reason: null,
      failure_code: null, failure_summary: null, rerun_of_job_id: null,
    }], next_cursor: null,
  } }));
  const outcomes = ["resolved", "unresolved", "infrastructure_error", "incomplete", "missing"];
  await page.route("**/api/v1/reports/comparisons?*", (route) => route.fulfill({ json: {
    columns: [{ job_id: jobId, agent_configuration_id: "agent-1", agent_display_name: "Fixture" }],
    rows: outcomes.map((outcome, index) => ({
      task_instance_id: `task-${index + 1}`, repo: "fixture/repo", cells: [{
        outcome, resolved: index === 0 ? true : index === 1 ? false : null,
        run_id: index < 4 ? runIds[index] : null,
        failure_code: index === 2 ? "HARNESS_PROTOCOL_ERROR" : null,
        report_path: index < 4 ? `/api/v1/reports/runs/${runIds[index]}` : null,
      }],
    })),
    totals: [{ resolved: 1, unresolved: 1, infrastructure_error: 1,
      incomplete: 1, missing: 1, decided: 4, total: 5 }],
  } }));
  await page.route(`**/api/v1/jobs/${jobId}`, (route) => route.fulfill({
    status: 503, json: { error: { code: "DEPENDENCY_UNAVAILABLE" } },
  }));
  let active = 0; let maximum = 0;
  await page.route("**/api/v1/reports/runs/*", async (route) => {
    active += 1; maximum = Math.max(maximum, active);
    await new Promise((resolve) => setTimeout(resolve, 80));
    const runId = route.request().url().split("/").at(-1) as string;
    const index = runIds.indexOf(runId);
    const values = [0, null, 3, 4];
    await route.fulfill({ json: {
      run: { run_id: runId, job_id: jobId, status: "COMPLETED", stage: "finished",
        task_instance_id: `task-${index + 1}`, agent_configuration_id: "agent-1",
        backend_job_ref: null, backend_trial_ref: null, failure_code: null,
        failure_summary: null, started_at: null, finished_at: null, warnings: [] },
      deterministic_result: null,
      process_metrics: { usage: { n_input_tokens: values[index], n_cache_tokens: null,
        n_output_tokens: values[index], cost_usd: index === 0 ? 0 : null },
        resources: { wall_time_sec: values[index], cpu_time_sec: values[index],
          peak_memory_bytes: values[index] } },
      judge_analyses: [], human_review: null, quality_tiebreak: null,
      review_status: "NOT_REQUIRED", artifact_links: [],
    } });
    active -= 1;
  });

  await navigation(page).getByRole("button", { name: "对比报告" }).click();
  const workspace = page.getByRole("region", { name: "对比报告工作区" });
  await workspace.getByRole("checkbox").check();
  await workspace.getByRole("button", { name: "生成对比（1）" }).click();
  const matrix = workspace.getByRole("region", { name: "题目配置对比矩阵" });
  for (const label of ["确定性通过", "确定性未通过", "基础设施故障", "未完成", "缺失"]) {
    await expect(matrix).toContainText(label);
  }
  await expect(matrix.getByRole("button", { name: /查看单次证据/ })).toHaveCount(4);
  await workspace.getByRole("button", { name: "加载用量与资源" }).click();
  const metrics = workspace.getByRole("region", { name: "用量与资源汇总" });
  await expect(metrics).toContainText("部分：7（3/5 个单元格有值）");
  await expect(metrics).toContainText("部分：0 USD（1/5 个单元格有值）");
  await expect(metrics).toContainText("未知（0/5 个单元格有值）");
  expect(maximum).toBeLessThanOrEqual(3);
});
