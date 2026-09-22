# 子行动 c：对比报告 UI —— 逐控件契约表

> 状态：**已完成并合入 `main`**（2026-09-21）。契约、实现、手机布局、证据钻取与回归均已收口；当前任务状态为 `ready-for-human`，历史分支不再作为接续入口。
>
> 契约权威：[`HTTP_API.md`](../../../../interfaces/HTTP_API.md) §10.4（`main` 现行版）；逐控件契约门槛见[实现地图 2.1 节](../../../../../.scratch/ui-catalog-providers/implementation-map.md)；任务 03 总览见[总行动](03-report-catalog.md)。
>
> 本表只描述**要接线的控件**；「无后端请求」只允许改变可见状态、URL 或向导步骤，且必须由浏览器测试断言不产生写请求。

## 1. 依赖的现存事实（2026-09-21 已核实）

- 后端 `GET /api/v1/reports/comparisons` 已在 `main` 注册并稳定：五档 `outcome`、`missing` 的 `null` 语义、`decided`/`total` 整数、跨仓库同名题隔离、UUID 规范化、20 个 Job 上限。
- Web 端**尚缺**：`job-client.ts` 没有 `comparisons` 方法；没有矩阵响应形状校验器；`features/jobs/reporting/` 目录不存在；`workbench/shell.tsx` 的 `View` 枚举没有 `reports`。
- Web 端**已有可复用**：`jobs()` 列表（含 `status`/游标）、`jobDetail()`、`runReport()`、`jobReport()`、`runArtifacts()`、`runTrajectory()`；单次报告页 `report.tsx`、证据页 `evidence.tsx`；`batch-report.tsx` 的四档文案（缺 `missing` 档）。
- 五档中文文案（新增 `missing`，其余沿用 batch-report 口径）：`resolved`=已解决、`unresolved`=未解决、`infrastructure_error`=基础设施错误、`incomplete`=未完成、`missing`=缺失。

## 2. 逐控件契约表

### 2.1 对比报告视图（`view=reports`）

| 页面与控件 | 前端处理 / URL | HTTP Interface | 后端与权限 / 完成后状态 | 验证 |
|---|---|---|---|---|
| 评测列表：批次勾选框 | `view=jobs` 每行新增勾选框（不影响原行点击进详情）；已勾选集合本地保存；20 个封顶后其余禁用；跨页勾选保留 | **无后端请求** | 无身份变化；纯选择状态 | 勾选/取消、跨翻页保留、20 封顶、协作者列表可见范围 |
| 评测列表：`对比所选` | 至少 1 项才可用；点击写入所选列表并跳 `view=reports`（清旧 `job`） | **无后端请求** | 无 | 0 项禁用、跳转后侧栏高亮 reports、浏览器断言零写请求 |
| 侧栏：「对比报告」 | 侧栏新增项；点击写 `view=reports` 并清空旧 `job`；移动菜单同项 | **无后端请求** | 无身份变化；任意已登录角色可见该项 | 桌面/手机导航、URL 刷新恢复 `view=reports`、浏览器断言零写请求 |
| 对比页进入（尚无选择） | 显示空态说明与批次选择控件，不自动发起对比请求 | **无** | 无后端请求 | 空态渲染、无网络活动 |
| 批次选择（多选，1–20） | **已定：评测列表勾选带入**——`view=jobs` 每行加勾选框；勾选后点「对比所选」写入所选列表并跳 `view=reports`。对比页内可逐项移除；追加须回列表再勾。所选列表**本地保存**（沿用三步向导"未提交选择只在本机"口径），不进 URL、刷新后回空态 | 选择来源为现有 `GET /api/v1/jobs`；带入本身**无新请求** | 可见范围与列表相同；collaborator 只能勾到自己的 Job | 边界：0 个禁用、20 个封顶、重复勾选去重、协作者范围、刷新后清空不残留他人选择 |
| `应用对比` / `刷新矩阵` | 拼 `job_ids` 为逗号分隔列表；请求期间锁按钮；成功后用响应整体替换本地矩阵，不拼接 | `GET /api/v1/reports/comparisons?job_ids=<uuid>,...` | Reporting；只读；任一不可见 Job 使整体 `404`；响应 `no-store` | 正常矩阵、空选择禁用、重复点击锁、404/401/503 呈现、失败后保留旧矩阵或清空（见 4.2） |
| 矩阵列头 | 每列显示 `agent_display_name`；列序 = 请求 `job_ids` 顺序；列头可点击进 Job 详情（见下） | 数据来自上述响应 `columns[]` | 同源显示；未知/畸形列形状失败关闭 | 多列渲染、列序、畸形响应不渲染假数据 |
| 矩阵行与单元格 | 行按 `(repo, task_instance_id)` 展示，同仓库同题合并标识；单元格按五档文案着色；`missing` 且 `run_id=null` 显示「无运行」，`missing` 且 `run_id` 非空显示「报告缺失」；`resolved`/`report_path` 为 `null` 时不渲染为 0 或假链接 | 数据来自 `rows[].cells[]` | 同源显示；`missing` 语义与 §10.4 一致 | 五档各至少一格、两种 missing 文案、null 不冒充 0、不同仓库同名题不合并 |
| 列汇总行 | 每列显示五档计数与 `decided/total` 比值（如 `6/6`）；**不生成**字符串覆盖率字段 | 数据来自 `totals[]` | 同源显示；v1 不显示计费或 Judge 分 | 汇总数与单元格一致、分母含 missing |
| 单元格钻取 | 有 `run_id` 的单元格可点，进入既有单次运行报告（沿用 02 的详情→报告动线，URL 带 `view=jobs&job=...` 或既有报告 URL 机制）；`missing` 且 `run_id=null` 不可点 | `GET /api/v1/reports/runs/{run_id}`（既有 `runReport`） | Reporting；与来源 Job 可见范围相同；无权/不存在收敛 404 | 钻取成功、missing 无 run_id 不可点、钻取回来矩阵不丢 |
| 列头钻取 | 点击列头进该 Job 详情，查看冻结配置/限制差异（计划第 5 节第 3 点） | `GET /api/v1/jobs/{job_id}`（既有 `jobDetail`） | Job Repository；可见范围同列表 | 列头进详情、返回保留选择 |
| 安全证据 | 复用既有证据页（制品索引/轨迹/下载），不在矩阵页内复制按钮 | `GET /api/v1/runs/{run_id}/artifacts`、`/trajectory`、`GET /api/v1/artifacts/{artifact_id}/content`（既有） | Artifact route；仅公开白名单类型 | 沿用既有 evidence 回归，不在本页新增证据入口 |

