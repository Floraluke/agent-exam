import { expect, test } from "@playwright/test";

test("batch progress survives refresh and opens every run report", async ({ page }) => {
  await page.goto("/");
  await page.getByLabel("账号", { exact: true }).fill("owner");
  await page.getByLabel("密码", { exact: true }).fill("synthetic browser password");
  await page.getByRole("button", { name: "登录", exact: true }).click();
  await page.getByRole("button", { name: "登记已核验题目" }).click();
  await page.evaluate(async () => {
    const response = await fetch("/api/v1/tasks/register", {
      method: "POST",
      credentials: "same-origin",
      headers: { "Content-Type": "application/json", "X-AgentExam-Request": "1" },
      body: JSON.stringify({ preset_id: "swe-gym-lite-example-2" }),
    });
    if (!response.ok) throw new Error("second synthetic task registration failed");
  });
  await page.getByRole("button", { name: "登记固定 Codex 配置" }).click();
  const jobs = page.getByRole("region", { name: "提交评测" });
  await jobs.getByRole("button", { name: "刷新可提交选项" }).click();
  await jobs.getByLabel("任务 example__repo-1").check();
  await jobs.getByLabel("任务 example__repo-2").check();
  await jobs.getByLabel("配置 Synthetic Codex").check();
  await expect(jobs.getByText("组合数量：2", { exact: true })).toBeVisible();
  await jobs.getByRole("button", { name: "提交等待批准" }).click();
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
});
