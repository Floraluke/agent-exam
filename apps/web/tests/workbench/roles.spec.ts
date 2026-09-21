import { expect, test } from "@playwright/test";

test("collaborator submits from the A workbench while only owner can decide", async ({
  page,
  browser,
}) => {
  await page.goto("/");
  await page.getByLabel("账号", { exact: true }).fill("owner");
  await page.getByLabel("密码", { exact: true }).fill("synthetic browser password");
  await page.getByRole("button", { name: "登录", exact: true }).click();
  const ownerNav = page.getByRole("navigation", { name: "主导航" });
  await ownerNav.getByRole("button", { name: "任务目录" }).click();
  await page.getByRole("button", { name: "登记已核验题目" }).click();
  await ownerNav.getByRole("button", { name: "配置目录" }).click();
  await page.getByRole("button", { name: "登记固定 Codex 配置" }).click();
  await ownerNav.getByRole("button", { name: "成员管理" }).click();
  const members = page.getByRole("region", { name: "成员管理" });
  await members.getByRole("button", { name: "创建邀请码" }).click();
  const token = await members.getByLabel("仅此一次的邀请码").inputValue();

  const guest = await browser.newContext({ ignoreHTTPSErrors: true });
  try {
    const teammate = await guest.newPage();
    await teammate.goto(page.url());
    await teammate.getByRole("button", { name: "使用邀请码加入" }).click();
    await teammate.getByLabel("邀请码", { exact: true }).fill(token);
    await teammate.getByLabel("新账号", { exact: true }).fill("workbench_teammate");
    await teammate.getByLabel("新密码", { exact: true })
      .fill("synthetic teammate password");
    await teammate.getByRole("button", { name: "加入平台" }).click();
    await teammate.getByLabel("账号", { exact: true }).fill("workbench_teammate");
    await teammate.getByLabel("密码", { exact: true })
      .fill("synthetic teammate password");
    await teammate.getByRole("button", { name: "登录", exact: true }).click();
    await expect(teammate.getByRole("heading", { name: "协作者工作台" })).toBeVisible();
    const teammateNav = teammate.getByRole("navigation", { name: "主导航" });
    await expect(teammateNav.getByRole("button", { name: "成员管理" })).toHaveCount(0);
    await teammateNav.getByRole("button", { name: "新建评测" }).click();
    const wizard = teammate.getByRole("region", { name: "新建评测向导" });
    await wizard.getByLabel("任务 example__repo-1").check();
    await wizard.getByRole("button", { name: "下一步" }).click();
    await wizard.getByLabel("配置 Synthetic Codex").check();
    await wizard.getByRole("button", { name: "下一步" }).click();
    const submitted = teammate.waitForResponse((response) =>
      response.request().method() === "POST" &&
      new URL(response.url()).pathname === "/api/v1/jobs",
    );
    await wizard.getByRole("button", { name: "提交并等待批准" }).click();
    const created = await (await submitted).json();
    await expect(teammate.getByRole("region", { name: "所有者决定" })).toHaveCount(0);

    await page.goto(`/?view=jobs&job=${created.job_id}`);
    await expect(page.getByText("等待所有者批准", { exact: true })).toBeVisible();
    await page.getByLabel("决定说明（可选）").fill("本轮暂不批准");
    await page.getByRole("button", { name: "拒绝批次" }).click();
    await expect(page.getByText("已拒绝", { exact: true })).toBeVisible();

    await teammate.reload();
    await expect(teammate.getByText("已拒绝", { exact: true })).toBeVisible();
    await expect(teammate.locator("body")).toContainText("决定说明：本轮暂不批准");
    await expect(teammate.getByRole("region", { name: "所有者决定" })).toHaveCount(0);
  } finally {
    await guest.close();
  }
});
