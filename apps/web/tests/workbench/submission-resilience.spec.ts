import { expect, test } from "@playwright/test";
import {
  loginOwner, openWizard, registerCatalog, reviewSelection,
} from "../support/workbench";

test("new-job history never restores controls for an unrelated existing job", async ({ page }) => {
  await loginOwner(page);
  await registerCatalog(page);
  const wizard = await openWizard(page);
  await reviewSelection(wizard, ["example__repo-1"]);
  await wizard.getByRole("button", { name: "提交并等待批准" }).click();
  await expect(wizard.getByText("等待所有者批准", { exact: true })).toBeVisible();
  const jobId = new URL(page.url()).searchParams.get("job");
  expect(jobId).not.toBeNull();

  await page.goBack();
  await expect(page.getByRole("heading", { name: "新建评测" })).toBeVisible();
  await expect.poll(() => new URL(page.url()).searchParams.get("job")).toBeNull();
  await expect(page.getByRole("button", { name: "刷新当前批次" })).toHaveCount(0);
  await expect(page.getByRole("region", { name: "所有者决定" })).toHaveCount(0);

  await page.goto(`/?view=new&job=${jobId}`);
  await expect(page.getByRole("heading", { name: "新建评测" })).toBeVisible();
  await expect.poll(() => new URL(page.url()).searchParams.get("job")).toBeNull();
  await expect(page.getByRole("button", { name: "刷新当前批次" })).toHaveCount(0);
  await expect(page.getByRole("region", { name: "所有者决定" })).toHaveCount(0);
});

test("uncertain submission reuses its key and locks duplicate clicks", async ({ page }) => {
  await loginOwner(page);
  await registerCatalog(page);
  const wizard = await openWizard(page);
  await reviewSelection(wizard, ["example__repo-1"]);

  const keys: string[] = [];
  const jobIds: string[] = [];
  let failDetail = true;
  await page.route(/\/api\/v1\/jobs\/[^/?]+$/, async (route) => {
    if (route.request().method() === "GET" && failDetail) {
      failDetail = false;
      await route.fulfill({
        status: 503,
        json: { error: { code: "DEPENDENCY_UNAVAILABLE", message: "unavailable", details: {}, request_id: "test" } },
      });
      return;
    }
    await route.continue();
  });
  await page.route("**/api/v1/jobs", async (route) => {
    if (route.request().method() !== "POST") {
      await route.continue();
      return;
    }
    keys.push(route.request().headers()["idempotency-key"] ?? "");
    const response = await route.fetch();
    const body = await response.json();
    jobIds.push(body.job_id);
    await new Promise((resolve) => setTimeout(resolve, 250));
    await route.fulfill({ response, json: body });
  });

  const submit = wizard.getByRole("button", { name: "提交并等待批准" });
  await submit.click();
  await expect(submit).toBeDisabled();
  await expect(page.locator("p[role=alert]")).toContainText("平台存储暂不可用");
  await expect(submit).toBeEnabled();
  await submit.click();
  await expect(wizard.getByText("等待所有者批准", { exact: true })).toBeVisible();
  expect(keys).toHaveLength(2);
  expect(new Set(keys).size).toBe(1);
  expect(keys[0]).not.toBe("");
  expect(new Set(jobIds).size).toBe(1);
});