### 2.2 与目录/成员的关系（任务 03 的动线，但**不新增控件**）

| 页面与控件 | 前端处理 / URL | HTTP Interface | 说明 | 验证 |
|---|---|---|---|---|
| 任务目录、配置目录、成员管理 | 沿用现有 `view=tasks` / `view=agents` / `view=members` 独立导航 | 既有接口，无新增 | 任务 03 只复用既有入口，不新增 Key 页面、不复制按钮 | 既有 catalog/membership 回归，本轮不新增用例 |

## 3. 预估修改文件（候选；写代码前须按本表逐行落实）

```text
apps/web/src/features/workbench/shell.tsx        # 修改：View 枚举加 "reports"、侧栏/移动菜单加「对比报告」项
apps/web/src/features/jobs/listing/view.tsx       # 修改：每行勾选框 + 「对比所选」（跨页保留勾选集合）
apps/web/src/features/jobs/reporting/
  comparison.tsx                                 # 新增：矩阵视图（列头、行、单元格、汇总、空态与错误态）
apps/web/src/lib/reporting/
  comparison-shapes.ts                           # 新增：columns/rows/totals/cells 运行时形状校验（未知失败关闭）
apps/web/src/lib/job-client.ts                   # 修改：新增 comparisons(ids) 调用
apps/web/tests/jobs/comparison.spec.ts           # 新增：本表 2.1 节的浏览器用例
```

`features/jobs/reporting/` 是[实现地图](../../../../../.scratch/ui-catalog-providers/implementation-map.md)已标注的候选目录；`reporting/` 下新增 1 个组件文件，不超文件数指标。后端与 `HTTP_API.md` **不修改**（契约已由 `main` 的 `7553ce0` 冻结）。

## 4. 已定与草案默认

1. ✅ 批次多选交互：列表勾选带入（2026-09-21 确认）。
2. ✅ 限制/工具/网络差异：列头进 Job 详情查看，矩阵页不额外请求、不动后端（2026-09-21 确认）。
3. 失败后矩阵状态：**草案默认**保留旧矩阵并提示失败 + 「重试」，不清空回空态。
4. 列汇总行呈现：**草案默认**只显示 `decided/total` 比值，五档细分靠单元格颜色承载。

## 5. 实施措施

按"一个失败用例→最小实现→通过→回归"推进，不先把所有层改完再补测试。

