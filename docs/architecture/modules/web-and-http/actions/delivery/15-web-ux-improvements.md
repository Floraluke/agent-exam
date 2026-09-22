# 行动：无障碍自动扫描 + 动作后刷新失败的可见提示 + 排行榜按上下文预填

> 状态：**已完成**（2026-09-22，基于 `main = 4c31c66`）。三件工作**串行**执行并各自单独跑过，最后跑全量。

## 1. 情况说明

**来源**：用户本轮直接下达的三项 Web 改进，前置条件与纪律已给定：

1. **无障碍自动扫描**：当前浏览器套件**零 a11y 断言**，且本机没有其它 a11y 工具链。用户已批准新增开发依赖。
2. **修掉"动作后刷新失败是静默的"**：`apps/web/src/features/jobs/submit.tsx` 的两处 `catch { /* keep error */ }`（第 90、107 行）在**冲突后重读失败**时既不更新页面也不提示，用户会以为操作没生效。用户与 E 都点名要夹具具备"**让下一次响应出错**"的能力。
3. **排行榜按上下文预填**：`apps/web/src/features/leaderboard/view.tsx` 的 5 个输入当前无默认值，而用户刚看过的批次里已带着**冻结的**这些值。此件**会产生一个新控件**，按实现地图第 2.2 节门槛必须**先补契约行**（见 §5）。

**已确认的边界与纪律**（用户给定，不得自行扩张）：

- 浏览器套件必须串行跑，且必须带 `AGENTEXAM_USE_SYSTEM_CHROME=1`（本机没有 Playwright 自带浏览器）。
- **单独过不算过，必须全量 `npm run test:e2e` 退出码 0**。
- 跑测副作用（`next-env.d.ts`、`tsconfig.json`）收尾必须还原；**不许 `git add`/`commit`/`push`**。
- a11y **只修机械性问题**（可访问名、label 关联、landmark/role、`aria-*` 用法、重复 id 等）；**颜色对比度、字号、版式只报告不改**。
- 第三件**只读现有数据、不新增后端接口**。

**开工前核实的事实**（读代码而不是猜）：

| 事实 | 依据 |
|---|---|
| `jobDetail` 的 HTTP 响应里**本就有**冻结的 `dataset_id`/`dataset_revision`/`split`/`repo` | `apps/backend/src/eval_platform/delivery/http/routes/jobs/schemas.py:34-42`（`TaskSnapshotResponse`） |
| 但 Web 的解析器把它们**丢掉了**，`JobDetail.task_snapshots` 只留 `task_id`/`instance_id`/`problem_statement` | `apps/web/src/lib/job-shapes.ts:65-72`、`apps/web/src/lib/contracts.ts:114-116` |
| 单次运行报告**没有**冻结数据集字段 | `routes/jobs/report_schemas.py` 的 `RunReportResponse`（无 dataset/split） |
| 排行榜 HTTP 查询参数与夹具任务的冻结值 | `apps/web/src/lib/leaderboard/client.ts:12-18`；`apps/backend/tests/catalog/conftest.py:32-53`（`synthetic-dataset` / `"a"*40` / `train` / `example/repo`） |
| 夹具已有 `__test__` 控制端点先例，且写请求需可信头 | `apps/backend/tests/identity/browser_server.py:184-237`；`delivery/http/security.py:trusted_write` |

**明确不做**：不改配色/字号/版式；不新增后端业务接口或表；不引入自动查询（预填后仍由用户点"查询排行榜"）；不重构 `submit.tsx` 的整体结构。

## 2. 实施措施

### 2.1 第一件：无障碍自动扫描

1. `apps/web` 新增开发依赖 `@axe-core/playwright`（**锁定 `4.13.0`**，与仓库其它 devDependency 的精确版本风格一致）。
   - **为什么值得多一个依赖**：① 当前套件**零 a11y 断言**，纯人工检查不可回归；② 本机没有其它 a11y 工具链（无 `pa11y`/`lighthouse`/浏览器扩展的脚本接口），Playwright 集成是唯一能进 CI 式回归的路径；③ 该包只是 `axe-core` 的薄封装（`axe-core` 已作为 `eslint-config-next` 的传递依赖存在于 lockfile），新增面很小；④ 用户已批准新增依赖。
