# Web 与 HTTP Module：进展与未决项

> 状态：2026-09-20 建立。本文件按时间**倒序**记录本 Module 的实际进展、环境验证结果与未决项；架构事实见[本模块架构](ARCHITECTURE.md)，接口权威见 [`HTTP_API.md`](../../../interfaces/HTTP_API.md)。
>
> 记录纪律：失败、跳过和未验证一律如实写出，不把"配置存在"等同于"实测通过"；真实设备名、账号与私有网络地址不入 Git。

## 2026-09-20：后端环境已恢复，契约测试已实跑（此前两处环境阻塞解除）

- **uv 安装**：按项目记录的做法 `python -m pip install --user uv`，版本 **0.12.17**（与 D 在 2026-09-19 记录一致）；直连 PyPI 成功、无需代理。已加入用户 PATH。
- **第二道卡点及处理**：本机只有 Python 3.14.5，不满足 `requires-python = ">=3.13,<3.14"`，导致项目指定命令 `uv sync --locked --no-python-downloads` 报 `No interpreter found for Python ==3.13.*`。处理方式是**把解释器作为独立一步装好、项目命令保持原样**：`uv python install 3.13` 装了 uv 管理的 **Python 3.13.15**（用户级、可 `uv python uninstall` 回退、经代理下载），随后原命令退出码 0。
- **实测输出**：`test_comparison_http.py` → **3 passed**（本分支无 D 的第 4 个用例）；`tests/jobs/reporting` → **14 passed / 2 skipped**；全量 → **2 failed / 404 passed / 84 skipped**。
- **与 D 基线的交叉验证**：2 个失败的**数量与原因完全一致**（缺 `framework/harbor`），收集总数只差 1（= D 新增的用例）；但**通过/跳过比例不可复现**（本机 84 skipped vs D 的 36），因此 D 的 `453 passed / 36 skipped` 是**环境相关值，不能当固定基线抄写**。详见[实现侦察行动](actions/03-comparison-api-impl.md)第 5.3 节。
- 仓库干净：`.venv/` 被 `.gitignore:31` 命中，未向仓库写入杂物；未改系统 Python、未动 uv 与 PATH 之外的机器配置。

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

诊断线索（供 A 参考，**根因未经验证**）：Tailscale 客户端本身处于已登录运行状态，`BackendState=Running`、`HaveNodeKey=true`，但它所在 tailnet 里**可见对端设备数为 0、自身 `Online=false`**，因此 `sss.tail03c757.ts.net` 无法解析、15432 不可达。候选原因是以下三条中的一条或多条：

1. B 的机器与 owner 的主机**不在同一个 tailnet**；
2. 在同一个 tailnet 但**未被授权访问**该主机；
3. **MagicDNS 未生效/未解析**该名称（校园 DNS 直接返回 `Non-existent domain`，说明没有本地 MagicDNS 接管该查询）。

这三条更像配置与授权层面的问题，**不是链路质量或端口问题**。哪一条为真未经验证，待 A 排查后回填。

**没有**在下结论前改动任何机器网络设置、代理或 Tailscale 配置。

明确未做：未安装/重装 Tailscale、未登录或切换账号、未改 tailnet/grants、未调整 FlClash 或系统代理、未重试 Navicat、未向 owner 主机做其他端口探测。

## 2026-09-20：§10.4 对比接口契约已提 PR（PR 尚未创建）

任务 03 子行动 a（契约落笔）已完成：

- 分支 `task03/comparison-api-spec` 已推送到 `origin`（个人 fork），HEAD `a951a2a`，含 2 个提交、2 个文件。
- 内容：`HTTP_API.md` 新增 §10.4 跨批次对比报告；§2.1 清单增列该端点并把已注册计数 31 改为 32；§15 追加变更记录。
- **PR 尚未创建**：本机 `gh` 的浏览器授权在 token 交换阶段因直连 `github.com` 超时失败，改走本机代理的方案待重试；因此只有创建链接，没有 PR 编号。
- 创建链接：`https://github.com/anphuchoang5-sys/agent-exam/compare/main...HeYuting1-alt:task03/comparison-api-spec?expand=1`
- 落笔依据与验证见[任务 03 契约行动](../../../actions/2026-09-20-task03-comparison-api-doc.md)。

## 2026-09-20：任务 03 接口实现侦察（结论与预期不同）

