# Web 与 HTTP Module：进展与未决项

> 状态：2026-09-22 已对齐核心诊断修复的本地提交（当前文档收尾尚未 push）。本文件按时间**倒序**记录本 Module 的实际进展、环境验证结果与未决项；架构事实见[本模块架构](ARCHITECTURE.md)，接口权威见 [`HTTP_API.md`](../../../interfaces/HTTP_API.md)。
>
> 记录纪律：失败、跳过和未验证一律如实写出，不把"配置存在"等同于"实测通过"；真实设备名、账号与私有网络地址不入 Git。

## 2026-09-22：核心诊断修复对账

- Web 比较加载已加入请求代次；清空或切换 Job 后，旧请求即使迟到也不能回写陈旧矩阵，浏览器竞态回归已覆盖。
- FastAPI 的成功/错误/限流/500 响应统一具备 `no-store`、`nosniff`、frame、referrer 和 permissions 安全头；未预期异常以响应与脱敏日志共享的 `request_id` 关联。Next.js 同步设置上述浏览器头和 CSP，不在未确认 HTTPS 终止边界时提前设置 HSTS。
- Web 已建立 ESLint 9 flat config，并通过 lint、TypeScript、生产构建和使用系统 Chrome 的 45 项 Playwright 回归；测试 runner 将 Next 专用输出隔离到 `.next-e2e`，且成功/失败都会恢复框架生成的配置引用。
- 2026-09-22 的官方 npm 审计发现 Next 15.5.25 固定带入的 PostCSS 8.4.31 存在已公开漏洞；现用 npm override 锁定 8.5.28，避免强制跨大版本升级 Next。覆盖后生产/全依赖审计均为 0 漏洞，且上述构建与 45 项浏览器回归重新通过。
- 任务 05 provider 失败码已有内部策略测试和 HTTP 文档，但生产 Worker/HTTP 尚无 provider 调用路径，所以两项端到端错误呈现验证仍待后续接线；真实 DeepSeek/Kimi 未调用。
- 本节是当前状态增量；下方 2026-09-21 各节保留当时协作和环境事实，不反向改写。

## 2026-09-22：任务 06/07 的结果展示回归测试设计（准备件，已合入）

任务 06/07 **未发布**，但[团队分工](../../../architecture/modules/TEAM_WORK_ALLOCATION.md)允许"提前阅读自己 Module 和准备测试设计"（明确同时**不允许**改后续任务代码、调真实模型、下载大体量镜像）。B 的切片是"结果展示回归"（06）/"展示回归"（07），已产出准备件：[B：任务 06/07 结果展示回归测试设计](../../../actions/2026-09-22-b-task06-07-results-presentation-test-design.md)。

- **内容**：权威来源对齐（story 24–27 与 19–21、覆盖 Q9/Q11/Q13、实现地图的"先补逐控件契约行"门槛）；三层测试归属与运行位置（契约层·浏览器层本机可写，真实 API 层只能在组长机器）；`B06-01…09`、`B07-01…09`、`B0X-10` 的用例映射，其中负例包括"**未知用量不得显示 0**""基础设施失败不冒充未通过""缺失轨迹不伪造补齐""排行榜不因换 UI 偷偷改规则""展示层不引入自动重试"；以及**开工前必须冻结**的五项（两个 provider 的预设 id/别名、Kimi 原生 Responses 字段映射、用量与费用口径、Token 计量口径、是否新增控件）。
- **明确不做**：不改产品代码、不调模型、不下载镜像；06/07 的任务单**目前尚不存在**（`.scratch/ui-catalog-providers/issues/` 只有 01–05），所以本文不构成开工授权。
- **`actions/` 目录已按最终口径拆分（2026-09-22）**：该目录曾达到 10 个文件、超过"每层文件夹不超过 8 个文件"的指标。**候选"按编号区间切（01–05 / 06+）"已否决**——编号不等于任务号（`07-t05-…` 属任务 05；`06`/`08` 是同一交付线程；`09` 是维护批次），按 06 切会把任务 05 的文件切进"记录"桶。最终口径：**根目录只留与任务直接对应的行动**（01、02、03×2、04、05、05b，共 7 个），**非任务的三份交付与维护记录移入 `actions/delivery/`**（`06` 已被取代、`08` 真实组件版交付、`09` 重跑与清理，共 3 个），顺带把 06/08 这对"被取代／取代"放在一起；`07-t05-…` 改名 `05b-t05-…`，避免编号被误读成"任务 07"。**没有移动 `05` 与 `03-*`**：它们被别人的文档直接引用（`.scratch` 的任务单、A 的回执、E 的进度日志、本模块 `ARCHITECTURE.md`），移动等于改他人文档。本次**未新增行动文档**：根目录正好卡在 8 个文件的上限，拆分这件事连同理由、做法与验证一并记在本节。
- **环境事实更正（2026-09-22）**：上述准备件形成时曾以“本机无 Docker”解释真实 API 层只能在负责人机器运行，该理由已经失效；本机 Docker 27.5.1 已把任务 05 的 T1 正常组和反向对照组实跑通过。06/07 的真实 API 联合验收仍须在负责人环境完成，是因为固定 Harbor、私有凭据/上游和正式运行身份尚不在本机，而不是因为本机缺 Docker。已结束的准备行动只作历史保留，不反向改写。