1. **接口层**：`lib/contracts.ts` 的 `ApiErrorCode` 与 `lib/api-client.ts` 的文案表补 `EMPTY_COMPARISON_SELECTION`、`COMPARISON_LIMIT_EXCEEDED`（后端 `service.compare` 会抛这两个码；不加会被前端收敛为 `UNAVAILABLE`，丢失可解释错误）。
2. **形状层**：新增 `lib/reporting/comparison-shapes.ts`，按 `report-shapes.ts` 的 helper 写法校验 `columns/rows/cells/totals`；五档取值、`missing` 的 `null` 语义、`decided+missing=total` 的算术一致性都在解析期失败关闭。五档类型与中文文案定义在本模块（**不改** §10.1 的 `BatchOutcome` 四档）。
3. **调用层**：`lib/job-client.ts` 加 `comparisons(ids)`，GET `reports/comparisons?job_ids=...`，与既有只读调用同形。
4. **矩阵视图**：新增 `features/jobs/reporting/comparison.tsx`（列头/行/单元格/汇总/空态/错误态/钻取）。单元格钻取复用 `runReport`，列头钻取复用 `jobDetail` 的既有动线。失败保留旧矩阵并提示 + 「重试」。
5. **入口与多选**：`workbench/shell.tsx` 加 `reports` 视图与侧栏项，并在壳内持有 `comparisonIds`（列表与矩阵共用，刷新即清空）；`jobs/listing/view.tsx` 加勾选框与「对比所选」。
6. **验证**：`npm run typecheck`、`npm run build`，并补 `tests/jobs/comparison.spec.ts` 浏览器用例（覆盖契约表 2.1 节的验证列）。

## 6. 自验证情况

2026-09-21 在本机执行并检查输出（命令在 `apps/web` 下）：

- `npm run typecheck`（`tsc --noEmit`）→ **退出码 0**，零类型错误。
- `npm run build`（`next build`）→ **退出码 0**，`Compiled successfully in 29.2s`，静态页生成 4/4。
- `npm run test:e2e -- comparison.spec.ts` → **3 passed**：
  - `owner compares two batches and reads the matrix without inventing results`：两列矩阵；列头是配置显示名且可点进批次详情；两批各一格有结果、一格缺失；缺失格显示「无运行」且**不提供钻取按钮**（`getByRole("button")` 计数为 0）；汇总行含 `decided/total` 比值；页面不出现 `coverage` 文本；单元格钻取进入既有单次运行报告并可返回矩阵。
  - `comparison selection stays opt-in and resets on reload`：0 项时「对比所选」禁用，勾选 1 项后可用；刷新后归零且 `job_ids` 不写进 URL。
  - `390 and 360 contain the matrix without page overflow`：手机菜单进入列表并勾选；断言矩阵容器 `overflow-x: auto`（页面本身是 `body { overflow-x: hidden }`，容器不接管宽表会被**裁掉**而非可滚动）且页面在 390/360 下均无横向溢出；两档各留一张截图到 `runtime/tests/03-comparison-mobile-{390,360}.png`（`runtime/` 被忽略）。
- `npm run test:e2e`（**全量 18 个 spec**）→ **退出码 0，全绿**；既有身份、目录、Job、报告、证据、制品保留、排行榜与工作台动线**无回归**。

**本轮由验证抓出并修复的缺陷（如实记录）**：首版矩阵只加了 `className="comparison-matrix"`，**没有对应的 CSS 规则**。由于 `body { overflow-x: hidden }`，宽表在手机上会被静默裁掉。补 `.comparison-matrix { overflow-x: auto }` + 五档着色后，由上面的手机用例断言容器的 `overflow-x` 与页面无溢出。这条也是"契约表写了移动端要求、但实现漏掉"的实例——契约行本身没有保证实现。

**未覆盖（如实记录）**：

环境前置（本机一次性，均不改仓库）：`npm ci --ignore-scripts`；按[依赖总表](../../../../dependencies/DEPENDENCIES.md)第 119 行生成自签证书到 `runtime/tests/`（`runtime/` 已被 `.gitignore:55` 命中；`-subj /CN=...` 在 Git Bash 下需 `MSYS_NO_PATHCONV=1`，否则参数被路径转换破坏）；用 `AGENTEXAM_USE_SYSTEM_CHROME=1` 复用系统 Chrome，避免下载 Playwright 浏览器。

**未覆盖（如实记录）**：

