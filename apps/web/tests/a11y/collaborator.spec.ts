// 基线没扫到的状态（二）：协作者视角。协作者看到的视图、导航项与批次范围都和所有者
// 不同，所以要真实协作者会话（邀请码兑换），而不是改一个角色字段。
// 扫描规则与"必须为零"的判定见 tests/support/a11y.ts（与 baseline.spec.ts 同语义）。
// 本文件自己造数据（一次性邀请码、协作者自己的批次），因此独立成文件。
import { expect, test } from "@playwright/test";
import type { Page } from "@playwright/test";
import { scan } from "../support/a11y";
import { loginOwner, navigation, openWizard, registerCatalog, reviewSelection }
  from "../support/workbench";

const TEAMMATE = "a11y_teammate";
const TEAMMATE_PASSWORD = "synthetic teammate password";

test.describe.configure({ timeout: 240_000 });

// 真实协作者会话：所有者在成员管理里签发一次性邀请码，访客在独立的浏览器上下文里
// 兑换并登录，此后这个上下文里的每个视图都是协作者看到的版本。
async function joinTeammate(owner: Page, teammate: Page) {
  await navigation(owner).getByRole("button", { name: "成员管理" }).click();
  const members = owner.getByRole("region", { name: "成员管理" });
  await members.getByRole("button", { name: "创建邀请码" }).click();
  const token = await members.getByLabel("仅此一次的邀请码").inputValue();
  await teammate.goto(owner.url());
  await teammate.getByRole("button", { name: "使用邀请码加入" }).click();
  await teammate.getByLabel("邀请码", { exact: true }).fill(token);
  await teammate.getByLabel("新账号", { exact: true }).fill(TEAMMATE);
  await teammate.getByLabel("新密码", { exact: true }).fill(TEAMMATE_PASSWORD);
  await teammate.getByRole("button", { name: "加入平台" }).click();
  await teammate.getByLabel("账号", { exact: true }).fill(TEAMMATE);
  await teammate.getByLabel("密码", { exact: true }).fill(TEAMMATE_PASSWORD);
  await teammate.getByRole("button", { name: "登录", exact: true }).click();
  await expect(teammate.getByRole("heading", { name: "协作者工作台" })).toBeVisible();
}

test("协作者视角的工作台、评测列表与对比报告", async ({ page, browser }) => {
  const info = test.info();
  await loginOwner(page);
  await registerCatalog(page);
  const guest = await browser.newContext({ ignoreHTTPSErrors: true });
  try {
    const teammate = await guest.newPage();
    await joinTeammate(page, teammate);
    const nav = navigation(teammate);
    // 协作者导航里没有成员管理，工作台是协作者版本。
    await expect(nav.getByRole("button", { name: "成员管理" })).toHaveCount(0);
    await scan(teammate, info, "协作者工作台");

    await nav.getByRole("button", { name: "评测", exact: true }).click();
    const list = teammate.getByRole("region", { name: "评测列表" });
    await expect(list).toBeVisible();
    await scan(teammate, info, "协作者评测列表（还没有自己的批次）");

    // 协作者提交自己的批次，由所有者批准执行完成，让对比矩阵有真实内容。
    // 协作者只看得见自己提交的批次，因此矩阵至少要有这一条才算扫到了内容。
    const wizard = await openWizard(teammate);
    await reviewSelection(wizard, ["example__repo-1"]);
    const submitted = teammate.waitForResponse((response) =>
      response.request().method() === "POST" &&
      new URL(response.url()).pathname === "/api/v1/jobs");
    await wizard.getByRole("button", { name: "提交并等待批准" }).click();
    const jobId = (await (await submitted).json()).job_id as string;
    expect(jobId).toBeTruthy();

    await page.goto(`/?view=jobs&job=${jobId}`);
    await page.getByRole("button", { name: "批准并排队" }).click();
    const refresh = page.getByRole("button", { name: "刷新当前批次" });
    await expect.poll(async () => {
      await refresh.click();
      return page.getByText("执行完成", { exact: true }).count();
    }, { timeout: 20_000 }).toBe(1);

    await nav.getByRole("button", { name: "评测", exact: true }).click();
    await expect(list).toContainText("选择对比");
    await scan(teammate, info, "协作者评测列表（含自己的批次）");

    await nav.getByRole("button", { name: "对比报告" }).click();
    const reports = teammate.getByRole("region", { name: "对比报告工作区" });
    await expect(reports.getByRole("checkbox")).toHaveCount(1);
    await reports.getByRole("checkbox").check();
    await reports.getByRole("button", { name: /生成对比/ }).click();
    await expect(reports.getByRole("region", { name: "题目配置对比矩阵" })).toBeVisible();
    await scan(teammate, info, "协作者对比报告（含矩阵）");
  } finally { await guest.close(); }
});
