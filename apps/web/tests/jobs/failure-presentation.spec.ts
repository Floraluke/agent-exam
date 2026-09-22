// 呈现验证：页面拿到“给定失败码 + 给定失败文案”时必须如实呈现（HTTP_API.md 第 10.2 节）。
// 造数据靠夹具的控制端点 POST /__test__/jobs/fail-next-run；本 spec 独立成文件，
// 因为造数据的用例不能与别的用例共享同一个后端状态。
import { expect, test } from "@playwright/test";
import type { Locator, Page } from "@playwright/test";
import { loginOwner, openWizard, registerCatalog, reviewSelection } from "../support/workbench";

// 链路将来会发出的五个受控码与逐字受控短文案（第 10.2 节的受控词汇表）。
const CONTROLLED: ReadonlyArray<readonly [string, string]> = [
  ["PROVIDER_CREDENTIAL_UNAVAILABLE", "模型凭据不可用，运行未开始。"],
  ["PROVIDER_ACCESS_DENIED", "模型访问未获授权。"],
  ["PROVIDER_REQUEST_REJECTED", "模型请求不符合受限策略。"],
  ["PROVIDER_BUDGET_EXHAUSTED", "运行额度或期限已用尽。"],
  ["PROVIDER_ACCESS_FAILED", "模型访问未完成。"],
];
// 链路永不会发出的内部码前缀：这些字串出现在页面文本里就是缺陷。
const INTERNAL_PREFIXES = [
  "UNCONTROLLED_AGENT_TYPE", "UNCONTROLLED_PROVIDER", "PROVIDER_BINDING_",
  "PROVIDER_TOKEN_", "PRIVATE_FILE_", "REQUEST_", "BUDGET_",
];
const backend = "http://127.0.0.1:8875/__test__";
const controlHeaders = {
  Origin: "https://127.0.0.1:3100", "X-AgentExam-Request": "1",
};
// 未知码：链路永不会发出，用来验证页面不把它当成已知状态。
const UNKNOWN_CODE = "PROVIDER_UNKNOWN_FOR_TEST";
const UNKNOWN_SUMMARY = "合成夹具注入的未知失败，仅供呈现验证。";

test.describe.configure({ mode: "serial" });

// 目录只登记一次：重复登记配置会新增第二个同名配置，把后续的定位变成歧义。
test.beforeAll(async ({ browser }) => {
  const page = await browser.newPage();
  await loginOwner(page);
  await registerCatalog(page);
  await page.close();
});

async function failNextSingleRun(page: Page, code: string, summary: string) {
  const jobs = await openWizard(page);
  await reviewSelection(jobs, ["example__repo-1"]);
  await jobs.getByRole("button", { name: "提交并等待批准" }).click();
  // 注入必须在批准之前完成：获批后 Worker 会立刻领走这个 Run。
  const armed = await page.request.post(`${backend}/jobs/fail-next-run`, {
    headers: controlHeaders, data: { failure_code: code, failure_summary: summary },
  });
  expect(armed.ok()).toBeTruthy();
  await jobs.getByRole("button", { name: "批准并排队" }).click();
  await expect.poll(async () => {
    await jobs.getByRole("button", { name: "刷新当前批次" }).click();
    return jobs.getByRole("article", { name: "评测批次详情" })
      .getByRole("heading", { name: "运行失败", exact: true }).count();
  }, { message: "批次没有进入运行失败", timeout: 20000 }).toBe(1);
  return jobs;
}

// 失败码与失败文案只出现在单题运行报告的“技术详情”里，先展开再断言呈现。
async function openRunReport(jobs: Locator) {
  await jobs.getByRole("button", { name: "查看单题运行报告" }).click();
  const report = jobs.getByRole("region", { name: "单题运行报告" });
  await report.locator("summary").click();
  return report;
}

for (const [code, summary] of CONTROLLED) {
  test(`受控码 ${code}：页面逐字呈现受控文案与失败码`, async ({ page }) => {
    await loginOwner(page);
    const jobs = await failNextSingleRun(page, code, summary);
    await jobs.getByRole("button", { name: "查看批次进度" }).click();
    const batch = jobs.getByRole("region", { name: "批次进度" });
    await expect(batch).toContainText("基础设施错误");
    await expect(batch).toContainText(new RegExp(`错误码：${code}。`));
    const report = await openRunReport(jobs);
    await expect(report).toContainText("基础设施错误：本次没有形成确定性成绩。");
    await expect(report.locator("code")).toHaveText(code);
    await expect(report.getByText(summary, { exact: true })).toBeVisible();
    await expect(page.getByText(summary, { exact: true })).toBeVisible();
  });
}

test("未知失败码：页面只显示码本身，不编造类别文案", async ({ page }) => {
  await loginOwner(page);
  const jobs = await failNextSingleRun(page, UNKNOWN_CODE, UNKNOWN_SUMMARY);
  const report = await openRunReport(jobs);
  // 未知码原样落在技术详情里且只出现一次：既没有被改写成别的码，也没有被当成已知状态重复呈现。
  await expect(report.locator("code")).toHaveText(UNKNOWN_CODE);
  await expect(report.locator("code")).toBeVisible();
  await expect(report.getByText(UNKNOWN_CODE, { exact: true })).toHaveCount(1);
  await expect(report.getByText(UNKNOWN_SUMMARY, { exact: true })).toBeVisible();
  for (const prefix of INTERNAL_PREFIXES) {
    await expect(page.locator("body"), `页面回显了内部码 ${prefix}`)
      .not.toContainText(prefix);
  }
  for (const [, summary] of CONTROLLED) {
    await expect(page.locator("body"), `页面凭空显示了受控文案 ${summary}`)
      .not.toContainText(summary);
  }
  // 也没有把未知码当成已知状态：仍是基础设施错误，且不显示任何确定性成绩。
  await expect(report).toContainText("基础设施错误：本次没有形成确定性成绩。");
  await expect(report).not.toContainText("确定性结果：");
});
