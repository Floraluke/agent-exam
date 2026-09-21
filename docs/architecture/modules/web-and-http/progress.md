# Web 与 HTTP Module：进展与未决项

> 状态：2026-09-21 重做（对齐 `main` 的 `fd369cc`）。本文件按时间**倒序**记录本 Module 的实际进展、环境验证结果与未决项；架构事实见[本模块架构](ARCHITECTURE.md)，接口权威见 [`HTTP_API.md`](../../../interfaces/HTTP_API.md)。
>
> 记录纪律：失败、跳过和未验证一律如实写出，不把"配置存在"等同于"实测通过"；真实设备名、账号与私有网络地址不入 Git。

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
| 共享 PostgreSQL `15432` 正向连通 | ⬜ 未通过 | Navicat 失败、TCP 不通；待 A 排查（报错原文待 B 补） |
| Tailscale 双机正向/负向 | ⬜ 未完成 | 本机 tailnet 内对端数为 0；另有 M1-14 的完整双机验收 |
| VPN 开/关两态、未获准设备负向 | ⬜ 未验证 | 属 M1-14 范围 |
| 共享 PostgreSQL 门禁用例 | ⬜ 仍 skipped | 需 `AGENTEXAM_RUN_IDENTITY_POSTGRES=1` + 可达 PG；**如实记为 skipped，不记为通过** |
| 本机在**新 main** 上重跑 | ⬜ 未做 | 环境已就绪；`main` 已含 `7553ce0`，可按 4 passed 预期重跑并核对那 2 个 Harbor 失败 |
| 实时 OpenAPI 计数 | ✅ 已复核 | 用真实装配读 OpenAPI：**32 个端点，与 §2.1 的 32 条逐条集合比对差异 0**（2026-09-21，见上） |
| OpenAPI 字段级 schema 对账 | ⬜ 未做 | 仅做过 §10.4 正文与实现的 20/20 静态字段对照 |
| `ruff` / `mypy` | ⬜ 未在 B 侧运行 | 工具可用；fengyy 的记录称其干净，B 未复现 |
| 与 D 的工作重复 | ✅ 已关闭 | D 于 2026-09-21 拍板：接受 `main` 为最终形态，`cdcb4cf`/`c5e036d` 不再合入，以 `7553ce0` 为准；"不收敛"决定作废；`xinyue-modules` 转历史存档。**收尾提交已核实**：`3930f24`（关闭提案）与其子提交 `775d7a1`（更正已归档提案）都在远端，`git ls-remote` 权威值为 `775d7a1d065632064de2c3d5f0636f7eb03a80c2`。另记一条拓扑事实：**D 的 `origin` 就是团队仓库本身**（只配了一个 remote、没有 fork），她的推送直达 `anphuchoang5-sys/agent-exam`，与 B 的 fork 提 PR 路径不同 |
| 任务 03 的 Web 对比页 | ✅ 已完成 | 契约（PR #7）、后端（`7553ce0`）与 Web 页面（PR #8）均已合入 `main`；见[对比页行动](actions/03-comparison-ui.md) |
| 任务 03 正式 issue | ❓ 待确认 | `.scratch` 下无 `03-*` 任务单，是否发布待 B 决定 |
