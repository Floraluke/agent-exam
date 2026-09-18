# Harbor 执行后端接口

> 文档状态：架构已确认；第四场真实 Codex 单题与固定 Fork 判卷通过；M0 核心闭环已通过；任务 13 的 `-04` 正式 Job/Run、固定 Fork、持久化、真实页面和双轴终审均通过
>
> 最后更新：2026-09-17（API扩展规划；执行接口不变）
>
> Harbor 固定版本：以 [`DEPENDENCIES.md`](../dependencies/DEPENDENCIES.md) 中的完整提交为唯一事实源
> 权威范围：本文件维护 AgentExam `ExecutionBackend` 与 Harbor 之间的输入、输出、字段映射、错误和验收门槛。Harbor 来源与恢复方式见 [`DEPENDENCIES.md`](../dependencies/DEPENDENCIES.md)；Codex 与自研 Agent 的凭据所有权和秘密边界只在 [`CODEX_AUTHENTICATION.md`](./CODEX_AUTHENTICATION.md) 维护。

## 新扩展的执行边界（规划，未实施）

[UI/题库/API计划](../../.scratch/ui-catalog-providers/plan.md)保留一平台Job→一Harbor Job→逐Run/Trial以及独立固定Fork判卷，不重建执行链。新题须先完成固定镜像与离线资格检查；第三方Codex由现有Adapter按冻结配置选择内部绑定，原M0单题与ChatGPT路径保留。