2. 新增 `apps/web/tests/a11y/baseline.spec.ts`，对九个可达视图用 `AxeBuilder.withTags(["wcag2a","wcag2aa"])` 扫描：**工作台、评测列表、批次详情、单次运行报告、对比报告（含矩阵）、任务目录、配置目录、排行榜（含查询后的榜单）、成员管理**。
   - 扫描函数把违规分成两桶：**必须为零**的（机械性问题）与**只报告**的（由显式 `REPORT_ONLY` 规则清单声明，逐条写理由）。只报告桶每次扫描都用 `console.log` 打出完整明细（rule id、impact、命中元素、axe 给的对比度数值），便于在套件日志里长期留痕；同时 `testInfo.attach` 附上 JSON（附件只在失败时保留），**不用它掩盖失败**。
3. 修掉机械性问题，**改动小而集中**：只动可访问名、label 关联、landmark/role、`aria-*`、重复 id。凡属对比度/字号/版式的，进 §7 的未修清单交用户决定。
4. 若某条规则属"工具误报/不适用"，用**最小范围**排除（`disableRules` 只列该 id，且在该行写明理由），不整类关闭。

### 2.2 第二件：动作后刷新失败的可见提示

1. **夹具新增控制端点** `POST /__test__/http/fail-next-response`（`apps/backend/tests/identity/browser_server.py`）：
   - 正文 `{"method": "GET", "path_suffix": "…", "status": 503, "code": "DEPENDENCY_UNAVAILABLE"}`，**一次生效、取走即清空**；
   - 用 ASGI 中间件在**进入路由之前**按 `方法 + 路径后缀` 匹配，命中则返回**平台既有稳定错误信封**（复用 `delivery/http/errors.py:error_response` 与 `security.secure_response`，使注入响应与真实错误响应在形状/安全头上不可区分）；
   - **未调用端点时行为必须不变**：队列为空即短路透传。
2. **产品代码**（`apps/web/src/features/jobs/submit.tsx`）：在 `decide` 与 `cancel` 的**动作后重读**失败处给出可见提示"刷新失败，当前显示的可能不是最新状态，请手动刷新。"。
   - 两条路径都要提示：① 写请求成功但重读失败（页面停在旧状态）；② `JOB_STATE_CONFLICT` 后的重读再次失败（今天的静默点）。
   - **保留既有错误文案**（冲突文案仍由 `role="alert"` 呈现，不被覆盖）；**不改成抛出**。
   - 提示用 `role="status"`（**不能用 `role="alert"`**：`tests/jobs.spec.ts:52` 等既有用例对 `alert` 做严格定位，新增 alert 会让它们变成多元素歧义）。
3. **新增浏览器用例** `apps/web/tests/jobs/refresh-failure.spec.ts`（独立成文件，因为它用夹具端点造数据）。

### 2.3 第三件：排行榜按上下文预填

1. **补契约行**（§5，先于代码），再写测试与实现。
2. 前端只读现有响应：把 `JobDetail.task_snapshots` 的 `dataset_id`/`dataset_revision`/`split`/`repo` 接进类型与解析器（`contracts.ts`、`job-shapes.ts`），**后端零改动**。
3. 批次详情（`features/jobs/details.tsx`）新增入口"按此条件查排行榜"：**仅当该批次所有题目快照的冻结条件一致**时显示，`href` 带上 `dataset_id`/`dataset_revision`/`split`/`repo`/`tool_profile_id`；条件不一致时不显示（不把不成立的单一条件写进 URL）。
4. 排行榜视图（`features/leaderboard/view.tsx`）在挂载时读这些参数**预填表单**，**不自动查询**、不改写 URL。

## 3. 实际改动的文件树

计划与实做一致，没有出入；下表为实际改动（行数为 `git diff --numstat` 与 `wc -l` 的实测值）。

