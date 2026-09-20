# Web 与 HTTP Module：进展与未决项

> 状态：2026-09-20 建立。本文件按时间**倒序**记录本 Module 的实际进展、环境验证结果与未决项；架构事实见[本模块架构](ARCHITECTURE.md)，接口权威见 [`HTTP_API.md`](../../../interfaces/HTTP_API.md)。
>
> 记录纪律：失败、跳过和未验证一律如实写出，不把"配置存在"等同于"实测通过"；真实设备名、账号与私有网络地址不入 Git。

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

侦察发现：**§10.4 的 HTTP 翻译层（路由、DTO、错误映射、OpenAPI）已由 D 实现并注册**（`bd47925`，经 B 批准本方案后在 B 的 HTTP 层落地），契约测试 3 个用例已存在。因此任务 03 的"接口实现"不是待开工项，而是**待 B 复核与验证**；真正待做的是对比页 UI。

- 侦察记录、可仿照的测试入口、验证方案与未决项见[实现侦察行动](actions/03-comparison-api-impl.md)。
- 侦察同时发现两处**只报告、未擅自改**的不一致：D 的提案文档 §2 示例仍写着实现中不存在的 `coverage` 字符串；提案 §4 声称"未知参数、重复参数返回 400"而实现未做该校验。

## 2026-09-20：建立本 Module 工作文档结构

按 B 的安排建立 `interface.md`、`progress.md` 与 `actions/`。**未新建 `architecture.md`**：同一事实的权威版本已存在（[本模块架构](ARCHITECTURE.md)），再建一份会违反项目"同一事实只设一个权威来源"的规则；如需另立目录结构见本文末尾待确认项。

## 2026-09-20：向 D 报告与待确认（只报告，未改 D 的文件）

以下四项 B 已核实，按"发现不一致先报告、不擅自改他人文档"的规则记录，等 D 处理。B 未改动 `docs/actions/2026-09-20-d-comparison-api-proposal.md` 或任何 D 的代码。

### 待 D 决定：五档枚举是否收敛

**问题**：五档单元格的五个取值目前有**两处独立声明**——D 层 `MatrixCell`（`application/reporting/matrix.py:17-23`）与 HTTP 层 `ComparisonOutcome`（`delivery/http/routes/jobs/report_comparisons.py:19-25`）。两者当前字面量相同，但各自维护会漂移。

**B 的判断（2026-09-20）**：**暂不收敛**。HTTP DTO 枚举与 domain 内部枚举分层独立是正常做法，不必强行共用。是否把 `MatrixCell` 提升为**跨模块公开 Interface**，应由 **D** 决定，不由 B 单方面改 B 的 HTTP 层。

**请 D 回答**：`MatrixCell` 是否升级为跨模块公开 Interface？若是，D 定公开名与位置，B 再改 HTTP 层的引用；若否，两处各自维护，但需在 D 的文档里明确"这是两个独立的分层枚举，不是同义重复"。

**时序**：即使 D 同意收敛，也要等后端依赖环境恢复、能够跑测试之后再单独开一个小 PR，不并在当前契约 PR 里。

### 报告 D：提案文档的两处过期描述

| # | 位置 | 事实 | 与什么冲突 |
|---|---|---|---|
| 1 | [D 的提案](../../../actions/2026-09-20-d-comparison-api-proposal.md) §2 的示例 JSON 与字段表 | 仍写着 `"coverage": "6/6"` 字符串 | 与该文档自己的 §6 决定 4（"不另设字符串覆盖率"）和已实现代码都不符；实现用整数 `decided` + `total`，测试断言 `body["totals"][0]["total"] == 2` |
| 2 | 同一提案 §4 的错误表 | 声称"未知参数、重复参数返回 400 `INVALID_REQUEST`" | 实现**没有**这个校验：本仓无严格 query 校验层，FastAPI 默认忽略未知 query 参数、重复标量参数取最后一个值。已实现的 400 只有空选择、非 UUID、超 20 三种（`test_comparison_http.py:115-129`） |

