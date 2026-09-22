// 无障碍基线：对九个可达视图做 axe 扫描（wcag2a + wcag2aa）。
// 分工：机械性问题（可访问名、label 关联、landmark/role、aria-*、重复 id）必须为零；
// 颜色对比度与视觉版式按约定只报告不改，在 REPORT_ONLY 里逐条列名并写明理由。
// 本 spec 自己造数据（登记目录、提交并批准批次），因此独立成文件：造数据的用例
// 不能与别的 spec 共享后端状态。
import { AxeBuilder } from "@axe-core/playwright";
import { expect, test } from "@playwright/test";
import type { Locator, Page, TestInfo } from "@playwright/test";
import {
  loginOwner, navigation, openWizard, registerCatalog, reviewSelection,
} from "../support/workbench";

type AxeViolations = Awaited<ReturnType<AxeBuilder["analyze"]>>["violations"];
type Violation = AxeViolations[number];

// 只报告、不修：配色与字号由用户决定是否调整（行动 15 §1 的修复边界）。
// 排除范围最小化——这里只列**规则 id**，其余规则照常参与"必须为零"的断言。
// 2026-09-22 已修：`form > button` 这类表单主按钮的悬停原来会被通用的
// `button:hover:not(:disabled)`（权重 0,2,1）压掉底色而字色仍是白色 → 白字落在 #f7faf8 上，实测 1.05:1。
// 已在 globals.css 补一条权重更高的悬停规则（深绿底 + 白字）。**因此 color-contrast 不再排除、参与断言**：
// 若再有对比度问题出现，就是要处理的，而不是预先放行。
const REPORT_ONLY: Record<string, string> = {};

// 夹具任务的冻结比较条件（与 tests/catalog/conftest.py 的 task_bundle 一致）。
const FROZEN = {
  dataset: "synthetic-dataset", revision: "a".repeat(40),
  split: "train", repo: "example/repo",
};

function detail(violation: Violation) {
  return `${violation.id}（${violation.impact}）命中 ${violation.nodes.length} 处：\n` +
    violation.nodes.map((node) => `  ${node.target.join(" ")} :: ` +
      `${node.html.slice(0, 200)}\n    ${node.failureSummary ?? ""}`).join("\n");
}

async function scan(page: Page, info: TestInfo, view: string, hover?: Locator) {
  // 默认让指针离开控件再扫描：否则上一次 click 留下的 hover 态会参与计算，
  // 扫描结果取决于"上一个动作点在哪"，同一页面在不同用例里结论会不一致。
  // 需要悬停态证据时显式传入要悬停的控件，让 hover 成为用例写明的状态而不是偶然。
  if (hover) await hover.hover();
  else await page.mouse.move(0, 0);
  const results = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa"]).analyze();
  const reported = results.violations.filter((item) => item.id in REPORT_ONLY);
  // 每个视图都打印一行覆盖情况：违规、只报告、真正被评估通过的规则数与需人工复核项。
  // 通过数长期为 0 就说明扫描没跑起来，而不是页面变好了。
  console.log(`[扫描·${view}] 必须为零 ${results.violations.length - reported.length}；` +
    `只报告 ${reported.length}；通过 ${results.passes.length}；` +
    `需人工复核 ${results.incomplete.length}`);
  for (const violation of reported) {
    console.log(`[只报告·${view}] ${violation.id}（${violation.impact}）命中 ` +
      `${violation.nodes.length} 处：` +
      violation.nodes.map((node) => node.target.join(" ")).join(" | "));
    for (const node of violation.nodes) {
      console.log(`[只报告明细·${view}] ${node.target.join(" ")} ` +
        `${JSON.stringify(node.any.map((check) => check.data))} :: ${node.html.slice(0, 140)}`);
    }
  }
  await info.attach(`a11y-${view}.json`, {
    body: JSON.stringify({ reported, all: results.violations }, null, 2),
    contentType: "application/json",
  });
  const blocking = results.violations.filter((item) => !(item.id in REPORT_ONLY));
  expect(blocking.map(detail), `${view} 仍有未修复的无障碍违规`).toEqual([]);
}

// 单条用例走完九个视图：视图之间共享同一个批次与目录，拆开每条都要重造数据。
test.describe.configure({ timeout: 180_000 });

// 扫描器自检：确认"0 违规"是因为页面没问题，而不是规则没跑。
// 往真实页面注入一个没有可访问名的控件，必须被 label 规则抓到并报出该元素。
test("扫描器不是空转：注入的无名控件会被抓到", async ({ page }) => {
  await loginOwner(page);
  await page.evaluate(() => {
    const orphan = document.createElement("input");
    orphan.id = "a11y-self-check";
    document.body.append(orphan);
  });
  const results = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa"]).analyze();
  const label = results.violations.find((item) => item.id === "label");
  expect(label?.nodes.flatMap((node) => node.target).join(" "),
    "自检注入的无名控件没有被 label 规则抓到").toContain("#a11y-self-check");
});

