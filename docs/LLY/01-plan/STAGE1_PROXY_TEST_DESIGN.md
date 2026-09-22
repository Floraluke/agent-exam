# 阶段 1（05 假提供方安全执行链）测试设计

> 状态（2026-09-22 按实际进度同步，含合并 `origin/main`）：**准备性设计；其中的用例归属已在 `tests/providers/{policy,contract,lifecycle,runtime}` 落地**。任务 05 已进 `main`，本机实施已获会话内实施开工同意；**集成层（负责人机器）部分仍等 T2**。本文件保留"权威验收要求 → 测试归属、断言与运行位置"的映射，不代表集成层测试已运行。
>
> 合并说明：本文件曾与 `origin/main` 的同名状态行冲突，对方那版写"准备性设计，未开工/实施开工与拓扑探针仍未获当轮授权"，是**本分支切片落地之前**的表述，已被上行取代；对方分支对被本文件描述的策略层所做的加固（出站头白名单、错误码类型化）见[进度日志](../03-progress/PROGRESS_LOG.md) 2026-09-22 的"核心诊断修复后对账"。
>
> 边界：本文件只做"把权威验收要求映射成可执行测试"这一层——测试归属、断言、运行位置与开工前必须冻结的未知。负例清单、安全候选、机制设计与预算的权威正文见第 1 节，本文不复制。
>
> 维护人：LLY（成员 E）　日期：2026-09-21，状态同步 2026-09-22

## 1. 权威来源（唯一事实源）

