# 阶段 1（05）实施方案

> **状态：方案就绪，未获实施开工授权。** 任务 05 仍为 `needs-info`；负责人 2026-09-21 回执明确"未授予实施开工许可，第 2–4 步仍须等待任务状态和开工授权；第 5 步还须等待单独的机器窗口与执行授权"。**本文是准备材料，不是开工命令。**
>
> 权威边界：文件树与候选实现边界见[实现地图第 3 节](../../../.scratch/ui-catalog-providers/implementation-map.md)；步骤与验收见[计划第 7 节](../../../.scratch/ui-catalog-providers/plan.md)；秘密边界见[认证接口第 4.1、5 节](../../interfaces/CODEX_AUTHENTICATION.md)；数值见[设计冻结底稿](STAGE1_PROXY_DESIGN_FREEZE.md)。本文不复制其正文。
>
> 维护人：LLY（成员 E）　日期：2026-09-21

## 1. 本次前提变更：本机已安装 Docker

原方案的前提是"E 的开发机不装 Docker，容器与网络部分全部在负责人机器上"。该前提**已变更**：

| 项 | 变更前 | 现在（2026-09-21 实测） |
|---|---|---|
| 本机 Docker | 未安装 | **已安装**：CLI 29.6.2 + Docker Desktop；**守护进程当前未运行** |
| WSL | 未核 | 存在 Ubuntu-22.04 |
| `framework/harbor` | 只在负责人机器 | **不变**——本机仍没有（`.gitignore` 排除） |

**因此机器分工修订为**：容器能力不再是"负责人独有"，但"固定 Harbor 是否允许替换网络附加"仍只能由负责人机器回答。拓扑实证据此**拆成两半**（见第 5 节）。

**同时如实记录一处风险**：阶段 0 当时**明确决定不装 Docker**，理由是"Docker 依赖虚拟网络，与本机现有的网络驱动问题叠加会放大风险"（同机 Tailscale 的 wintun 虚拟网卡装不上、aTrust 虚拟网卡同样失败，问题在网络设备安装层）。本机 Docker 能否创建自定义网络**尚未验证**，这正是前置核对第 1 项"创建能力未实证"所指。

## 2. 文件树（按实现地图第 3 节候选树；本次不创建）

```text
apps/backend/src/eval_platform/
├─ adapters/execution/provider_access/      # 新增：代理的内部实现，不向应用暴露新业务端口
│  ├─ __init__.py                           # 内部导出
│  ├─ binding.py                            # Run 绑定；有限 provider 选择
│  ├─ secrets.py                            # 私有文件权限/结构验证与可信读取
│  ├─ service.py                            # 代理入口、鉴权、流生命周期
│  ├─ request_policy.py                     # 路径/字段/模型/工具白名单与出站前拒绝
│  ├─ transport.py                          # 固定 HTTPS 上游；无跳转/重试/正文日志
│  ├─ budget.py                             # 原子预留、usage 结算、未知关闭（A 保守上界）
│  └─ network.py                            # 私有拓扑组合与正反可达性预检
├─ adapters/execution/codex/provider_config.py  # 新增：固定 TOML/模型目录渲染及摘要
├─ adapters/execution/harbor/               # 修改：已有映射与生命周期；根目录保持 8 文件
├─ application/agent_registry.py            # 修改：只登记已审核的 API 预设
├─ domain/agent.py                          # 修改：新身份版本；旧指纹完全兼容
├─ delivery/http/catalog_schemas.py         # 修改：受控目录响应，不接受 Key/URL
├─ delivery/catalog_presets.py              # 修改：非秘密提供方模板
├─ delivery/worker/runtime.py               # 修改：不再无条件要求 ChatGPT auth，按 Run 选绑定
└─ adapters/persistence/catalog/
   ├─ schema.sql                            # 修改：新安装约束；不增加表
   └─ upgrade_api.sql                       # 新增（候选）：显式升级旧约束，不自动开机迁移

apps/backend/tests/providers/               # 新增：分层门禁
├─ policy/                                  # 请求策略、令牌边界、账本、秘密外表面（本机）
├─ lifecycle/                               # 终止路径与令牌回收的替身测试（本机）
├─ integration/                             # 容器拓扑、直连拒绝、清理（负责人机器）
└─ runtime/verify.ps1                       # 分层验证入口（沿用 catalog/jobs 既有模式）
```

注意两点：`provider_access/` 恰好 8 个文件，已达每层文件夹上限，**内部如需再拆必须建子目录**；`tests/providers/` 同为上限边界。

## 3. 分片顺序

每片按"一个失败用例 → 最小实现 → 通过 → 回归"推进。**S2–S9 不依赖拓扑结论**，可与拓扑实证并行；只有 S10 必须等。

