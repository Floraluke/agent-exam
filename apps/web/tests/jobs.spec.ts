import { expect, test } from "@playwright/test";

test("registered selection submits and reloads a waiting frozen job", async ({ page }) => {
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
  await expect(jobs.getByText("组合数量：1", { exact: true })).toBeVisible();
  await expect(jobs.getByLabel("评测赛道")).toHaveValue("closed_book");
  await expect(jobs.getByLabel("资源限制")).toHaveValue("default-single-host-v1");
  const response = page.waitForResponse((candidate) =>
    candidate.request().method() === "POST" &&
    new URL(candidate.url()).pathname === "/api/v1/jobs",
  );
  await jobs.getByRole("button", { name: "提交等待批准" }).click();
  const created = await (await response).json();
  await expect.poll(() => new URL(page.url()).searchParams.get("job"))
    .toBe(created.job_id);
  await expect(jobs.getByText("等待所有者批准", { exact: true })).toBeVisible();
  await expect(jobs.getByText("冻结运行数：1", { exact: true })).toBeVisible();
  await expect(jobs).not.toContainText("成绩");
  await page.reload();
  await expect(jobs.getByText("等待所有者批准", { exact: true })).toBeVisible();
  await jobs.getByRole("button", { name: "刷新当前批次" }).click();
  await expect(jobs.getByText("冻结运行数：1", { exact: true })).toBeVisible();
});

test("malformed nested job options fail closed", async ({ page }) => {
  await page.route("**/api/v1/job-options", async (route) => {
    await route.fulfill({ json: {
      batch_presets: [{}], evaluation_tracks: ["closed_book"],
      limit_profiles: [{}], maximum_agent_configurations: 3, maximum_runs: 60,
    } });
  });
  await page.goto("/");
  await page.getByLabel("账号", { exact: true }).fill("owner");
  await page.getByLabel("密码", { exact: true }).fill("synthetic browser password");
  await page.getByRole("button", { name: "登录", exact: true }).click();
  await expect(page.locator("p[role=alert]")).toContainText("暂时无法连接平台");
  await expect(page.getByRole("region", { name: "提交评测" }))
    .not.toContainText("undefined");
});