## 2026-09-22：在新 main 上重跑两套测试、清一处死代码、交 D 一条契约缺口（`fb8aadf` 历史时点）

`main` 已从 `1888aa2` 前进到 `fb8aadf`（E 的提供方访问链 PR #24/#25、B 的契约对齐 PR #26），**B 的界面此前从未在这些提交上验证过**。本节保留该提交当时的实测与缺口；当前结论以本文件“未验证项与待确认项”表及[核心诊断报告](../../../reviews/2026-09-21-core-code-diagnostic-report.md)为准。本轮把挂着的那几条待办一次收掉：

- **后端全量（`fb8aadf`，本机）**：**2 failed / 494 passed / 106 skipped**（60.35s）。两个失败仍是 `tests/contract/test_execution_network.py` 的两条 Harbor 契约用例（本机缺 `framework/harbor`），**可移植基线成立**；passed/skipped 由旧记录的 408/86 升到 494/106，来自 E 那批提交新增的测试（`tests/providers/policy/*` 等）。
- **静态检查**：`ruff check` 与 `ruff format --check` 对 `tests/identity/browser_server.py` 全过；mypy 按**项目范围**跑（`MYPYPATH=src mypy src/eval_platform`）为 **175 个源文件零问题**。**注意一处工具链事实**：按配置裸跑 `mypy`（`packages = ["eval_platform"]`）在本机不可用——报缺 `py.typed` 标记，解析到的是未安装标记的包而不是 `src/` 树；因此"B 侧没跑过 mypy"这条的结论只能由路径方式给出。对**单个测试文件**跑 mypy 会连带检查范围外的夹具（268 个未标注类错误），**那是噪声不是结论**。
- **死代码清理**：`apps/web/src/lib/job-client.ts` 的 `runArtifacts`（`GET /runs/{id}/artifacts`，全仓无界面调用）连同其无用导入一并删除；`npm run typecheck` 通过。本轮唯一的代码改动。
- **浏览器全量**：`AGENTEXAM_USE_SYSTEM_CHROME=1 npm run test:e2e` **退出码 0**，22 个 spec 全绿（每个 spec 单独起一次合成后端与前端 dev；运行器遇首个失败即中止）。
- **给 A 的脱离版补 `README.md`**：这是什么、怎么打开、与"跑起来的前端"的差别、已知边界、反馈什么最有价值。
- **交 D 一条契约缺口**（见下表）：未完成批次的批次报告返回 500。

## 2026-09-21：任务 05 的受控词汇对齐（E 请求；B 侧只改契约）

E 已把任务 05 的提供方访问链合入 `main`（PR #24/#25，本地 `1888aa2` → `acbabbf` 共 22 个提交），请求 B 对齐两处契约。**B 先核实代码事实再改文档**，结论与差异如下：