| 片 | 内容 | 位置 | 等拓扑？ |
|---|---|---|---|
| S1 | 设计冻结定稿：数值已确认（负责人 2026-09-21），机制部分定稿并标注候选/未证 | E 本机 | 否 |
| S2 | `provider_config.py`：TOML 渲染 + 摘要；**显式写入 `request_max_retries = 0` 与 `stream_max_retries = 0`** | E 本机 | 否 |
| S3 | `secrets.py`：私有文件为普通文件、非链接、属主与最小权限；拒绝共享/同步目录与宽读权限 | E 本机 | 否 |
| S4 | `request_policy.py`：字段/模型/工具白名单；未知字段一律拒绝；剥离客户端认证头 | E 本机 | 否 |
| S5 | `budget.py`：A 保守上界计数（记录高估公式并证明不低估）、原子预留、usage 缺失/断流失败关闭、重启不重置 | E 本机 | 否 |
| S6 | `binding.py` + `service.py`：Run 绑定、令牌生命周期、代理入口与流；权限与错误码映射 | E 本机 | 否 |
| S7 | `transport.py`：固定上游、不跟随重定向、不重试、无正文日志 | E 本机 | 否 |
| S8 | 目录与身份扩展：`domain/agent.py`、`agent_registry.py`、`catalog_schemas.py`、`catalog_presets.py`、`schema.sql`、`upgrade_api.sql`；旧指纹兼容 | E 本机（需真实 PG） | 否 |
| S9 | `delivery/worker/runtime.py`：按 Run 选绑定，不再无条件要求 ChatGPT auth | E 本机 | 否 |
| S10 | `provider_access/network.py` 与网络拓扑接线 | 待定 | **是** |
| S11 | 集成层验证：容器拓扑、直连拒绝、宿主隔离、假 Key 探查、精确清理 | 负责人机器 | 是 |

## 4. 每片的验证方式

| 层次 | 手段 | 开关 / 入口 |
|---|---|---|
| 静态 | `ruff check`、`ruff format --check`、`mypy` | 现有命令，无开关 |
| 策略 / 契约 / 生命周期 | `pytest tests/providers/{policy,contract,lifecycle}` 用替身与假上游 | 新增候选开关 `AGENTEXAM_RUN_PROVIDER_PROBE=1`（沿用现有 13 个 `AGENTEXAM_RUN_*` 形态） |
| 真实 PG | 目录与身份扩展片；复用阶段 0 的 `agentexam_dev` / `agentexam_identity_test` | `AGENTEXAM_RUN_*` 既有开关 |
| 集成 | 容器拓扑与清理 | 仅负责人机器；`tests/providers/runtime/verify.ps1` |

"出站计数为 0"一律**以假上游服务的请求记录为证**，不凭日志文本推断。受控文案（`failure_summary` / `stage_message`）按[设计冻结第 3.7 节](STAGE1_PROXY_DESIGN_FREEZE.md)断言不命中哨兵值。

## 5. 拓扑实证拆成两半

| 半 | 要回答的问题 | 位置 | 依赖 |
|---|---|---|---|
| **T1** | **这套双网络拓扑能否形成"做题侧只通代理、只有代理侧出网"的边界**（与 Harbor 无关的纯 Docker/Compose 层） | **E 本机（新可能）** | 本机 Docker 能创建自定义网络 |
| **T2** | **固定 Harbor 是否允许替换或绕过它自己的侧车网络附加** | 负责人机器 | `framework/harbor` |

T1 可覆盖任务 05 断言清单中**不依赖 Harbor 的全部条目**：做题侧→代理通、做题侧→公网不通、做题侧→宿主网关/metadata 不通（"其他 Trial 网络"用第二个容器模拟）、代理→假上游通、结构检查、假 Key 正对照、进程与文件隔离。T2 只回答"能否接到固定 Harbor 上"。

**T1 的价值**：本机先把拓扑概念证掉，负责人那边只需做 Harbor 集成那一半，风险与工作量都小得多；若拓扑本身不成立，也能最早发现。
**T1 的边界（不得混淆）**：T1 通过**不等于**任务 05 的拓扑验收通过——最终仍须在固定 Harbor 上成立。T1 是降风险，不是验收。

T1 第一步必须先验证**本机 Docker 能否创建自定义网络**（前置第 1 项至今未勾）。若本机因虚拟网络问题无法创建，则退回原方案：两半都在负责人机器做。

## 6. 待授权清单

以下三项**均未取得**，不得由本方案或"9 项已确认"推断为已获得：

1. **任务 05 实施开工授权**——S1–S9 的代码实现。负责人本轮只授权填文档、同步分支、提交并推送。
2. **T1 在本机的执行授权**——启动 Docker Desktop、创建与删除专属网络/容器/卷；范围沿用负责人已确认的 `agentexam-t05-topology` 项目名、`internal`/`egress` 网络、`workload`/`proxy`/`fake-upstream` 服务与对应标签。
3. **T2 在负责人机器的窗口与执行授权**——资源范围已确认，窗口为空。

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

本文只是把权威要求编排成可执行顺序，**不替代**上述文件，也不构成开工或执行授权。