新增代理为Trial内部可信辅助进程，不是HTTP业务服务、Worker或Evaluator。公开Execution请求不含Key/私有路径；真正开始已批准Run后才读取所需私有profile，网络、限额、令牌撤销与Key隔离见[认证4.1](./CODEX_AUTHENTICATION.md#41-codex-第三方-api-扩展规划2026-09-17)。现有共享网络命名空间侧车不能直接充当凭据代理，具体拓扑须通过专属合成正反例。

接口合同保持原状态、Observer准入、取消与崩溃恢复语义。代理故障或超限按现有基础设施/策略错误收束，不自动续跑、重试或切换供应商，不以代理机制擅自强杀当前协作取消中的Trial。新版本工具/网络/额度配置先冻结、再参与既有快照校验；现有租约必须覆盖实际准备/执行/判卷/收尾，代理准备不能形成无界等待。

配置请求的既有探针不证明完整Trial；具体假值→真实单题→矩阵门禁见[验证计划](../../.scratch/ui-catalog-providers/verification.md)。长期暂停后重新核对依赖身份与提供方事实，不改上游固定源码或静默升级CLI。

## 1. 先用小白能懂的话解释

一次用户操作可能选择 3 个 Agent 和 5 道题。AgentExam 把这次操作叫一个**评测 Job**；它在 PostgreSQL 排队。轮到它后，Harbor 收到一份执行计划，并把组合展开成 15 次独立尝试。Harbor 把每次尝试叫 **Trial**，AgentExam 把同一事实叫一条**评测运行**。

```text
1 个 AgentExam 评测 Job
    → 1 个 Harbor Job
        → N 个 Harbor Trial
            ↔ N 条 AgentExam 评测运行
```

Harbor 负责“让 Agent 做题并留下过程证据”，固定 SWE-Bench-Fork 负责“在干净环境判卷”。Harbor 自带的 reward 不能替代本项目最终判卷。

实现顺序固定为：先用本机脚本跑通一个 Codex 的真实 Harbor→patch→SWE-Bench-Fork 技术闭环；再接入 Web、PostgreSQL、所有者批准和正式报告，形成 Codex-only MVP；随后登记 Harbor 已有的 Aider、Claude Code；P2 最后才接自研 Agent。脚本原型不创建正式 Job、不进入排行榜，也不要求先实现 Web/数据库。

## 2. 模块 seam

```mermaid
flowchart LR
    O[Job Orchestrator] -->|ExecutionJobRequest + run_id Observer| P[ExecutionBackend interface]
    H[HarborExecutionAdapter] -. 实现 .-> P
    F[ProcessExecutionAdapter<br/>验收失败时的后备实现] -. 实现 .-> P
    H --> J[Harbor Job]
    J --> T[Harbor Trials<br/>n_concurrent_trials=1]
    T --> A[Agent + Docker Environment]
    T --> R[Trial result / trajectory / artifacts]
    H -->|started/finished 身份 + ExecutionTrialResult[]| O
    O --> E[固定 SWE-Bench-Fork Evaluator]
```

这是一个深模块：调用方只学习一组项目对象，Harbor 的目录、Pydantic 类型、CLI 参数和异常都留在 Adapter 实现内部。

## 3. AgentExam 输入

`ExecutionJobRequest` 已在 M0 后端实现为项目 Python 类型；下表仍是其权威语义：

| 字段 | 含义 | 约束 |
|---|---|---|
| `job_id` | 平台评测 Job ID | 全链路追溯；不可复用 |
| `runs[]` | 待执行的逐题运行 | 每项固定 `run_id`、一个任务、一个 Agent 配置和 `attempt_index=1` |
| `evaluation_policy` | 赛道、网络和工具策略 | MVP 固定 `closed_book`；`open_book_experimental` 只保留接缝且禁用；每条运行保存快照 |
| `limit_profile` | CPU、内存、超时、PID、输出限制模板 | 只能来自所有者登记模板，不能接受用户任意 Docker 参数 |
| `backend_revision` | Harbor 固定提交 | 必须等于依赖事实源中已允许版本 |
| `artifact_contract_version` | 必需制品约定版本 | 不支持时在启动前失败 |

公开 Job 请求、`ExecutionJobRequest` 和 PostgreSQL 只保存非秘密的模型提供方、认证类型与 Agent Configuration 身份；它们不接收 `auth.json`、DeepSeek/Kimi Key 内容，也不保存真实宿主路径。

`CODEX_AUTH_JSON_PATH` 只存在于执行节点本机、未跟踪的秘密配置中。执行节点在启动受控 Codex Trial 时解析它，路径和值都不进入上表的业务请求。

P2 自研 Agent 的 DeepSeek/Kimi 真实 Key 同样只存在于评测机所有者控制的本机可信秘密配置中，但与 Codex 不同：Key 不直接交给被测 Agent 容器。Agent 只能使用运行时受限、可撤销的模型访问能力；该能力由现有 Execution Backend/LLM Provider Implementation 提供，具体采用宿主进程还是可信侧车以及 Docker 网络怎样防绕过留到 P2 原型裁决，不阻塞 MVP。

每个 `runs[]` 项只包含 Agent 可见任务视图；gold patch、`test_patch`、`FAIL_TO_PASS`、`PASS_TO_PASS` 和其他运行答案不得进入 Harbor Agent instruction。

## 4. Harbor `JobConfig` 映射

以下字段来自固定提交真实源码，不是根据记忆创造：

| Harbor 字段 | AgentExam 映射 | 首版规则 |
|---|---|---|
| `job_name` | 安全化的 `job_id` | 不含用户名、秘密或仓库路径 |
| `jobs_dir` | 后端受控临时目录 | 不由 HTTP 用户传入 |
| `agents` | Job 选中的已登记 Agent 配置 | 只从 Agent Registry 转换 |
| `tasks` | SWE-Gym Adapter 产生的受控 Harbor Task | 精确本地路径/身份由 Task Adapter 生成 |
| `datasets` | 暂不作为首版主要输入 | 首版先显式列出少量固定 tasks，避免隐式扩大数据集 |
| `n_attempts` | 每个 Agent×任务的尝试数 | 首版固定 `1` |
| `n_concurrent_trials` | Harbor 同时执行的 Trial 数 | 单机硬性固定 `1` |
| `environment.type` | 环境提供者 | 首版固定 Docker |
| `environment.delete` | 完成后清理环境 | 默认 `true`；清理失败必须留证 |
| `environment.*_enforcement_policy` | CPU/内存执行策略 | 具体策略须通过本机原型，不沿用未验证默认值 |
| `environment.override_*` | 已登记资源模板覆盖值 | 只能由平台生成，不能由普通用户提交 |
| `verifier.disable` | 是否运行 Harbor Verifier | 固定 `true`；最终交给 SWE-Bench-Fork |
| `artifacts` | 需从 Trial 环境收集的文件 | 至少覆盖补丁、轨迹及必要日志；必需制品缺失视为执行失败 |
| `retry.max_retries` | Harbor 内部重试 | 首版固定 `0`，重跑由平台创建新运行，避免覆盖证据 |

固定提交的 `JobPlan.build_trial_configs()` 已核验为按：

```text
n_attempts × task_configs × agents
```

展开 Trial。首版 `n_attempts=1`，所以每个任务与 Agent 配置组合恰好对应一条评测运行。

平台把冻结运行按 `task_id → agent_configuration_id → run_id` 排成稳定顺序；配置中的 tasks 与 agents 按相同顺序首次出现，因此与 Harbor 的 tasks×agents 展开一致。随机 `run_id` 不能决定笛卡尔积顺序，否则多配置批次可能把 Trial 生命周期绑错运行。

## 5. Agent 和 Task 映射

### 5.1 `AgentConfig`

Harbor 固定提交已核验字段包括 `name`、`import_path`、`model_name`、`n_concurrent`、`concurrency_group`、`skills`、`kwargs`、`env` 和 `extra_allowed_hosts`。

映射纪律：

- 内置 Agent 依次接入：Codex MVP 完成后再接 Harbor 已有的 Aider、Claude Code；不为同一能力另写一套 Adapter。
- P2 自研 Agent 只支持 Python，并实现 [`RUNNER_PROTOCOL.md`](./RUNNER_PROTOCOL.md) 的固定进程 Interface；平台拥有的包装实现把审核后的模块映射为 Harbor Agent，普通用户不能直接提交 Harbor `import_path`、shell 命令或环境变量。完整 manifest 字段、Python 版本、依赖锁格式和包装 extension point 留待 P2 确认/实测。
- 公开 Job、数据库和对外接口只记录非秘密的认证类型，不接收凭据文件、内容或真实路径。
- 对首个 Codex 原型，可信执行节点通过显式私有运行绑定 `codex_auth_path` 提供机器所有者的凭据，不从环境变量隐式接受凭据路径；该绑定不是公开 Job 字段。凭据只在受控 Trial 的最小生命周期内使用，当前隔离/清理证据与未验证的 Token 刷新见 [`CODEX_AUTHENTICATION.md`](./CODEX_AUTHENTICATION.md#63-其他尚待实测项)。
- P2 自研 Agent 只允许登记 `deepseek` 或 `kimi` 提供方；同一源码切换提供方必须生成独立 Agent Configuration。真实提供方 Key 只由执行节点可信实现读取，不直接注入被测 Agent 容器；提交者只能选择已登记配置，不能提供 Key、Base URL 或代理。
- `n_concurrent` 不得超过 Job 的 `n_concurrent_trials=1`。

### 5.2 `TaskConfig`

Harbor 固定提交支持本地 `path`、Git 任务 `git_url + git_commit_id + path`，或包任务 `name + ref`。AgentExam 首版使用 SWE-Gym Adapter 生成的少量、固定、本地 Harbor Task，并把数据集 revision、split 和 `instance_id` 继续保存在自身任务快照中。

该映射不允许把用户提交的任意任务 Git URL 直接交给 Harbor，也不允许用 `latest` 代替固定 revision。

## 6. Harbor 输出与 AgentExam 输出

### 6.1 已核验的 Harbor 输出

固定提交的内存 `JobResult` 包含 Job ID、起止时间、总 Trial 数、聚合统计和 `trial_results`；真实 NOP 运行确认 Job 根目录落盘的 `result.json` 会排除 `trial_results`，每条完整结果只落在对应 Trial 子目录的 `result.json`。Adapter 因此必须枚举子目录并严格绑定身份，不能从 Job 根结果猜配。`TrialResult` 已核验包含：

- `id`、`task_name`、`trial_name`、`trial_uri`、`task_id`、`task_checksum`；
- 解析后的 `config` 与 `agent_info`；
- 可选 `agent_result`、`verifier_result`、`exception_info`；
- 环境准备、Agent 安装/执行和 Verifier 的时间数据。

Harbor Job 目录会保存 Job/Trial 的 `config.json`、`result.json`、Agent 日志、可用时的 `trajectory.json` 和收集的 artifacts。固定 `SingleStepTrial` 及真实 NOP 已确认顺序为：运行 Agent → 同步日志 → 执行任务 `verifier.collect` hook → 收集 artifacts → 可选运行 Verifier；`verifier.disable=true` 时仍执行前两类收集。

固定源码还确认 Trial 在 START 前写自身 `config.json`，在 END 前写自身 `result.json`。任务 07 的 CLI Adapter 以这两个受信文件发出只含冻结 `run_id` 的开始/结束通知；每 0.1 秒的有界进程轮询只是发现文件，不解析 stdout/stderr。重复文件只通知一次；重复身份、无法解析、未知 task+agent 或结果身份不一致不会直接推进平台状态，最终由返回矩阵闭合为明确错误。Harbor Job 汇总 `result.json` 缺失时，Adapter 仍扫描受信的逐 Trial 结果、保留已完成项，并附加 `HARBOR_JOB_RESULT_MISSING` 协议警告；未知、重复或损坏 Trial 也以受控协议警告使 Job 收束为部分错误。通知不是数据库写权限，所有推进仍须 Repository 校验 Worker、租约、Job/Run 版本和顺序。

### 6.2 Adapter 必须返回的项目结果

每个 Trial 必须转换为一条 `ExecutionTrialResult`：

| 字段 | 含义 |
|---|---|
| `run_id` | 对应 AgentExam 评测运行 |
| `backend_job_ref` / `backend_trial_ref` | Harbor Job/Trial 的安全不透明标识；不得使用宿主绝对路径 |
| `termination_reason` | 规范化的完成、超时、认证、资源、Agent、制品或内部错误 |
| `patch_ref` | 必需的 Git unified diff 制品；可为空补丁，但引用和 SHA-256 必须存在 |
| `trajectory_ref` | 可用时的 ATIF/规范化轨迹制品；缺失必须带能力/错误说明 |
| `raw_config_ref` / `raw_result_ref` | 脱敏后的 Harbor 原始配置与结果制品 |
| `usage` | Harbor/Agent 实际报告的 token、成本和时间；不支持的字段为未知，不写 0 |
| `warnings` | artifact best-effort 失败、轨迹能力差异等可审计警告 |

脱敏后的原始配置、结果、日志、轨迹和制品也必须明确排除 `auth.json`、`$CODEX_HOME`、Harbor secrets 目录、Token 和真实宿主凭据路径；MinIO 不得接收这些内容。

`ExecutionBackend` 不返回 `resolved`。补丁正确与否只由后续 `PatchEvaluator` 返回。

## 7. `model_patch` 缺口

Harbor 固定提交的 `TrialResult` 没有标准 `model_patch` 字段。Harbor 的 artifact 收集还是 best-effort：收集失败会进入 manifest，但不会自动让 Trial 失败。因此 AgentExam 必须额外执行以下强约束：

1. 在 Harbor 清理 Agent 环境前，由受控机制从固定 `base_commit` 的工作区提取 Git diff。
2. 把 diff 写入约定 artifact，并记录字节数与 SHA-256。
3. Harbor Adapter 读取后重新校验；制品缺失或哈希不一致时返回 `patch_extraction_failed`。超过 256 KiB 写警告；超过 1 MiB 返回 `PATCH_TOO_LARGE` 并拒绝进入 Harness，绝不截断。
4. 空补丁是合法执行结果，但也必须有一个 0 字节 patch 制品和对应哈希。
5. 二进制 patch 返回 `BINARY_PATCH_NOT_ALLOWED`，不进入 Harness；MVP 只接受文本统一 diff。
6. 同一字节内容保存到 MinIO，并作为 SWE-Bench-Fork prediction 的 `model_patch`。

M0 已选择固定 Harbor 支持的任务级 `verifier.collect` hook：在容器销毁前相对任务 `base_commit` 生成 `model.patch`、SHA-256、字节数和二进制标志，再把整个 `/logs/artifacts` 目录收集到宿主 `artifacts/agentexam`。真实 NOP 已验证空 patch 与元数据、Verifier 关闭、UTF-8 CLI 退出和 Compose 资源清理；固定摘要、禁网容器测试又验证了跟踪文件修改、新文件、删除和 Agent 自行 commit 四种非空结果都能相对固定 `base_commit` 生成完整 patch，并通过宿主强校验。真实 Codex 使用该出口并接入独立判卷的证据见[第四场记录](#第四次授权运行真实补丁与独立判卷通过2026-09-08)。M0 使用本机制品，MinIO 落盘属于 M1。

## 8. 运行身份映射

Adapter 必须保存不可变映射：

```text
job_id ↔ Harbor job id/path
run_id ↔ task_id + agent_configuration_id + attempt_index ↔ Harbor trial id/name
```

首版尝试数固定为 1，因此 `(job_id, task_id, agent_configuration_id)` 唯一。Harbor 生成的 `trial_name` 不能替代平台 `run_id`；如果映射无法确定，禁止把 Trial 结果猜配给某条运行。

## 9. 状态与错误映射

| Harbor/Adapter 现象 | 平台运行结果 | 是否进入 SWE-Bench-Fork |
|---|---|---:|
| Agent 完成且 patch 制品校验通过 | `completed` 执行结果 | ✅ |
| Agent 完成且 patch 为 0 字节 | `completed` 执行结果 | ✅，由 Fork 记录未解决/空补丁 |
| `exception_info` 为 Agent/认证/超时错误 | 对应规范化失败 | ❌ |
| 环境创建、资源或网络策略失败 | `sandbox_failed` / `policy_failed` | ❌ |
| artifact manifest 报告必需 patch 失败 | `patch_extraction_failed` | ❌ |
| 文本 patch 超过 1 MiB | `PATCH_TOO_LARGE` 无效 Agent 输出 | ❌ |
| 二进制 patch | `BINARY_PATCH_NOT_ALLOWED` 无效 Agent 输出 | ❌ |
| Trial 身份无法映射到 `run_id` | `backend_protocol_error` | ❌ |
| Harbor Job 进程异常退出 | 未完成运行标记明确失败；保留已完成 Trial | 仅已取得可信 patch 的运行继续 |
| Harbor reward/Verifier 输出 | 仅保存为调试证据或完全禁用 | ❌，不能作为最终事实 |

平台 Job 可以“部分完成”：已经形成可信逐题结果的运行保留，其余运行明确失败；不得为了让 Job 看起来整齐而丢弃已完成证据或伪造结果。

执行中收到取消请求时，Adapter 不再启动新的 Trial；当前 Trial 不强杀，只运行到 Job 创建时冻结的超时并保存真实结果。宿主机、Worker 或 Harbor 中断不能触发自动续跑或自动重试；可证明已经完成的 Trial 只做幂等收束，否则记录 `INFRASTRUCTURE_INTERRUPTED`，新尝试必须由所有者创建新 Job。

任务 09 的实际 Adapter 协议只在提供 `ExecutionProgressObserver` 时启用。父进程在本次 `run_root/trial-control` 下创建私有控制目录；固定 Harbor 子进程在第 N 个 Trial 入队前写 `ready-NNNN` 并等待 `permit-NNNN`。父进程先读取并保存前一 Trial 的真实 `result.json`，再调用 `trial_started(run_id) -> bool`：允许时写 permit，取消事务已胜出时由 Repository 原子取消未启动 Run、返回 false 并写 `stop`。子进程看到 stop 后直接返回已经完成的结果，不启动当前及后续 Trial；Adapter 只映射监视器已确认完成的结果。

该协议没有新增公开执行后端或 Harbor 配置字段。`harbor_entry` 只接受与配置同目录且精确名为 `trial-control` 的非符号链接目录，并在加载固定 Harbor revision 后安装受控顺序 runner；路径或来源不符立即失败关闭。固定 Harbor 当前没有公开的“停止未来 Trial、保留当前 Trial”Interface，所以此实现绑定其私有 `_run_trials_with_queue`；上游 revision 变化时必须先通过入口来源检查和协议测试，不能静默兼容。控制文件不含用户身份、凭据、任务正文或结果正文。

## 10. P2 Agent 源码提交入口（MVP 禁用）

本节只保存未来扩展接缝。MVP 的 Web、HTTP API 和 Agent Registry 不公开源码提交入口，只能选择项目预登记 Agent。

可信参与者可以提交：

- Git 仓库 URL；
- 完整 commit SHA；
- 仓库根目录中的 `agent-exam.yaml`；
- 面向审核者的名称与说明。

P2 提交只创建 `PENDING_REVIEW` 记录，不会触发 Harbor、Docker build 或任意仓库代码执行。所有者审核来源、commit、manifest、依赖与权限后，才生成已登记 Agent 配置。分支名、`latest`、请求正文中的 shell 命令和未经审核的 `import_path` 均不能进入执行链路。

已确认 `agent-exam.yaml` 的 P2 首版只描述 Python 固定进程 Interface，并且必须存在、固定在同一 commit、由平台静态解析并经所有者审核。它不能携带 shell、API Key、自定义提供方/Base URL、代理、宿主路径或 Harbor 原生配置。完整字段、Python 版本和依赖锁格式留到 P2，不臆造尚未讨论的启动字段。

## 11. Mock 与正式结果

- Mock Adapter 只用于应用用例、错误分支、状态机和 HTTP contract 测试。
- Mock 产生的 Job/运行必须带 `result_scope=internal_test`，并使用独立测试数据库或明确测试标记。
- 报告、演示、正式榜和实验榜查询必须排除 `internal_test`。
- 正式结果必须来自真实 Agent + 真实 Harbor/Docker 执行 + 固定 SWE-Bench-Fork；不能用预制 patch 冒充 Agent 输出。

## 12. 单机资源规则

- PostgreSQL 同时只允许一个平台重型 Job 处于执行状态。
- Harbor `n_concurrent_trials` 固定为 `1`；不得因为 Job 中任务多就自动提高。
- 具体 Trial 内存、CPU、磁盘和超时模板必须根据真实单题峰值确定。本机事实只在 [`LOCAL_DOCKER_ENVIRONMENT.md`](../operations/LOCAL_DOCKER_ENVIRONMENT.md) 维护。
- 单个轨迹、stdout、stderr 或 Judge 原始制品最多 50 MiB，超过只能显式标记截断；每运行原始制品总额最多 200 MiB。核心配置、确定性结果、最终 patch 和测试摘要优先完整保存，不能用静默丢失伪装证据完整。
- Web 创建 Job 时必须显示组合产生的 Trial 数；耗时只能基于真实历史数据估算，没有历史数据时显示“未知”，不能承诺完成时间。

当前 M0 覆盖差距（2026-09-08，只读核对）：生产执行器已对 stdout/stderr 分别落实 50 MiB 上限和显式截断记录，但尚未对全部原始制品落实每运行 200 MiB 总额。超限轨迹当前返回缺失引用及 `TRAJECTORY_TOO_LARGE` 警告，没有生成带截断状态的轨迹制品引用。小体积真实单题通过不能代替上述边界验收；这些是相对本节完整规则的实现缺口，不修改限额，也不自动认定全部延后至 M1。完整限制对象的阶段差异见 [模块契约](../architecture/MODULE_CONTRACTS.md#41-当前-m0-实现与目标契约的区别)，下一项处理范围由用户确认。

## 13. 分阶段验收

### 13.1 M0：本机 Codex 技术原型

从固定 revision 的 `SWE-Gym/SWE-Gym-Lite` 先选择 1 道真实任务，必要时扩至 3 道，并使用 Harbor 内置 Codex Agent 验证。认证政策已确认为评测机所有者的 ChatGPT Pro `auth.json`，首轮 CLI 版本、模型与推理强度见 [依赖总表](../dependencies/DEPENDENCIES.md#2-当前依赖总表)，已确认而不再待选。第四场固定单题核心闭环已经通过，完整验收状态见本节末的[验收对账](#暂停后的验收对账2026-09-08)。以下带日期的实验段落保留当时状态，不能用较早的“未运行”覆盖后续成功记录。

M0 用本机脚本编排，不实现 Web、PostgreSQL、MinIO、登录或审批；证据写入受控本机临时目录，标为技术原型，不进入正式排行。验收项：

1. Harbor 固定提交可在本机安装并创建 Docker Trial。
2. `n_concurrent_trials=1` 与资源/网络策略实际生效。
3. Agent 看不到 gold patch 和判分字段。
4. 自动取得 patch（含新建/修改/删除文件和空补丁）、校验 SHA-256，并验证 256 KiB 警告、1 MiB/二进制拒绝且不截断。
5. ATIF/原始轨迹、Harbor config/result、stdout/stderr 可追溯到同一次原型运行；日志限额有显式标记。
6. `verifier.disable=true` 时 Harbor 不产生最终判卷，但 artifacts 仍可取得。
7. 同一 patch 交给固定 SWE-Bench-Fork 后得到可信 `resolved` 和原始测试证据。
8. 超时、认证失败、patch 缺失和清理失败均映射为明确错误；脚本失败不伪装成正式结果。
9. Trial 前后人工检查容器、可写层、日志、轨迹和本机证据目录；成功、失败、超时三条路径均不得遗留凭据内容、真实秘密路径或可复用 Token。

任何一项失败都必须先诊断；如果补丁出口、资源治理或轨迹在限定验证周期内无法稳定满足，则按 ADR 回退到 `ProcessExecutionAdapter`。

当前实施状态（2026-09-06）：固定公开 Task 渲染、隐藏字段隔离、Harbor 配置/运行身份映射、collect hook、宿主 patch 强校验、Trial 结果映射和薄 `HarborExecutionAdapter` 已实现。stdout/stderr 由生产有界执行器同时排空，每路最多持久化 50 MiB；超限、进程树清理失败或日志收束不完整均显式传播为运行告警。当前完整测试数量以 M0 行动记录为准；生产有界执行器接真实 Harbor CLI 和正式 mapper 的 NOP 正常路径为 `1 passed in 18.87s`，固定摘要、禁网容器中的修改/新建/删除/Agent commit 四类非空 patch 为 `4 passed in 5.91s`。公开 `HarborExecutionAdapter.execute()` 的阻塞 collect 探针先真实复现外层强杀留下 1 个容器、1 个网络和 1 个本地镜像；生产修复只从本 Job 路径名一致的 Trial 配置推导固定规则的 Compose project，并按 label 删除、复核容器/网络/卷/本地镜像，复测为 `1 passed in 49.47s`，前后 Docker 对象计数相同。固定 Fork 五类独立补丁判卷已通过，M0 入口已连接既有 ports 并维护原型证据；真实 Codex 与生成阶段网络/凭据/轨迹仍未完成，不能据此把 M0 标记完成。编排只允许内部测试/NOP，CLI 提供 `--check` 与 `--check-network`，两者均不启动真实模型；无模型串联结果及 Windows 长路径修复见 [M0 行动记录](../actions/2026-09-05-m0-codex-harbor-implementation.md)。

网络预检补充：M0 CLI 现提供互斥的 `--check` 与 `--check-network`；前者只检查任务，后者检查内核前提，均不调用模型。固定 Harbor 的 `models/task/config.py` 已有 `network_mode`（`public` / `no-network` / `allowlist`）和 `allowed_hosts`。Docker Implementation 的 `_egress_control_kernel_support()` 检查 `CONFIG_NFT_FIB_INET=[ym]`，能力不足时由 `validate_network_policy_support()` 拒绝不受支持策略；这是固定源码事实，不是白名单 Trial 已通过。项目新增的 `adapters/execution/preflight.py` 属于执行适配层内部诊断，不新增 port，不替代后续真实端点和防绕过测试。

本机已在获授权的 WSL 更新与 Docker 重启后通过内核预检，实际值和恢复证据唯一维护在 [Docker 事实第 3.4 节](../operations/LOCAL_DOCKER_ENVIRONMENT.md#34-harbor-网络前置条件)。预检无凭据、禁网、固定摘要、禁止拉取、按唯一标签清理；未知或清理未验证均返回非零。不得自动降为 `public`，也不得仅凭内核配置受支持就打开真实 Codex 入口。

#### 无凭据网络探针（2026-09-07）

固定 Harbor `DockerEnvironment` 的受控 HTTP/IPv4 探针已通过；其安全模板及原始 Git blob 导出已接入生产 `HarborExecutionAdapter`，并经无模型 Trial、判卷串联和超时清理复测。**配置接线已验证，但完整闭卷隔离和真实 Codex 尚未验收。** 通过 `AGENTEXAM_RUN_NETWORK_INTEGRATION=1` 显式运行 `tests/integration/test_harbor_network.py`；同目录 `network_probe.py` 在固定 Harbor 环境调用原生策略接口。固定输入见 [依赖第 6.3 节](../dependencies/DEPENDENCIES.md#63-网络探针的固定镜像与构建输入)。

接线位于既有 Execution Backend 内部，不新增业务 port：

- `tasks/swe_gym.py` 输出显式空 `allowlist` Task 基线及受限 Compose；不继承上游默认 `public`。可信本机构造配置 `HarborExecutionAdapter.network_hosts` 只接受精确 DNS 名称元组，规范化后冻结到 Job 的 `environment.extra_allowed_hosts`；不接受 URL、IP、通配符或宿主别名，不开放给用户 Job 输入。这是语法与配置约束，不是 DNS 重绑定防护。
- 固定 Harbor 的真实解析契约证明：该列表加入环境基线，setup、Agent 和 verifier 阶段继承同一基线。引导前重新检查 Task、阶段覆盖及完整 Compose，拒绝额外环境参数、挂载或网络配置覆盖。
- `network.py` 的主容器模板去全部能力、禁止提权、清空大小写代理变量；CPU/内存来自既有 `RunLimits`，内存与含交换总限额相等。PID=64 沿用本次 M0 探针；侧车为 0.5 CPU / 128 MiB / PID=64。这些不是已验收的真实 Codex 资源模板。不设置显式网络，交由原生 Harbor 挂接侧车网络命名空间。
- `harbor_entry.py` 使用固定 Harbor 环境的 Python 调用原 CLI；校验固定提交、跟踪文件工作树和实际导入来源，从固定 blob 导出运行副本并保存哈希。最初未修改规则；当前已授权的限定 DNS 适配和双哈希见本节较后的“限定 DNS 适配”。只保留必需宿主环境变量，启用 `PYTHONSAFEPATH` 防止相邻同名 `harbor` 包遮蔽上游；最初网络取证时真实 Agent 仍被 `REAL_CODEX_NOT_READY` 拒绝，后续入口状态见本节较后的“正式 Codex 入口接线”。

| 检查 | 实际行为 |
|---|---|
| 初始 allowlist、public 正对照、恢复 allowlist | 允许目标返回自身标记；禁止目标仅在 public 返回自身标记，其余为 curl 52 |
| 已解析 IP 的宿主 FlClash / Desktop 代理访问外部 HTTPS | public 两条均 exit 0；allowlist 两条均 curl 56 / CONNECT aborted，不依赖 DNS 失败判定 |
| 伪造 Host 为允许目标、连接地址仍为禁止目标 | 实际返回允许目标标记，未取得禁止目标内容；不是“所有伪造请求均被拒绝” |
| 主容器设置 GOST 套接字标记 | CapDrop=ALL 时出现 PermissionError，不能冒充侧车的豁免流量 |
| no-network 阶段的两个受控 HTTP 目标 | 已解析 IP 后仍为 curl 52；仅证明这些 TCP 路径被阻断 |
| 正常停止侧车后再访问两目标 | 已解析 IP 后均 curl 7；该停止场景没有恢复对目标的访问 |

测试拒绝把 DNS 解析失败、命令不存在或其他任意非零退出算作可信阻断；无法建立 public 正对照也不能通过。独立网络夹具还检查无宿主挂载、非 privileged、主容器去全部能力、禁止提权、正数 CPU/内存限额和 PID=64；原生侧车独立保留 NET_ADMIN/NET_RAW。生产模板本身不添加挂载，但真实 Harbor Trial 仍按上游默认挂载 verifier 日志、Agent 日志和 artifacts 三个宿主目录，不能把独立夹具的“无挂载”推广为生产 Trial 无挂载或凭据生命周期已通过。全部本轮 Compose 资源精确清理，共享固定镜像/内容哈希缓存保留。逐项结果及接线失败修正见 [M0 行动记录](../actions/2026-09-05-m0-codex-harbor-implementation.md#2026-09-07-网络配置接线与本地检查点)。

未验收：真实模型端点及证书校验、IPv6、已有长连接及突发故障/侧车重启、完整 Codex Trial 工具/资源兼容和凭据生命周期。无凭据安装已通过，见依赖第 2.1 节；受控 TLS/SNI 与已实测开放的 DNS/ICMP 边界见下节。仍未证明侧车到真实模型端点的 FlClash 出站路径，清空 Agent 代理变量不等于已解决侧车外网连通。继续禁止真实 Codex 入口；下一步在既有 Execution Adapter 内补齐这些限制，若必须改变已确认边界或采用后备 Adapter，先按 ADR 取得确认。

#### 无凭据追加边界取证（2026-09-07）

状态：受控 TLS 路由符合预期；DNS/ICMP 在受控测试网络内开放已复现，但公网可达性、外泄利用链及风险接受尚未确认。原先“必须先封死这两类协议”的结论超出实测与已确认闭卷政策，现予更正；风险分级和处置建议见 [风险评估](../research/2026-09-07-dns-icmp-risk-assessment.md)，不视为已经批准的策略变更。使用固定原生侧车与项目四容器夹具，在两个受控服务内临时生成自签证书；原 HTTP/代理对照复测，随后执行以下检查：

| 检查 | 实际结果与限定结论 |
|---|---|
| TLS public 正对照 | 两目标分别返回自身标记 |
| TLS allowlist | 允许目标返回标记，禁止目标为 curl 35 / TLS EOF；结合正对照判定此受控路径被阻断 |
| 连接禁止目标 IP，但使用允许目标的 TLS 域名 | 返回允许目标标记，未取得禁止目标内容；不是所有域名伪装都会报错 |
| ICMP ping socket | public 与 no-network 均从另一受控测试容器收到携带合成标记的 echo reply；主容器已 CapDrop=ALL 仍可用 SOCK_DGRAM/IPPROTO_ICMP |
| DNS | public 解析对照别名成功；no-network 下另一个未先查询的受控别名也成功解析，证明该 resolver 通道仍开放 |

原因与固定上游脚本一致：`bin/network-policy` 显式放行所配置 DNS resolver 和 ICMP，`deny-all` 实际只拒绝受控 TCP 出站；去 NET_RAW 不能阻止本机已允许的 ping socket。这证明原生 `no-network` 不等于 Docker `network none`，不是 FlClash 配置故障。闭卷要求保留模型必需网络并拒绝一般联网，不等于零网络报文；是否超出许可范围应按实际目的地与用途判断。当前既不能宣称完整闭卷/凭据验收通过，也不能把内部别名解析及容器间回显写成已证实公网外泄。

证据为忽略目录 `runtime/prototype/m0-network-extra-20260907-03/` 的 `extra-summary.json`、`summary.json`、`containers.json` 与 `extra-cleanup.json`；诊断程序退出 0 表示取证完成，不表示网络安全通过。自签 TLS 使用测试专用 `curl -k`，不证明真实端点证书校验。探针是一次性诊断证据，尚未沉淀为常规自动回归；前两轮失败/无效对照见行动记录。全程无真实凭据/模型调用，专属容器、网络、卷、镜像复核无残留。

#### 假凭据读取与日志能力（2026-09-07）

用户已授权假值安全收尾和后续兼容接线。既有有界进程执行器支持内部 `redactions` 参数；Codex 兼容实现保留在 Execution Adapter 内。最新完整假值 Job/Trial 已复现原生输出、刷新假值及 patch 的未保护通路，并修复非 root 上传兼容；四场生命周期/漏洞正对照通过，不是完整安全验收。兼容类只在测试进程中绑定，生产真实凭据及非 NOP 入口继续关闭。事实与剩余项唯一维护在 [认证接口第 6.2 节](./CODEX_AUTHENTICATION.md#62-2026-09-07-假凭据安全收尾)。

#### 正式 Codex 入口接线与两次模型前失败（2026-09-07）

上述段落记录当时状态；当前增量已经在既有 Execution Adapter 内接入正式任务 UID/collect、固定离线 CLI/PATH、显式本机认证引用及 `AgentFactory` 注册。`harbor_entry.py` 不再无条件拒绝 Codex，而是只允许 NOP，或同时满足固定 `0.153.0`、`openai/gpt-5.6-terra`、`medium`、Web 关闭和完整私有运行绑定的 Codex；缺失绑定和任意配置漂移都在 Harbor/容器/模型前失败。认证路径与离线输入路径不写入 Job 配置；准确凭据边界以[认证接口的接线小节](./CODEX_AUTHENTICATION.md#正式运行入口接线2026-09-07接线完成时尚未真实调用)及其后的首次真实 Trial 记录为准。

生产 `GuardedCodex.install()` 已用固定摘要镜像、`network none` 和假认证执行：重新核验 bundle 后上传固定目录，以 UID 65534 执行真实 `codex --version` / `exec --help`，且没有 curl/npm 回退；专属容器清理复核为空。完整假认证 success Trial 也在新生产 UID/PATH 下得到合成 patch 并自然清理。默认轻量回归为 190 passed / 19 skipped；这些结果只证明接线和失败关闭，未读取真实登录、未调用模型，也不能替代真实端点、Token 刷新、模型工具链和本次真实 Trial 清理证据。

原型 `run_prototype()` 现允许显式 `codex` 类型并仍复用同一 `ExecutionBackend → patch 强校验 → PatchEvaluator` 数据流；没有自动重试。网络主机名仍由可信本机构造器精确提供，不从 Job 或凭据推导。固定 CLI 二进制只读字符串显示 ChatGPT 模式涉及 `chatgpt.com` 后端及可能的 `auth.openai.com` 刷新路径，但 OpenAI 官方认证/安全页面没有提供本项目可直接采用的完整防火墙域名清单；这项观察不是权威 allowlist，也没有证明侧车经 FlClash 的真实 TLS 出站。首次真实运行的所有者授权已经列明并采用这些候选主机；该场没有到达出站阶段，故网络事实仍待下一次经授权的单题核验。

首次经授权的 `m0-real-codex-20260907-01` 已实际进入 Harbor，但在 Agent setup 的版本核验阶段以 `CODEX_OFFLINE_INSTALL_FAILED` 结束；Harbor 主进程正常退出且无超时，没有模型请求、usage、trajectory、可接纳 patch 或 Fork 判卷，专属 Compose 四类资源残留均为 0。真实 Harbor、deny-all、假认证、无模型复现定位为 Docker 执行层在精确版本行前增加一条非空输出，而原实现只取第一行。生产安装现严格检查最后一条非空行是 `codex-cli 0.153.0`；最小红绿回归、同一真实 Harbor 无模型路径和最终固定镜像安装契约均通过。该修复没有改变网络、凭据或 Agent 运行策略。

用户另行授权第二场。两次 import-only 命令错误未创建运行；随后 `m0-real-codex-20260907-02` 因调用层把 `codex_archive` 误指向不存在的 Windows `.zip`，在 `prepare_codex_bundle()` 中以 `CODEX_PACKAGE_INVALID` 结束。此时尚无 Harbor 配置、Job、容器、凭据上传、模型请求、patch 或判卷。正确固定 Linux `.tgz` 的大小和 SHA-512 已重新核对并与生产常量一致，所以不修改或放宽安装校验。该场属于启动编排错误，不是题目失败；按照不自动重试约束，后续真实单题仍须所有者重新批准。

#### 第三次授权运行：DNS 转发失败（2026-09-07）

`m0-real-codex-20260907-03` 经用户明确授权，使用同一预检/启动构造，正确绑定固定 Linux `.tgz` 后实际进入 Codex 会话。Harbor Trial 为 `python--mypy-15413__ECQo82F`。本场官方主机 DNS 解析失败，Agent 在 900 秒限额后以 `AgentTimeoutError` 结束，mapper 为 `timed_out`；Harbor 主进程正常退出 0、无外层进程超时，完整 Trial 墙钟 929.036897 秒。原型 `resolved=null`，没有模型回复、完成的 turn、工具执行或可用 usage；0-byte collect 文件没有作为有效补丁进入判卷。

DNS 因果对照已定位：主容器/侧车使用 Docker `127.0.0.11`，内部别名可解析，两个批准官方域名均 SERVFAIL；宿主及同一镜像/同一 bridge 的独立无凭据容器均可解析。Docker 配置的实际外部 DNS 转发地址是 `192.168.65.7`。固定侧车 nft 脚本只为 resolv.conf nameserver 放行 DNS，其他非 TCP 出站 reject，拦住了外部转发。在独立、无凭据、无宿主挂载的诊断侧车中，原规则复现失败；仅补 `ip daddr 192.168.65.7 udp dport 53 accept` 后两个批准主机均恢复解析。诊断容器随后精确清理；生产 Trial 规则从未更改。

这证明了该次 DNS 阻塞的根因和最小诊断修正，不证明真实 TLS/HTTP/WebSocket、账号、模型或完整网络保护通过。该次结束时，生产调整尚待确认，规则只存在于诊断容器；后续授权及实际接线见下节，不把历史诊断结果直接当作当前实现。

本场和两个诊断标签的容器均无残留，真实 Trial 的网络、卷、临时镜像也为空；私有目录和认证副本核验见[认证记录](./CODEX_AUTHENTICATION.md#第三次授权运行dns-阻塞后超时2026-09-07)，完整证据身份及哈希见[M0 行动记录](../actions/2026-09-05-m0-codex-harbor-implementation.md#2026-09-07-第三次授权的固定真实单题)。本次没有 Fork 判卷，M0/MVP 均未完成。

#### 限定 DNS 适配（2026-09-08）

用户已明确批准把上述限定修正接入现有网络适配层。`network.py` 现在仅在导出的 `bin/network-policy` 运行副本内增加 `192.168.65.7/UDP 53` 的 egress accept，不修改固定 Harbor 工作树、主机白名单、其他 UDP、ICMP、代理或宿主设置。正式入口和网络测试复用同一导出。

每次安装受控策略前，脚本要求 Docker resolv.conf 中的 nameserver/ExtServers 行恰为 `nameserver 127.0.0.11` 与 `# ExtServers: [192.168.65.7]`；未知、多解析器、IPv6/host-forwarder 标记等配置以 `HARBOR_DOCKER_DNS_CONFIG_UNSUPPORTED` 在调用 nft 前退出，初始侧车不会标记 ready。固定源码的两个定位点必须各出现一次，否则导出报 `HARBOR_DNS_POLICY_SOURCE_UNSUPPORTED`，不会进入 Harbor。没有自动探测并放行任意 resolver 的后备策略。

`network-source.json` 的 `upstream_sha256` 是五个固定原始 blob 的身份，`sha256` 是实际导出文件身份，`adaptation` 为 `docker-desktop-dns-192.168.65.7-udp53-v1`；只有 network-policy 允许不同。构建缓存继续按生效内容命名，旧缓存保留。该项不新增应用层接口。

同一固定 Harbor 回归已先复现 DNS 失败，再在适配后验证两个官方主机解析成功；原有受控 HTTP、宿主/桌面代理绕过拒绝、socket mark 权限、deny-all/恢复/侧车停止和精确资源清理检查通过。源码/哈希契约和轻量回归通过。追加检查以 UID 65534 运行：shell 中已知配置到达 nft 调用标记，8 种未知配置均在调用前退出；同一受控 UDP 目标在 public 回显成功、allowlist 下 `PermissionError` 拒绝。真实侧车 nft 规则确认仅多出已批准的一条 UDP53 accept。

在只含 `auth.openai.com` / `chatgpt.com` 的 allowlist 下，不使用代理环境变量、不带认证且未使用 `-k` 的 HTTPS HEAD 均 curl exit 0、`ssl_verify_result=0`、HTTP 403。这证明两个主机根路径的 TLS 连接和证书校验可用，不证明真实 Codex 模型 API、WebSocket、账号或 Token 刷新成功，也没有证明具体经过了哪条 FlClash 路由。完整回归及追加探针的各轮精确 Compose 容器/网络/卷/镜像残留均为空；第一次追加探针因拒绝错误类型断言不准确而中止的证据也已保留。命令、红绿与限制见[M0 行动记录](../actions/2026-09-05-m0-codex-harbor-implementation.md#2026-09-08已授权的限定-dns-适配)。

该例外限制的是 DNS 转发目的地址和端口，不按查询域名过滤，不证明 DNS 无外传风险。截至该次无凭据 DNS 验证结束时，没有运行新的 Codex 单题、使用真实登录或生成新补丁/判卷；第四场真实调用尚未授权，M0 尚未完成。随后第四场的单独授权与结果见下节，不将运行许可泛化为剩余风险豁免。

#### 第四次授权运行：真实补丁与独立判卷通过（2026-09-08）

用户授权第四场固定单题后，`m0-real-codex-20260908-04` 首次完成真实 Codex → 补丁 → 固定 SWE-Bench-Fork 的完整链路。Trial `python--mypy-15413__hkKTeaa` 实际使用 Codex 0.153.0 / openai/gpt-5.6-terra / medium，原生异常为空、执行 completed、warnings=[]；模型有完成 turn、真实命令和文件修改。不是 NOP 或合成测试。

真实补丁 1,225 bytes，修改 `mypy/checker.py` 与 `test-data/unit/check-flags.test`；执行产物、Fork 输入和实际使用 patch.diff 的 SHA-256 均为 `d5fefec345eb335c9b17d6305037ef47214c56d265f1ca11175c88c90d3ad09d`。独立原始报告 patch_successfully_applied=true、resolved=true，覆盖数据集登记的 FAIL_TO_PASS 用例；PASS_TO_PASS 登记为空，不能据此宣称整个 mypy 测试集通过。ATIF/原始事件、配置、进程记录及判卷证据均对应同一 Run，未截断、未自动重试。

实际公开任务字节、固定配置、verifier.disable、单并发/单尝试/零重试已核对。运行中独立 inspect/top 确认 Agent UID 65534、主容器去全部能力/禁止提权、资源限制与共享侧车；Fork 容器独立、断网、无宿主挂载。正常结束后两套执行资源均精确清理，本场凭据副本与私有目录检查见[认证记录](./CODEX_AUTHENTICATION.md#第四次真实单题通过2026-09-08)。真实补丁/报告/用量哈希、现场与事后取证区别、Windows 收尾检查偏差均记录在[M0 行动记录](../actions/2026-09-05-m0-codex-harbor-implementation.md#2026-09-08第四次授权的固定真实单题)。

**M0 真实单题核心闭环已通过；尚不宣称所有安全/生命周期验收或 MVP 完成。** 本场证明当前账号/模型路径及实际工具执行可用，不证明 Token 刷新、所有 IPv6/长连接/故障路径或全面输出保护。下一步是按本节及认证接口核对 M0 剩余验收边界，再进入 M1；不为了已有成功结果自动新增真实单题。

#### 暂停后的验收对账（2026-09-08）

本表沿用上述实验和 [M0 行动记录](../actions/2026-09-05-m0-codex-harbor-implementation.md) 中的运行证据，并结合本轮静态代码核对；本轮没有运行模型、Docker 或测试，也没有重新读取受 ACL 限制的私有原始输出。“已有证据”仅覆盖注明范围，不代表完整阶段验收。

| 原验收项 | 已有证据与仍缺部分 |
|---|---|
| 1. 固定 Harbor 安装与 Docker Trial | 已有真实 NOP 和第四场 Codex Trial 证据。 |
| 2. 单并发、资源与网络策略 | 第四场固定单并发/单尝试、资源限制、非 root 和受控侧车已核对；完整 IPv6、长连接、故障路径及具体代理路由仍未全部验证。 |
| 3. 隐藏判分字段隔离 | 已有 Task Catalog/公开任务契约测试及第四场实际公开任务字节核对；不向 Agent 提供 gold patch 和判分字段。 |
| 4. 补丁出口、哈希和拒绝边界 | 已有空/修改/新建/删除/自行 commit 收集证据及大小、二进制拒绝契约测试；第四场真实补丁与 Fork 输入哈希一致。 |
| 5. 同 Run 输出追溯及日志限额 | 第四场小体积轨迹/配置/输出/判卷证据可追溯；stdout/stderr 有界。完整制品总额和超限轨迹表示仍有[第 12 节](#12-单机资源规则)所列实现缺口。 |
| 6. 禁用 Harbor 最终判卷但收集制品 | NOP 与第四场均有证据，最终正确性仍由独立 Fork 判定。 |
| 7. 同补丁的固定 Fork 独立判卷 | 第四场已有真实 `resolved=true` 及原始报告；仅覆盖登记用例，不代表整个 mypy 测试集。 |
| 8. 失败映射与清理 | 已有错误映射契约、真实 Agent 超时及 NOP 外层超时清理回归；非超时崩溃/外层中断、上传中断等路径尚未充分验证，不能由超时通过外推。 |
| 9. 生命周期与秘密残留 | 已有假凭据正对照、第三场超时及第四场正常路径的限定检查；真实 Token 刷新和完整失败路径仍待核验。私有原始输出适用[认证第 6.2 节](./CODEX_AUTHENTICATION.md#62-2026-09-07-假凭据安全收尾)的阶段例外，不能据此免除凭据隔离与清理。 |

代码待同步但本轮不修改：`adapters/execution/preflight.py` 中 `task_preflight()` 返回的 `pending` 仍含 `fixed Codex version/model/effort` 这一已经解决的旧提示；`real_codex_ready=false` 本身仍表示诊断不授予真实运行许可，不能为了消除陈旧提示就改为自动放行。该命令的输出不是当前项目验收状态的权威来源。

清理验证边界：当前 Harbor Adapter 对外层超时设有显式资源清理后备路径；这不证明普通非零退出、宿主进程被中断或私有上传中断时均已完成相同生命周期验证。这里只记录覆盖不足，不声称本轮复现了新故障。更完整的凭据边界继续由[认证第 6.3 节](./CODEX_AUTHENTICATION.md#63-其他尚待实测项)维护。

用户已要求放缓开发，本轮只同步事实。尚未验收不等于已经失败；哪些缺口在 M0 收尾处理、哪些适用既有例外或留待后续阶段，需要依据原验收边界由用户确认，不能自动扩大安全工程或直接开始 M1。

### 13.2 M1：Codex 平台 MVP

M1 接 Web、PostgreSQL 和 MinIO，最终验证协作者提交 → 所有者批准 → 本机 Worker → Harbor → patch → SWE-Bench-Fork → 报告的完整真实闭环。还必须覆盖两类角色、无公开注册、任务原始快照、取消/中断不自动重试、制品保留/清理审计和确定性结果报告。分析扩展阶段以[总架构第 3.1 节](../architecture/ARCHITECTURE.md#31-m1-交付边界2026-09-09-已确认)为准。只有 M1 通过才称为 MVP 完成。

2026-09-09 最新安排：用户允许按 Spec 分任务推进 M1 本机开发与内部测试；这不把第 13.1 节剩余项标为通过。进入真实执行或对外验收前仍须完成对应门槛与授权，不因开发许可而自动运行模型、Docker 探针或接受网络/刷新残余风险；恢复入口见 [HANDOFF](../../HANDOFF.md)。

2026-09-13 任务 13 已增加生产 Worker Composition Root，并用正式目录 preset 验证 Harbor 配置：业务身份 `openai_chatgpt` 只在 Adapter 内映射成固定上游名 `openai`，最终仍由 `harbor_entry.validate_agent_mode` 精确接受 `openai/gpt-5.6-terra`、Codex 0.153.0、medium、web disabled。固定归档、认证文件元数据、Harbor/Fork 干净 revision 和任务快照均在领取前核验；没有新增 `ExecutionBackend` 或 `PatchEvaluator` Interface。

同日无模型证据为：固定 Codex 离线安装/Harbor 复用 `1 passed`，真实 45 秒外层超时及 Compose 精确清理 `1 passed`，专属 PG/MinIO 取消/恢复/制品回归 `135 passed`；一次性编排预检确认 storage/HTTP ready、零 Job、零认证读取、零模型调用和清理完成。首次真实 Run 完成提交/批准并产生 1302 字节 patch，但 composition root 漏传 `LocalArtifactReader`，在固定 Fork 前以 `EVIDENCE_UNAVAILABLE` 失败；`10f0c53`、`3d66230`、`1b8e9ba` 依次补回 reader、修复绝对/相对引用和集中安全校验。第二次获批 Run 在源码等价的 `m1-task13-20260913-02` 中只尝试一次：平台 Job/Run 均为 `COMPLETED`、固定 Fork `resolved=true`，但忽略态验收器误读 Trial 配置并在浏览器前退出。该验证器及浏览器前置门禁经红绿和双轴评审修复后，`m1-task13-20260914-04` 用一次模型尝试、零重试完成正式 Job/Run、固定 Fork、MinIO/PostgreSQL 读回与真实页面报告，最终 `status=passed/phase=complete/cleanup=verified`；patch SHA-256 为 `d5fefec345eb335c9b17d6305037ef47214c56d265f1ca11175c88c90d3ad09d`，submitted/resolved/error=`1/1/0`，独立 Docker 标签查询为空。详细限制见[任务 13 行动](../actions/2026-09-13-m1-local-real-acceptance.md)。

### 13.3 后续 Agent

M1 通过后，先使用相同契约登记并验证 Harbor 已有的 Aider、Claude Code。P2 自研 Agent 再追加验证：固定 Python 进程 Interface 能由平台包装为 Harbor Agent；DeepSeek 与 Kimi 分别形成独立配置；被测容器、环境快照、日志、轨迹和制品均不出现真实提供方 Key；受控模型访问失败只影响该运行并留下明确错误。P2 未完成不阻塞 MVP，也不得提前把自研 Agent 写成已支持。

## 14. 固定提交来源

- [`JobConfig`](https://github.com/harbor-framework/harbor/blob/6af8d6e31eced13b93849cdf80feeadf24603d15/src/harbor/models/job/config.py)
- [`JobPlan` Trial 展开](https://github.com/harbor-framework/harbor/blob/6af8d6e31eced13b93849cdf80feeadf24603d15/src/harbor/job_plan.py)
- [`TrialConfig`](https://github.com/harbor-framework/harbor/blob/6af8d6e31eced13b93849cdf80feeadf24603d15/src/harbor/models/trial/config.py)
- [`TrialResult`](https://github.com/harbor-framework/harbor/blob/6af8d6e31eced13b93849cdf80feeadf24603d15/src/harbor/models/trial/result.py)
- [`SingleStepTrial`](https://github.com/harbor-framework/harbor/blob/6af8d6e31eced13b93849cdf80feeadf24603d15/src/harbor/trial/single_step.py)
- [Artifact collection](https://github.com/harbor-framework/harbor/blob/6af8d6e31eced13b93849cdf80feeadf24603d15/docs/content/docs/run-jobs/results-and-artifacts.mdx)
- [Resource management](https://github.com/harbor-framework/harbor/blob/6af8d6e31eced13b93849cdf80feeadf24603d15/docs/content/docs/tasks/managing-resources.mdx)

## 15. 变更记录

- 2026-09-03：创建；记录已确认的 Harbor 执行 seam、真实 Job/Trial 字段、固定单机并发、补丁出口缺口、Mock 隔离和原型退出条件。
- 2026-09-04：确认首个原型数据集为 `SWE-Gym/SWE-Gym-Lite`，范围为 1～3 道真实任务；revision、split 和具体实例保持待核验。
- 2026-09-04：确认首个真实原型 Agent 为 Codex；认证采用评测机所有者的 ChatGPT Pro `auth.json`，个人凭据不得进入公共输入、数据库或制品。
- 2026-09-04：Codex CLI 项目版本、模型、端点、Token 刷新、脱敏、清理和 Harbor 容器运行仍待固定或实测。
- 2026-09-05：确认首版自研 Agent 为 Python 固定进程 Interface，由平台包装进 Harbor；只允许 DeepSeek/Kimi 独立配置，真实 Key 不直接进入被测容器，具体受控访问部署与网络隔离仍待原型。
- 2026-09-05：固定 M0 本机 Codex 脚本原型、M1 Codex 平台 MVP、Aider/Claude Code、P2 自研 Agent 的顺序；补充闭卷限制、取消/中断不自动重试和 patch/原始制品限额。
- 2026-09-06：真实 Harbor NOP Docker Trial 与项目结果映射通过；薄进程 Adapter、有界双流日志和宿主进程树超时终止完成测试；记录落盘 Job 结果不含 `trial_results`、Windows CLI UTF-8 要求、任务 collect hook/单目录 artifact 契约，以及仍未通过的真实 Codex、Harbor 超时后 Compose 清理和固定 Fork 门槛。
- 2026-09-06：阻塞 collect 的公开 Adapter 探针复现外层强杀后的 Compose 残留；新增基于本 Job Trial 身份的精确 project label 清理与日志线程总收束期限，真实超时、正常 NOP 和父子进程回归均通过。真实 Codex 与固定 Fork 仍未通过。