- **§10.2 受控失败码**：`provider_access/failures.py` 的 `_GROUPS` 与 `GENERIC_FAILURE` 确实是"四类受控码 + 兜底 `PROVIDER_ACCESS_FAILED`"，映射关系与中文短句**逐字核对一致**。已把五个码、各自归入的内部错误族、"内部错误码绝不回显、未映射落兜底"、"配置期专用码不入表"写入 §10.2。**并明确标注实现状态**：映射表与词汇表门禁已在 `main`，但 `provider_access` 包外**没有任何调用方**——代理链尚未接入运行主链路，所以这是**已冻结的契约词汇，不代表已生效**。
- **受控提供方值**：E 的转述把 `authentication_type=provider_run_token` 也算作要公开的身份，**与代码不符**。`AgentSummary`/`AgentDetail`（`catalog_schemas.py`）只返回 `agent_type` 与 `model_provider`，不含 `authentication_type` 或凭据 profile；文档第 650 行本就规定"不返回 authentication/credential profile"。故 §4.2/§6 只公开 `model_provider` 的受控集合（`openai_chatgpt` / `internal_test_fake`），并写明按记录如实呈现、超出集合失败关闭（`UNCONTROLLED_PROVIDER` / `UNCONTROLLED_AGENT_TYPE`），以及**公开 `internal_test_fake` 是有意的**（让受控预设不可能被误当成真实供应商配置）。
- **命名与粒度**：**沿用 E 的实现**（五码；额度与期限合并进 `PROVIDER_BUDGET_EXHAUSTED`，不拆分）。理由：它与已合入的库级 CHECK、`DATA_MODEL.md` 与 E 的映射表/门禁完全一致，拆分会同时改代码与用例，而对所有者没有可操作差别。
- **顺带核对 E 报告的自身缺陷已修**：`catalog_schemas.py` 现经 `_controlled(...)` 输出 `agent_type`/`model_provider`，超出受控集合时抛 `UNCONTROLLED_*` 而不是回退默认值——原来的"给 `model_provider="deepseek"` 的记录却照旧回 `openai_chatgpt`"的假报告路径不再存在；`06f59ce fix(catalog): honour the agent_type filter instead of dropping it` 也在同一批。

**B 侧由此新增的待办**：按此前约定，浏览器夹具（`apps/backend/tests/identity/browser_server.py`）需要加"**强制下一次响应出错**"的控制端点，用于"未知错误码失败关闭"的呈现验证；等代理链落地后与"受控文案忠实呈现"一起排期。

## 2026-09-21：A 要求的"所有前端"脱离版（第一版被否决，已重做为真实组件版）

A 明确范围是**所有前端**，并要"根据拉取到的 web 文件夹里现有的前端进行修改"。B 的第一版做成了**自造外观**的仿制原型（`ui-full-web-20260921`），**被 A 否决**："刚做的页面很差，旧的完全不行，不要了"——该目录与 5 张截图已删除。

重做后的方向：**不改 `apps/web` 任何文件**，把它的真实组件（`SessionPanel` + 真实 `globals.css`）打成脱离版，数据改为**从仓库自带的合成后端录制真实响应**再回放。

- **交付物**：`runtime/prototype/real-web-detached-20260921/standalone.html`（542 KB，双击即开）——页面就是真实前端，不是仿制品。
- **实测**（系统 Chrome 无头，`file://` 与 `http://` 两个入口各跑一遍，均"全部检查通过"）：8 视图内容级断言全过；批次详情 934 字含冻结运行数/限制/任务/配置/网络与工具策略/冻结版本；对比矩阵勾选后出现五档结果词；回放**精确命中 22 · 未录到 0**；390px 无横向溢出。
- **过程中修掉的三个真缺陷**：`file://` 盘符导致路径判断不命中（请求漏到真实网络）、真实代码 `pushState` 传 **URL 对象**而垫片只认字符串（导致批次详情整页只剩标题）、制品下载链接在 `file://` 下点了没反应。
- **教训**：第一版探针只断言"文本长度 ≥ N 字"，因此**放过了"整页只剩标题"**；已改为内容级断言，改完立刻抓出"列表第一页批次没录详情"的数据缺口（子代理逐行点开 27 个批次补录，自查缺失 0）。
- **局限**：写操作只回放录制响应、不改变状态；详情快照是"决策前"状态；未录到的组合回落同路径最接近的响应；只测了 Chrome，未做无障碍审计。
- 细节见[行动记录 08](actions/delivery/08-real-web-detached-build.md)；被取代的[行动记录 06](actions/delivery/06-full-web-standalone-prototype.md)只作历史保留。

## 2026-09-21：A 要求的"所有前端的脱离版 HTML 原型"（不入仓库）

A 指示"把 web 里的前端代码弄成一个脱离的 HTML，根据 HTTP API 接口文档修改"，并明确范围是**所有前端**。已交付单文件 `standalone.html`（88.4 KB，双击即开、不连任何服务、合成数据），覆盖真实前端的 8 个视图面：工作台、评测列表与详情、三步提交向导、对比矩阵（含**每列用量/费用/耗时与总量/部分/未知三档覆盖**）、单次 Run 报告与证据、任务目录、配置目录、排行榜、成员与邀请。

