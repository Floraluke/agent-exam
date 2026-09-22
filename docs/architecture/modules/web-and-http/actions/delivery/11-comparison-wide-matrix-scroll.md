# 行动：多列矩阵横向滚动缺口——定位根因并补回回归用例

> 状态：**已完成**（2026-09-22）。本行动收口 `progress.md` 里挂了一轮的"对比矩阵在**多列**量级下的横向滚动手感"缺口。
>
> 放在 `delivery/` 而不是 `actions/` 根目录：根目录正好卡在"每层不超过 8 个文件"的上限，而这条缺口不挂在任何未完成任务上（任务 03 已合并收口）。

## 1. 情况说明

**缺口原文**（`progress.md` 的"B 可自行收口的已知缺口"）：曾写过 12 列的宽矩阵用例，断言容器真的横向滚动，**单独通过但全量 suite 里不稳定**（勾选框计数竞态、矩阵表未渲染两种失败模式），按"不稳定测试比没有测试更糟"撤掉。

**本轮结论（与原来的描述不同，请以本条为准）**：缺的不是"滚动没被覆盖"，而是两点——

1. `jobs/comparison.spec.ts` 的 390/360 用例**已经**断言了容器 `overflow-x: auto` 与页面不溢出，但它只有 **2 列**，宽表是否真的会超出容器、超出后是否真的滚得动，**没有被验证**。这是真正缺的断言。
2. 旧版不稳的根因是**两条**，不是"断言写得不对"：
   - **测量早于渲染**：在矩阵渲染完成前读几何，于是读到空表或还没撑开的表（对应"矩阵表未渲染"那类失败）。
   - **与兄弟用例共享后端造成的状态耦合**：造 12 个批次是**状态变更性**造数，而仓库的 runner（`tests/run-browser-tests.mjs`）**对每个 spec 文件才起一次干净后端**。把这条用例塞进 `jobs/comparison.spec.ts` 会污染同文件其他用例看到的批次集合——本轮实测复现：同文件 6 条里 **3 条失败**（包括两个本来合规的既有用例）。所谓"勾选框计数竞态成 0"，真相是**它读到的列表已被造数/其他用例改动**，不是勾选框本身的竞态。

## 2. 实施措施

1. **独立成文件**：`apps/web/tests/reporting/comparison-wide-scroll.spec.ts`（一个文件一份干净后端，与 `jobs/wizard-scale.spec.ts`、`jobs/interruption-recovery.spec.ts` 同形）。文件头写明"独立成文件是刻意的"及其理由，防止后人合并回去。
2. **等状态而不是等计数**：等 `.job-row` 第一行可见 → 再勾选；等 `.comparison-table thead th` 列数到位 → **再**量几何。
3. **去掉隐式耦合**：不假设"全库恰好 12 个批次"，按实际行数取 `min(count, 12)`，列数断言也随之用 `wanted + 1`。
4. **三层断言**：① 容器 `scrollWidth > clientWidth`（真的超出）；② `scrollLeft` 赋值后真的改变（真的滚得动，而不只是 CSS 属性写着 `auto`）；③ 页面本身 `documentElement.scrollWidth <= clientWidth`（不被撑破）。
5. 截图留存：`runtime/tests/03-comparison-wide-many-columns-390.png`。

## 3. 实际改动的文件树

| 路径 | 改动 |
|---|---|
| `apps/web/tests/reporting/comparison-wide-scroll.spec.ts` | 新增：多列矩阵的横向滚动回归（本行动唯一代码改动） |
| `docs/architecture/modules/web-and-http/progress.md` | 缺口行由"⬜ 缺口保留"改为已关闭，并写明**根因与本轮更正** |
| `docs/architecture/modules/web-and-http/ARCHITECTURE.md` | "待完成"里移除该缺口 |
| `docs/architecture/modules/web-and-http/actions/delivery/11-comparison-wide-matrix-scroll.md` | 本文件（新增） |

## 4. 自验证方式

```bash
cd apps/web
AGENTEXAM_USE_SYSTEM_CHROME=1 npx playwright test reporting/comparison-wide-scroll.spec.ts --repeat-each=3
AGENTEXAM_USE_SYSTEM_CHROME=1 npm run test:e2e     # 全量，仓库的判定标准
```

**成功标准**：重复跑稳定通过；**且必须在全量里通过**（沿用既有纪律：单独过、全量挂不算）。

## 5. 自验证情况

| 检查 | 实际输出 |
|---|---|
| 重复 3 次（单文件） | `3 passed (21.0s)`，每条 3.0–3.3s |
| **全量** | **退出码 0**，23 个 spec 全绿（22 个既有 + 本行动新增的 1 个）；运行器遇首个失败即以非零码中止，故 0 即全绿 |
| 反向验证（把用例放进 `jobs/comparison.spec.ts` 跑） | `6 failed / 6 passed`，其中 3 条失败属于**同文件的既有用例**——这条反证直接确认了"共享后端耦合"是旧版不稳的根因之一 |

## 6. 未验证 / 局限

- 只在系统 Chrome 无头下验证；未在真机触屏上试手感（"滚动手感"这类主观项不在断言范围内）。
- 断言的是**机制**（超出、可滚、不撑破），不是"好不好滚"；触控板/惯性滚动的手感无法用这条用例守护。
- 未覆盖 20 列上限（§10.4 的一次最多 20 个批次）：本用例用 12 列，已足以让容器超出；上限本身由 HTTP 层的 `COMPARISON_LIMIT_EXCEEDED` 与既有用例覆盖，不在此重复。
