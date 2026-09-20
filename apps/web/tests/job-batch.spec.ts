import { expect, test } from "@playwright/test";
import { loginOwner, openWizard, registerCatalog, reviewSelection } from "./support/workbench";

test("batch progress survives refresh and opens every run report", async ({ page }) => {
  await loginOwner(page);
  await registerCatalog(page, true);
  let jobs = await openWizard(page);
  await reviewSelection(jobs, ["example__repo-1", "example__repo-2"]);
  await expect(jobs.getByText("2 道题 × 1 个配置 = 2 个 Run", { exact: true }))
    .toBeVisible();
  await jobs.getByRole("button", { name: "提交并等待批准" }).click();
  await jobs.getByRole("button", { name: "批准并排队" }).click();
  const refresh = jobs.getByRole("button", { name: "刷新当前批次" });
  await expect.poll(async () => {
    await refresh.click();
    return jobs.getByText("执行完成", { exact: true }).count();
  }).toBe(1);
  await jobs.getByRole("button", { name: "查看批次进度" }).click();
  let batch = jobs.getByRole("region", { name: "批次进度" });
  await expect(batch).toContainText("已完成 2");
  await expect(batch).toContainText("已解决 2");
  await expect(batch).toContainText("example__repo-1");
  await expect(batch).toContainText("example__repo-2");
  await expect(jobs).toContainText("并发固定为 1");
  await expect(batch).not.toContainText("harbor.stdout.log");

  await page.reload();
  await jobs.getByRole("button", { name: "查看批次进度" }).click();
  batch = jobs.getByRole("region", { name: "批次进度" });
  await expect(batch).toContainText("已完成 2");
  const reports = batch.getByRole("button", { name: /运行报告$/ });
  await expect(reports).toHaveCount(2);
  await reports.first().click();
  await expect(jobs.getByRole("region", { name: "单题运行报告" }))
    .toContainText("确定性结果：已解决");
  await reports.nth(1).click();
  await expect(jobs.getByRole("region", { name: "单题运行报告" }))
    .toContainText("确定性结果：已解决");

  jobs = await openWizard(page);
  await reviewSelection(jobs, ["example__repo-1", "example__repo-2"]);
  await jobs.getByRole("button", { name: "提交并等待批准" }).click();
  await jobs.getByRole("button", { name: "拒绝批次" }).click();
  await jobs.getByRole("button", { name: "查看批次进度" }).click();
  batch = jobs.getByRole("region", { name: "批次进度" });
  await expect(batch).toContainText("未完成 2");
  const canceledReports = batch.getByRole("button", { name: /运行报告$/ });
  await expect(canceledReports).toHaveCount(2);
  await canceledReports.first().click();
  await expect(jobs.getByRole("region", { name: "单题运行报告" }))
    .toContainText("本次没有形成确定性成绩");
});
