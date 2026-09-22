# 阶段 1（05）实施方案

> **状态（2026-09-22 按实际进度同步）：S1–S8 与 T1 已实施完毕**，其中 `service.py` 按[服务实施计划](STAGE1_PROXY_SERVICE_PLAN.md)拆为 S6a–S6e 五片全绿，S8 含受控身份与预设。**S9、S10、S11 未做，均等 T2**（口径统一：S9 的绑定接法由 T2 决定）。用户已于会话内同意本机实施开工与 T1 执行（负责人 2026-09-21 书面回执原写"未授予实施开工许可"，**仍待其补一句书面确认**）。**T2 的窗口已可用、资源范围已确认，仍缺一句书面授权与在那台机器上的实际执行。**
>
> 权威边界：文件树与候选实现边界见[实现地图第 3 节](../../../.scratch/ui-catalog-providers/implementation-map.md)；步骤与验收见[计划第 7 节](../../../.scratch/ui-catalog-providers/plan.md)；秘密边界见[认证接口第 4.1、5 节](../../interfaces/CODEX_AUTHENTICATION.md)；数值见[设计冻结底稿](STAGE1_PROXY_DESIGN_FREEZE.md)。本文不复制其正文。
>
> 维护人：LLY（成员 E）　日期：2026-09-21，状态同步 2026-09-22

## 1. 本次前提变更：本机已安装 Docker

原方案的前提是"E 的开发机不装 Docker，容器与网络部分全部在负责人机器上"。该前提**已变更**：

| 项 | 变更前 | 现在（2026-09-21 实测） |
|---|---|---|
| 本机 Docker | 未安装 | **已安装**：CLI 29.6.2 + Docker Desktop；**守护进程当前未运行** |
| WSL | 未核 | 存在 Ubuntu-22.04 |
| `framework/harbor` | 只在负责人机器 | **不变**——本机仍没有（`.gitignore` 排除） |

**因此机器分工修订为**：容器能力不再是"负责人独有"，但"固定 Harbor 是否允许替换网络附加"仍只能由负责人机器回答。拓扑实证据此**拆成两半**（见第 5 节）。

**同时如实记录一处风险**：阶段 0 当时**明确决定不装 Docker**，理由是"Docker 依赖虚拟网络，与本机现有的网络驱动问题叠加会放大风险"（同机 Tailscale 的 wintun 虚拟网卡装不上、aTrust 虚拟网卡同样失败，问题在网络设备安装层）。本机 Docker 能否创建自定义网络**已于 2026-09-21 验证通过**（见第 5 节 T1 执行结果）。

## 2. 文件树（**实际已建**，2026-09-22 按 `git ls-files` 核对）

```text
apps/backend/src/eval_platform/
├─ adapters/execution/provider_access/          # 已建（顶层 7 文件）：代理的内部实现，不向应用暴露新业务端口
│  ├─ __init__.py                               #   内部导出
│  ├─ secrets.py                                #   私有文件权限/结构验证与可信读取（注册上游清单）
│  ├─ request_policy.py                         #   字段/模型/工具白名单与出站前拒绝
│  ├─ budget.py                                 #   原子预留、usage 结算、未知关闭（A 保守上界）
│  ├─ binding.py                                #   Run 绑定与令牌生命周期
│  ├─ transport.py                              #   固定 HTTPS 上游；无跳转/重试/正文日志
│  ├─ failures.py                               #   内部错误码 → 受控文案映射（含词汇表门禁）
│  └─ server/                                   # 已建（8 文件，已达每层上限）：入口、流与生命周期
│     ├─ service.py                             #   六步失败关闭流水线（形状→鉴权→策略→凭据→预留→出站）
│     ├─ http.py                                #   入站表面：受控文案应答、字节透传、客户端消失也结算
│     ├─ stream.py                              #   SSE 分帧与终止事件/usage 的有界扫描
│     ├─ runner.py                              #   执行即结算：任何结束都只结算一次
│     ├─ egress.py                              #   全项目唯一开 socket 处：一次尝试、不跟随重定向
│     ├─ closure.py                             #   撤销令牌 + 关闭账本（首个原因不被改写）
│     ├─ contracts.py                           #   跨边界值
│     └─ __init__.py
├─ adapters/execution/codex/provider_config.py  # 已建：固定 TOML 渲染 + sha256（只接受环境变量名）
├─ application/agent_registry.py                # 已改：只登记已审核预设，成对校验受控身份
├─ domain/agent.py                              # 已改：`CONTROLLED_IDENTITIES` 为唯一权威清单
├─ delivery/http/catalog_schemas.py             # 已改：按记录如实呈现；超集合抛 CatalogUnavailable（503）
├─ delivery/catalog_presets.py                  # 已改：受控预设单独一份，生产 `AGENT_PRESETS` 不含假服务
├─ adapters/persistence/catalog/schema.sql      # 已改：两条 CHECK 改为受控集合并命名
├─ adapters/persistence/catalog/__init__.py     # 已改：`upgrade_api_constraints()` 显式升级（未新增 .sql）
└─ delivery/worker/runtime.py                   # **未改（S9）**：仍无条件要求 ChatGPT auth、单一 adapter

apps/backend/tests/providers/                   # 已建：分层门禁（166 条用例）
├─ policy/                                      # 已建（8 文件，达每层上限）：策略、令牌、账本、秘密、受控文案
├─ contract/                                    # 已建：假 Responses 上游 + 事件构造 + 独立启动脚本
├─ lifecycle/                                   # 已建：终止路径、结算一次、秘密外表面（56 条用例）
└─ runtime/                                     # 已建：T1 拓扑探针 5 文件，负责人机器可直接复用
                                                # 未建：S10 的 `net/` 与 S11 的集成层入口（`Dockerfile.proxy`/`verify.ps1`）
```

