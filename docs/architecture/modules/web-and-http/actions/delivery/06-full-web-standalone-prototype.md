# 行动：所有前端的脱离版 HTML 原型（**已被取代**）

> 状态：**已被取代**（2026-09-21 同日）。**本文件描述的原型已被 A 否决并删除**——A 指出"刚做的页面很差，要根据拉取到的 web 文件夹里现有的前端进行修改"：这份记录做的是**自造外观**的仿制原型，方向错误。
>
> 取代它的是[用真实 apps/web 组件做脱离版单文件](08-real-web-detached-build.md)：不再仿造外观，直接把 `apps/web` 的真实组件与真实 `globals.css` 打成脱离版，数据改为**录制仓库自带合成后端的真实响应**，且不改动 `apps/web` 任何文件。
>
> 本文件保留作历史记录（其中"探针只断言字数"的做法正是漏掉空洞页的原因，已在 08 中改为内容级断言），**不得再作为当前交付说明引用**。

## 原始记录（已失效）

A 要求"把整个前端做成脱离服务器的 HTML 原型"的创建、接线、实测与打包。原型本身**不进入仓库**（`runtime/` 已被 `.gitignore` 忽略）。

## 1. 情况说明

**来源**：A（项目负责人）指示——"pull 项目后 web 是你要修改的，让你的 AI 把里面的前端代码弄成一个脱离的 HTML，根据 HTTP API 接口文档修改，如果没有拉取最新代码先拉取"。B 追问范围，A 答复"**所有前端**"。

**范围**：把 `apps/web` 的全部页面面（8 个视图）做成**双击即可打开、不连接任何服务**的合成数据原型，交互与字段按 [`HTTP_API.md`](../../../../../interfaces/HTTP_API.md) 对齐，供 A 看动线并提修改意见。

**已确认的事实**：

- 代码已是最新 `main`（`ae5e40b`）；`apps/web` 的真实实现仍是权威，本原型只是它的可视化提案，**不是**第二套前端。
- 本仓库既有的同类先例：`runtime/prototype/ui-comparison-metrics-20260921/`（任务 03 的"每列用量/费用/耗时"指标原型，已交付 A）。本行动是其超集。

**明确不做**：

- 不改 `apps/web` 的任何真实代码，不新增 HTTP 端点，不改任何其他 Module 的文件。
- 不连接任何真实服务；不调用模型；不读数据库。
- 登录页与"邀请加入"入口页**未做**，用侧栏的"切换为协作者视角"代替入口与角色差异展示（真实前端是一个独立的全屏入口，脱离版没有会话概念）。

**已知并有意的偏差**（页面内已就地标注，不假装与文档一致）：

| 偏差 | 说明 |
|---|---|
| 配置目录的"登记新配置"表单用了自由字段 | 真实接口 `POST /api/v1/agent-configurations` 只接受服务端固定 `preset_id`（§6.2）。表单上方已写明"不接受下面这些自由字段"，保留表单只为展示信息密度 |
| 成员列表保留了 owner 行 | 真实 `GET /api/v1/members` 不含 owner（§3.3）。保留是为了对照演示"禁止停用 owner → 403"这条规则，页面已注明 |
| 排行榜的过程指标覆盖档位 | fixture 的 `LEADERBOARD[].processes` 是扁平数字，没有 §10.3 的 `{value, coverage}` 逐字段覆盖数，页面用 `selected_runs/total_tasks` 近似并标注为"原型口径" |
| 多数 Run 点进去只有部分报告 | 只有 `run-13`/`run-16` 造了完整报告；其余显示真实存在的字段（状态、任务、指标），其余保持未知，**不用假数据填充** |

## 2. 实施措施

1. 读 `apps/web` 的真实实现与 `HTTP_API.md` 相关小节，确定 8 个视图与字段来源。
2. 搭外壳：`ui-kit.js` 抽公共元素工厂 → `fixtures.js` 合成数据 → `router.js` 会话壳（导航、`view/job/run` 状态、角色切换、移动菜单）。
3. 逐视图实现，**每步都在浏览器里渲染验证过再往下**：home → jobs（列表 + 详情 + 生命周期动作）→ wizard（三步向导）→ reports（对比矩阵）→ run-report（单次报告与证据）→ catalog（任务/配置目录）→ admin（排行榜/成员）。
4. 写一次性探针 `runtime/tests/zz-full-web-probe.mjs`（8 视图 × 桌面/手机 + 动线点击 + 角色边界），用系统 Chrome 跑。
5. 按探针结果修缺陷（见第 5 节）。
6. 用 `runtime/tests/build-standalone.mjs` 打包成单文件 `standalone-发给A.html`，**用同一支探针再验一遍**。

