import { expect, test } from "@playwright/test";
import { loginOwner, navigation } from "../support/workbench";

const jobId = "00000000-0000-4000-8000-000000000091";

test("clearing selection invalidates an in-flight comparison", async ({ page }) => {
  let releaseComparison: (() => void) | undefined;
  const comparisonReleased = new Promise<void>((resolve) => {
    releaseComparison = resolve;
  });
  let comparisonStarted: (() => void) | undefined;
  const started = new Promise<void>((resolve) => {
    comparisonStarted = resolve;
  });
  await page.route("**/api/v1/jobs?limit=20", (route) => route.fulfill({ json: {
    items: [{
      job_id: jobId, status: "COMPLETED", evaluation_track: "closed_book",
      result_scope: "internal_test", batch_preset: "demo", limit_profile_id: "tiny",
      trial_count: 1, run_ids: [], estimated_finish_at: null,
      created_at: "2026-09-21T00:00:00Z", owner_decided_by: "owner-id",
      owner_decided_at: "2026-09-21T00:00:01Z", owner_decision_reason: null,
      cancel_requested_by: null, cancel_requested_at: null, cancel_reason: null,
      failure_code: null, failure_summary: null, rerun_of_job_id: null,
    }], next_cursor: null,
  } }));
  await page.route("**/api/v1/reports/comparisons?*", async (route) => {
    comparisonStarted?.();
    await comparisonReleased;
    await route.fulfill({ json: {
      columns: [{
        job_id: jobId, agent_configuration_id: "agent-1", agent_display_name: "Fixture",
      }],
      rows: [],
      totals: [{
        resolved: 0, unresolved: 0, infrastructure_error: 0,
        incomplete: 0, missing: 0, decided: 0, total: 0,
      }],
    } });
  });
  await page.route(`**/api/v1/jobs/${jobId}`, (route) => route.fulfill({
    status: 503, json: { error: { code: "DEPENDENCY_UNAVAILABLE" } },
  }));

  await loginOwner(page);
  await navigation(page).getByRole("button", { name: "对比报告" }).click();
  const workspace = page.getByRole("region", { name: "对比报告工作区" });
  await workspace.getByRole("checkbox").check();
  await workspace.getByRole("button", { name: "生成对比（1）" }).click();
  await started;
  await workspace.getByRole("button", { name: "清空选择" }).click();
  releaseComparison?.();

  await expect(workspace.getByText("还没有选择要对比的批次")).toBeVisible();
  await expect(workspace.getByRole("region", { name: "题目配置对比矩阵" }))
    .toHaveCount(0);
});