- **性质**：这是给 A 看动线的**提案原型**，不是第二套前端；`apps/web` 的真实实现仍是权威，A 的反馈要落到真实代码与 [`HTTP_API.md`](../../../interfaces/HTTP_API.md) 上，不在原型里定稿。
- **实测**（本机系统 Chrome，无头；多文件版与单文件版各跑一遍，结果一致）：8 视图 × {1440, 390} 无脚本报错、无请求失败、无横向溢出；评测列表 → 详情 → 单次证据、矩阵指标开关与单元格下钻、角色切换（导航 8 → 7、批准按钮 0）全部点通。
- **过程中修掉的真实缺陷**：`file://` 下 `pushState` 抛 `SecurityError`（交付物正是本地双击打开）、配置目录在 390px 溢出、矩阵 `totals` 与矩阵行自相矛盾（`job-4` 被错算成"总量"）、多数 Run 下钻是空页、邀请有效期 fixture 与文档冲突。逐条根因与处理见[行动记录](actions/delivery/06-full-web-standalone-prototype.md)。
- **未验证**：只测了 Chrome；未逐控件遍历；未做无障碍审计；所有写操作都是本地反馈文字，**不代表真实接口已验证**。

## 2026-09-21：B 剩余工作清点（截至任务 03/04/05 的 B 切片全部合入）

**结论：B 已没有"可立即开工的实现任务"。** 剩下的分三类，都不是"还没做"，而是被外部条件挡住或尚未发布：

**一、等他人（不能自行推进）**

| 事项 | 等谁 | 依据 |
|---|---|---|
| 任务 05 的两项呈现验证（受控文案的忠实呈现、未知错误码的失败关闭） | 等 E 的假提供方链落地 | [任务 05 行动](actions/05-necessary-error-presentation.md)第 4 节 |
| 共享 PostgreSQL `15432` 正向、Tailscale 双机、VPN 两态、未获准设备负向 | 等 A 排查网络与授权 | 本文件"共享环境接入尝试"节 |
| M1-14 的 HTTPS Web 与浏览器协作验收 | A 主责；依赖同一环境 | [M1-14 任务单](../../../../.scratch/m1-platform/issues/14-private-remote-acceptance.md) |
| 任务 05 整体开工 | 9 项负责人决定已确认；仍等 A 给出实施指令与拓扑探针窗口 | [任务 05 issue](../../../../.scratch/ui-catalog-providers/issues/05-fake-provider-secure-execution-chain.md)与[负责人回执](../../../LLY/01-plan/TASK05_OWNER_ACTION_REQUIRED.md) |

**二、未实施或未获授权、按计划只能准备测试设计（不得先改产品代码）**

| 事项 | B 的切片 | 计划许可 |
|---|---|---|
| 06 DeepSeek / 07 Kimi | 结果展示回归 | 计划第 1 节允许"提前阅读自己 Module 和准备测试设计"，不允许改后续任务代码、不调用真实模型 |
| 08 冻结矩阵与全量回归 | 页面/浏览器回归 | 同上；前置是 03/04/06/07 已验收 |

**三、B 可自行收口的已知缺口（不需要任何人）**

| 缺口 | 现状与原因 |
|---|---|
| 对比矩阵在**多列**量级下的横向滚动手感 | ⬜ **缺口保留（2026-09-21）**：曾写过 12 列的宽矩阵用例断言容器真的横向滚动，**单独通过但全量 suite 里不稳定**（勾选框计数竞态、矩阵表未渲染），已按"不稳定测试比没有测试更糟"撤掉；补测前需先查清它与全量长时运行的相互影响 |
| ~~第三个配置（凑"六题×三配置"）~~ | ✅ **已关闭（2026-09-21，C 答复）**：**不加**、维持六题 + 两配置。理由：① 任务 08 的冻结矩阵本就是"六题×两个新 API 配置 = 12 个 Run"，与现状正好对上；② 第三配置唯一能多验的"3 个恰好允许、4 个拒绝"边界已在 HTTP 层覆盖（`tests/jobs/scale/test_continuous_preset_bounds_sixty_runs_and_three_configurations`）；③ 等 05–07 落地 DeepSeek/Kimi 预设后再看是否需要，不预支。**不为它拆夹具文件、不再涨行数** |
| 真后端上的"六题可选"核对 | ✅ **已改期到任务 08（2026-09-21，C 答复）**：浏览器侧继续用合成后端；真后端核对由 C 提供 preset id 与门禁证据（白名单六条在 `adapters/tasks/catalog.py` 的 `FIXED_TASK_IMAGES`），**联合验收放到 08 的正式部署窗口**，不再作为 B 的当前待办 |
| 五档文案一致性 | ✅ **已核对（2026-09-21，D 答复）**：口径按 B 定的五个词，D 已把后端报告渲染器统一到同一套（`5373bf6`），并修掉她发现的后端旧用词；B 侧同步修掉两处前端残留（`report.tsx` 的"基础设施失败"、`comparison.tsx` 的"未通过"）与两处注释 |
| B 侧尚未运行 `ruff` / `mypy` | 仅指后端文件；B 改过的 `browser_server.py` 已跑过 `ruff check` 与 `format`，其余后端文件不属 B |
| 页面渲染面的哨兵扫描 | C 已覆盖 12 个 HTTP 读取面；网页面只在本轮动线可达的目录页做过，报告/证据/排行榜页未扫描 |