| 路径 | 改动 | 行数 |
|---|---|---|
| `apps/backend/tests/identity/browser_server.py` | 新增"让下一次响应出错"控制端点 `POST /__test__/http/fail-next-response` + 匹配中间件 | +32（247 → 279） |
| `apps/web/package.json` | 新增 devDependency `@axe-core/playwright@4.13.0`（精确版本，与仓库风格一致） | +1 |
| `apps/web/package-lock.json` | 锁文件同步 | +14 |
| `apps/web/tests/a11y/baseline.spec.ts` | 新增：12 个视图状态的 axe 扫描（含悬停态）+ 扫描器自检；172 行 | 新增 |
| `apps/web/src/features/jobs/submit.tsx` | 修改：动作后重读失败时给出可见提示，保留既有错误文案 | +24/−6 |
| `apps/web/tests/jobs/refresh-failure.spec.ts` | 新增：3 条用例（未注入时不变、批准后重读失败、冲突后重读失败）；99 行 | 新增 |
| `apps/web/src/lib/contracts.ts` | 修改：`JobDetail.task_snapshots` 增补冻结字段类型 | +1 |
| `apps/web/src/lib/job-shapes.ts` | 修改：解析 `dataset_id`/`dataset_revision`/`split`/`repo`（响应本就有，此前被丢弃） | +5 |
| `apps/web/src/lib/leaderboard/client.ts` | 修改：`filtersFromQuery`/`leaderboardHref`（筛选条件 ↔ URL 参数） | +23 |
| `apps/web/src/features/jobs/details.tsx` | 修改：批次详情新增"按此条件查排行榜"入口（含"条件须一致"的可见条件） | +18 |
| `apps/web/src/features/leaderboard/view.tsx` | 修改：按 URL 参数预填表单，不自动查询 | +10/−2 |
| `apps/web/tests/leaderboard/prefill-from-batch.spec.ts` | 新增：2 条用例（预填 + 不自动查询 + 查询走原接口；条件不一致不显示入口）；107 行 | 新增 |
| `docs/architecture/modules/web-and-http/actions/delivery/15-web-ux-improvements.md` | 本文件（新增） | — |
| `docs/architecture/modules/web-and-http/progress.md` | 修改：新增本轮小节（含 a11y 未修清单） | — |

**设计模式**：本次无新增模式。三件都是既有结构的**修改**——第二件沿用 `submit.tsx` 既有的"忙碌/错误"本地状态族（新增一个并列的 `notice`），第三件沿用既有"URL 查询参数 → 视图状态"的读法（`listing/view.tsx`、`shell.tsx` 已有先例）与既有 `LeaderboardFilters` 形状。

**指标**：新增/改动的 TS 源文件均在 200 行以内（最大为 `tests/a11y/baseline.spec.ts` 172 行）。夹具 `browser_server.py` 增至 **279 行**，继续超出"≤200 行"的默认指标——该文件的既有例外此前已获用户确认（见[行动 14](14-fixture-failure-injection-and-presentation-verifications.md) §6），本轮新增 32 行已在任务报告中说明，**未拆文件**；拆分需把夹具装配与 uvicorn 入口一起搬家，会影响既有其它 spec 的加载路径，留作后续候选。

## 4. 自验证方式

```bash
cd apps/web
npm run typecheck && npm run lint                    # 静态检查
# 单跑：用仓库 runner 指定单个 spec——每个 spec 各起一次干净后端，并自动还原生成文件
AGENTEXAM_USE_SYSTEM_CHROME=1 npm run test:e2e -- baseline.spec.ts
AGENTEXAM_USE_SYSTEM_CHROME=1 npm run test:e2e -- refresh-failure.spec.ts
AGENTEXAM_USE_SYSTEM_CHROME=1 npm run test:e2e -- prefill-from-batch.spec.ts
AGENTEXAM_USE_SYSTEM_CHROME=1 npm run test:e2e        # 全量，判定标准（退出码 0）
cd ../backend && .venv/Scripts/python.exe -m ruff check tests/identity/browser_server.py
```

**成功标准**：三个新 spec 单独跑通过；全量 `npm run test:e2e` 退出码 0；a11y 扫描要么通过、要么只剩 §7 明确报告并可解释的项；夹具未调用端点时行为不变。

## 5. 第三件的逐控件契约行

同一事实的权威来源仍是 [HTTP API §10](../../../../../interfaces/HTTP_API.md) 与本模块 `ARCHITECTURE.md`；本表只登记**本次新增控件**的完整契约，不复制接口正文。按实现地图 §2.1 的门槛，12 项必填内容逐项落在下表；**没有"不适用"项**——纯客户端导航也有明确的 HTTP 结论（无请求）。