**完成标准**：8 个视图在 1440 与 390 两个宽度下都无脚本报错、无横向溢出；关键动线可点通；单文件版与多文件版结果一致。

## 3. 实际文件树

### 3.1 原型（`runtime/prototype/ui-full-web-20260921/`，**gitignored、不入库**）

| 路径 | 行数 | 职责 |
|---|---|---|
| `index.html` | 47 | 外壳：侧栏、移动端菜单、角色切换、`#view-mount`、按序引入脚本 |
| `styles.css` | 89 | 产品配色、面板/表格/胶囊/向导步骤、移动端抽屉、`.matrix-scroll` 横向滚动 |
| `scripts/ui-kit.js` | 137 | 共享元素工厂（`el`/`button`/`pill`/`heading`/`panel`/`kvGrid`/`select`/格式化函数） |
| `scripts/fixtures.js` | 185 | 核心合成数据：状态字典、6 道 mypy 题、2 个配置、提交选项、4 个 Job、2 份完整 Run 报告、轨迹、排行榜、邀请与成员 |
| `scripts/fixtures-comparison.js` | 58 | 对比响应（`{columns, rows, totals}`）与逐 Run 过程指标；**由 `fixtures.js` 派生**，必须在它之后加载 |
| `scripts/router.js` | 107 | 会话壳：导航、`view/job/run` 状态、`file://` 下的 URL 降级、未实现视图占位 |
| `scripts/views/home.js` | 95 | 角色首页：可见范围统计、owner 待批准分组、最近批次 |
| `scripts/views/jobs.js` | 150 | 评测列表（筛选 + 游标翻页）与详情（批次概要、决定、失败、生命周期动作、Run 列表） |
| `scripts/views/wizard.js` | 199 | 三步提交向导：预设与题数 → 配置与轨道 → 确认与幂等键说明 |
| `scripts/views/reports.js` | 166 | 对比矩阵：列选择、五档单元格、`decided/total` 汇总、**每列用量/费用/耗时与覆盖档** |
| `scripts/views/run-report.js` | 176 | 单次 Run 报告与证据：确定性结果、过程指标、制品元数据与下载规则、公开轨迹；缺数据时走"部分报告"分支 |
| `scripts/views/catalog.js` | 172 | 任务目录（题面预览）与配置目录（指纹、禁用、登记演示） |
| `scripts/views/admin.js` | 197 | 排行榜（含过程指标覆盖档）与成员/邀请管理 |
| `standalone-发给A.html` | 1802 | **交付物**：内联全部 11 个脚本与样式，88.4 KB，双击即开 |

**设计模式角色**：`ui-kit.js` 是**工厂 + 模板方法**的构件层（统一构造 DOM，各视图只声明内容）；`router.js` 是**注册表 + 策略**（每个视图文件把渲染函数注册进 `window.VIEW_RENDERERS`，路由器按 `state.view` 选择策略）；`fixtures-comparison.js` 是**派生数据源**，避免矩阵与批次列表两份数据各说各话。

### 3.2 验证工具（`runtime/tests/`，gitignored）

| 路径 | 职责 |
|---|---|
| `zz-full-web-probe.mjs` | 一次性验收探针：8 视图 × 2 宽度、脚本报错、横向溢出与越界元素、动线点击、角色边界、截图 |
| `build-standalone.mjs` | 把多文件原型打包成单文件；校验内联后不再有外部引用 |
| `prototype-fullweb-*.png`（5 张） | 证据截图：首页、矩阵指标（1440/390）、手机评测、协作者视角 |

### 3.3 本行动改动的仓库文档

| 路径 | 改动 |
|---|---|
| `docs/architecture/modules/web-and-http/actions/delivery/06-full-web-standalone-prototype.md` | 本文件（新增） |
| `docs/architecture/modules/web-and-http/progress.md` | 新增"所有前端的脱离版原型"小节与指针 |

## 4. 自验证方式