test("各可达视图的 axe 基线扫描无未处理违规", async ({ page }) => {
  const info = test.info();
  await loginOwner(page);
  await registerCatalog(page, true);

  // 登记目录会把当前视图留在配置目录，先明确回到工作台再扫描。
  const nav = navigation(page);
  await nav.getByRole("button", { name: "工作台" }).click();
  await expect(page.getByRole("region", { name: "所有者工作台" })).toBeVisible();
  await scan(page, info, "工作台");

  await nav.getByRole("button", { name: "任务目录" }).click();
  await expect(page.getByRole("region", { name: "任务目录" })).toContainText("example__repo-1");
  await scan(page, info, "任务目录");

  await nav.getByRole("button", { name: "配置目录" }).click();
  await expect(page.getByRole("region", { name: "Codex 配置目录" }))
    .toContainText("Synthetic Codex");
  await scan(page, info, "配置目录");

  await nav.getByRole("button", { name: "成员管理" }).click();
  await expect(page.getByRole("region", { name: "成员管理" })).toBeVisible();
  await scan(page, info, "成员管理");

  await nav.getByRole("button", { name: "排行榜" }).click();
  const leaderboard = page.getByRole("region", { name: "基础排行榜" });
  await expect(leaderboard).toBeVisible();
  await scan(page, info, "排行榜");

  // 批次详情：先看"等待批准"态，再看批准后的完成态。
  const jobs = await openWizard(page);
  await reviewSelection(jobs, ["example__repo-1"]);
  await jobs.getByRole("button", { name: "提交并等待批准" }).click();
  await expect(jobs.getByText("等待所有者批准", { exact: true })).toBeVisible();
  await scan(page, info, "批次详情（等待批准）");

  await jobs.getByRole("button", { name: "批准并排队" }).click();
  const refresh = jobs.getByRole("button", { name: "刷新当前批次" });
  await expect.poll(async () => {
    await refresh.click();
    return jobs.getByText("执行完成", { exact: true }).count();
  }, { timeout: 20_000 }).toBe(1);
  await scan(page, info, "批次详情（执行完成）");

  await jobs.getByRole("button", { name: "查看单题运行报告" }).click();
  await expect(jobs.getByRole("region", { name: "单题运行报告" })).toBeVisible();
  await scan(page, info, "单次运行报告");

  await page.getByRole("button", { name: "返回评测列表" }).click();
  await expect(page.getByRole("region", { name: "评测列表" })).toContainText("选择对比");
  await scan(page, info, "评测列表");

  // 排行榜带上真实榜单：只报告项在收藏/展开后的表格里可能出现新的命中元素。
  await nav.getByRole("button", { name: "排行榜" }).click();
  await leaderboard.getByLabel("数据集 ID").fill(FROZEN.dataset);
  await leaderboard.getByLabel("数据集 revision").fill(FROZEN.revision);
  await leaderboard.getByLabel("数据集 split").fill(FROZEN.split);
  await leaderboard.getByLabel("代码仓库").fill(FROZEN.repo);
  await leaderboard.getByRole("button", { name: "查询排行榜" }).click();
  await expect(leaderboard).toContainText("并列第");
  await scan(page, info, "排行榜（含榜单）");
  // 悬停态单独扫描一次：这是唯一已实测到的对比度命中（表单主按钮），
  // 显式写进用例，证据每次都随套件产出，而不是靠"某次鼠标刚好停在那里"。
  await scan(page, info, "排行榜查询按钮（悬停态）",
    leaderboard.getByRole("button", { name: "查询排行榜" }));

  // 对比报告：第二个批次让矩阵有两列。
  const second = await openWizard(page);
  await reviewSelection(second, ["example__repo-2"]);
  await second.getByRole("button", { name: "提交并等待批准" }).click();
  await expect(second.getByText("等待所有者批准", { exact: true })).toBeVisible();
  await nav.getByRole("button", { name: "评测", exact: true }).click();
  const checks = page.getByLabel("选择对比");
  await expect(checks).toHaveCount(2);
  await checks.nth(0).check();
  await checks.nth(1).check();
  await page.getByRole("button", { name: /对比所选/ }).click();
  const workspace = page.getByRole("region", { name: "对比报告工作区" });
  await workspace.getByRole("button", { name: /生成对比/ }).click();
  await expect(workspace.getByRole("region", { name: "题目配置对比矩阵" }))
    .toBeVisible();
  await scan(page, info, "对比报告（含矩阵）");
});
