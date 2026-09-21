import { expect, test } from "@playwright/test";
import {
  loginOwner, navigation, openWizard, registerCatalog, reviewSelection,
} from "../support/workbench";

async function completeOwnerJob(page: import("@playwright/test").Page) {
  const wizard = await openWizard(page);
  await reviewSelection(wizard, ["example__repo-1"]);
  await wizard.getByRole("button", { name: "提交并等待批准" }).click();
  await wizard.getByRole("button", { name: "批准并排队" }).click();
  const refresh = wizard.getByRole("button", { name: "刷新当前批次" });
  await expect.poll(async () => {
    await refresh.click();
    return wizard.getByText("执行完成", { exact: true }).count();
  }).toBe(1);
}

test("collaborator compares only their own server-visible batches", async ({ page, browser }) => {
  await loginOwner(page);
  await registerCatalog(page);
  await completeOwnerJob(page);
  await navigation(page).getByRole("button", { name: "成员管理" }).click();
  const members = page.getByRole("region", { name: "成员管理" });
  await members.getByRole("button", { name: "创建邀请码" }).click();
  const token = await members.getByLabel("仅此一次的邀请码").inputValue();

  const guest = await browser.newContext({ ignoreHTTPSErrors: true });
  try {
    const teammate = await guest.newPage();
    await teammate.goto(page.url());
    await teammate.getByRole("button", { name: "使用邀请码加入" }).click();
    await teammate.getByLabel("邀请码", { exact: true }).fill(token);
    await teammate.getByLabel("新账号", { exact: true }).fill("comparison_teammate");
    await teammate.getByLabel("新密码", { exact: true }).fill("synthetic teammate password");
    await teammate.getByRole("button", { name: "加入平台" }).click();
    await teammate.getByLabel("账号", { exact: true }).fill("comparison_teammate");
    await teammate.getByLabel("密码", { exact: true }).fill("synthetic teammate password");
    await teammate.getByRole("button", { name: "登录", exact: true }).click();
    const teammateNav = navigation(teammate);
    await expect(teammateNav.getByRole("button", { name: "成员管理" })).toHaveCount(0);
    await teammateNav.getByRole("button", { name: "对比报告" }).click();
    const reports = teammate.getByRole("region", { name: "对比报告工作区" });
    await expect(reports.getByRole("checkbox")).toHaveCount(0);
    await expect(reports).toContainText("暂无可对比的评测批次");

    await teammateNav.getByRole("button", { name: "新建评测" }).click();
    const wizard = teammate.getByRole("region", { name: "新建评测向导" });
    await reviewSelection(wizard, ["example__repo-1"]);
    const submitted = teammate.waitForResponse((response) =>
      response.request().method() === "POST" &&
      new URL(response.url()).pathname === "/api/v1/jobs");
    await wizard.getByRole("button", { name: "提交并等待批准" }).click();
    const created = await (await submitted).json();

    await page.goto(`/?view=jobs&job=${created.job_id}`);
    await page.getByRole("button", { name: "批准并排队" }).click();
    const ownerRefresh = page.getByRole("button", { name: "刷新当前批次" });
    await expect.poll(async () => {
      await ownerRefresh.click();
      return page.getByText("执行完成", { exact: true }).count();
    }).toBe(1);

    await teammateNav.getByRole("button", { name: "对比报告" }).click();
    await expect(reports.getByRole("checkbox")).toHaveCount(1);
    await reports.getByRole("checkbox").check();
    await reports.getByRole("button", { name: "生成对比（1）" }).click();
    await expect(reports.getByRole("region", { name: "题目配置对比矩阵" }))
      .toContainText("确定性通过");
  } finally { await guest.close(); }
});