```bash
# 多文件版
node runtime/tests/zz-full-web-probe.mjs
# 单文件交付物
node runtime/tests/zz-full-web-probe.mjs "file:///D:/agent-exam/runtime/prototype/ui-full-web-20260921/standalone-%E5%8F%91%E7%BB%99A.html"
```

**成功标准**：两次都输出"全部检查通过"，且不得出现 `pageerror` / `console error` / `requestfailed`。

## 5. 自验证情况

**实跑结果（2026-09-21，系统 Chrome，无头）**：两个版本**逐项一致地全部通过**。

```text
8 视图 × {1440, 390}：标题符合、无脚本报错、无请求失败、无横向溢出
jobs 详情 job-1（6 个 Run 单元格）→ 单次报告 run-1（5 个字段，走"部分报告"分支）
对比矩阵：指标默认隐藏（0 格）→ 点击后 9 格；总量 3 / 部分 5 / 未知 1
矩阵单元格下钻 → run-13（3 张表，含制品区块 1）
角色切换：导航 8 → 7 项，成员管理 0，批准按钮 0，"共 2 个批次（第 1 / 1 页）"
全部检查通过（无脚本报错、无横向溢出、关键动线可点）
```

**过程中由探针抓出并修掉的真实缺陷**：

| # | 缺陷 | 根因 | 处理 |
|---|---|---|---|
| 1 | `file://` 下点导航会抛 `SecurityError` | 带 URL 参数的 `history.pushState` 在 `origin` 为 `null` 时被禁止——而交付物正是双击打开的本地文件 | `router.js` 检测 `file:` 协议时跳过 URL 同步，改用内存状态；URL 不跟着变，按钮照常工作 |
| 2 | 配置目录在 390px 横向溢出 `459 > 390` | 表单控件（`input`/`select`）的固有宽度把网格列的 `min-width: auto` 撑开 | `label.field` 与 `select`/`input[type=text]` 加 `min-width: 0` 与 `max-width: 100%` |
| 3 | 矩阵 `totals` 与矩阵行自相矛盾：`job-4` 只有 5 个 Run 却被算成"总量" | fixture 的 `totals` 从 `job.runs` 数，而矩阵行按 6 道题生成，第 6 格是 `missing` | 改为**从矩阵单元格本身数出**总计，保证 `rows` 与 `totals` 永不矛盾（修后 `job-4` 正确显示"部分 5/6"，三档齐全） |
| 4 | 多数 Run 点进去是空页 | 只有两个 Run 造了完整报告 | 新增"部分报告"分支：显示该 Run 确实存在的状态与指标，其余显式保持未知 |
| 5 | 邀请 fixture 写 7 天，文档写 24 小时（第 151 行） | fixture 与权威文档冲突 | 按文档改为 24 小时 |

**行数指标**：`fixtures.js` 一度涨到 241 行超指标，已把对比/指标数据拆成 `fixtures-comparison.js`；现**全部文件 ≤ 200 行**（最大 199），`scripts/` 4 个文件、`scripts/views/` 7 个文件，均 ≤ 8。

**未验证 / 局限（如实记录）**：

- 只有**系统 Chrome 无头**一种引擎；未在 Firefox/Safari/真机触屏上验证。
- 探针只覆盖 8 个视图的主路径与 5 条动线；**未**逐控件遍历（例如向导的越界分支只有子代理在 DOM 桩里验过，未在浏览器里逐档点过）。
- 未做无障碍审计（对比度、读屏、键盘完整可达性）。
- 原型不连服务，因此**所有"提交/批准/取消/生成邀请"都是本地反馈文字**，不代表真实接口已验证。
- 与真实 `apps/web` 的视觉差异未做像素对照；配色沿用 A 版设计变量的近似值。

## 6. 交付与后续

交付物是 `runtime/prototype/ui-full-web-20260921/standalone-发给A.html`（单文件、88.4 KB），直接发给 A 双击打开即可。A 的反馈属于**产品行为与界面动线**的取舍，按协作规则应回到 [`HTTP_API.md`](../../../../../interfaces/HTTP_API.md) 与 `apps/web` 真实实现上落地，不在原型里定稿。

**待 A 反馈后可能出现的新增项**（现在不做）：登录/加入入口页、三级以上窄屏（360px）复测、真实后端的字段对照。
