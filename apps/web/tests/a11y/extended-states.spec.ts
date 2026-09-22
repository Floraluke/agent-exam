// 基线没扫到的状态（一）：无会话的登录页与邀请加入页、390/360 手机宽度
// （手机端侧栏默认收起，展开主导航后另扫一次），以及夹具注入故障后页面上的错误提示。
// 扫描规则与"必须为零"的判定见 tests/support/a11y.ts（与 baseline.spec.ts 同语义）。
// 本文件自己造数据（一次性邀请码、待批准的批次），因此独立成文件：
// runner 对每个 spec 文件各起一次干净后端状态，造数据的用例不能与别的 spec 共享。
import { expect, test } from "@playwright/test";
import type { Page } from "@playwright/test";
import { scan } from "../support/a11y";
import {
  loginOwner, navigation, openWizard, registerCatalog, reviewSelection,
} from "../support/workbench";

const CONTROL = "http://127.0.0.1:8875/__test__";
const VISITOR = "a11y_visitor";
const TEAMMATE_PASSWORD = "synthetic teammate password";

test.describe.configure({ timeout: 180_000 });

// 夹具的一次性故障注入（与 tests/jobs/refresh-failure.spec.ts 同一端点）：让下一条
// 匹配的响应以给定稳定错误码收束，用来造出页面上真实可见的错误提示。
async function failNext(page: Page, method: string, path: string) {
  const armed = await page.request.post(`${CONTROL}/http/fail-next-response`, {
    headers: { Origin: "https://127.0.0.1:3100", "X-AgentExam-Request": "1" },
    data: { method, path_suffix: path, status: "503", code: "DEPENDENCY_UNAVAILABLE" },
  });
  expect(armed.ok()).toBeTruthy();
}

test("无会话的登录页与邀请加入页", async ({ page, browser }) => {
  const info = test.info();
  // 邀请码由所有者真实签发：加入页要带着真码走通一遍，而不是只渲染空表单。
  await loginOwner(page);
  await navigation(page).getByRole("button", { name: "成员管理" }).click();
  const members = page.getByRole("region", { name: "成员管理" });
  await members.getByRole("button", { name: "创建邀请码" }).click();
  const token = await members.getByLabel("仅此一次的邀请码").inputValue();

  const guest = await browser.newContext({ ignoreHTTPSErrors: true });
  try {
    const visitor = await guest.newPage();
    await visitor.goto("/");
    await expect(visitor.getByRole("button", { name: "登录", exact: true })).toBeVisible();
    await scan(visitor, info, "登录页（无会话）");

    await visitor.getByRole("button", { name: "使用邀请码加入" }).click();
    const join = visitor.getByRole("region", { name: "受邀加入" });
    await expect(join).toBeVisible();
    await scan(visitor, info, "加入页（空表单）");
    await join.getByLabel("邀请码", { exact: true }).fill(token);
    await join.getByLabel("新账号", { exact: true }).fill(VISITOR);
    await join.getByLabel("新密码", { exact: true }).fill(TEAMMATE_PASSWORD);
    await scan(visitor, info, "加入页（已填真实邀请码）");
    await join.getByRole("button", { name: "加入平台" }).click();
    await expect(visitor.getByText("加入成功，请使用新账号登录。")).toBeVisible();
    await scan(visitor, info, "加入页（加入成功后）");

    // 登录失败的错误态：注入一次 503，页面必须给出可见的错误提示而不是静默失败。
    // 断言限定在登录卡片内：Next 的路由播报器也是一个空的 role=alert。
    await failNext(visitor, "POST", "/api/v1/auth/login");
    await visitor.getByLabel("账号", { exact: true }).fill(VISITOR);
    await visitor.getByLabel("密码", { exact: true }).fill(TEAMMATE_PASSWORD);
    await visitor.getByRole("button", { name: "登录", exact: true }).click();
    const card = visitor.getByRole("region", { name: "平台账号" });
    await expect(card.getByRole("alert")).toBeVisible();
    await scan(visitor, info, "登录页（登录失败的错误态）");
  } finally { await guest.close(); }
});

test("390 与 360 手机宽度：侧栏收起与展开主导航", async ({ page }) => {
  const info = test.info();
  await page.setViewportSize({ width: 390, height: 844 });
  await loginOwner(page);
  const nav = navigation(page);
  const menu = page.getByRole("button", { name: "打开主导航" });
  await expect(menu).toBeVisible();
  await expect(nav).not.toBeVisible();
  await scan(page, info, "工作台·390·侧栏收起");

  await menu.click();
  await expect(nav).toBeVisible();
  await scan(page, info, "工作台·390·主导航展开");

  await page.setViewportSize({ width: 360, height: 800 });
  await expect(nav).toBeVisible();
  await scan(page, info, "工作台·360·主导航展开");

  await page.getByRole("button", { name: "关闭主导航" }).click();
  await expect(nav).not.toBeVisible();
  await scan(page, info, "工作台·360·侧栏收起");
});

test("批次详情重读失败后的错误态", async ({ page }) => {
  const info = test.info();
  await loginOwner(page);
  await registerCatalog(page);
  const jobs = await openWizard(page);
  await reviewSelection(jobs, ["example__repo-1"]);
  // 批次 ID 取自创建响应：URL 的 job 参数是提交成功后才写上的。
  const created = page.waitForResponse((response) =>
    response.request().method() === "POST" &&
    new URL(response.url()).pathname === "/api/v1/jobs");
  await jobs.getByRole("button", { name: "提交并等待批准" }).click();
  const jobId = (await (await created).json()).job_id as string;
  expect(jobId).toBeTruthy();
  await expect(jobs.getByText("等待所有者批准", { exact: true })).toBeVisible();

  // 注入一次详情重读失败：批准本身成功，但页面拿不到新状态，于是出现错误提示与过期提示。
  await failNext(page, "GET", `/api/v1/jobs/${jobId}`);
  await jobs.getByRole("button", { name: "批准并排队" }).click();
  await expect(jobs.getByRole("alert")).toHaveText("平台存储暂不可用，请稍后重试。");
  await scan(page, info, "批次详情（重读失败的错误态）");
});