**当前主工作区状态（2026-09-21 本次交接核对）**：`main = origin/main = c71d342`；没有重新查询其他成员 fork 或 `upstream`，不得沿用更早的三端相等结论。已关闭的 `task03/comparison-api-spec` 仅作历史存档，其提交不需要再合入 `main`。

## 2026-09-21：任务 03/04/05 的 B 切片全部收口

- **任务 03（对比报告）**：契约随 PR #7 合入，Web 对比页随 PR #8 合入 `main`（`18bbd8d`）——五档与缺失语义、`decided/total` 汇总、单元格与列头钻取、手机 390/360 的横向滚动容器。实现与验证见[对比页行动](actions/03-comparison-ui.md)。
- **任务 04 的 B 切片**：三步向导在六题 + 两配置 + `continuous(1–20)` 下的浏览器动线、以及网页读取面的隐藏字段暴露扫描，随 PR #11 合入（`41fbd5d`）。测试夹具由 2 题扩到 6 题 + 2 配置，**超 200 行指标已按例外记录并获用户确认**（理由、风险与拆分评估见该行动第 8 节）。
- **任务 05 的 B 切片**：仅必要错误呈现的通道审计 + `HTTP_API.md` §10.2 的字段内容约束，随 PR #13 合入（`f05fa10`）。反泄漏的保证点在**写入侧**；B 侧两项呈现验证待假提供方链落地。
- **§2.1 与实时 OpenAPI 对账**：32 vs 32、逐条差异 0，随 PR #12 合入。
- **合并后回归**：后端 2 failed / 417 passed / 101 skipped（2 个失败为已知 `framework/harbor` 环境缺口）；浏览器全量 19 个 spec 全绿。
- **方法记录（供后续会话）**：本机 `gh` 已登录 `HeYuting1-alt`，PR 的创建与合并可由 B 侧直接完成，不再依赖网页手工操作；但 **`gh` 不读 Windows 系统代理**，必须显式带 `HTTPS_PROXY`（本机 `127.0.0.1:7892`），否则浏览器授权会在换取 token 时超时。

## 2026-09-21：§2.1 端点清单与实时 OpenAPI 对账（差异 0）

`HTTP_API.md` §2.1 自称列出"已经注册的 32 个 HTTP 端点"，此前一直**未用实时 OpenAPI 复核**（本条关掉该悬项）。用真实装配读 OpenAPI（不连库，只装配路由）：

```bash
cd apps/backend
AGENTEXAM_PUBLIC_ORIGIN=https://127.0.0.1:3100 \
AGENTEXAM_DATABASE_URL="postgresql://u:p@127.0.0.1:1/none" \
.venv/Scripts/python.exe -c "
from eval_platform.delivery.http.app import create_runtime_app
print(len(create_runtime_app().openapi()['paths']))"
```

结果：**文档 §2.1 = 32 条，实时 OpenAPI = 32 条，逐条集合比对差异 0**（含本次新增的 `GET /api/v1/reports/comparisons`）。脚本把两边的 `方法 + 路径` 都收成集合后求对称差，所以"数量相同但内容不同"也会被抓出来。

**为什么用真实装配而不是测试夹具**：`create_app(...)` 按传入的服务**条件注册**路由器，测试夹具不传 `leaderboard` 等依赖，用夹具读 OpenAPI 会少算端点、对不上 §2.1。真实装配必须走 `create_runtime_app()`；它只构造 Postgres 仓储、不在装配期连接，因此给一个假 DSN 即可读到完整路由表。

**仍未验证**：OpenAPI 的**字段级** schema 与 §10.4 正文仍只做过静态对照（20/20 字段命中；该对照记录在已关闭的 `task03/comparison-api-spec` 分支的 `docs/actions/2026-09-20-task03-comparison-api-doc.md`，**不随 main 发布，故此处不写链接**），没有把 OpenAPI 的响应 schema 与正文逐字段程序化比对。

## 2026-09-21：对比接口的加固与契约已由 main 完成；两个 PR 的处置

