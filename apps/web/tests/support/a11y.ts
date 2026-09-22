// 无障碍扫描的共享入口：规则集（wcag2a + wcag2aa）与"必须为零 / 只报告"的分工，
// 与 tests/a11y/baseline.spec.ts 保持一致。基线里的 scan 是私有函数，且额外支持
// 显式传入要悬停的控件；本轮不改它的逻辑，因此这里导出同语义的一份给新增 spec 复用。
import { AxeBuilder } from "@axe-core/playwright";
import { expect } from "@playwright/test";
import type { Page, TestInfo } from "@playwright/test";

type AxeViolations = Awaited<ReturnType<AxeBuilder["analyze"]>>["violations"];
type Violation = AxeViolations[number];

// 只报告、不修：配色与字号由用户决定是否调整。排除范围最小化——这里只列**规则 id**，
// 其余规则照常参与"必须为零"的断言。当前为空：新扫出的对比度命中先报告选择器与实测
// 比值，确有必要时才加条目并写明理由，不整类排除。
const REPORT_ONLY: Record<string, string> = {};

function detail(violation: Violation) {
  return `${violation.id}（${violation.impact}）命中 ${violation.nodes.length} 处：\n` +
    violation.nodes.map((node) => `  ${node.target.join(" ")} :: ` +
      `${node.html.slice(0, 200)}\n    ${node.failureSummary ?? ""}`).join("\n");
}

export async function scan(page: Page, info: TestInfo, view: string) {
  // 默认让指针离开控件再扫描：否则上一次点击留下的 hover 态会参与计算，结论取决于
  // "上一个动作点在哪"。需要悬停态证据的用例应显式说明，而不是靠偶然。
  await page.mouse.move(0, 0);
  // 再等 CSS 过渡跑完：抽屉式主导航在滑动过程中位置与层叠关系还没定稳，axe 会把本来
  // 能判定通过的对比度降级成"需人工复核"。要扫描的是最终状态，不是过渡中的某一帧。
  await page.evaluate(() => Promise.all(
    document.getAnimations()
      .filter((animation) => animation instanceof CSSTransition)
      .map((animation) => animation.finished.catch(() => undefined)),
  ));
  const results = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa"]).analyze();
  const reported = results.violations.filter((item) => item.id in REPORT_ONLY);
  // 每个视图都打印一行覆盖情况：违规、只报告、真正被评估通过的规则数与需人工复核项。
  // 通过数长期为 0 就说明扫描没跑起来，而不是页面变好了。
  console.log(`[扫描·${view}] 必须为零 ${results.violations.length - reported.length}；` +
    `只报告 ${reported.length}；通过 ${results.passes.length}；` +
    `需人工复核 ${results.incomplete.length}`);
  // 需人工复核不是违规，但它是"扫描器没给出结论"的证据，逐条列出规则与命中元素，
  // 免得只能用总数为 1 这种无法复核的说法收尾。
  for (const item of results.incomplete) {
    console.log(`[需人工复核·${view}] ${item.id}（${item.impact}）命中 ` +
      `${item.nodes.length} 处：` +
      item.nodes.map((node) => node.target.join(" ")).join(" | "));
  }
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
