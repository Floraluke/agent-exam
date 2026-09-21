import { expect, test } from "@playwright/test";
import type { Page } from "@playwright/test";
import { loginOwner, openWizard, registerCatalog, reviewSelection } from "./support/workbench";

// 网页渲染面的哨兵扫描：C 已对 12 个 HTTP 公开读取面做过同类扫描，网页面按分工归 B。
// 这些值覆盖隐藏判卷字段、凭据引用与制品内部键——页面文本里出现任何一个都是缺陷。
const SENTINELS = [
  "codex-secrets", "private synthetic message", "private-test-reference",
  "HIDDEN_ANSWER", "hidden_test", "hidden_pass",
  "gold_patch", "test_patch", "object_key",
];

async function expectNoSentinels(page: Page, where: string) {
  for (const sentinel of SENTINELS) {
    await expect(page.locator("body"), `${where} 出现了哨兵 ${sentinel}`)
      .not.toContainText(sentinel);
  }
}

test("run report opens safe trajectory and downloadable patch", async ({ page }) => {
  await loginOwner(page);
  await registerCatalog(page);
  const jobs = await openWizard(page);
  await reviewSelection(jobs, ["example__repo-1"]);
  await jobs.getByRole("button", { name: "提交并等待批准" }).click();
  await jobs.getByRole("button", { name: "批准并排队" }).click();
  const refresh = jobs.getByRole("button", { name: "刷新当前批次" });
  await expect.poll(async () => {
    await refresh.click();
    return jobs.getByText("执行完成", { exact: true }).count();
  }).toBe(1);
  await jobs.getByRole("button", { name: "查看单题运行报告" }).click();
  const evidence = jobs.getByRole("region", { name: "安全证据" });
  await expect(evidence).toContainText("最终补丁");
  await expect(evidence).toContainText("测试摘要");
  // 单次运行报告页（含用量、资源、判卷摘要）整页扫描。
  await expectNoSentinels(page, "单次运行报告");
  await page.route("**/api/v1/runs/*/trajectory?*", async (route) => {
    const url = new URL(route.request().url()); url.searchParams.set("limit", "1");
    await route.continue({ url: url.toString() });
  });
  await evidence.getByRole("button", { name: "查看安全轨迹" }).click();
  await expect(evidence).toContainText("调用工具 Read");
  await evidence.getByRole("button", { name: "加载更多轨迹" }).click();
  await expect(evidence).toContainText("正文未公开");
  const pending = page.waitForEvent("download");
  await evidence.getByRole("link", { name: "下载最终补丁" }).click();
  await expect((await pending).suggestedFilename()).toBe("agent.patch");
  // 轨迹与下载都展开之后再扫一遍安全证据页。
  await expectNoSentinels(page, "安全证据");
});