`main` 前进 7 个提交（`beed93f → fd369cc`），其中 **`7553ce0 fix: harden comparison reports and preset upgrade`**（fengyy，来源为"对 D 合并内容审查发现的问题"）**已把比较接口的加固与契约全部落到 main 上**：

- 严格参数校验：`delivery/http/routes/jobs/reporting/comparisons.py:111-114`，拒绝未知查询参数与重复 `job_ids` → `400 INVALID_REQUEST`；**对比路由已从 `report_comparisons.py` 移入 `reporting/` 内部子目录**。
- `HTTP_API.md` §10.4 由该提交**重写**并成为现行正文：含未知/重复参数 400、UUID 去空白并规范化为小写、**跨仓库同名 `instance_id` 不合并**（矩阵键改为 `(repo, task_instance_id)`）、五档与缺失语义、`decided`/`total` 整数。
- 五档枚举**收敛**：`ComparisonOutcome` 现由 `application/reporting/matrix.py` 提供，HTTP 层改为 import（此前的"两处独立声明"不再存在）。
- `routes/jobs/` 顶层回到 **8 个 `.py`**，满足"每层不超过 8 个文件"指标。
- 同时新增 `continuous` 批次的显式、幂等、失败关闭的旧库约束升级入口。

**B 侧两个 PR 的处置**（经确认 `7553ce0` 为最终版）：

| PR | 分支 | 处置 | 理由 |
|---|---|---|---|
| #3 | `task03/comparison-api-spec` | **关闭（不合并）** | `main` 上已有 §10.4；合并会整段替换该节。分支保留，其契约行动（`docs/actions/2026-09-20-task03-comparison-api-doc.md`，**在已关闭的分支上、不会进 main**）已把"待补两条 400"标为**已解除** |
| #4 | `docs/web-http-module-scaffold` | **重做**（并入 `main` 后按新事实修正） | 模块工作文档本身仍有价值；但内容需对齐新 `main` |

**随之取消/作废的两项**：

- **`routes/jobs/` 的 `schemas/` 拆分取消**：指标已由 main 的 `reporting/` 子目录达到，原方案不再必要（D 曾同意，已被现实超越）。
- **"§10.4 待补两条 400"作废**：已由 `7553ce0` 实现并写入契约。

**与 D 的工作重复（✅ 已由 D 拍板关闭，2026-09-21）**：D 的 `cdcb4cf`、`c5e036d`（分支 `xinyue-modules`）都不在 `main` 上，落到 main 的是 fengyy 独立实现的同一批加固（且更完整）。**D 已明确拍板**：接受 `main` 为最终形态——`cdcb4cf` / `c5e036d` 不再合入 main，以 fengyy 的 `7553ce0` 加固为准（UUID 规范化、跨仓库同名隔离都更完整）；"`ComparisonOutcome` 与 `MatrixCell` 不收敛"的决定**作废**，以 main 的收敛实现为准（`matrix.py` 提供 `ComparisonOutcome`）；`xinyue-modules` 转为历史存档，D 后续基于最新 main 继续。

## 2026-09-20：后端环境已恢复，契约测试已实跑

（此节结论**仍然有效**，是 B 侧唯一的本机实测记录。）

- **uv 安装**：`python -m pip install --user uv` → `uv 0.12.17`（与 D 的记录一致）；直连 PyPI 成功、无需代理；已加入用户 PATH。
- **第二道卡点及处理**：本机只有 Python 3.14.5，不满足 `requires-python = ">=3.13,<3.14"`，导致 `uv sync --locked --no-python-downloads` 报 `No interpreter found for Python ==3.13.*`。处理方式：把解释器作为**独立一步**装好（`uv python install 3.13` → uv 管理的 **Python 3.13.15**，用户级、可回退、经代理下载），项目原命令保持原样，随后退出码 0 建立 `.venv`。
- 工具可用：`argon2 25.1.0`、`pytest 9.0.2`、`ruff 0.15.17`、`mypy 1.18.2`；解释器 Python 3.13.15。
- **实测输出**（当时基于 `beed93f`）：

```text
tests/jobs/reporting/test_comparison_http.py -q  →  3 passed
tests/jobs/reporting -q                          →  14 passed, 2 skipped
全量 -q                                          →  2 failed, 404 passed, 84 skipped
```