| 项 | 内容 |
|---|---|
| **控件** | 批次详情内的链接「按此条件查排行榜」（新控件） |
| **可见/禁用条件** | 在评测详情（`features/jobs/details.tsx`）内渲染，且**仅当该批次全部题目快照的冻结条件一致**（`dataset_id`/`dataset_revision`/`split`/`repo` 四元组唯一）时显示；不一致（跨数据集或跨 split 的批次）**不显示**，因为此时不存在单一可比的冻结条件。无禁用态（纯导航，无前置写操作）。角色无关：owner 与 collaborator 都能打开详情，排行榜本身对已登录用户只读开放 |
| **用户意图** | 用刚看过的批次**冻结的**比较条件去查排行榜，不必手抄数据集 ID/revision/split |
| **前端事件与状态** | `JobDetails` 为纯展示组件、无本地状态；点击是浏览器整页导航（`<a href>`，是既有"查看批次"链接的同款做法）。`WorkbenchShell` 按 `view=leaderboard` 渲染 `LeaderboardView`；后者用 `useState` 初始化函数读 URL 查询参数**预填 5 个输入**，**不自动发起查询**；用户仍须自己点「查询排行榜」。未预填到的输入保持空 |
| **URL 行为** | 目标 `/?view=leaderboard&dataset_id=…&dataset_revision=…&split=…&repo=…&tool_profile_id=…`（参数名与排行榜 HTTP 查询名同形，便于对照）。**只读**：排行榜视图不写回、不 `replaceState`、不改写既有参数；缺参时对应输入留空；`view` 由既有壳解析（未知值回落到 `home`）。刷新与前进后退保持同一预填结果 |
| **HTTP 方法/路径/查询/body/Header** | **导航本身无任何 HTTP 请求**（纯客户端 URL + 渲染）。用户点「查询排行榜」后沿用既有 `GET /api/v1/leaderboard?evaluation_track=closed_book&dataset_id=…&dataset_revision=…&split=…&repo=…&tool_profile_id=…&limit=20`（可选 `&cursor=…`）。GET 无 body；无 `Idempotency-Key`；无自定义请求头（仅同源会话 Cookie） |
| **响应解析器** | `leaderboardPage()`（`src/lib/leaderboard/shapes.ts`）逐字段运行时校验；畸形或缺失即抛 `ApiError("UNAVAILABLE")`，**不伪造空榜** |
| **FastAPI 路由** | `GET /api/v1/leaderboard` → `delivery/http/routes/leaderboard/routes.py`（会话检查、查询参数白名单与长度校验先于用例调用） |
| **Application 用例与持久化端口** | `LeaderboardReporting.page(query)` → `LeaderboardRepository` 端口；生产为 `PostgresLeaderboardRepository`，浏览器夹具为 `BrowserLeaderboardRepository`。排名、分母与可比性分组规则在 `domain/leaderboard/policy.py`，**本次不改** |
| **权限与前置状态** | 需已登录（会话 Cookie）；排行榜只读，owner 与 collaborator 同权。前置状态：该批次详情已成功读取（拿到题目快照），故入口只在详情出现，列表页不出现 |
| **稳定错误** | 导航无错误。查询失败沿用既有稳定码与文案：`VALIDATION_ERROR`（422）、`DEPENDENCY_UNAVAILABLE`（503）、`AUTHENTICATION_REQUIRED`（401）、`RATE_LIMITED`（429）；**不新增错误码** |
| **成功后的重新读取/导航** | 成功后**不导航、不改 URL**，只替换榜单区域（`setSearched`/`setApplied`）；「加载下一页」沿用服务端不透明 cursor。**刻意不做**：不因预填而自动发起查询（预填只是默认值，不是授权） |
| **浏览器及 HTTP 测试** | 新增 `apps/web/tests/leaderboard/prefill-from-batch.spec.ts`（2 条浏览器用例：① 批次入口 → URL 带出冻结条件 → 表单被预填、**未自动查询** → 点查询仍走既有接口且参数就是预填值、并命中既有响应；② 冻结条件不一致时不显示入口）。HTTP 层本次**零改动**，排行榜既有 HTTP/契约用例继续作为后端证据，因此不新增 HTTP 用例 |

## 6. 自验证结果

全部命令在本机实跑，输出为实际值。

