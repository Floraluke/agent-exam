import { expect, test } from "@playwright/test";

test("owner dashboard reads visible jobs and priority groups from the server", async ({
  page,
}) => {
  await page.goto("/");
  await page.getByLabel("账号", { exact: true }).fill("owner");
  await page.getByLabel("密码", { exact: true }).fill("synthetic browser password");
  await page.getByRole("button", { name: "登录", exact: true }).click();
  const navigation = page.getByRole("navigation", { name: "主导航" });
  await navigation.getByRole("button", { name: "任务目录" }).click();
  await page.getByRole("button", { name: "登记已核验题目" }).click();
  await navigation.getByRole("button", { name: "配置目录" }).click();
  await page.getByRole("button", { name: "登记固定 Codex 配置" }).click();
  await navigation.getByRole("button", { name: "新建评测" }).click();
  const wizard = page.getByRole("region", { name: "新建评测向导" });
  await wizard.getByLabel("任务 example__repo-1").check();
  await wizard.getByRole("button", { name: "下一步" }).click();
  await wizard.getByLabel("配置 Synthetic Codex").check();
  await wizard.getByRole("button", { name: "下一步" }).click();
  const response = page.waitForResponse((item) =>
    item.request().method() === "POST" && new URL(item.url()).pathname === "/api/v1/jobs",
  );
  await wizard.getByRole("button", { name: "提交并等待批准" }).click();
  const created = await (await response).json();

  const dashboardStatuses: string[] = [];
  page.on("request", (request) => {
    const url = new URL(request.url());
    if (url.pathname === "/api/v1/jobs" && url.searchParams.has("status")) {
      dashboardStatuses.push(url.searchParams.get("status") ?? "");
    }
  });
  await navigation.getByRole("button", { name: "工作台" }).click();
  await expect(page.getByRole("region", { name: "当前可见评测" }))
    .toContainText(created.job_id);
  await expect(page.getByRole("region", { name: "待处理审批" }))
    .toContainText(created.job_id);
  await expect(page.getByRole("region", { name: "待处理审批" }))
    .toContainText("最多显示服务器返回的 5 条");
  await expect(page.getByRole("region", { name: "执行队列" })).toBeVisible();
  await expect(page.getByRole("region", { name: "异常评测" })).toBeVisible();
  await expect.poll(() => new Set(dashboardStatuses)).toEqual(new Set([
    "AWAITING_OWNER_APPROVAL", "QUEUED", "PREPARING", "EXECUTING",
    "FINALIZING", "CANCEL_REQUESTED", "COMPLETED_WITH_ERRORS", "FAILED",
  ]));
  await page.getByRole("button", { name: "刷新工作台" }).click();
  await expect(page.getByRole("region", { name: "当前可见评测" }))
    .toContainText("等待所有者批准");
  await page.screenshot({
    path: "../../runtime/tests/task-02-workbench-desktop.png", fullPage: true,
  });
  await page.getByRole("button", { name: "查看全部评测" }).click();
  await expect(page.getByRole("region", { name: "评测列表" })).toBeVisible();
});