注意三点：① `provider_access/` 顶层 7 文件、`server/` 8 文件（**均达每层上限**），因此 S10 的 `net/` 必须落成**子目录**；② `tests/providers/policy/` 8 文件（达上限），新增用例需落在子目录；③ T1 探针原计划为 `verify.ps1`（沿用 catalog/jobs 的 PowerShell 入口），实际按 E 本机已跑通的 bash 版本纳入（`tests/providers/runtime/` 现 5 文件，仍有 3 个空位）；T2 若需要容器内跑 pytest，仍可另加 `verify.ps1`。

## 3. 分片顺序

每片按"一个失败用例 → 最小实现 → 通过 → 回归"推进。**S2–S8 不依赖拓扑结论**（S2 仅剩字段名与事件词表需在 T2 现场用固定 CLI 对账）；**S9、S10、S11 均等 T2**——S9 决定的是"worker 按 Run 选绑定"的接法，而绑定形态（代理入口、令牌来源、网络附加方式）由 T2 的拓扑结论决定。此前本节写"S2–S9 不依赖拓扑结论"，与[服务实施计划](STAGE1_PROXY_SERVICE_PLAN.md)第 3 节冲突；**2026-09-22 按较新文档统一为"S9 依赖 T2"**（用户确认）。

| 片 | 内容 | 位置 | 等拓扑？ | 状态（2026-09-22） |
|---|---|---|---|---|
| S1 | 设计冻结定稿：数值已确认（负责人 2026-09-21），机制部分定稿并标注候选/未证 | E 本机 | 否 | 数值已回填；机制候选；**"请求字段白名单"仍待 T2 现场用固定 CLI 复核** |
| S2 | `provider_config.py`：TOML 渲染 + 摘要；**显式写入 `request_max_retries = 0` 与 `stream_max_retries = 0`** | E 本机 | 否（对账在 T2） | **已完成**；两个重试参数在顶层与 provider 表**并列各写一次**（仓库内无"固定 0.153.0 读哪一层"的依据），字段名与事件词表待 T2 对账 |
| S3 | `secrets.py`：私有文件为普通文件、非链接、属主与最小权限；拒绝共享/同步目录与宽读权限 | E 本机 | 否 | **已完成** |
| S4 | `request_policy.py`：字段/模型/工具白名单；未知字段一律拒绝；剥离客户端认证头 | E 本机 | 否 | **已完成** |
| S5 | `budget.py`：A 保守上界计数（记录高估公式并证明不低估）、原子预留、usage 缺失/断流失败关闭、重启不重置 | E 本机 | 否 | **已完成** |
| S6 | `binding.py` + `service.py`：Run 绑定、令牌生命周期、代理入口与流；权限与错误码映射 | E 本机 | 否（**网络接线属 S10**） | **已完成**：`binding.py` 完成；`service.py` 按服务计划拆为 **S6a–S6e 五片全绿**（`server/` 8 文件、56 条用例） |
| S7 | `transport.py`：固定上游、不跟随重定向、不重试、无正文日志 | E 本机 | 否 | **已完成** |
| S8 | 目录与身份扩展：`domain/agent.py`、`agent_registry.py`、`catalog_schemas.py`、`catalog_presets.py`、`schema.sql`、升级入口；旧指纹兼容 | E 本机（需真实 PG） | 否 | **已完成**：库级约束改为受控集合并命名，升级复用既有模式（`upgrade_api_constraints()`，未新增 `.sql`），已在本机真实旧库实测 |
| S9 | `delivery/worker/runtime.py`：按 Run 选绑定，不再无条件要求 ChatGPT auth | E 本机 | **是**（绑定接法由 T2 决定） | **未做**，等 T2 |
| S10 | `net/`（原 `network.py`）与网络拓扑接线 | 待定 | **是** | **未做**，等 T2 |
| S11 | 集成层验证：容器拓扑、直连拒绝、宿主隔离、假 Key 探查、精确清理 | 负责人机器 | 是 | **未做**；T1 探针已入仓库 `apps/backend/tests/providers/runtime/` 供复用，T2 窗口已可用、待一句书面授权与执行 |

## 4. 每片的验证方式