| 内容 | 唯一维护位置 |
|---|---|
| 代理机制、秘密边界、最小机制设计六条 | [认证接口第 4.1 节](../../interfaces/CODEX_AUTHENTICATION.md#41-codex-第三方-api-扩展规划2026-09-17)、[第 5 节强制安全约束](../../interfaces/CODEX_AUTHENTICATION.md#5-实现时的强制安全约束) |
| 代理与限额的负例矩阵 | [验证规范第 4 节](../../../.scratch/ui-catalog-providers/verification.md) |
| 候选内部树、安全候选、兼容方案 | [实现地图第 3、4、5 节](../../../.scratch/ui-catalog-providers/implementation-map.md) |
| 型号、端点、人民币价格、预算推导 | [提供方配置与预算研究](../../research/2026-09-17-codex-provider-config-and-budget.md) |
| 05 的步骤、验收与停止条件 | [执行计划第 7 节](../../../.scratch/ui-catalog-providers/plan.md) |

## 2. 测试分层与运行位置

本机（`D:\agent-exam`）原按阶段 0 决定不安装 Docker，且 `framework/`、`runtime/`、固定镜像只在组长机器上。因此**设计的第一原则是让绝大多数断言落在不需要容器的一层**，把容器依赖压到最小。

> **2026-09-21 前提变更**：本机已安装 Docker Desktop（CLI 29.6.2，守护进程未运行），容器能力不再是负责人机器独有；但 `framework/harbor` 仍只在负责人机器。拓扑实证据此拆为**纯 Docker/Compose 层（本机可做）**与**固定 Harbor 集成层（仍须负责人机器）**，见[任务 05 实施方案](STAGE1_IMPLEMENTATION_PLAN.md)第 5 节。
>
> **2026-09-22 进展**：T1 已在纯 Docker 层证成（探针七条断言全部测到并通过，含反向对照自检），T2 仍未执行；下表已按拆分后的实际运行位置更新。

| 层 | 覆盖什么 | 运行位置 | 依赖 |
|---|---|---|---|
| 策略层 `tests/providers/policy/` | 请求白名单、令牌边界、账本算术、秘密外表面 | **本机（已落地，8 文件）** | 纯 Python + 替身，无 IO |
| 契约层 `tests/providers/contract/` | 假上游的请求记录、拒绝形状、事件构造 | 本机（**已落地**） | 仓库内假 Responses 上游（明文 HTTP；代理→上游的 TLS 包装属集成层）；**固定 CLI 的字段名与事件词表对账待 T2** |
| 生命周期层 `tests/providers/lifecycle/` | 五种结束路径的收束与令牌回收 | **本机（已落地，56 条用例）** | 现有 job/orchestrator 测试替身 |
| 集成层 | 容器拓扑、直连拒绝、宿主隔离、精确清理 | T1 探针在 `tests/providers/runtime/`（**任意有 Docker 的机器，本机已跑**）；T2 入口（`Dockerfile.proxy`/`verify.ps1`）**未建，仅负责人机器** | Docker；`framework/harbor` **仅 T2 需要** |

原则：**新增容器断言前先问"能否用替身在本机证同一件事"**。集成层只保留"必须由真实隔离环境才能证伪"的项。

## 3. 负例到可执行测试的映射

下表把[验证规范第 4 节](../../../.scratch/ui-catalog-providers/verification.md)的五组要求逐条落成测试归属。用例名是设计建议，不是已存在的测试。

### 3.1 出站前拒绝（策略层，本机）

| 负例 | 建议用例 | 断言 |
|---|---|---|
| 未批准 / 错误 profile | `test_reject_unapproved_run`、`test_reject_unknown_profile` | 假上游收到请求数 **0**；错误不含路径与 Key |
| 缺密钥 / 宽权限 / 链接文件 | `test_reject_missing_secret`、`test_reject_wide_permissions`、`test_reject_symlinked_secret` | 绑定失败关闭，出站 0 |
| 错误模型 / 路径 / Host | `test_reject_unlisted_model`、`test_reject_unlisted_path`、`test_reject_unlisted_host` | 出站 0 |
| 任意 Authorization | `test_strip_client_auth_header` | 客户端认证头被剥离；上游只收到代理注入的凭据 |
| URL / 重定向 | `test_reject_absolute_url`、`test_no_redirect_follow` | 出站 0 或跳转不跟随 |
| 额外远程工具 | `test_reject_unlisted_tool` | 出站 0 |

计数手段：**假上游服务本身就是计数器**——断言它的请求记录长度而非日志文本。这样"出站 0"是可证事实，不是推断。

### 3.2 越权与绕过（策略层，本机）

| 负例 | 建议用例 | 断言 |
|---|---|---|
| 跨 Run 令牌 | `test_token_bound_to_single_run` | 令牌在另一 `run_id` 上被拒 |
| 过期 / 撤销令牌 | `test_reject_expired_token`、`test_reject_revoked_token` | 期限与撤销各自独立生效 |
| 同令牌重放超额 | `test_reject_replay_over_quota` | 不扩大已授权限 |
| 客户端改 TOML / CLI / env | `test_client_override_cannot_widen_scope` | 容器侧改动不扩大权限（依据研究第 6.1 节的命令行覆盖事实） |
| 直连供应商 / 宿主 / metadata / 其他 Trial | 集成层 `test_reject_direct_egress_paths` | 做题侧对这些目标的直连全部拒绝，**仅组长机器** |
| IPv6 / DNS 旁路 | 集成层 `test_reject_bypass_paths` | 需真实网络隔离，**仅组长机器** |

### 3.3 秘密外表面（策略层，本机）

用**假 Key**探查，绝不使用真实凭据（验证规范明确"假值探查也是秘密保护测试，不复制任何真实 Key"）。

| 探查面 | 建议用例 | 断言 |
|---|---|---|
| argv / 共享 env | `test_fake_key_absent_from_argv_and_env` | 假 Key 在参数与共享环境变量中 0 命中 |
| 容器配置可见面 | `test_fake_key_absent_from_rendered_config` | 渲染后的 TOML 只含代理地址、模型与令牌来源 |
| 日志 / 轨迹 / 错误 | `test_fake_key_absent_from_logs_and_errors` | 含探针主动制造失败的路径 |
| 数据库 / 制品 / 公开报告 | `test_fake_key_absent_from_persisted_outputs` | 复用现有存储替身 |
| 代理自身 | `test_proxy_holds_secret_only_in_memory` | 代理侧无正文日志 |

以下两项必须在真实容器内探查，**仅组长机器**：

| 探查面 | 建议用例 | 断言 |
|---|---|---|
| 容器文件 / 进程 | 集成层 `test_fake_key_absent_from_container_fs_and_processes` | 做题侧文件系统与进程环境 0 命中 |
| Docker inspect / patch | 集成层 `test_fake_key_absent_from_inspect_and_patch` | 检视输出与收集到的补丁 0 命中 |

### 3.4 预算与计量（策略层，本机）

| 场景 | 建议用例 | 断言 |
|---|---|---|
| 原子预留 | `test_reserve_is_atomic_under_concurrency` | 并发下不超发 |
| 恰好临界 / 超一单位 | `test_boundary_exact`、`test_boundary_over_by_one` | 临界放行、超一单位拒绝 |
| 多轮累计含反复历史 | `test_multi_turn_accounting_includes_history` | 累计不因轮次重置 |
| 输出含推理 Token | `test_output_includes_reasoning_tokens` | 与研究第 2 节的官方口径一致 |
| 断流 / 未知 usage | `test_unknown_usage_fails_closed` | **保守占用并停止新增调用，不把未知当零、不退款为零** |
| 429 / 5xx / CLI 重连 | `test_provider_errors_do_not_expand_budget` | 不静默增额、不自动重试 |
| 进程重启 / 状态丢失 | `test_lost_ledger_state_refuses_new_run` | 失去已花费证据时失败关闭，不重置为满额 |

### 3.5 生命周期与清理

| 场景 | 建议用例 | 位置 | 断言 |
|---|---|---|---|
| 正常结束 / 错误 / 模型超时 | `test_termination_contracts` | 生命周期层（替身） | 按合同收束，旧 Job 不续跑 |
| 协作取消 / 外层超时 | 复用现有 cancel/cleanup 测试入口 | 生命周期层 | 取消语义不变，不因代理机制强杀当前 Trial |
| 代理 / Worker 崩溃 | `test_crash_leaves_no_continuation` | 生命周期层 + 集成层 | 只能按已持久化证据收束 |
| 新 Job 重试 | `test_retry_creates_new_job_awaiting_approval` | 生命周期层 | 重试创建全新 Job 并**重新等待 owner 批准**，不复用旧授权 |
| 令牌撤销与资源清理 | `test_exact_cleanup_after_each_outcome` | **仅组长机器** | 专属容器/网络/卷残留为 0，失败资源单列 |

## 4. 开关与验证入口（沿用现有约定）

| 项 | 候选值 | 依据 |
|---|---|---|
| 显式开关 | `AGENTEXAM_RUN_PROVIDER_PROBE=1` | 现有 13 个开关均为 `AGENTEXAM_RUN_<区域>=1` 形态 |
| 分层入口 | `tests/providers/runtime/verify.ps1` | 现有 `tests/catalog/runtime/verify.ps1`、`tests/jobs/runtime/verify.ps1` |
| 门禁原则 | 未设开关时全部 skip，不得计为通过 | 现有默认回归的 82–84 项跳过即此模式 |

命名与目录均为**候选**，需在 05 正式发布时按当时实现确认；不在本次创建任何目录或文件。

## 5. 开工前必须先冻结、现在不得预设

这些是实现地图第 5 节与认证接口第 4.1 节明示**尚未验证**的项。测试设计必须等它们冻结后再落代码，否则测试会变成对假设的编码。

> **2026-09-22 状态**：四项里已有三项冻结（见下），仅"请求字段白名单"仍待 T2 现场用固定 CLI 复核。本节保留为设计记录。
>
> 合并说明：对方分支（`origin/main`）的同名清单是**实施之前**的版本，写"账本可执行算法未实现""私有文件尚未创建或验权"，与本分支已完成的 S5/S3 实现不符，故采用下方本分支版本；对方版本未含本清单之外的额外事实。

1. **Token 上界、请求字段白名单、账本具体格式**——**数值部分已冻结**（负责人 2026-09-21 拍板：输入 300,000 / 输出 32,000 / 期限 900 秒 / 频率 3 次每分钟 / 支出目标 ¥100，第 7 项选 A 保守上界，见[设计冻结底稿第 3.4 节](STAGE1_PROXY_DESIGN_FREEZE.md)）；**账本格式已实现**（`budget.py` 的 A 保守上界计数，含"记录高估公式"并要求证明不低估）；**仅"请求字段白名单"仍待冻结**——须在 T2 现场用固定 CLI 0.153.0 复核字段名与事件词表。
2. **固定 CLI 是否需要容器承载**——研究第 6.1 节的探针证明了配置与请求路由事实，但探针边界未说明是否用容器封装；**待 T2 结论**（S10/S11 随拓扑一起定）。
3. **Compose 拓扑不能沿用侧车**——认证接口第 4.1 节第 5 条明确警告：现有主容器与网络侧车共享网络命名空间，照搬后不能宣称防绕过。**T1 已用独立双网络拓扑证成边界概念；接到固定 Harbor 上仍待 T2。**
4. **私有文件路径、格式与权限拒绝条件**——**已冻结并实现**：负责人 2026-09-21 选定仓库外私有路径、当前 Windows 用户为属主、绝对路径不入 Git（[设计冻结底稿](STAGE1_PROXY_DESIGN_FREEZE.md)）；拒绝条件落在 `secrets.py`（普通文件、非链接、最小权限、拒绝共享/同步目录）。

## 6. 前置条件与风险

| 项 | 影响 | 现状 |
|---|---|---|
| 第一步必须在组长机器（**2026-09-21 部分变更并已执行 T1**） | 原为"本机无 Docker，拓扑实证与集成层全部无法在本机运行"。本机已装 Docker；**T1（纯 Docker 层）已在本机证成**（7 条断言全通过，含反向对照自检），**T2（固定 Harbor 集成层）仍须负责人机器** | T1 与 Harbor 无关，**T1 通过不等于第 2 项验收通过**；T2 资源范围已确认、**窗口已可用**（2026-09-21 用户告知），仍缺一句书面授权与实际执行 |
| 05 已发布（**2026-09-22 更正**） | 本文件不能替代任务单与验收依据 | 05 已发布且已进 `main`（`6ccf001` 是 `origin/main` 的祖先），本机实施已获会话内实施开工同意；任务单与 Comments 为准 |
| 04 已发布并验收完成（**2026-09-22 更正**） | 原记"E 在 04 中 12 h 的 Fork 资格验证" | 五题 ×（参考/空/错误）15/15 场景由 C 在负责人机器执行完毕，证据见 `runtime/fork-evidence/`；**该事实的工时归属仍待与负责人确认** |
| 真实调用授权 | 06/07 的前置，与 05 的假提供方阶段分离 | 历史 ChatGPT 许可不覆盖 DeepSeek/Kimi |

## 7. 本文不构成什么

- 不构成 05 的实施授权，不构成对 03–08 任何任务的开工许可。
- 不声称任何测试已编写或已运行；本机未创建 `tests/providers/`，未运行产品测试。
- 不复制权威正文；所有验收要求以第 1 节链接的文件为准，两者冲突时以权威文件为准。
