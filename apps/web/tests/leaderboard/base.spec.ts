import { expect, test } from "@playwright/test";
import {
  loginOwner, navigation, openWizard, registerCatalog, reviewSelection,
} from "../support/workbench";

test("official-looking leaderboard stays comparable and links to its source", async ({
  page,
}) => {
  await loginOwner(page);
  await registerCatalog(page, true);
  const jobs = await openWizard(page);
  await reviewSelection(jobs, ["example__repo-1"]);
  const submitted = page.waitForResponse((response) =>
    response.request().method() === "POST" &&
    new URL(response.url()).pathname === "/api/v1/jobs",
  );
  await jobs.getByRole("button", { name: "提交并等待批准" }).click();
  const job = await (await submitted).json();
  await jobs.getByRole("button", { name: "批准并排队" }).click();
  await expect.poll(async () => {
    const response = await page.request.get(`/api/v1/jobs/${job.job_id}`);
    return (await response.json()).status;
  }).toBe("COMPLETED");

  await navigation(page).getByRole("button", { name: "排行榜" }).click();
  const leaderboard = page.getByRole("region", { name: "基础排行榜" });
  await expect(leaderboard).toBeVisible({ timeout: 5_000 });
  await leaderboard.getByLabel("数据集 ID").fill("synthetic-dataset");
  await leaderboard.getByLabel("数据集 revision").fill("a".repeat(40));
  await leaderboard.getByLabel("数据集 split").fill("train");
  await leaderboard.getByLabel("代码仓库").fill("example/repo");
  await leaderboard.getByRole("button", { name: "查询排行榜" }).click();

  await expect(leaderboard).toContainText("并列第 1 名");
  await expect(leaderboard).toContainText("1 / 2 · 50.0%");
  await expect(leaderboard).toContainText("基础设施错误 0");
  await expect(leaderboard).toContainText("未知 1");
  await expect(leaderboard).toContainText("网络策略 agentexam-closed-book-v1");
  await leaderboard.getByText("完整比较条件", { exact: true }).click();
  await expect(leaderboard).toContainText("任意主机 否");
  await expect(leaderboard).toContainText("Agent 900 秒 / 1 CPU / 4096 MB");
  await expect(leaderboard).toContainText("并发 1 / 自动重试 0");
  await expect(leaderboard).toContainText("缓存 token：unknown（覆盖 0/1）");
  await leaderboard.getByText("纳入来源", { exact: true }).click();
  const source = leaderboard.getByRole("link", { name: "查看运行报告" });
  await expect(source).toHaveAttribute("href", `/api/v1/reports/runs/${job.run_ids[0]}`);

  await page.route("**/api/v1/leaderboard?*", async (route) => {
    await route.fulfill({
      status: 503,
      contentType: "application/json",
      body: JSON.stringify({
        error: {
          code: "DEPENDENCY_UNAVAILABLE", message: "safe", details: {},
          request_id: "req_synthetic",
        },
      }),
    });
  });
  await leaderboard.getByLabel("数据集 ID").fill("other-dataset");
  await leaderboard.getByRole("button", { name: "查询排行榜" }).click();
  await expect(leaderboard.getByRole("alert")).toContainText("平台存储暂不可用");
  await expect(leaderboard.locator("article.leaderboard-row")).toHaveCount(0);
});

test("leaderboard explains empty and dependency-error states", async ({ page }) => {
  await loginOwner(page);
  await navigation(page).getByRole("button", { name: "排行榜" }).click();
  const leaderboard = page.getByRole("region", { name: "基础排行榜" });
  await leaderboard.getByLabel("数据集 ID").fill("missing-dataset");
  await leaderboard.getByLabel("数据集 revision").fill("missing-revision");
  await leaderboard.getByLabel("数据集 split").fill("test");
  await leaderboard.getByRole("button", { name: "查询排行榜" }).click();
  await expect(leaderboard).toContainText("没有符合条件的正式结果");

  await page.route("**/api/v1/leaderboard?*", async (route) => {
    await route.fulfill({
      status: 503,
      contentType: "application/json",
      body: JSON.stringify({
        error: {
          code: "DEPENDENCY_UNAVAILABLE", message: "safe", details: {},
          request_id: "req_synthetic",
        },
      }),
    });
  });
  await leaderboard.getByRole("button", { name: "查询排行榜" }).click();
  await expect(leaderboard.getByRole("alert")).toContainText("平台存储暂不可用");
});
