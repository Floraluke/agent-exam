import { expect, test } from "@playwright/test";
import type { Page } from "@playwright/test";
import {
  loginOwner,
  navigation,
  openWizard,
  registerCatalog,
  reviewSelection,
} from "../support/workbench";

async function submit(page: Page, taskName: string) {
  const jobs = await openWizard(page);
  await reviewSelection(jobs, [taskName]);
  await page.getByRole("button", { name: "提交并等待批准" }).click();
  await expect(page.getByRole("heading", { name: "评测详情" })).toBeVisible();
}

async function openComparison(page: Page) {
  const nav = navigation(page);
  await nav.getByRole("button", { name: "评测", exact: true }).click();
  const compare = page.getByRole("button", { name: /对比所选/ });
  await expect(compare).toBeDisabled();
  const checks = page.getByLabel("选择对比");
  await checks.nth(0).check();
  await checks.nth(1).check();
  await compare.click();
  await expect(nav.getByRole("button", { name: "对比报告", exact: true }))
    .toHaveAttribute("aria-current", "page");
}

test("owner compares two batches and reads the matrix without inventing results", async ({
  page,
}) => {
  await loginOwner(page);
  await registerCatalog(page, true);
  await submit(page, "example__repo-1");
  await submit(page, "example__repo-2");
  await openComparison(page);

  await page.getByRole("button", { name: "应用对比" }).click();
  const table = page.getByRole("region", { name: "跨批次对比报告" })
    .getByRole("table");
  await expect(table).toBeVisible();

  // 两列 = 两个所选批次；两批次用同一配置，故显示名相同、各自可点进批次详情。
  await expect(table.getByRole("columnheader")).toHaveCount(3);
  await expect(table.getByRole("button", { name: "Synthetic Codex" })).toHaveCount(2);

  // 每列只覆盖自己提交的那道题：两列各一格有结果、一格缺失。
  const incomplete = table.locator('tbody td[data-outcome="incomplete"]');
  const missing = table.locator('tbody td[data-outcome="missing"]');
  await expect(incomplete).toHaveCount(2);
  await expect(missing).toHaveCount(2);
  // 缺失格没有 Run：显示「无运行」，不冒充未通过，也不提供钻取。
  await expect(missing.first()).toContainText("无运行");
  await expect(missing.first().getByRole("button")).toHaveCount(0);

  // 汇总只用 decided/total 两个整数表达，不返回字符串覆盖率字段。
  const totals = table.locator("tfoot tr");
  await expect(totals).toContainText("有结论 / 总数");
  await expect(totals).toContainText(/\d+\/\d+/);
  await expect(page.locator("body")).not.toContainText("coverage");

  // 钻取：有 run_id 的单元格进入既有单次运行报告，返回后矩阵仍在。
  await table.getByRole("button", { name: /查看 example__repo-1 运行报告/ })
    .first().click();
  await expect(page.getByRole("region", { name: "对比中的单次运行报告" }))
    .toBeVisible();
  await page.getByRole("button", { name: "返回对比矩阵" }).click();
  await expect(table).toBeVisible();

  // 逐项移除使所选集合收缩；清空回到空态。
  const selected = page.getByRole("list", { name: "已选批次" });
  await expect(selected.getByRole("listitem")).toHaveCount(2);
  await selected.getByRole("button").first().click();
  await expect(selected.getByRole("listitem")).toHaveCount(1);
  await page.getByRole("button", { name: "清空选择" }).click();
  await expect(page.getByText("还没有选择要对比的批次")).toBeVisible();
});