- 后端的两条 400（空选择、超过 20）**未在浏览器用例里断言**：前端在 0 项时禁用按钮、在 20 项时禁用勾选框，所以正常操作打不到这两条错误；服务端边界由后端契约测试覆盖。
- **多列量级的横向滚动仍属缺口（2026-09-21 保留）**：曾写过一个宽矩阵用例（经接口批量建 12 个批次、在 390px 下断言容器 `scrollWidth > clientWidth`），**单独跑能通过，但在全量 suite 里不稳定**——先后出现两种失败：列表异步加载导致勾选框计数为 0、矩阵表未渲染出来。按"不稳定的测试比没有测试更糟"（会随机把全量打红、挡住所有人）**已撤掉**。补测前需先查清它与全量长时运行的相互影响（同轮全量还出现过一次 `page.reload: net::ERR_TOO_MANY_RETRIES` 的 dev server 重载错误，怀疑相关）。`runtime/tests/03-comparison-wide-390.png` 仍在该用例单独通过时留下的，可作参考证据但不是通过记录。
- `data-outcome` 是为可测性加的 DOM 语义属性，属实现细节，**未写进 `HTTP_API.md`**。
- 矩阵页的手机截图在 `runtime/tests/`（gitignored），**没有进仓库**；需要长期证据时另行安排。

## 7. 明确不做（v1）

- 不新增端点、不修改 `HTTP_API.md`；不改后端与 `report_comparisons.py`。
- 不实现每列指标汇总（用量/费用/耗时）——§10.4 明确不含计费，惰性取用留待后续（**2026-09-21 已出静态原型，见第 8 节**）。
- 不在矩阵页内复制证据下载按钮；下载仍走既有证据页。
- 不引入 Judge 分或"公平排名"提示之外的排序（计划第 5 节与 Q12）。

## 8. 后续增量原型：每列用量 / 费用 / 耗时（2026-09-21）

第 4 节的契约表当时把"每列指标汇总（用量/费用/耗时）"明确标为 **v1 不做、留作增量**。A 指示"按 HTTP 接口文档出 HTML 原型，满意后再落地"，因此先做**静态原型**，本轮**不写产品代码**。

- **位置（本地、被 Git 忽略，与任务 01 的"原型不提交成生产功能"一致）**：`runtime/prototype/ui-comparison-metrics-20260921/`——`index.html`、`styles.css`、`scripts/{fixtures.js,views.js}`；每个文件 ≤200 行，全部合成数据，页面**不发起任何网络请求**。
- **截图证据**：`runtime/tests/prototype-metrics-desktop-1440.png`、`runtime/tests/prototype-metrics-mobile-390.png`。
- **原型要确认的五条规则**（全部来自既有契约与计划，不是新发明）：① 只在所有组成值可用时才称"总量"，否则显示"部分"并给覆盖数；② **未知不等于 0**（`value=null` 显示"未知"，真正的 0 才显示 0）；③ 耗时是 **Run 用时汇总**，不是整批墙钟；④ 指标**按需取得**，不打开页面就为每个格子发请求；⑤ 覆盖数来自服务端，前端不自己数。
- **五个可一键切换的演示场景**：全部 Run 可用 / 部分 Run 缺用量（显示"部分 · 覆盖 2/3"）/ 费用未知 / 零用量 / 该列没有 Run（整块"无可用 Run"，不显示 0）。
- **形状依据**：每列指标沿用 §10.3 的 `{value, coverage}`；矩阵与五档沿用 §10.4 与 `comparison-shapes.ts` 的既有口径。
- **本轮验证**：用一次性 Playwright 配置（原型是 `file://`，不需要 Next/FastAPI）实跑，断言五个场景的文案与"点开才出现明细"；390px 下页面无横向溢出——首轮曾溢出，根因是 **grid 子项默认 `min-width: auto` 被宽表的 min-content 撑开**，加 `min-width: 0` 修复。一次性 spec 与配置文件**已删除**，不进套件。

**落地路径已由 §10.4 给出（2026-09-21 复核后更正）**：本行原先写"§10.4 不返回这些指标、落地前必须先改契约"，**该判断偏悲观且有误导**。复核 `main` 的 §10.4 原文：指标**不靠对比响应新增字段**，而是矩阵成功后以**最多 3 个并发**读取所选列的 `GET /jobs/{job_id}` 冻结快照；用量**须由用户明确点击后**才以最多 3 个并发读取有 `report_path` 的 `GET /reports/runs/{run_id}`；缺失单元格与任一 Run 指标为 `null` 都保持未知，**只有每个组成单元格都有值才显示"总量"，否则显示"部分"或"未知"**。因此本原型的五条规则与 §10.4 **一致**，落地不需要改契约或加字段；落地时前端只需按既有端点取值并按上述口径聚合。

**待确认（给 A / 用户）**：① "部分 2/3"这种覆盖写法是否清楚；② 零与未知的视觉区分是否够（零＝"零"标签＋淡绿底，未知＝灰底灰字）；③ 是否要把整批墙钟也显示出来对比（当前刻意只显示 Run 用时汇总，避免与"整批等待"混淆）。