侦察发现：**§10.4 的 HTTP 翻译层（路由、DTO、错误映射、OpenAPI）已由 D 实现并注册**（`bd47925`，经 B 批准本方案后在 B 的 HTTP 层落地）；契约测试当时 3 个用例，其后 D 追加第 4 个（`cdcb4cf`）。因此任务 03 的"接口实现"不是待开工项，而是**待 B 复核与验证**；真正待做的是对比页 UI。

- 侦察记录、可仿照的测试入口、验证方案与未决项见[实现侦察行动](actions/03-comparison-api-impl.md)。
- 侦察同时发现两处**只报告、未擅自改**的不一致：D 的提案文档 §2 示例仍写着实现中不存在的 `coverage` 字符串；提案 §4 声称"未知参数、重复参数返回 400"而实现未做该校验。**两处均已由 D 在 `c5e036d` 收口**，其中第二条 D 选择补实现而非改措辞。

## 2026-09-20：建立本 Module 工作文档结构

按 B 的安排建立 `interface.md`、`progress.md` 与 `actions/`。**未新建 `architecture.md`**：同一事实的权威版本已存在（[本模块架构](ARCHITECTURE.md)），再建一份会违反项目"同一事实只设一个权威来源"的规则；如需另立目录结构见本文末尾待确认项。

## 2026-09-20：向 D 的报告与 D 的回复（四项全部关闭）

以下四项 B 已核实，并按"发现不一致先报告、不擅自改他人文档"的规则向 D 提出；**D 已于同日全部回复**，四项现均已关闭。B 自始至终未改动 `docs/actions/2026-09-20-d-comparison-api-proposal.md` 或任何 D 的代码。

### 待 D 决定：五档枚举是否收敛

**问题**：五档单元格的五个取值目前有**两处独立声明**——D 层 `MatrixCell`（`application/reporting/matrix.py:17-23`）与 HTTP 层 `ComparisonOutcome`（`delivery/http/routes/jobs/report_comparisons.py:19-25`）。两者当前字面量相同，但各自维护会漂移。

**B 的判断（2026-09-20）**：**暂不收敛**。HTTP DTO 枚举与 domain 内部枚举分层独立是正常做法，不必强行共用。是否把 `MatrixCell` 提升为**跨模块公开 Interface**，应由 **D** 决定，不由 B 单方面改 B 的 HTTP 层。

**D 的回复（已完成）**：同意 B 的分层判断——`ComparisonOutcome` 与 `MatrixCell` **保持独立声明、不收敛、不提升为跨模块公开接口**，D 已在其文档中记录该决定。**问题关闭**，`report_comparisons.py` 不改。

### 报告 D：提案文档的两处过期描述

| # | 位置 | 事实 | 与什么冲突 |
|---|---|---|---|
| 1 | [D 的提案](../../../actions/2026-09-20-d-comparison-api-proposal.md) §2 的示例 JSON 与字段表 | 仍写着 `"coverage": "6/6"` 字符串 | 与该文档自己的 §6 决定 4（"不另设字符串覆盖率"）和已实现代码都不符；实现用整数 `decided` + `total`，测试断言 `body["totals"][0]["total"] == 2` |
| 2 | 同一提案 §4 的错误表 | 声称"未知参数、重复参数返回 400 `INVALID_REQUEST`" | 当时对比端点**没有**这条校验（400 只有空选择、非 UUID、超 20）。**但 B 起初"本仓无严格 query 校验层"的表述是错的**——该机制早已存在于 `leaderboard/routes.py:53-57`、`jobs/routes.py:83-95`、`catalog.py:123-125` 三处，B 的搜索未递归进 `routes/` 子目录。D 选择补实现，成为第 4 处 |

**D 的处理（已完成，`c5e036d` / `cdcb4cf`）**：①§2 示例 JSON 的 `coverage` 改为 `total`，字段表与硬规则段落同步改正；②选择**补实现**——新增 `_reject_foreign_params` 与第 4 个契约用例，行为与排行榜等既有读端点一致（"400 先于 401"经 D 确认为有意设计）。**问题关闭。**

**对 §10.4 的影响**：D 补了实现之后，§10.4 需要新增这两条 400 与优先级说明。B 决定**有意延后**——因为该实现只在 `upstream/xinyue-modules`，写进契约会让契约 PR 依赖 D 的分支合并，并使 main 上出现暂无可读实现的契约描述。触发条件与理由见[契约行动](../../../actions/2026-09-20-task03-comparison-api-doc.md)。

### 报告超指标：`routes/jobs/` 文件数

