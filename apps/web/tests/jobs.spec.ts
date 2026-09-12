import { expect, test } from "@playwright/test";

test("owner approves a frozen job and reloads its audit", async ({ page }) => {
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
  await expect(jobs).toContainText("模型：openai_chatgpt / test-model");
  await expect(jobs).toContainText("网络策略：agentexam-closed-book-v1");
  await expect(jobs).toContainText("冻结版本：Harbor");
  await expect(jobs).not.toContainText("成绩");
  await expect(jobs).toContainText("不要填写凭据、Token 或宿主机路径");
  await jobs.getByLabel("决定说明（可选）").fill("   ");
  await jobs.getByRole("button", { name: "批准并排队" }).click();
  await expect(jobs.getByRole("alert")).toHaveText("请检查输入格式。");
  await jobs.getByLabel("决定说明（可选）").fill("  已核对冻结范围  ");
  const stale = await page.context().newPage();
  await stale.goto(page.url());
  const staleJobs = stale.getByRole("region", { name: "提交评测" });
  await expect(staleJobs.getByText("等待所有者批准", { exact: true }))
    .toBeVisible();
  const approved = page.waitForResponse((candidate) =>
    candidate.request().method() === "POST" &&
    new URL(candidate.url()).pathname.endsWith(`/jobs/${created.job_id}/approve`),
  );
  await jobs.getByRole("button", { name: "批准并排队" }).click();
  expect((await approved).status()).toBe(200);
  await expect(jobs.getByText("已批准，等待执行", { exact: true })).toBeVisible();
  await expect(jobs.getByText("决定说明：已核对冻结范围", { exact: true }))
    .toBeVisible();
  await expect(jobs.getByText(/^决定者：/)).toBeVisible();
  await staleJobs.getByRole("button", { name: "拒绝批次" }).click();
  await expect(staleJobs.getByRole("alert"))
    .toHaveText("批次状态已经改变，请刷新后查看。");
  await expect(staleJobs.getByText("已批准，等待执行", { exact: true }))
    .toBeVisible();
  await stale.close();
  await page.reload();
  await expect(jobs.getByText("已批准，等待执行", { exact: true })).toBeVisible();
  await jobs.getByRole("button", { name: "刷新当前批次" }).click();
  await expect(jobs.getByText("决定说明：已核对冻结范围", { exact: true }))
    .toBeVisible();
});

test("collaborator cannot decide and sees the owner's rejection", async ({
  page, browser,
}) => {
  await page.goto("/");
  await page.getByLabel("账号", { exact: true }).fill("owner");
  await page.getByLabel("密码", { exact: true }).fill("synthetic browser password");
  await page.getByRole("button", { name: "登录", exact: true }).click();
  await page.getByRole("button", { name: "登记已核验题目" }).click();
  await page.getByRole("button", { name: "登记固定 Codex 配置" }).click();
  const members = page.getByRole("region", { name: "成员管理" });
  await members.getByRole("button", { name: "创建邀请码" }).click();
  const token = await members.getByLabel("仅此一次的邀请码").inputValue();

  const guest = await browser.newContext({ ignoreHTTPSErrors: true });
  try {
    const teammate = await guest.newPage();
    await teammate.goto(page.url());
    await teammate.getByRole("button", { name: "使用邀请码加入" }).click();
    await teammate.getByLabel("邀请码", { exact: true }).fill(token);
    await teammate.getByLabel("新账号", { exact: true }).fill("job_teammate");
    await teammate.getByLabel("新密码", { exact: true })
      .fill("synthetic teammate password");
    await teammate.getByRole("button", { name: "加入平台" }).click();
    await teammate.getByLabel("账号", { exact: true }).fill("job_teammate");
    await teammate.getByLabel("密码", { exact: true })
      .fill("synthetic teammate password");
    await teammate.getByRole("button", { name: "登录", exact: true }).click();
    const jobs = teammate.getByRole("region", { name: "提交评测" });
    await jobs.getByRole("button", { name: "刷新可提交选项" }).click();
    await jobs.getByLabel("任务 example__repo-1").check();
    await jobs.getByLabel("配置 Synthetic Codex").check();
    const submitted = teammate.waitForResponse((candidate) =>
      candidate.request().method() === "POST" &&
      new URL(candidate.url()).pathname === "/api/v1/jobs",
    );
    await jobs.getByRole("button", { name: "提交等待批准" }).click();
    const created = await (await submitted).json();
    await expect(jobs.getByRole("region", { name: "所有者决定" })).toHaveCount(0);

    await page.goto(`/?job=${created.job_id}`);
    const ownerJobs = page.getByRole("region", { name: "提交评测" });
    await expect(ownerJobs.getByText("等待所有者批准", { exact: true }))
      .toBeVisible();
    await ownerJobs.getByLabel("决定说明（可选）").fill("冻结范围不正确");
    await ownerJobs.getByRole("button", { name: "拒绝批次" }).click();
    await expect(ownerJobs.getByText("已拒绝", { exact: true })).toBeVisible();

    await teammate.reload();
    await expect(jobs.getByText("已拒绝", { exact: true })).toBeVisible();
    await expect(jobs.getByText("决定说明：冻结范围不正确", { exact: true }))
      .toBeVisible();
    await expect(jobs.getByRole("region", { name: "所有者决定" })).toHaveCount(0);
  } finally { await guest.close(); }
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
