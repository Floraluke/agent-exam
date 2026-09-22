// 多列矩阵的横向滚动：**独立成文件**是刻意的。
// 这条用例要造 12 个批次，而仓库的 runner（tests/run-browser-tests.mjs）对
// **每个 spec 文件各起一次干净后端**。放进 jobs/comparison.spec.ts 会污染同文件
// 其他用例看到的数据（实测：一并放进去时同文件 6 条里有 3 条失败）。
import { expect, test } from "@playwright/test";
import { loginOwner, navigation, registerCatalog } from "../support/workbench";

test("a many-column matrix really scrolls inside its container", async ({ page }) => {
  await loginOwner(page);
  await registerCatalog(page, true);

  // 12 个批次用页面内 fetch 批量造（沿用分页用例的手法），不走 12 次向导。
  await page.evaluate(async () => {
    const read = async (path: string) => (await fetch(path)).json();
    const [tasks, agents, options] = await Promise.all([
      read("/api/v1/tasks?limit=100"),
      read("/api/v1/agent-configurations?limit=100&agent_type=codex"),
      read("/api/v1/job-options"),
    ]);
    const body = JSON.stringify({
      task_ids: [tasks.items[0].task_id],
      agent_configuration_ids: [agents.items[0].agent_configuration_id],
      evaluation_track: "closed_book",
      batch_preset: options.batch_presets[0].batch_preset,
      limit_profile_id: options.limit_profiles[0].limit_profile_id,
    });
    for (let index = 0; index < 12; index += 1) {
      const response = await fetch("/api/v1/jobs", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-AgentExam-Request": "1",
          "Idempotency-Key": `wide-matrix-${String(index).padStart(4, "0")}`,
        },
        body,
      });
      if (!response.ok) throw new Error(`setup failed: ${response.status}`);
    }
  });

  // 窄视口下 12 列必然宽于容器：滚动是确定要发生的，断言才有意义。
  await page.setViewportSize({ width: 390, height: 844 });
  const nav = navigation(page);
  await page.getByRole("button", { name: "打开主导航" }).click();
  await nav.getByRole("button", { name: "评测", exact: true }).click();
  await expect(nav).not.toBeVisible();

  // 等列表渲染出来再勾选（不用固定等待，也不假设全库只有我造的这 12 个）。
  const rows = page.locator(".job-row");
  await expect(rows.first()).toBeVisible();
  const wanted = Math.min(await rows.count(), 12);
  expect(wanted).toBeGreaterThan(1);
  for (let index = 0; index < wanted; index += 1) {
    await page.getByLabel("选择对比").nth(index).check();
  }
  await page.getByRole("button", { name: new RegExp(`对比所选（${wanted}/`) }).click();
  await page.getByRole("button", { name: "应用对比" }).click();

  const scroll = page.locator(".comparison-scroll.comparison-matrix");
  await expect(scroll).toBeVisible();
  // 决定性的一步：**先等列数到位，再量几何**。旧版在渲染完成前测量，
  // 于是读到空表或还没撑开的表——那才是"矩阵表未渲染"那类失败的根因。
  await expect(page.locator(".comparison-table thead th")).toHaveCount(wanted + 1);
  await expect.poll(() => scroll.evaluate((box) => box.scrollWidth > box.clientWidth))
    .toBe(true);
  const moved = await scroll.evaluate((box) => { box.scrollLeft = 200; return box.scrollLeft; });
  expect(moved).toBeGreaterThan(0);
  // 容器接管滚动，页面本身仍不被撑破。
  expect(await page.evaluate(() =>
    document.documentElement.scrollWidth <= document.documentElement.clientWidth)).toBe(true);
  await page.screenshot({
    path: "../../runtime/tests/03-comparison-wide-many-columns-390.png", fullPage: true,
  });
});
