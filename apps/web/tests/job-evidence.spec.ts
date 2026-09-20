import { expect, test } from "@playwright/test";
import { loginOwner, openWizard, registerCatalog, reviewSelection } from "./support/workbench";

test("run report opens safe trajectory and downloadable patch", async ({ page }) => {
  await loginOwner(page);
  await registerCatalog(page);
  const jobs = await openWizard(page);
  await reviewSelection(jobs, ["example__repo-1"]);
  await jobs.getByRole("button", { name: "提交并等待批准" }).click();
  await jobs.getByRole("button", { name: "批准并排队" }).click();
  const refresh = jobs.getByRole("button", { name: "刷新当前批次" });
  await expect.poll(async () => {
    await refresh.click();
    return jobs.getByText("执行完成", { exact: true }).count();
  }).toBe(1);
  await jobs.getByRole("button", { name: "查看单题运行报告" }).click();
  const evidence = jobs.getByRole("region", { name: "安全证据" });
  await expect(evidence).toContainText("最终补丁");
  await expect(evidence).toContainText("测试摘要");
  await page.route("**/api/v1/runs/*/trajectory?*", async (route) => {
    const url = new URL(route.request().url()); url.searchParams.set("limit", "1");
    await route.continue({ url: url.toString() });
  });
  await evidence.getByRole("button", { name: "查看安全轨迹" }).click();
  await expect(evidence).toContainText("调用工具 Read");
  await evidence.getByRole("button", { name: "加载更多轨迹" }).click();
  await expect(evidence).toContainText("正文未公开");
  await expect(evidence).not.toContainText("private synthetic message");
  const pending = page.waitForEvent("download");
  await evidence.getByRole("link", { name: "下载最终补丁" }).click();
  await expect((await pending).suggestedFilename()).toBe("agent.patch");
  await expect(page.locator("body")).not.toContainText("codex-secrets");
});