**请 D 处理**：①的示例与字段表与 §6 决定 4 对齐；②要么补实现、要么改提案措辞。两者都属 D 维护，B 不代改。`HTTP_API.md` §10.4（B 落笔）**已经**按实现写，无 `coverage`、无未实现的参数校验规则，因此无需随之改动。

### 报告超指标：`routes/jobs/` 文件数

`apps/backend/src/eval_platform/delivery/http/routes/jobs/` 现有 **9 个 `.py` 文件**（`__init__.py`、`batch_schemas.py`、`cancel_schemas.py`、`decision_schemas.py`、`report_comparisons.py`、`report_routes.py`、`report_schemas.py`、`routes.py`、`schemas.py`）加 `lifecycle/` 子目录，超过项目"每层文件夹默认不超过 8 个文件"的指标；`report_comparisons.py` 随 D 的实现（`bd47925`）加入，是该偏差的一部分。

**现状与请求**：这是**既有偏差**，不是任务 03 造成的；任务 03 不新增后端文件。B **未擅自拆分或移动**。按项目规则超指标需要单独说明理由、风险与拆分评估并取得确认——请 D 与 B 共同确认一个拆分方案（例如把 `*_schemas.py` 归入 `schemas/` 子目录），再单独开工，不并入当前契约 PR。



## 未验证项与待确认项

| 项 | 状态 | 说明 |
|---|---|---|
| 共享 PostgreSQL `15432` 正向连通 | ⬜ 未通过 | Navicat 失败、TCP 不通；待 A 排查（报错原文待 B 补） |
| Tailscale 双机正向/负向 | ⬜ 未完成 | 本机 tailnet 内对端数为 0；另有 M1-14 的完整双机验收 |
| VPN 开/关两态、未获准设备负向 | ⬜ 未验证 | 属 M1-14 范围，不因本次接入尝试而改变结论 |
| 对比接口 §10.4 与实现的字段一致性 | ⚠️ 已静态核对 | 20/20 字段命中；未运行测试复核 |
| 对比接口契约测试的实际运行 | ⛔ 被环境阻塞 | `apps/backend` 无 `.venv`；本机**没有 `uv`**（PATH、常见安装位置、用户目录全盘搜索都没有）。项目指定命令是 `uv sync --locked --no-python-downloads`（见[依赖总表](../../../dependencies/DEPENDENCIES.md)）。按 B 指示"uv 不在就先报告、不用系统 Python 硬装"，本轮**未恢复环境、未跑测试** |
| 后端依赖环境（`argon2`/`pytest`/`ruff`/`mypy`） | ⛔ 未恢复 | 系统 Python 3.14.5 缺 `argon2`，`tests/jobs/conftest.py` 的 `Argon2Passwords` 导入失败、夹具无法装配；`ruff`/`mypy` 不在 PATH。**这是当前本地跑测试的真实阻塞，而不是数据库** |
| `HTTP_API.md` §2.1 计数与实时 OpenAPI 的一致性 | ⚠️ 待确认 | 已注册计数改为 32 与源码路由数一致，但**未重新启动应用读取实时 OpenAPI** 复核 |
| 对比页 UI | ⬜ 未发布 | 依赖接口实现复核完成 |
| `gh` 登录与 PR 创建 | ⬜ 未完成 | 见上文 |
| 模块文档目录位置 | ✅ 已确认 | 2026-09-20 决定保留在 `docs/architecture/modules/web-and-http/`，不另建 `docs/modules/`（既有约定，且 Windows 大小写不敏感会让 `architecture.md` 与 `ARCHITECTURE.md` 撞名）。`ARCHITECTURE.md` 的 31→32 计数与导航行保留 |
| 五档枚举是否收敛 | ❓ 待 D 回答 | B 已决定**暂不收敛**；是否把 `MatrixCell` 提升为跨模块公开 Interface 由 D 决定，见上节 |
| `routes/jobs/` 超 8 文件指标 | ❓ 待 B 与 D 共同确认 | 既有偏差（9 个 `.py`）；未擅自拆分，见上节 |
| 对比接口所属任务的正式 issue | ❓ 待确认 | `.scratch` 下无 `03-*` 任务单，是否发布待 B 决定 |