`apps/backend/src/eval_platform/delivery/http/routes/jobs/` 现有 **9 个 `.py` 文件**（`__init__.py`、`batch_schemas.py`、`cancel_schemas.py`、`decision_schemas.py`、`report_comparisons.py`、`report_routes.py`、`report_schemas.py`、`routes.py`、`schemas.py`）加 `lifecycle/` 子目录，超过项目"每层文件夹默认不超过 8 个文件"的指标；`report_comparisons.py` 随 D 的实现（`bd47925`）加入，是该偏差的一部分。

**D 的回复（已完成）**：D 确认偏差属实，**同意 B 的拆分方案**（4 个 `*_schemas.py` 归入 `schemas/` 子目录，顶层降到 5 个 `.py`），并明确"目录 DRI 是 B，由 B 在 PR 里执行，D 不动你的目录结构"。**执行待办**：单独分支 + 测试验证，不并入当前契约 PR。



## 未验证项与待确认项

| 项 | 状态 | 说明 |
|---|---|---|
| 共享 PostgreSQL `15432` 正向连通 | ⬜ 未通过 | Navicat 失败、TCP 不通；待 A 排查（报错原文待 B 补） |
| Tailscale 双机正向/负向 | ⬜ 未完成 | 本机 tailnet 内对端数为 0；另有 M1-14 的完整双机验收 |
| VPN 开/关两态、未获准设备负向 | ⬜ 未验证 | 属 M1-14 范围，不因本次接入尝试而改变结论 |
| 对比接口 §10.4 与实现的字段一致性 | ✅ 已核对 | **字段级 20/20 命中**；D 本次新增的是行为（两条 400），字段对照覆盖不到，见下条 |
| 对比接口契约测试的实际运行 | ✅ 已跑（2026-09-20） | `test_comparison_http.py` **3 passed**（本分支无 D 的第 4 个用例）；`tests/jobs/reporting` **14 passed / 2 skipped**；全量 **2 failed / 404 passed / 84 skipped**。详见[实现侦察行动](actions/03-comparison-api-impl.md)第 5 节 |
| 后端依赖环境（`argon2`/`pytest`/`ruff`/`mypy`） | ✅ 已恢复 | `uv 0.12.17` + uv 管理的 Python 3.13.15；`.venv` 已建于 `apps/backend`；argon2 25.1.0、pytest 9.0.2、ruff 0.15.17、mypy 1.18.2 全部可用。**本机此前真正的阻塞是环境，不是数据库** |
| 共享 PostgreSQL 门禁用例（2 个 skip） | ⬜ 仍 skipped | 需 `AGENTEXAM_RUN_IDENTITY_POSTGRES=1` + 可达 PG；本机共享库不通，**如实记为 skipped，不记为通过** |
| `HTTP_API.md` §2.1 计数与实时 OpenAPI 的一致性 | ⚠️ 待确认 | 已注册计数改为 32 与源码路由数一致，但**未重新启动应用读取实时 OpenAPI** 复核 |
| 对比页 UI | ⬜ 未发布 | 依赖接口实现复核完成 |
| `gh` 登录与 PR 创建 | ⬜ 未完成 | 见上文 |
| 模块文档目录位置 | ✅ 已确认 | 2026-09-20 决定保留在 `docs/architecture/modules/web-and-http/`，不另建 `docs/modules/`（既有约定，且 Windows 大小写不敏感会让 `architecture.md` 与 `ARCHITECTURE.md` 撞名）。`ARCHITECTURE.md` 的 31→32 计数与导航行保留 |
| 五档枚举是否收敛 | ✅ 已关闭 | D 已确认**不收敛、不提升为跨模块公开接口**，两处独立声明各自维护，见上节 |
| `routes/jobs/` 超 8 文件指标 | ⏳ 待 B 执行 | D 已同意拆分方案并明确由 B 执行；单独分支 + 测试验证，见上节 |
| **§10.4 待补两条 400** | ⏳ 有意延后 | 实现见 `cdcb4cf`（在 `upstream/xinyue-modules`，**未合入 main**）；触发器与理由见[契约行动](../../../actions/2026-09-20-task03-comparison-api-doc.md)。不阻塞对比页 UI |
| 基线可移植性 | ⚠️ 已查明 | 可移植的只有"2 failed 固定为那两条 Harbor 契约用例"；passed/skipped 数随门禁环境变化，**不可照抄 D 的 453/36** |
| 对比接口所属任务的正式 issue | ❓ 待确认 | `.scratch` 下无 `03-*` 任务单，是否发布待 B 决定 |