| 检查 | 命令 | 实际输出 |
|---|---|---|
| 静态检查 | `npm run typecheck` | 通过（无输出） |
| 静态检查 | `npm run lint`（`eslint . --max-warnings 0`） | 通过（0 error / 0 warning） |
| 生产构建 | `npm run build` | 通过 |
| 后端夹具 | `.venv/Scripts/python.exe -m ruff check` + `format --check` | `All checks passed!` / `1 file already formatted`（ruff 0.15.17） |
| **第一件单独跑** | `AGENTEXAM_USE_SYSTEM_CHROME=1 npm run test:e2e -- baseline.spec.ts` | **2 passed（21.2s）** |
| **第二件单独跑** | `… -- refresh-failure.spec.ts` | **3 passed（15.4s）** |
| **第三件单独跑** | `… -- prefill-from-batch.spec.ts` | **2 passed（17.3s）** |
| **全量（判定标准）** | `AGENTEXAM_USE_SYSTEM_CHROME=1 npm run test:e2e` | **退出码 0**：29 个 spec 文件、**59 passed / 0 failed / 0 skipped**（日志 `runtime/tests/full-e2e.log`，已核对零失败行） |
| 改动范围 | `git status --short` | 只有上表列出的文件；框架生成的 `next-env.d.ts`、`tsconfig.json` 已用 `git checkout --` 还原。**未 `git add`/`commit`/`push`** |

**负控（证明断言不是空转）**：

| 负控 | 做法 | 结果 |
|---|---|---|
| a11y 扫描器 | 临时把「数据集 ID」的 `<label>` 包裹改成 `<div>`（去掉隐式关联） | 扫描**失败**：`label（critical）命中 1 处 … Element does not have an implicit (wrapped) <label>`；改回后恢复 0 违规 |
| a11y 扫描器（常驻自检） | 在真实页面注入一个无 `id`/`label` 的 `<input>`（已写进 spec 的自检用例） | `label` 规则抓到 `#a11y-self-check`；证明"0 违规"不是规则没跑 |
| 刷新失败提示 | 临时把 `setNotice(...)` 改成静默注释 | 用例 2、3 **失败**在"提示可见"断言上（用例 1 仍通过，符合预期）；改回后 3 passed |
| 排行榜预填 | 临时把 `useState(initialFilters)` 改回 `useState(empty)` | 用例 1 **失败**：`expect(locator).toHaveValue` 收到 `""`；改回后 2 passed |
| 夹具行为不变 | 不调用新端点时正常走完"提交 → 批准 → 重读详情" | `refresh-failure.spec.ts` 第 1 条用例通过；其余 26 个既有 spec 全量通过 |

## 7. a11y 扫描清单：12 个视图状态与未修项

**扫描口径**：`AxeBuilder.withTags(["wcag2a","wcag2aa"])`。每个视图打印一行覆盖情况（"通过"是 axe 真正评估过并放行的规则数），并对 `REPORT_ONLY` 命中的规则输出完整明细。**必须为零**的一栏就是本次修复边界内的机械性问题。

| 视图状态 | 必须为零 | 只报告 | 通过规则数 |
|---|---|---|---|
| 工作台 | 0 | 0 | 18 |
| 任务目录 | 0 | 0 | 20 |
| 配置目录 | 0 | 0 | 20 |
| 成员管理 | 0 | 0 | 19 |
| 排行榜（空表单） | 0 | 0 | 20 |
| 批次详情（等待批准） | 0 | 0 | 23 |
| 批次详情（执行完成） | 0 | 0 | 21 |
| 单次运行报告 | 0 | 0 | 23 |
| 评测列表 | 0 | 0 | 21 |
| 排行榜（含榜单） | 0 | 0 | 22 |
| 排行榜查询按钮（悬停态） | 0 | **1** | 22 |
| 对比报告（含矩阵） | 0 | 0 | 25 |

**修了的**：**无**。12 个视图状态、共 254 条规则评估里，机械性问题（可访问名、`label` 关联、landmark/role、`aria-*`、重复 id）实测 **0 条**——这不是"没查"，而是本仓库页面此前已在 `aria-label`、`label`、`aria-current`、`lang`、标题等方面做对了。第一件的交付物因此是**防回归层 + 扫描器自检**，不是修复清单。

**只报告的（1 条，交用户决定）**：

| rule id | 影响面 | 命中元素 | axe 实测数据 | 不改理由 |
|---|---|---|---|---|
| `color-contrast` | serious（1 处） | `form > button`，即 `<button>查询排行榜</button>` 的**悬停态** | `fgColor #ffffff`／`bgColor #f7faf8`／**contrastRatio 1.05:1**（要求 4.5:1）；16px、bold（不属"大号文本"） | 属配色决定：要改就动 hover 底色或主按钮字色（`globals.css`），按约定只报告 |