test("comparison selection stays opt-in and resets on reload", async ({ page }) => {  await loginOwner(page);
  await registerCatalog(page);
  await submit(page, "example__repo-1");

  const nav = navigation(page);
  await nav.getByRole("button", { name: "评测", exact: true }).click();
  await page.getByLabel("选择对比").first().check();
  await expect(page.getByRole("button", { name: /对比所选（1\// })).toBeEnabled();

  // 选择只在本机会话：刷新后回到 0，也不写进 URL。
  await page.reload();
  await nav.getByRole("button", { name: "评测", exact: true }).click();
  await expect(page.getByRole("button", { name: /对比所选（0\// })).toBeDisabled();
  await expect(page.getByLabel("选择对比").first()).not.toBeChecked();
  expect(new URL(page.url()).searchParams.get("job_ids")).toBeNull();
});

test("390 and 360 contain the matrix without page overflow", async ({ page }) => {
  // 准备阶段用默认桌面宽度：既有助手按侧栏常驻编写，手机端侧栏是收起的。
  await loginOwner(page);
  await registerCatalog(page, true);
  await submit(page, "example__repo-1");
  await submit(page, "example__repo-2");

  await page.setViewportSize({ width: 390, height: 844 });
  // 手机端经菜单进入评测列表；点导航后菜单自动收起。
  const nav = navigation(page);
  await page.getByRole("button", { name: "打开主导航" }).click();
  await expect(nav).toBeVisible();
  await nav.getByRole("button", { name: "评测", exact: true }).click();
  await expect(nav).not.toBeVisible();
  await page.getByLabel("选择对比").nth(0).check();
  await page.getByLabel("选择对比").nth(1).check();
  await page.getByRole("button", { name: /对比所选/ }).click();
  await page.getByRole("button", { name: "应用对比" }).click();

  const table = page.getByRole("region", { name: "跨批次对比报告" })
    .getByRole("table");
  await expect(table).toBeVisible();
  // 宽表必须由矩阵容器承载横向滚动：body 是 overflow-x: hidden，
  // 容器不接管的话宽表会被裁掉而不是可滚动。
  await expect.poll(() => page.evaluate(() => {
    const box = document.querySelector(".comparison-matrix");
    return box !== null && getComputedStyle(box).overflowX === "auto";
  })).toBe(true);
  await expect.poll(() => page.evaluate(() =>
    document.documentElement.scrollWidth <= document.documentElement.clientWidth,
  )).toBe(true);
  await page.screenshot({
    path: "../../runtime/tests/03-comparison-mobile-390.png", fullPage: true,
  });

  await page.setViewportSize({ width: 360, height: 800 });
  await expect(table).toBeVisible();
  await expect.poll(() => page.evaluate(() =>
    document.documentElement.scrollWidth <= document.documentElement.clientWidth,
  )).toBe(true);
  await page.screenshot({
    path: "../../runtime/tests/03-comparison-mobile-360.png", fullPage: true,
  });
});

test("a wide matrix scrolls inside its container instead of breaking the page", async ({
  page,
}) => {
  await loginOwner(page);
  await registerCatalog(page, true);
  // 夹具的 preset 按需登记，这里补齐到六题 + 两配置，才有 12 列可比。
  await page.evaluate(async () => {
    const register = async (path: string, presetId: string) => {
      const response = await fetch(path, {
        method: "POST", credentials: "same-origin",
        headers: { "Content-Type": "application/json", "X-AgentExam-Request": "1" },
        body: JSON.stringify({ preset_id: presetId }),
      });
      if (!response.ok) throw new Error("wide-matrix catalog registration failed");
    };
    for (const index of [3, 4, 5, 6]) {
      await register("/api/v1/tasks/register", `swe-gym-lite-example-${index}`);
    }
    await register("/api/v1/agent-configurations", "codex-0153-terra-low");
  });
  // 用接口批量建批次（六题 × 两配置 = 12 列），避免为凑列数在向导里点 12 次。
  const created = await page.evaluate(async () => {
    const read = async (path: string) =>
      (await (await fetch(path, { credentials: "same-origin" })).json()) as {
        items: Record<string, string>[];
      };
    const taskPage = await read("/api/v1/tasks?limit=100");
    const agentPage = await read(
      "/api/v1/agent-configurations?agent_type=codex&enabled=true&limit=100");
    const taskIds = taskPage.items.map((item) => item.task_id);
    const agentIds = agentPage.items.map((item) => item.agent_configuration_id);
    let count = 0;
    for (const taskId of taskIds) {
      for (const agentId of agentIds) {
        const response = await fetch("/api/v1/jobs", {
          method: "POST", credentials: "same-origin",
          headers: {
            "Content-Type": "application/json", "X-AgentExam-Request": "1",
            "Idempotency-Key": crypto.randomUUID(),
          },
          body: JSON.stringify({
            task_ids: [taskId], agent_configuration_ids: [agentId],
            evaluation_track: "closed_book", batch_preset: "continuous",
            limit_profile_id: "default-single-host-v1",
          }),
        });
        if (!response.ok) throw new Error("wide-matrix fixture job failed");
        count += 1;
      }
    }
    return { tasks: taskIds.length, agents: agentIds.length, count };
  });
  expect(created.count).toBe(created.tasks * created.agents);
  expect(created.count).toBeGreaterThanOrEqual(10);

  await page.setViewportSize({ width: 390, height: 844 });
  const nav = navigation(page);
  await page.getByRole("button", { name: "打开主导航" }).click();
  await nav.getByRole("button", { name: "评测", exact: true }).click();
  // 勾上当前列表里的全部批次（含本文件前几条用例留下的，故按实际数量断言）。
  const checks = page.getByLabel("选择对比");
  const total = await checks.count();
  expect(total).toBeGreaterThanOrEqual(created.count);
  for (let index = 0; index < total; index += 1) await checks.nth(index).check();
  await page.getByRole("button", { name: /对比所选/ }).click();
  await page.getByRole("button", { name: "应用对比" }).click();

  const table = page.getByRole("region", { name: "跨批次对比报告" })
    .getByRole("table");
  await expect(table).toBeVisible();
  await expect(table.getByRole("columnheader")).toHaveCount(total + 1);

  // 关键断言：这么多列必须真的把容器压出横向滚动，而页面本身不溢出。
  await expect.poll(() => page.evaluate(() => {
    const box = document.querySelector(".comparison-matrix");
    return box !== null && box.scrollWidth > box.clientWidth;
  })).toBe(true);
  await expect.poll(() => page.evaluate(() =>
    document.documentElement.scrollWidth <= document.documentElement.clientWidth,
  )).toBe(true);
  await page.screenshot({
    path: "../../runtime/tests/03-comparison-wide-390.png", fullPage: true,
  });
});