- **两个失败**：同在 `tests/contract/test_execution_network.py`，一条 `FileNotFoundError [WinError 2]`、一条 `git -C D:\agent-exam\framework\harbor rev-parse HEAD` 退出码 128——因 `framework/`（gitignored）在本机未恢复。与 D、fengyy 对该环境缺口的描述一致。
- **基线可移植性（重要，勿照抄数字）**：可移植的只有"**2 failed，固定是那两条 Harbor 契约用例，原因是本机缺 `framework/harbor`**"。`passed/skipped` 数随本机门禁环境变化——本机为 404 passed / 84 skipped，D 的记录是 453 / 36（差异来自 `AGENTEXAM_RUN_IDENTITY_POSTGRES`、`AGENTEXAM_RUN_CATALOG_MINIO`、`AGENTEXAM_RUN_JOB_MINIO`、`AGENTEXAM_RUN_CODEX_TRIAL_PROBE` 与 `framework/harbor` 的可用性）。**不得把任何一组数字当作跨机器的固定基线。**
- 仓库干净：`.venv/` 被 `.gitignore:31` 命中；未改系统 Python。

## 2026-09-20：共享环境接入尝试（未接通）

B 手动尝试从本机接入 owner A 的共享评测环境，**未接通**：

| 检查项 | 结果 | 来源 |
|---|---|---|
| Tailscale 客户端 | 已安装、服务 Running、网卡 Up；`BackendState=Running`、`HaveNodeKey=true`（已登录） | ZCode 在本机实测 |
| Tailscale 可见对端 | **对端设备数为 0，自身 `Online=false`** | ZCode 在本机实测 |
| 解析 `sss.tail03c757.ts.net` | 失败，校园 DNS 返回 `Non-existent domain` | ZCode 在本机实测 |
| `Test-NetConnection sss.tail03c757.ts.net -Port 15432` | **False** | ZCode 在本机实测 |
| Navicat 连 `sss.tail03c757.ts.net:15432` | 失败 | B 手动尝试；**报错原文未提供，故不在此转述** |

已把问题报给 owner A 排查，**不阻塞** B 的文档和代码工作。

诊断线索（供 A 参考，**根因未经验证**）：客户端已登录运行但 tailnet 内看不到任何对端，故 `*.ts.net` 无法解析、15432 不可达。候选原因：① 与 owner 主机不在同一 tailnet；② 在同一 tailnet 但未被授权；③ MagicDNS 未生效。更像配置与授权层面，**不是链路或端口问题**。**没有**在下结论前改动任何机器网络设置、代理或 Tailscale 配置。

## 2026-09-20：向 D 的报告与结果（含 B 自身一处更正）

四项经 D 回复后**全部关闭**；其中两项最终**由 fengyy 在 main 上实现**（见上）。B 自始至终未改动 D 的文件。

| # | 事项 | 结果 |
|---|---|---|
| 1 | 五档枚举是否收敛 | D 回复"保持独立、不收敛、不提升为跨模块公开接口"——但**该决定已被 main 推翻**：`7553ce0` 把 `ComparisonOutcome` 收敛到 `matrix.py` |
| 2 | 提案 §2 示例仍写 `coverage` | D 在 `c5e036d` 收口为 `decided + total` ✅ |
| 3 | 提案 §4 声称未知/重复参数返回 400 而实现未做 | D 先补实现（`cdcb4cf`），其后 fengyy 在 main 上以更完整的方式实现 ✅ |
| 4 | `routes/jobs/` 9 个 `.py` 超指标 | fengyy 的 `reporting/` 子目录使顶层回到 8 ✅（原定的 `schemas/` 拆分取消） |

**B 自身的一处更正（保留在案）**：B 最初写的"本仓没有严格 query 校验层"是**错的**——该机制早已存在于 `leaderboard/routes.py:53-57`、`jobs/routes.py:83-95`、`catalog.py:123-125` 三处（均在会话检查前执行），B 的搜索未递归进 `routes/` 子目录。对比端点当时缺这条校验是**真实的缺口**，但"本仓没有该机制"的表述不成立。

## 未验证项与待确认项

