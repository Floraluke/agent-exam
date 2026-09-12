import { expect, test } from "@playwright/test";

test("run report opens safe trajectory and downloadable patch", async ({ page }) => {
  await page.goto("/");
  await page.getByLabel("账号", { exact: true }).fill("owner");
  await page.getByLabel("密码", { exact: true }).fill("synthetic browser password");
  await page.getByRole("button", { name: "登录", exact: true }).click();
  await page.getByRole("button", { name: "登记已核验题目" }).click();
  await page.getByRole("button", { name: "登记固定 Codex 配置" }).click();
  const jobs = page.getByRole("region", { name: "提交评测" });
  await jobs.getByRole("button", { name: "刷新可提交选项" }).click();
  await jobs.getByLabel("任务 example__repo-1").check();
  await jobs.getByLabel("配置 Synthetic Codex").check();
  await jobs.getByRole("button", { name: "提交等待批准" }).click();
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
  await evidence.getByRole("button", { name: "查看安全轨迹" }).click();
  await expect(evidence).toContainText("调用工具 Read");
  await expect(evidence).not.toContainText("private synthetic message");
  const pending = page.waitForEvent("download");
  await evidence.getByRole("link", { name: "下载最终补丁" }).click();
  await expect((await pending).suggestedFilename()).toBe("agent.patch");
  await expect(page.locator("body")).not.toContainText("codex-secrets");
});