| 层次 | 手段 | 开关 / 入口 |
|---|---|---|
| 静态 | `ruff check`、`ruff format --check`、`mypy`（用 `MYPYPATH=src` 路径方式；裸跑 `mypy` 在本机解析到未装 `py.typed` 的包，属工具链事实，见 B 的记录） | 现有命令，无开关 |
| 策略 / 契约 / 生命周期 | `pytest tests/providers/{policy,contract,lifecycle}` 用替身与假上游 | 无需开关，默认回归即运行 |
| 真实 PG | 目录与身份扩展片；复用阶段 0 的 `agentexam_dev` / `agentexam_identity_test` | `AGENTEXAM_RUN_*` 既有开关 |
| 集成 | 容器拓扑与清理 | T1（纯 Docker 层）：任意有 Docker 的机器，`bash tests/providers/runtime/topology-probe.sh`；T2（固定 Harbor）仅负责人机器 |

"出站计数为 0"一律**以假上游服务的请求记录为证**，不凭日志文本推断。受控文案（`failure_summary` / `stage_message`）按[设计冻结第 3.7 节](STAGE1_PROXY_DESIGN_FREEZE.md)断言不命中哨兵值。

## 5. 拓扑实证拆成两半（T1 已完成，T2 未执行）

| 半 | 要回答的问题 | 位置 | 依赖 |
|---|---|---|---|
| **T1** | **这套双网络拓扑能否形成"做题侧只通代理、只有代理侧出网"的边界**（与 Harbor 无关的纯 Docker/Compose 层） | **E 本机（新可能）** | 本机 Docker 能创建自定义网络（**已通过**） |
| **T2** | **固定 Harbor 是否允许替换或绕过它自己的侧车网络附加** | 负责人机器 | `framework/harbor` |

T1 可覆盖任务 05 断言清单中**不依赖 Harbor 的全部条目**：做题侧→代理通、做题侧→公网不通、做题侧→宿主网关/metadata 不通（"其他 Trial 网络"用第二个容器模拟）、代理→假上游通、结构检查、假 Key 正对照、进程与文件隔离。T2 只回答"能否接到固定 Harbor 上"。

**T1 的价值**：本机先把拓扑概念证掉，负责人那边只需做 Harbor 集成那一半，风险与工作量都小得多；若拓扑本身不成立，也能最早发现。
**T1 的边界（不得混淆）**：T1 通过**不等于**任务 05 的拓扑验收通过——最终仍须在固定 Harbor 上成立。T1 是降风险，不是验收。

T1 第一步必须先验证**本机 Docker 能否创建自定义网络**（前置第 1 项，2026-09-21 已通过）。若本机因虚拟网络问题无法创建，则退回原方案：两半都在负责人机器做——**该退回分支未触发**。

**T1 执行结果（2026-09-21）**：本机 Docker 能创建自定义网络（前置第 1 项通过）；探针七条断言全部测到并通过（**28 项判定**全 PASS，连续两次一致），并附反向对照自检（故意把做题侧接进出网网络时断言 2/3 如预期失败）。**T2 仍未执行**——固定 Harbor 是否允许替换侧车网络附加仍无结论。证据见[本机实施行动](../../actions/2026-09-21-task05-local-implementation.md)。

## 6. 待授权清单

状态更新（2026-09-22）：

1. **任务 05 本机实施**——用户已在会话内同意（①任务 05 实施开工、②T1/T2 拆分、③T1 在本机执行），**S1–S8、T1 与 S6a–S6e 已按其执行完毕**。**负责人书面回执原写"未授予实施开工许可"，该书面确认至今未补**（2026-09-22 复核，任务单 Comments 已记录此缺口）。
2. **T1 在本机的执行授权**——已获用户同意并已执行完毕：探针 run 02 七条断言全部通过，资源按 `agentexam.task=05` 标签精确创建与删除、残留复核为 0、未执行全局 prune。
3. **T2 在负责人机器的窗口与执行授权**——**窗口已可用**（用户 2026-09-21 告知）、**资源范围已确认**；**仍缺一句书面授权与在那台机器上的实际执行**，固定 Harbor 上的 7 条断言因此仍未执行。执行命令与回报要求见[组长机器预案附二](../../actions/2026-09-21-task05-owner-machine-runbook.md)。

## 7. 权威来源

| 内容 | 位置 |
|---|---|
| 候选文件树与实现边界 | `.scratch/ui-catalog-providers/implementation-map.md` 第 3、5 节 |
| 步骤、验收、停止条件 | `.scratch/ui-catalog-providers/plan.md` 第 7 节 |
| 秘密边界与强制安全约束 | `docs/interfaces/CODEX_AUTHENTICATION.md` 第 4.1、5 节 |
| 面向用户的受控文案 | `docs/interfaces/HTTP_API.md` 第 10.2 节 |
| 已确认数值与剩余边界 | `docs/LLY/01-plan/STAGE1_PROXY_DESIGN_FREEZE.md` |
| 测试归属与断言 | `docs/LLY/01-plan/STAGE1_PROXY_TEST_DESIGN.md` |
| 负责人侧执行范围 | `docs/LLY/01-plan/TASK05_OWNER_ACTION_REQUIRED.md` |
| 实时进度与实测数字 | `docs/LLY/03-progress/PROGRESS_LOG.md` |

本文只是把权威要求编排成可执行顺序，**不替代**上述文件，也不构成开工或执行授权。