| 项 | 状态 | 说明 |
|---|---|---|
| 共享 PostgreSQL `15432` 正向连通 | ⬜ 未通过 | Navicat 失败、TCP 不通；**根因见下方 Tailscale 一行**（B 与 owner 不在同一 tailnet）。B 当前不需要数据库，暂不重试（2026-09-21 用户决定） |
| Tailscale 双机正向/负向 | ⬜ **根因已定位** | 2026-09-21 复测：A 批准后本机**自身 `Online` 由 false 变 true**、已分配 tailnet IPv4，但对端仍为 **0**——**本机处于另一个 tailnet**（自身 tailnet 名与 tailnet IPv4 属私有信息，不入 Git），因此 `sss.tail03c757.ts.net` 解析不到、443 与 15432 均不可达。**A 侧需要把 owner 的设备节点共享给 B 的账号，或把 B 邀请进 `tail03c757`**；不是链路或端口问题。**2026-09-21 再复测**：A 把 B 的邮箱加进了 grants 规则后仍不通——**grants/ACL 只在同一个 tailnet 内生效**，B 的设备不在该 tailnet，规则不适用；仍然是上面两条之一才能真正打通（建议用**共享单个设备节点**，对 B 而言可保留自己的 tailnet，暴露面也最小） |
| VPN 开/关两态、未获准设备负向 | ⬜ 未验证 | 属 M1-14 范围 |
| 共享 PostgreSQL 门禁用例 | ⬜ 仍 skipped | 需 `AGENTEXAM_RUN_IDENTITY_POSTGRES=1` + 可达 PG；**如实记为 skipped，不记为通过** |
| 本机 Docker / 任务 05 T1 | ✅ 已完成 | 2026-09-22：Docker 27.5.1；正常拓扑 `status=verified`，反向对照 `status=negative-control-ok`，容器/网络/卷残留均为 0。固定 Harbor T2 仍未由此通过 |
| 本机在**当前 main** 上重跑 | ✅ 已完成 | 2026-09-22（`01feba4`）：后端默认 **510 passed / 102 skipped**，分支覆盖率 86.38%；仓库根统一入口 **521 passed / 112 skipped**。环境门控项仍按 skipped 记录；完整证据见[诊断报告 §8.2](../../../reviews/2026-09-21-core-code-diagnostic-report.md#82-最终实测) |
| 实时 OpenAPI 计数 | ✅ 已复核 | 用真实装配读 OpenAPI：**32 个端点，与 §2.1 的 32 条逐条集合比对差异 0**（2026-09-21，见上） |
| OpenAPI 字段级 schema 对账 | ⬜ 未做 | 仅做过 §10.4 正文与实现的 20/20 静态字段对照 |
| `ruff` / `mypy` | ✅ 当前统一入口通过 | Ruff lint 与 321 文件格式检查通过；修正 src 布局配置后，无参数 Mypy 对 177 个源文件通过，不再需要路径绕行 |
| 受控集合以外记录的 HTTP 表现 | ❓ **待 E 决定** | `_controlled` 数据层"失败关闭"是对的（抛 `ValueError`，不回退默认值），但 HTTP 层只注册了 `AuthenticationRequired`/`CatalogError`/`JobError`/`RequestValidationError`/`IdentityUnavailable`/`HTTPException`，**没有 `ValueError` 处理器**，故当前表现为 500、不带受控错误码。是否包装成受控错误（例如沿用 503 `DEPENDENCY_UNAVAILABLE`）由 E 定；B 只在 §4.2 写了"失败关闭"，**未承诺状态码** |
| 未完成批次的批次报告 | ✅ 已由当前实现关闭 | `JobReporting.job()` 逐个验证实际 Run report；等待批准、排队和运行中批次均返回 200，并用 `pending_runs` / `incomplete` 表达未完成。`tests/jobs/execution/batch/test_http_stages.py` 覆盖各持久化阶段 |
| 浏览器夹具"强制下一次响应出错"控制端点 | ⬜ 待排期 | 用于"未知错误码失败关闭"的呈现验证；按约定等代理链落地后与"受控文案忠实呈现"一起做 |
| 与 D 的工作重复 | ✅ 已关闭 | D 于 2026-09-21 拍板：接受 `main` 为最终形态，`cdcb4cf`/`c5e036d` 不再合入，以 `7553ce0` 为准；"不收敛"决定作废；`xinyue-modules` 转历史存档。**收尾提交已核实**：`3930f24`（关闭提案）与其子提交 `775d7a1`（更正已归档提案）都在远端，`git ls-remote` 权威值为 `775d7a1d065632064de2c3d5f0636f7eb03a80c2`。另记一条拓扑事实：**D 的 `origin` 就是团队仓库本身**（只配了一个 remote、没有 fork），她的推送直达 `anphuchoang5-sys/agent-exam`，与 B 的 fork 提 PR 路径不同 |
| 任务 03 的 Web 对比页 | ✅ 已完成 | 契约（PR #7）、后端（`7553ce0`）与 Web 页面（PR #8）均已合入 `main`；见[对比页行动](actions/03-comparison-ui.md) |
| 任务 03 正式 issue | ❓ 待确认 | `.scratch` 下无 `03-*` 任务单，是否发布待 B 决定 |