**这条为什么不止是"颜色不好看"**（根因是 CSS 权重，不是随手写错一个色值）：全局 `button:hover:not(:disabled) { background: #f7faf8 }`（`src/app/globals.css:23`）的权重是 (0,2,1)，压过同表 `form > button { background: var(--accent); color: white }`（`globals.css:27`）的 (0,0,2)；hover 规则**只改底色、不改字色**，于是白字落在近白底上。

**影响面（为什么按"表单主按钮"这一类报）**：只命中 `form > button` 这一条选择器分支，即**所有 `<form>` 的主提交按钮**：登录「登录」、排行榜「查询排行榜」、成员管理「创建邀请」、目录「登记已核验题目」。实测两处启用态样本（登录页 1.05:1、排行榜 1.05:1）。权重同为 (0,2,1) 但写在后面的两条**不受影响**：`.heading-actions button:last-child`（新建评测／对比所选，实测 6.48:1）与 `.wizard-actions button:nth-last-child(2)`（向导主按钮）。禁用态（`opacity: .5`）不触发 hover 规则，故也不受影响。

**未覆盖 / 局限（如实记录，不当作通过）**：

- **只有 `wcag2a`/`wcag2aa`**（用户指定）：`landmark-one-main`、`region`、`heading-order` 等 best-practice 规则**不在扫描范围**，"内容都在地标内""页面只有一个 main"这类问题不会被发现。
- **折叠内容不会被扫到**：`<details>` 收起时其内容不参与渲染，因此排行榜行的"完整比较条件／过程指标／纳入来源"、单次报告的"技术详情"等**没有进扫描**。
- **状态覆盖有限**：只扫了 owner 角色、默认桌面宽度下的 12 个状态；协作者视图、390/360 手机宽度、登录/加入页、错误态与空态（除排行榜空态外）未扫描。既有 `tests/workbench/mobile.spec.ts`、`tests/identity.spec.ts` 覆盖了这些路径的行为，但不是 a11y 扫描。
- **悬停态只点测了主按钮一类**：`details`/`summary`、导航按钮、表格斑马纹等其它元素的悬停/聚焦视觉未逐一点测。聚焦态有全局 `:focus-visible` 描边（`globals.css:25`），但未做对比度实测。

## 8. 实际结果、偏差与未做的事

**三件全部落地，无计划外偏差**。以下为需要如实说明的点：

1. **第一件没有"修"任何东西**（见 §7）：机械性问题实测为 0。为避免"绿 = 没跑"的误判，spec 里加了常驻自检用例（注入无名控件必须被抓到），并在每次扫描打印"通过规则数"。
2. **扫描前会把指针移开**（`page.mouse.move(0, 0)`）：否则上一次 click 留下的悬停态会参与计算，同一页面在不同用例里结论不一致。悬停态改为**显式指定要悬停的控件**再扫一次，让它是写明的状态而不是偶然命中。
3. **第二件比"改两处静默 catch"多改了一处**：除两处 `catch { /* keep error */ }` 外，"写请求成功但重读失败"这条路径也会显式提示，并且**照旧保留**它原有的 `DEPENDENCY_UNAVAILABLE` 文案（不吞掉）。这是"动作后刷新失败"最直白的一种情形，用户点名的用例也用它。
4. **提示用 `role="status"` 而不是 `role="alert"`**：既有 `tests/jobs.spec.ts:52` 等用例对 `alert` 做严格定位，新增 alert 会让它们变成多元素歧义。提示在**手动刷新成功后清除**，否则"可能已过期"会一直误导。
5. **第三件没有新增任何后端接口**：冻结条件本就在 `GET /api/v1/jobs/{id}` 的 `task_snapshots` 里（`routes/jobs/schemas.py:34-42`），是 Web 解析器此前把 `dataset_id`/`dataset_revision`/`split`/`repo` 丢掉了；本次只补回解析与展示。
6. **第三件的两个明确取舍**：① `evaluation_track` **不进 URL**——客户端固定 `closed_book`（`lib/leaderboard/client.ts` 写死），预填不需要它；② 预填的值**只用于表单默认值**，不自动查询、不改写 URL，用户仍要点「查询排行榜」。
7. **夹具端点未调用时行为不变**：队列为空即透传；新增的 32 行把 `browser_server.py` 推到 279 行（既有已确认例外，见 §3）。
8. **跑测副作用已还原**：直接 `npx playwright test` 会让 Next dev 重建 `next-env.d.ts`/`tsconfig.json`；收尾用 `git checkout --` 还原，`git status --short` 只剩本轮预期文件（见 §6）。
