# 模块职责与输入输出契约

> 文档状态：架构边界已确认；字段契约 v0.3；M0 核心闭环通过，M1 任务 01–13 已验收；任务 13 的 `-04` 正式执行、判卷、持久化、页面和双轴终审均通过；M1/MVP 尚未完成
>
> 最后更新：2026-09-17（补充现实模块文档入口；未改变已实现接口）
> 权威范围：本文件只维护项目内部模块的职责、输入、输出、错误、不变量和依赖。当前 Interface、Implementation 与 Adapter 的现实代码地图见[模块架构索引](./modules/README.md)；全局组成见 [`ARCHITECTURE.md`](./ARCHITECTURE.md)，字段级边界见 [`RUNNER_PROTOCOL.md`](../interfaces/RUNNER_PROTOCOL.md)、[`HTTP_API.md`](../interfaces/HTTP_API.md) 和 [`DATA_MODEL.md`](./DATA_MODEL.md)。

## 扩展合同增量：已确认方向、未实现

[扩展规格](../../.scratch/ui-catalog-providers/spec.md)新增 Codex + 两家按量API，不启动P2自研Agent。以下当前模块的责任不变，具体执行顺序见[计划](../../.scratch/ui-catalog-providers/plan.md)：

- Task Catalog：仅登记资格合格的固定题目，沿用公开/隐藏数据分离；候选存在不等于目录可用。
- Agent Registry：计划增加有限受控API预设；不是开放任意模型、地址、命令或Key输入。身份、SQL约束与快照校验必须同时升级，旧指纹兼容。
- Job Submission/Repository：新连续规模版本只影响新提交；仍原子保存冻结Job、全部Run和初始事件并立即等待批准，不读Key/启动Agent。原恢复不续跑、新Job重试保留。
- ExecutionBackend：接口不变，Harbor Adapter内部在已批准Run开始时建立受控代理绑定。提供方鉴权、协议、限额或生命周期失败映射现有基础设施/策略错误，不伪装为题目未通过、不自动重试。代理不能判分或自行领取任务。
- PatchEvaluator/报告/排行榜：固定Fork独立判断补丁；报告对比复用既有数据，可比性按冻结条件校验，不新增Judge评分或计费平台。

代理短命令牌、真实Key、私有拓扑与故障关闭合同由[认证4.1](../interfaces/CODEX_AUTHENTICATION.md#41-codex-第三方-api-扩展规划2026-09-17)维护。当前只有配置探针，安全实现未验收；后文旧版规模/提供方限制表示当前代码，不撤销此规划。

## 1. 先用小白能懂的话解释

一个“模块”可以理解成一个只开一个窗口的部门。调用者只需要知道：

1. 应该交给窗口什么材料（输入）；
2. 窗口会交回什么结果（输出）；
3. 哪些情况算业务上没成功，哪些情况是系统坏了（错误）；
4. 窗口永远不能破坏什么规则（不变量）。

例如 Execution Backend 只负责“让一批 Agent 工作并按逐题运行拿回补丁和证据”，不负责判断补丁对不对；Patch Evaluator 只负责“用测试判补丁”，不负责评价 Agent 是否积极。这样 Harbor Job/Trial 的复杂性不会污染业务模块。

## 2. 状态和命名规则

- **已确认**：用户已经决定的项目规则。
- **已核验**：从上游源码或官方文档查到的事实。
- **候选 v0.1**：本项目拟采用、等待继续讨论的内部契约。
- **待确认/待实测**：需要业务决定或真实运行证据。
- 本文中的类型名是为了讨论边界的概念名，不等于已经存在的 Python 类。
- 领域词义以 [`CONTEXT.md`](../../CONTEXT.md) 为唯一事实源，本文不重新定义同义词。

## 3. 模块依赖方向

```mermaid
flowchart LR
    WEB[Next.js Web] --> HTTP[HTTP Delivery]
    HTTP --> APP[Application Use Cases]
    WORKER[Worker Shell] --> APP
    APP --> DOMAIN[Domain Rules]
    APP --> PORTS[Ports / 内部接口]
    ADAPTERS[External Adapters] -. 实现 .-> PORTS
    ADAPTERS --> EXT[SWE-Gym / Harbor / SWE-Bench-Fork / Docker / PostgreSQL / MinIO / LLM]

    DOMAIN -. 不允许依赖 .-> EXT
```

硬规则：

- `domain` 不依赖 FastAPI、PostgreSQL、Docker、MinIO、SWE-Gym 或任何 Agent CLI。
- `application` 只依赖领域对象和小型 ports，不直接拼 CLI 命令或 SQL。
- `adapters` 可以依赖外部工具，但外部类型不能向内泄漏到所有模块。
- Web 不直接操作 Docker、数据库或 MinIO；Worker 不绕过状态机直接改运行状态。
- 模块之间不得循环依赖。

## 4. 公共输入输出对象

下表是模块之间传递的最小概念对象。字段的存储映射见 [`DATA_MODEL.md`](./DATA_MODEL.md)。

| 对象 | 必需内容 | 明确不包含 | 主要生产者 → 消费者 |
|---|---|---|---|
| `EvaluationTask` | `instance_id`、数据集身份/版本、`repo`、`base_commit`、`problem_statement`、原始任务 JSON 制品引用、验证引用 | 不向 Agent 暴露 gold `patch`、`test_patch`、隐藏测试答案 | Task Catalog → Job Submission、Job Orchestrator、Patch Evaluator |
| `AuthenticatedActor` | 可信会话中的用户 ID 与 `collaborator`/`owner` 角色 | 密码、会话秘密、由请求正文自报的角色 | HTTP Delivery → 授权保护的应用用例 |
| `AgentConfiguration` | 登记 ID、Agent 类型/版本、模型提供方/模型、非秘密认证配置引用、关键配置、Adapter 类型、配置指纹 | 明文 API key、临时登录 token | Agent Registry → Job Submission、Job Orchestrator、Execution Backend |
| `EvaluationJobSpec` | `job_id`、选中的任务/Agent 配置、赛道、限制模板、预计运行数、结果范围 | Harbor `JobConfig`、用户任意命令/路径 | Job Submission → Job Repository、Job Orchestrator |
| `OwnerDecision` | `job_id`、批准或拒绝、规范化可选说明、可信会话中的所有者身份、决定时间及幂等哈希 | Codex 凭据、任意资源覆盖、请求正文伪造的批准人 | Owner Approval → Job Repository |
| `CancellationRequest` | `job_id`、可信会话用户 ID、规范化可选说明、请求时间、幂等键哈希和正文哈希 | 请求正文伪造的用户/角色、强杀命令、凭据或任意资源覆盖 | Job Cancellation → Job Repository |
| `EvaluationPolicy` | `evaluation_track`（MVP 仅 `closed_book`，预留 `open_book_experimental`）、已登记网络策略、已登记工具配置及其版本 | 按模型国别猜测的能力、用户任意代理/网址配置 | Job Submission → Job Orchestrator、Execution Backend、Reporting |
| `RunLimits` | 墙钟超时、CPU、内存、PID、patch/日志/单运行原始制品大小、Agent 特有限制 | 用户可随意提交的宿主机权限 | Job Submission → Job Orchestrator、Execution Backend、Artifact Store |
| `ExecutionJobRequest` | Job 身份、逐题 `run_id` 映射、任务、Agent 配置、策略、限制、后端版本 | 判分答案、gold patch、Harbor 外的任意执行命令 | Job Orchestrator → Execution Backend |
| `ExecutionTrialResult` | `run_id`、后端 Job/Trial 引用、终止原因、补丁/轨迹/原始结果引用、资源汇总 | `resolved` 或“补丁是否修好”的结论 | Execution Backend → Job Orchestrator |
| `EvaluationRequest` | `run_id`、`instance_id`、`model_patch`、可追溯的 Agent 身份 | Agent 的自然语言自评 | Job Orchestrator → Patch Evaluator |
| `DeterministicResult` | `resolved`、补丁应用情况、测试分类、Harness 报告/日志引用、基础设施错误 | LLM 主观评分 | Patch Evaluator → Job Orchestrator、Reporting、Judge |
| `TraceEvent` | 时间、序号、事件类型、来源、公开载荷、原始事件引用 | 思维链、秘密、未脱敏环境变量 | Adapter/Recorder → Artifact Store、Reporting |
| `JudgeRequest` | `failure_diagnosis`/`quality_tiebreak` 用途、触发上下文、任务/补丁/确定性结果/轨迹的受控引用、Prompt 与输入策略版本 | 凭据、隐藏答案、无关宿主信息、未清洗完整日志 | Job Orchestrator → Judge |
| `JudgeAnalysis` | 用途、状态、失败分类或匿名两两质量比较结果、比较范围、解释、证据引用、模型/Prompt/输入策略/rubric 版本、原始响应引用 | 对 `resolved` 的覆盖权、无证据的强制胜者 | Judge → Review、Reporting |
| `HumanReviewRecord` | 运行或 Job 级质量比较、复核结论、对 Judge 的确认/修正、备注、复核者、时间 | 对原始制品的覆写、人工指定质量胜者 | Review → Job/Run Repository |
| `ArtifactRef` | 对象键、类型、大小、SHA-256、内容类型、保留级别、截断/删除状态、创建时间 | 制品正文 | Artifact Store → 其他所有模块 |

### 4.1 当前 M0 实现与目标契约的区别

上表描述完整平台的概念契约，不代表所有同名 Python 类型已经具备全部字段。当前 M0 保留公开 `EvaluationTask` 与受限 `EvaluatorTaskData`，通过 `TaskBundle` 关联；不把隐藏判分字段放回 Agent 可见对象。`RunLimits` 目前只有墙钟、CPU、内存和存储字段，部分额外限制由执行实现中的固定值落实，尚未形成完整的冻结限制模板。制品限制的实际覆盖见 [Harbor 单机资源规则](../interfaces/HARBOR_EXECUTION.md#12-单机资源规则)。

M0 的制品引用指向本机原型证据，尚不是带完整保留/删除状态的 MinIO `Artifact Store`；`DeterministicResult` 返回判卷标志和报告引用，测试明细保留在报告中，无法形成可信结果的错误通过 `EvaluationError` 表达。以上属于当前阶段覆盖差异，不能把目标对象表当作已实现清单，也不据此提前新增 M1 模块。

## 5. 模块总表

阶段范围以[总架构第 3.1 节](./ARCHITECTURE.md#31-m1-交付边界2026-09-09-已确认)为准。本文保留完整目标契约；M1 不实例化 Judge/Human Review，也不要求相关专用 port 或 Adapter，Owner Approval 与安全证据查询仍启用。

| 模块 | 大致做什么 | 主要输入 | 主要输出 | 不负责 |
|---|---|---|---|---|
| HTTP Delivery | 把浏览器请求翻译为应用用例 | HTTP 请求 | HTTP 响应/错误 | 运行 Agent、写 SQL |
| 身份/成员用例（任务 01–02，已批准） | owner 引导/恢复、登录/退出、可信身份、受控邀请及停用 | 本机维护、会话或受控邀请输入 | 公开身份/邀请/成员或安全错误 | 管理 Codex 凭据、执行 Job、公开注册、任意角色管理 |
| Task Catalog | 从固定 SWE-Gym 数据取得任务 | 数据集版本 + `instance_id` | `EvaluationTask` | 运行或判题 |
| Agent Registry | 只提供已审核 Agent 配置 | 配置 ID/筛选条件 | `AgentConfiguration` | 下载任意仓库 |
| Job Submission | 校验矩阵并创建等待所有者批准的 Job | 任务 ID[] + Agent 配置 ID[] + 赛道/限制模板 | `job_id`、`run_id[]`、Trial 数和 `AWAITING_OWNER_APPROVAL` | 执行评测、替所有者批准 |
| Owner Approval | 由评测机所有者批准或拒绝冻结的 Job | `JobApprovalDecision` + 待批准 Job | `QUEUED` 或 `REJECTED` Job + 审计事件 | 运行 Agent、读取 Codex 凭据、修改冻结配置 |
| Job Cancellation | 授权并记录协作式取消 | `CancellationRequest` + 当前 Job | `CANCELED` 或 `CANCEL_REQUESTED` Job + 审计事件 | 强杀当前 Trial、删除证据、自动重试 |
| Job/Run Repository | 保存、领取、推进和查询 Job/运行 | Job/运行状态命令 | 持久化结果/查询视图 | 保存大制品正文、调度 Harbor Trial |
| Job Orchestrator | 编排一个 Job 的执行和逐题判卷 | 已领取 Job | Job 汇总与逐题完整结果 | 理解 Harbor 类型或具体 CLI |
| Execution Backend | 执行一批 Agent×任务并返回逐题补丁/证据 | `ExecutionJobRequest` | `ExecutionTrialResult[]` | 判断补丁正确性、管理业务队列 |
| Agent Source Review（P2） | 未来审核自研源码提交并登记可执行配置；MVP 不实现 | Git URL + commit + manifest + 审核决定 | 已登记/拒绝的 Agent 配置 | 审核前执行仓库代码 |
| Patch Evaluator | 调用 SWE-Bench-Fork 判卷 | `EvaluationRequest` | `DeterministicResult` | LLM 评分 |
| Trajectory Recorder | 规范化并保存可公开过程证据 | 原始 CLI/进程事件 | JSONL 轨迹引用 + 汇总 | 保存思维链或秘密 |
| Artifact Store | 保存不可变文件证据 | 字节流 + 元数据 | `ArtifactRef` | 决定运行状态 |
| Judge（M1 后） | 按已确认触发规则清洗证据并执行失败诊断或质量并列比较 | `JudgeRequest` | `JudgeAnalysis` | 修改确定性事实、在证据不足时强行排序 |
| Human Review（M1 后） | 领取抽检并保存人工结论 | 待复核运行 + 人工输入 | `HumanReviewRecord` | 重跑 Agent |
| Reporting | 组合只读报告和排行榜 | 查询条件 | 报告/排行视图 | 改写原始结果 |
| Worker Shell | 原子领取平台 Job 并调用 Job Orchestrator | Worker 身份 + 轮询配置 | 心跳/Job 执行结果 | 包含业务判定规则 |

## 6. 逐模块契约

### 6.1 HTTP Delivery

| 项目 | 候选 v0.1 契约 |
|---|---|
| 调用方 | Next.js Web；首版不允许 Web 直接访问存储 |
| 输入 | 经过版本化的 HTTP 请求、路径参数和查询参数 |
| 输出 | 稳定的 JSON 成功响应，或统一 `ApiError` |
| 错误 | 请求格式错误、资源不存在、状态冲突、服务暂不可用 |
| 不变量 | 只调用 application 用例；不执行 Agent、不拼 SQL、不返回 MinIO 密钥；不开放注册；从可信会话提供 `AuthenticatedActor`，不能相信正文中的用户或角色 |
| 依赖 | Job Submission、Review、Reporting 等应用入口 |
| 验证 | OpenAPI schema 检查；请求/响应契约测试；错误码测试 |

详细端点只在 [`HTTP_API.md`](../interfaces/HTTP_API.md) 维护。

#### 6.1.1 身份用例与存储 Interface（2026-09-11）

用户已确认在既有单体的应用层补齐身份用例，而不拆新服务。HTTP 入口和本机 owner CLI 调用 IdentityService；它只依赖领域对象、IdentityRepository 和 Passwords ports。登录密码由 Argon2 Adapter 处理，身份由 PostgreSQL Adapter 持久化；测试可替换外部存储和时间，但不能替换应用授权逻辑。

IdentityRepository 提供建立唯一 owner、按登录名读取账号、核验版本并签发会话、读取会话身份、撤销会话及原子恢复 owner；调用方不见 SQL/连接类型，存储错误统一转为 IdentityUnavailable，冲突为 IdentityConflict。Passwords 只提供 hash/verify，密码库不进入领域/用例层。

不变量：不信任正文角色；不存在/错误密码对外同样拒绝；恢复保留 owner ID、撤销全部旧会话，旧版本登录不能绕过恢复。事务细节由[数据契约](DATA_MODEL.md#40-身份表accounts-与-sessions)维护，Cookie/Origin 与端点由[HTTP 契约](../interfaces/HTTP_API.md#32-任务-01-身份-http-切片)维护；本模块不承担 Worker、任务批准或模型认证。

当前真实验证和环境缺口见[身份行动](../actions/2026-09-11-m1-owner-identity.md)。用户确认结构不等于身份任务全部验收通过。

任务 02 在同一分层增加 MembershipService，复用 Passwords；经已确认 MembershipRepository 提供 create/redeem/list/revoke invitation、list/disable member 六个操作。它不接收 SQL、连接或客户端自报角色；管理操作必须使用 IdentityService 从当前会话获得的 owner，兑换只建立 collaborator。PostgresMembershipRepository 实现存储边界，身份和成员 Adapter 共用内部短事务/错误转换；不是新认证服务。

Invitation、InvitationSummary、Member 是不含凭据的领域值，创建用例只额外返回一次随机邀请码；列表为有界分页。错误为 MembershipForbidden、InvitationUnavailable、MemberNotFound、IdentityConflict/IdentityUnavailable，由 Delivery 转为稳定 HTTP 错误。字段、到期和原子性唯一维护在[数据契约](DATA_MODEL.md#401-邀请表invitations)，端点在[HTTP 契约](../interfaces/HTTP_API.md#33-任务-02-邀请与成员-http-切片)。受控本机补表命令和运行组装不会自动创建成员。当前验收与待验证项见[成员行动](../actions/2026-09-11-m1-collaborator-invitations.md)。

### 6.2 Task Catalog

任务 03 已实现并完成本任务验收：`TaskCatalog.register/get/list` 只接受可信 Actor 和受控预置 ID/查询参数；`TaskSource.load(instance_id)` 复用既有 SWE-Gym Adapter。TaskRepository 的 `publish/get/list` 隐藏任务+制品索引的原子发布和稳定 UUID 分页；同身份同内容返回原记录，变化抛出 CatalogConflict。ArtifactStore 的 `put_immutable/read_verified` 隐藏条件写与实际字节校验。对象写入/验证先于数据库短事务，数据库失败不立即删对象；任务 Repository 读出时核验标准正文摘要，普通查询另校验对应原始对象；不一致或缺失均返回安全依赖错误。HTTP 切片及隔离真实持久化已通过，实际证据与未覆盖边界见任务 03 行动；不会修改 M0 的 ExecutionBackend/PatchEvaluator Interface。

| 项目 | 候选 v0.1 契约 |
|---|---|
| 调用方 | Job Submission、Job Orchestrator、Reporting |
| 输入 | `dataset_id`、`dataset_revision`、`split`、`instance_id` |
| 输出 | 规范化 `EvaluationTask`、内容哈希固定的原始任务 JSON `ArtifactRef`，以及仅供 Evaluator 使用的验证引用 |
| 错误 | 数据集不存在、任务不存在、字段缺失、固定版本校验不一致 |
| 不变量 | 同一数据集版本和任务 ID 必须返回相同标准字段与原始 JSON 哈希；Agent 可见视图不得包含 gold patch/测试答案 |
| 依赖 | SWE-Gym 数据；SWE-Bench-Fork 的任务字段约定 |
| 验证 | 用固定样例检查字段映射；测试秘密字段不会进入 Runner 输入 |

### 6.3 Agent Registry

任务 03 已落地 `AgentRegistry.register/get/list/disable` 和 AgentConfigurationRepository：只从服务端固定 preset 建立配置，管理动作要求可信 owner；查询允许已登录协作者。复用 AgentConfiguration 的不可变关键配置与指纹，公开选项仅受控 reasoning_effort；同指纹登记返回原身份，禁用只改变状态/首次禁用时间，不删除或隐式重新启用。PostgreSQL Adapter 重算指纹以核对读出内容，外部驱动错误转换为安全 CatalogUnavailable。HTTP 切片、真实事务和浏览器管理流程已有验证，当前完整回归与评审状态见任务 03 行动。

| 项目 | 候选 v0.1 契约 |
|---|---|
| 调用方 | Job Submission、Job Orchestrator、Execution Backend、Reporting |
| 输入 | 登记配置 ID，或只读筛选条件 |
| 输出 | 固定版本的 `AgentConfiguration`；可展示列表 |
| 错误 | 未登记、已禁用、版本/镜像不存在、配置指纹不匹配 |
| 不变量 | 只返回项目预登记配置；当前为 Codex/ChatGPT，本次计划扩展 Codex `deepseek`/`kimi`；Agent + 提供方 + 模型 + 关键配置共同构成身份；Aider/Claude Code和P2自研不在本轮实施范围 |
| 依赖 | PostgreSQL 配置记录；项目内 Adapter Factory |
| 验证 | 未登记命令不能运行；相同配置生成相同指纹；秘密不进入查询结果 |

### 6.4 Job Submission

任务 04 的最小实现已落地提交、列表、详情和只读选项，并由 HTTP、合成 Adapter 与真实 PG 验证；任务 05 的 Owner Approval 已接在冻结结果之后，领取与执行仍保持后续任务边界。JobSubmission 只依赖 TaskCatalog、AgentRegistry、JobRepository 和服务端 `SubmissionPolicy`，构造中没有 ExecutionBackend、PatchEvaluator 或凭据提供方。

| 项目 | 候选 v0.1 契约 |
|---|---|
| 调用方 | HTTP Delivery |
| 输入 | `AuthenticatedActor`、`task_ids[]`、`agent_configuration_ids[]`、`evaluation_track`、登记的规模预设与 `limit_profile_id` |
| 输出 | 新 `job_id`、`AWAITING_OWNER_APPROVAL` Job、交叉组合产生的 `run_id[]`、`trial_count`、创建时间 |
| 错误 | 任务/Agent 不存在、配置禁用、限制越界、重复幂等键冲突 |
| 不变量 | 只有受邀 `collaborator`/`owner` 可提交；任务与 Agent 列表非空且去重；首版每组合尝试一次；demo 1–3 题、quick 5 题、standard 10–20 题，最多 3 个启用配置和 60 条 Run；MVP 只接受 `closed_book`；创建时冻结任务/Agent/后端/策略/限制；新 Job 不得直接排队；不接收任意 shell 命令或资源值；Mock Job 必须隔离为 `internal_test` |
| 依赖 | Task Catalog、Agent Registry、Job/Run Repository |
| 验证 | 合法矩阵生成正确数量的运行；越权限制被拒绝；重复幂等请求不产生两个 Job；超出规模预设在执行前拒绝 |

### 6.5 Owner Approval

任务 05 实际 `OwnerApproval` 只依赖 `JobRepository` 与时钟。它从可信会话取 actor，规范化可选说明，计算决定正文/幂等键哈希后调用一次 `decide`；构造中没有 ExecutionBackend、PatchEvaluator、Harbor、Docker 或凭据提供方。Web 只对 owner 且待批 Job显示控件，HTTP 仍执行最终授权。

| 项目 | 当前 v0.1 契约 |
|---|---|
| 调用方 | HTTP Delivery；调用身份必须来自可信会话 |
| 输入 | 可信 `AuthenticatedActor`、`job_id`、approve/reject、可选规范化说明与 `Idempotency-Key` |
| 输出 | 批准时为 `QUEUED` Job；拒绝时为 `REJECTED` Job；两者都追加包含决定者和时间的状态事件 |
| 错误 | 非所有者身份、Job 不存在、并发版本冲突、Job 已被决定、数据库暂不可用 |
| 不变量 | 只有评测机所有者角色可决定；不能由正文指定决定者；不能在批准时改任务/Agent/赛道/限制；不读取凭据、不启动 Docker；同键同决定重放原结果，同键异正文或已决定状态明确冲突；同一 Job 只接受一次最终决定 |
| 依赖 | Job/Run Repository |
| 验证 | 提交者批准返回禁止；所有者批准只发生一次且进入 `QUEUED`；拒绝后永不被 Worker 领取；并发批准/拒绝只有一个成功 |

### 6.5.1 Job Cancellation

任务 09 的 `JobCancellation` 只依赖 `JobRepository` 与时钟。它从可信会话读取 actor，协作者只能匹配 Job 的 `created_by`，owner 可取消任意 Job；其他协作者与记录不存在统一返回不存在。说明和幂等值在应用层规范化，Repository 用同一 Job 行锁原子决定直接终结或仅登记请求，不接触 Harbor、模型或真实凭据。

| 项目 | 当前 v0.1 契约 |
|---|---|
| 调用方 | HTTP Delivery；调用身份必须来自可信会话 |
| 输入 | 可信 `AuthenticatedActor`、`job_id`、可选规范化说明与 `Idempotency-Key` |
| 输出 | 当前 Job 记录及首次受理状态；待批/排队/未启动准备态首次为 `CANCELED`，执行态首次为 `CANCEL_REQUESTED`；均含请求人、时间、说明和状态事件 |
| 错误 | Job 不存在或不可见、终态/并发状态冲突、同键异正文冲突、数据库暂不可用 |
| 不变量 | 正文不能指定身份；相同键和正文在 Job 后续收束后仍重放首次受理状态；直接取消和 Worker 对账均复用同一未启动 Run 写入；执行中不强杀当前 Trial、不覆盖完成结果、不删除制品、不自动重试 |
| 依赖 | Job/Run Repository |
| 验证 | HTTP 各可取消阶段与越权；真实 PostgreSQL 的批准/领取竞争；受控执行保留当前结果并阻止后续 Trial；浏览器区分请求态和终态 |

### 6.5.2 Interruption Recovery

任务 10 的 `JobRecovery` 只依赖既有 `JobRepository`、`JobSubmission` 与时钟。HTTP 从可信会话取得 owner，应用层把 `job_id`、owner 身份和当前时间封装为 `RecoveryRequest`；Repository 在一个短事务中锁 Job 和 Runs，并只接受已过期的活跃租约。手动重试不是执行旧 Run，而是复用提交用例重新核对当前目录、冻结新快照并创建关联 Job。

| 项目 | 当前 v0.1 契约 |
|---|---|
| 调用方 | HTTP Delivery；调用身份必须来自可信 owner 会话 |
| 输入 | 收束：`RecoveryRequest(job_id, actor_user_id, occurred_at)`；重试：旧 `job_id` 与 `Idempotency-Key` |
| 输出 | 收束后的原 Job，或带 `rerun_of_job_id`、全新 Run 且等待批准的新 Job |
| 错误 | 非 owner、Job 不存在、租约未过期/状态不允许、持久化证据错配或数据库暂不可用、重试幂等冲突 |
| 不变量 | 不自动扫描、续跑、排队、判卷或调用模型；完成结果须与摘要、冻结 Harness revision 和布尔关系一致，活跃 Run 记基础设施中断，PENDING Run 取消；持久化取消意图在 FINALIZING 后仍有效；重复收束不加事件；重试保留原 `created_by` 访问范围并重新等待批准 |
| 依赖 | Job/Run Repository、Job Submission；无 ExecutionBackend/PatchEvaluator/Harbor 依赖 |
| 验证 | HTTP 权限/正文、混合 Run、取消交叉、PG 并发/回滚、旧 Worker、重复恢复与浏览器重试动线 |

### 6.6 Job/Run Repository

当前 `JobRepository` Interface 已包含任务 04 创建/读取/分页、任务 05 `decide(OwnerDecision)`、任务 06 的领取/结果/报告、任务 07 的逐 Run 生命周期、任务 09 的 `cancel(CancellationRequest)` 与返回 `TrialStart` 准入结果的 `start_run`，以及任务 10 的 `recover(RecoveryRequest)`。生产 PostgreSQL Adapter 以短事务、Worker 租约和 Job/Run 行版本推进；领取另用事务级 advisory lock、活跃状态检查及 `FOR UPDATE SKIP LOCKED` 保证单机全局一个重型 Job。外部执行/判卷期间不持有事务；逐 Run 顺序固定为任务 ID、配置 ID、Run ID。恢复只在租约过期后读取数据库终态和 `deterministic_results`，并核对 Run 摘要、冻结 Harness revision 与结果布尔关系；任一错配整笔回滚。

| 项目 | 候选 v0.1 契约 |
|---|---|
| 调用方 | Job Submission、Owner Approval、Job Cancellation、Job Recovery、Worker Shell、Job Orchestrator、Review、Reporting |
| 输入 | 创建 Job/运行、所有者批准/拒绝/取消/恢复请求、原子领取一个已批准 Job、合法状态迁移、附加结果、查询命令 |
| 输出 | 当前 Job/运行、领取结果、版本号或只读查询视图 |
| 错误 | 状态冲突、并发版本冲突、记录不存在、数据库暂不可用 |
| 不变量 | 状态迁移只按 `DATA_MODEL.md`；待批准/已拒绝 Job 不能被领取；一个 `QUEUED` Job 只被一个 Worker 领取；单机最多一个重型 Job 活跃；执行中取消请求不强杀当前 Trial，只阻止后续 Trial；崩溃不自动续跑/重试；大制品只存引用 |
| 依赖 | PostgreSQL Adapter |
| 验证 | 并发批准/拒绝、取消/批准/领取和重复恢复；待批准/已拒绝/已取消 Job 不可领取；执行中取消后新 Run 准入返回拒绝；过期 Worker 失效、损坏证据和事务回滚测试 |

### 6.7 Job Orchestrator

| 项目 | 候选 v0.1 契约 |
|---|---|
| 调用方 | Worker Shell |
| 输入 | 已领取且处于 `PREPARING` 的 Job 及其 `PENDING` 运行快照 |
| 输出 | Job 汇总、逐题运行结果，或明确的部分/整体基础设施失败记录 |
| 错误 | 任务准备、Agent、补丁提取、Evaluator 或存储阶段错误；Judge 错误单独记录为分析不可用，不能伪装成确定性运行失败；所有错误必须带阶段和证据引用 |
| 不变量 | 每条运行先完成 Harbor 执行、证据保存和固定 Fork 干净验证；收到取消请求后不启动下一条 Trial，当前 Trial 至多运行到冻结超时；Failure Judge 只按人工请求/抽样运行，Quality Judge 只在整个可比批次形成严格确定性并列后运行；Harbor reward 与 Judge 都不能写入确定性结果；已完成 Trial 的证据不因后续 Trial/Judge 失败而丢失 |
| 依赖 | M1：Task Catalog、Execution Backend、Patch Evaluator、Artifact Store、Job/Run Repository；Judge 仅后续启用 |
| 验证 | 用 Fake ports 覆盖每个分支；任一步骤失败都不会伪装成完成；重试不覆盖旧制品 |

这是一个“深模块”：对外只有“执行一个 Job”，内部隐藏逐 Trial 判卷、部分失败、证据保存和汇总，不让 Worker 参与编排细节。

M1 不进入上述 Judge/Review 分支；确定性结果和制品固定后完成逐题收束，不因未开发分析模块而保留虚假的分析中或待复核状态。

任务 06 已实现单 Run 子集：`JobExecutor` 只接受一个已领取的 Run，从冻结快照构造 `ExecutionJobRequest.single_run`，并直接使用 Run 冻结的执行契约版本。既有 Harbor 与 Fork Adapter 继续返回受控本地引用；`LocalArtifactReader` 只在固定根目录内按类型、大小和 SHA-256 读取，`EvidencePublication` 再把 patch、Harness 报告和测试输出规范化为 `runs/{run_id}/{type}/{sha256}` 长期对象。编排校验后端身份、patch 字节/哈希/大小/文本 diff，再调用一次固定 Fork Evaluator；空补丁必须同时为未应用、未解决，超过 256 KiB 保留警告，超过 1 MiB、二进制或非 diff 收束为平台失败。多组合 Job 在任务 07 前不领取。

任务 07 已实现多 Run 子集：`JobExecutor` 一次构造完整冻结矩阵并调用一次 Backend；`BatchProgress` 只接受规范顺序的开始/结束身份，重复通知幂等忽略，乱序或返回身份缺失以安全错误收束。每项返回结果独立保存 patch、调用 Evaluator 并发布确定性结果；中间错误不会抹掉先前结果，也不会阻止后续返回项收束。全部 Run 终止后才进入 `FINALIZING`；全部有可信确定性结果为 `COMPLETED`，部分错误为 `COMPLETED_WITH_ERRORS`，无可汇总结果为 `FAILED`。Harbor Job 汇总缺失时仍保留可验证的逐 Trial 结果，协议异常不会把 Job 误报为全成功；后端审计引用只能是安全不透明标识，不能泄漏宿主路径。

任务 09 让 `BatchProgress.trial_started(run_id)` 返回准入布尔值。Repository 在这个短事务内重新读取 Job：正常时把 Run 推进为 `RUNNING_AGENT` 并返回租约，已进入 `CANCEL_REQUESTED` 时把该 Run 和其余未启动 Run 写为 `CANCELED` 并返回拒绝。当前已获准的 Trial 继续经过证据保存和确定性判卷；最终化读取取消审计并把 Job 收束为 `CANCELED`，不会把已完成结果重写成失败或删除制品。

### 6.8 Execution Backend

| 项目 | 候选 v0.1 契约 |
|---|---|
| 调用方 | Job Orchestrator |
| 输入 | `ExecutionJobRequest`；只含已登记任务/Agent、冻结策略、限制和 `run_id` 映射 |
| 输出 | Observer 以 `trial_started(run_id) -> bool` 决定下一 Trial 是否准入并通知已准入项结束；最终仍返回已实际完成且与请求对应的 `ExecutionTrialResult[]`，补丁、轨迹和原始输出均通过 `ArtifactRef` 关联 |
| 错误 | 后端版本不符、配置映射失败、认证、环境、超时、Agent、补丁提取、Trial 身份或制品错误 |
| 不变量 | Observer 不传日志、结果正文或凭据，只传冻结 `run_id` 和准入布尔值；拒绝后端不得启动该 Trial；不能宣判 `resolved`；不能把自然语言回答当补丁；不能运行未登记配置；Harbor `TrialResult` 不向调用方泄漏；并发固定 1；MVP 只要求 Codex，随后复用 Harbor 的 Aider/Claude Code；P2 自研 Agent 才运行已审核 Python 进程 Interface 且不取得 DeepSeek/Kimi 真实 Key |
| 依赖 | Agent Registry、Harbor 固定提交、Docker、Trajectory Normalizer、Artifact Store；P2 自研 Agent 才复用现有 LLM Provider Adapter 的受控访问 Implementation |
| 验证 | Harbor/Fake Backend 共用同一 interface contract；空补丁与失败分开；真实 SWE-Gym 单题原型覆盖补丁、轨迹、资源和清理 |

M0 当前实现注记：执行 port、Harbor Adapter、配置/身份映射、patch 校验及本机原型编排已存在；第四场真实 Codex 已接通独立判卷。已有运行证据与完整验收的区别统一见 [Harbor 验收对账](../interfaces/HARBOR_EXECUTION.md#暂停后的验收对账2026-09-08)，不把完整平台所需依赖写成已实现。

Harbor 映射见 [`HARBOR_EXECUTION.md`](../interfaces/HARBOR_EXECUTION.md)；生产网络配置已在既有 Backend 内接线，最新真实运行及未验收边界统一见其[第四场记录](../interfaces/HARBOR_EXECUTION.md#第四次授权运行真实补丁与独立判卷通过2026-09-08)和验收对账，不增加公开请求字段或新 port。自研/后备进程边界见 [`RUNNER_PROTOCOL.md`](../interfaces/RUNNER_PROTOCOL.md)。

### 6.9 Agent Source Review（P2，MVP 不实现）

| 项目 | 候选 v0.1 契约 |
|---|---|
| 调用方 | P2 自研 Agent 提交入口、所有者审核界面；MVP 无调用方 |
| 输入 | 固定 Git URL、完整 commit SHA、仓库根 `agent-exam.yaml`、说明和审核决定 |
| 输出 | `PENDING_REVIEW` 提交记录，或审核通过后新 `AgentConfiguration` |
| 错误 | URL/commit/manifest 无效、来源不可访问、危险声明、重复提交、权限不足 |
| 不变量 | 不得为 MVP 预先实现；P2 审核前不执行仓库代码、不构建镜像；自研接入首版只接受固定 Python 进程 Interface；不把提交者输入直接变成 Harbor `import_path`/命令，不接收 shell、Key、自定义提供方/Base URL、代理或宿主路径；禁用不删除历史配置 |
| 依赖 | Agent Registry、PostgreSQL；manifest 的完整字段、Python 版本和依赖锁格式仍待确认/实测 |
| 验证 | 未审核提交无法创建 Job；分支/`latest` 被拒绝；审核事件可追溯；非 Python Interface、秘密、任意命令和未允许提供方不进入公开配置 |

### 6.10 Patch Evaluator

| 项目 | 候选 v0.1 契约 |
|---|---|
| 调用方 | Job Orchestrator |
| 输入 | `EvaluationRequest` |
| 输出 | `DeterministicResult` 和 Harness 制品引用 |
| 错误 | prediction 格式错误、镜像构建失败、补丁无法应用、测试超时、Harness 异常 |
| 不变量 | 直接调用固定版本 SWE-Bench-Fork；Agent 生成环境的残留不得进入验证；Judge 不能改写输出 |
| 依赖 | SWE-Bench-Fork、SWE-Gym 数据/环境、Fork 自身 Docker Harness、Artifact Store |
| 验证 | gold patch、空 patch、错误 patch、不可应用 patch、测试超时五类样例 |

注意：补丁“可应用但测试未通过”是一次正常完成的确定性评测；Harness 无法完成才是基础设施错误。

M0 当前实现：`SWEbenchEvaluator` 复用已校验 Task Catalog，逐字段核对请求中的 Evaluator 视图，冻结 JSONL 和不可覆盖证据目录。`EvaluationError` 在既有 port 中表达无法形成可信结果的错误及证据引用；`DeterministicResult` 只返回真实空补丁分类或完整、相互一致的报告。固定 Fork 在独立禁网容器中通过 gold、空、错误、不可应用和测试超时五类验证；框架实际调用与基础设施适配边界见 [`FRAMEWORK_INTERFACES.md` 第 5 节](../interfaces/FRAMEWORK_INTERFACES.md#5-swe-bench-fork-patch-evaluator)。真实 Codex 补丁接入该判卷路径的证据见 [Harbor 第四场记录](../interfaces/HARBOR_EXECUTION.md#第四次授权运行真实补丁与独立判卷通过2026-09-08)。

### 6.11 Trajectory Recorder

| 项目 | 候选 v0.1 契约 |
|---|---|
| 调用方 | Execution Backend Adapter 内部实现 |
| 输入 | Codex/Claude/Aider/自研 Agent 的原始事件，外加统一时间和来源信息 |
| 输出 | 按序 JSONL 轨迹 `ArtifactRef`，以及工具调用数、耗时、token 等只展示汇总 |
| 错误 | 事件无法解析、序号断裂、大小超限、写入失败 |
| 不变量 | 保存可观察事件，不要求或保存私密思维链；保留 `raw_type` 以便审计；任何秘密先脱敏；缺失指标写“不支持/未知”而不是 0，过程指标不参与排名 |
| 依赖 | Artifact Store；各 CLI 的官方事件格式 |
| 验证 | 预制事件样本契约测试；坏行容错；脱敏、顺序和汇总一致性检查 |

### 6.12 Artifact Store

| 项目 | 已实现的 M1 契约 |
|---|---|
| 调用方 | Job Orchestrator、Execution Backend、Recorder、Evaluator、Judge、Reporting |
| 输入 | 任务、`job_id` 或 `run_id` 所有者范围、制品类型、文件名、内容流、内容类型、保留级别 |
| 输出 | 带 SHA-256、大小、对象键、警告/截断状态和保留元数据的 `ArtifactRef` |
| 错误 | 写入/读取失败、校验和不一致、对象不存在、类型不允许、patch/单运行原始制品超过硬限制 |
| 不变量 | 制品写入后不可覆盖；重跑创建新 `run_id`；对象键不包含秘密或用户路径；任务原始 JSON、配置快照、确定性结果、最终 patch 和测试摘要长期保留；大型轨迹/stdout/stderr/Judge 原始响应 30 天后才可由所有者本地维护命令清理，删除后元数据与审计保留 |
| 依赖 | MinIO；PostgreSQL 中的 `artifact_records` 索引 |
| 验证 | 同内容校验、覆盖拒绝、断流、缺失对象、大文件流式测试；256 KiB patch 警告、1 MiB patch 拒绝不截断、50 MiB 日志显式截断、200 MiB 单运行原始制品硬限制与所有者清理审计 |

任务 08 没有新增存储 Interface：`EvidencePublication` 从受限原始引用派生公开测试计数和安全轨迹，Artifact Store 仍只负责不可变字节及哈希/大小/类型校验。公开轨迹不会复制消息正文或工具参数；patch 命中合成凭据、私有路径或参考答案标记时整份拒绝发布。

任务 12 在同一 Module 内深化既有 Interface：`ArtifactReader.read_bounded_verified` 流式读取并验证完整来源，返回带可见标记、实际保留大小和原大小的有界正文；`ArtifactStore.delete_verified` 只删除身份、大小和哈希均匹配的精确对象。`EvidencePublication` 分别处理核心 `long_term` 和私有 `raw_30d`，单原始制品最多 50 MiB、单 Run 合计最多 200 MiB；总额越界产生 `RAW_ARTIFACT_RUN_LIMIT_EXCEEDED`，超大原始轨迹产生 `PUBLIC_TRAJECTORY_RAW_LIMIT_EXCEEDED` 并只省略派生公开轨迹，均不影响核心结果。`ArtifactRetention` 经 `JobRepository.expired_artifacts/begin_artifact_deletion/confirm_artifact_deletion/mark_artifact_deleted` 编排 owner-only 本机清理：先持久化意图，再核验精确对象并确认，最后删除和审计。对象失败不写最终审计；数据库最终审计失败后只有已确认意图能根据精确对象缺失收束，未确认意图的意外缺失持续失败。它不调用 Execution Backend、Evaluator、Harbor 或模型，也不删除长期证据。

### 6.13 Judge

阶段：M1 后启用，以下为保留契约，不纳入当前实现与验收；范围来源见第 5 节指针。

| 项目 | 候选 v0.1 契约 |
|---|---|
| 调用方 | Job Orchestrator；Failure 可由人工请求/抽样触发，Quality 由批次严格并列判定触发 |
| 输入 | `JudgeRequest`；只含用途、触发上下文和受控证据引用，Implementation 负责加载、裁剪、脱敏、去重、限量并生成实际模型输入 |
| 输出 | `JudgeAnalysis`、清洗后输入与原始响应 `ArtifactRef` |
| 错误 | 模型不可用、超时、schema 不合格、证据不足、内容被拒绝 |
| 不变量 | `failure_diagnosis` 只诊断且不计分；`quality_tiebreak` 仅在同数据集/版本、题目集合、赛道、Harness、尝试数和限制下，至少两个 Agent 的逐题 `resolved` 向量完全相同且存在共同通过题时运行；Quality 对共同通过题的匿名补丁按“切题且最小、可读/可维护、健壮性、副作用风险”两两比较并交换 A/B 顺序运行两次，只有两次同意同一赢家才记胜负，否则该对为平；多 Agent 按胜 1、平 0.5、负 0 聚合；必须保存 rubric/模型/Prompt/输入策略版本和证据引用；不能接收秘密；失败时保留确定性结果或并列；同版本不得重复生成分析，新版本只能追加 |
| 依赖 | LLM Provider Adapter、Artifact Store |
| 验证 | 固定证据集上的触发/不触发、清洗、schema/分类测试；Quality 覆盖匿名化、A/B 反序一致/冲突和三 Agent 循环积分；模型失败不丢失确定性结果且不强行打破并列；版本均可追溯 |

### 6.14 Human Review

阶段：M1 后启用；这里复核 Judge 结论，不是第 6.5 节仍属 M1 的 Owner Approval。

| 项目 | 候选 v0.1 契约 |
|---|---|
| 调用方 | HTTP Delivery、抽检规则；人工调用者只能是 `owner` |
| 输入 | 待复核运行/Quality 比较、所有者提交的确认或作废、可选失败分类修正、备注、幂等键 |
| 输出 | `HumanReviewRecord` 和更新后的复核状态 |
| 错误 | 非待复核状态、重复提交冲突、运行不存在、必需证据缺失 |
| 不变量 | 人工记录只能追加或版本化修订，不覆盖确定性结果、Judge 原始响应或旧复核证据；所有者可把 Quality Judge 作废并恢复并列，但不能指定赢家或手填排名分 |
| 依赖 | Run Repository、Reporting |
| 验证 | 领取冲突、重复提交、修正 Judge 而不改测试事实、审计字段完整性测试 |

### 6.15 Reporting

M1 只组合确定性结果、过程指标和安全证据；分析/复核的兼容空值由 [HTTP API](../interfaces/HTTP_API.md#103-排行榜)规定，不为只读报告创建空壳 Judge 依赖。下表的抽检视图属于后续阶段。

任务 08 已深化 `JobReporting`：Job/Run 报告、制品索引、轨迹分页和正文下载使用同一 official 范围与 owner/创建者授权；其他账号和内部测试资源按不存在处理。授权后先按 PostgreSQL 索引从 Artifact Store 复核完整报告，再只外发 `agent_patch/public_test_summary/public_trajectory`。轨迹按连续序号分页，正文下载使用受控类型、MIME 与文件名；原始 Harness、对象键、消息正文、工具参数、私密思维链和配置不返回。缺失、损坏、断流或类型错配明确失败。

任务 12 允许同一授权范围通过制品索引和报告 `artifact_links` 查询所有闭合 Run 制品的安全元数据，但正文仍只外发公开三类。元数据包含实际/原始大小、哈希、创建/到期时间、截断事实、保留类别、删除审计和 `available/not_ready/deleted`；删除正文返回 410，受限或尚不可公开正文返回 409，不存在或越权仍统一 404。HTTP 没有删除路由，页面不给原始制品下载入口。

任务 11 在同一 Reporting 能力内增加 `LeaderboardReporting`，但不复用已承载生命周期写入的 `JobRepository`。新的 `LeaderboardRepository.page(LeaderboardQuery)` 是只读 Interface：PostgreSQL Adapter 先以 SQL 固定 `result_scope='official'` 和终态 Job，以目录 Task/源 Artifact 筛选后验证完整冻结 Task、Run 配置外键及 Agent 目录全字段与 Agent 快照、策略/限制快照、Harbor 执行身份、Run 摘要、结果布尔关系、Harness revision 与过程指标结构，最后交给共享领域策略聚合；任一损坏统一依赖不可用。所有已认证成员可读取正式团队汇总；响应不含提交者、凭据引用、对象键或秘密。浏览器测试只在显式环境门控下注入读取 `internal_test` 内存 Job 的 Adapter，不能进入生产装配。

| 项目 | 候选 v0.1 契约 |
|---|---|
| 调用方 | HTTP Delivery |
| 输入 | 运行 ID；或排行榜的闭卷赛道、数据集 ID/revision/split、可选 repo/工具策略及游标 |
| 输出 | 运行详情、证据索引、轨迹分页、排行榜聚合和抽检视图 |
| 错误 | 资源不存在、筛选/游标无效、数据库或制品暂不可用 |
| 不变量 | 只读；排行榜按完整 Agent 身份和完整冻结条件分组；只有已开始正式 Run 才产生参赛配置，未开始题仍留在全题分母但不产生来源/指标；最早可信确定性结果不能被重复/重试覆盖；失败、未知、未解决分列；过程指标不参与排名且缺失不写 0；MVP 只发布闭卷正式主榜，稳定游标不破同分，`quality_tiebreak=null` |
| 依赖 | 单 Run/Job 报告依赖 `JobRepository` 与 Artifact Store；排行榜仅依赖 `LeaderboardRepository`，其生产 Adapter 只读既有目录/Job/Run/结果表 |
| 验证 | 固定选择/分母/并列/未启动取消样例；HTTP 参数/分页/空/错误；损坏内部快照仍被 SQL 预排除、损坏正式 Task/Agent/策略/限制/执行身份统一失败关闭的真实 PG；少量页面主流程、完整条件和成功后失败状态测试 |

### 6.16 Worker Shell

| 项目 | 候选 v0.1 契约 |
|---|---|
| 调用方 | 单机进程管理器/容器启动命令 |
| 输入 | `worker_id`、轮询间隔、固定重型 Job 并发 1、优雅停止信号 |
| 输出 | 心跳、Job 领取记录、一次 Job Orchestrator 调用结果 |
| 错误 | 数据库不可用、失去租约、进程停止 |
| 不变量 | 只负责循环和进程生命周期；只领取 `QUEUED` Job；业务流程只调用 Job Orchestrator；任何配置下都不得同时执行两个重型 Job；不拥有批准权限；租约/进程中断不自动续跑或重新排队，须记录基础设施中断并等待所有者显式新建重试 |
| 依赖 | Job/Run Repository、Job Orchestrator |
| 验证 | 双 Worker 不重复领取同一 Job且不产生两个活跃 Job；停止时不误报完成；超期租约由明确恢复流程处理 |

任务 06 已实现 `run_once(worker_id)` 的薄 Shell：返回值只表示本轮是否领取并委托过一个 Job，运行成败保存在 Job/Run 状态与报告中。常驻轮询、优雅停止、过期租约与中断恢复留给任务 09/10。

任务 13 的 `delivery/worker/runtime.py` 是 owner-local Composition Root，不是新的业务 Module 或执行 Interface。`agentexam-worker <worker_id>` 每次只读取一组显式环境配置，先核验项目 runtime 内证据根、固定 Codex 归档元数据/哈希、认证文件元数据、Harbor/Fork 干净 revision 与固定任务快照，再组装生产 Adapters 并调用一次既有 `run_once`。`LocalArtifactReader` 是 Harbor/Fork 本地证据的 source：绝对引用直接解释，项目相对引用以显式 `reference_root` 解释，但两者解析后都必须处于专属 `root` 安全根内；MinIO Artifact Store 只负责规范化后的 destination，不能同时充当本地 source。数据库连接、对象存储凭据和私有认证路径不进入 `repr` 或错误输出；缺失/错配在领取 Job 前失败关闭。目录的 `openai_chatgpt` 由 Harbor Adapter 映射成固定上游运行名 `openai`，不改冻结身份。首次真实 Run 因遗漏 source reader 在判卷前以 `EVIDENCE_UNAVAILABLE` 失败；`10f0c53` 补回 reader，`3d66230` 修复 Fork 相对引用。第二次真实 Job/Run 均完成且固定 Fork `resolved=true`，随后失败来自独立验收器误读 Trial 配置。修复后的 `-04` 以一次模型尝试、零重试完成同一 Composition Root、固定 Fork、持久化和真实页面报告，证明没有另建或绕开本 Module Interface 的执行链。

## 7. 必须跨模块保持的规则

1. `job_id` 是批次主线，`run_id` 是每个 Agent×任务尝试及其制品的追溯主线；二者不可互相替代。
2. Job 创建时冻结数据集版本、Harbor/Fork 提交、Agent 配置指纹、执行协议和限制。
3. Agent 只看到 Issue 与仓库快照，不看到 gold patch、`test_patch` 或隐藏判分答案。
4. Agent 原始 stdout 和 Harbor `TrialResult` 都不是最终补丁；Execution Backend 必须从受控 Git 工作区提取并校验 diff。
5. 确定性结果、Judge 分析和人工复核是三类不同事实，任何一层不得覆写上一层原始证据。
6. 工具调用、token、耗时是只展示的过程指标，不进入正确性排名；缺失标记“不支持/未知”，不能写 0。
7. 未登记 Agent、未固定版本或携带任意 shell 命令的请求不得进入执行链路。
8. 每次运行冻结 `evaluation_track`、网络策略和工具配置；MVP 只允许 `closed_book`，保留的 `open_book_experimental` 字段不能被创建或混入主榜，未来开卷统一使用平台 Web 工具。
9. 模型来源国家不能推导网络能力；只以该次运行实际登记并验证的工具和网络策略为准。
10. Mock 只允许 `internal_test`，报告和排行榜必须从查询层排除；生产 Reporting 默认只发布 `official`，内部范围只允许显式门控的测试装配注入。
11. 远端提交只创建 `AWAITING_OWNER_APPROVAL`；只有可信会话中的评测机所有者能把它推进到 `QUEUED`，Worker 对待批准和已拒绝 Job 必须不可见。
12. 远程接入的网络成员身份只决定“能否到达 Web”，不能替代应用中的所有者授权。
13. 当前实现预登记 Codex/ChatGPT；本轮计划增加 Codex DeepSeek/Kimi，见本文开头。P2自研才实现Python进程Interface；提交者不填Key或任意提供方、Base URL、代理、启动命令。
14. P2 DeepSeek/Kimi 真实 Key 只由评测机可信秘密配置持有；当前不实现该访问路径，未来被测 Agent 也只能取得受限且可撤销的单次运行能力，不能取得提供方 Key。
15. Judge 输入清洗属于现有 Judge Implementation，不新增独立顶层 Module；Failure/Quality 的触发与输出语义必须显式区分。
16. 平台角色只允许 `collaborator` 与唯一 `owner`；不开公共注册，所有者在本机建立/恢复账号并邀请协作者，同时承担批准、配置管理、制品清理和人工复核。
17. 待批准/排队 Job 可直接取消；执行中取消只阻止后续 Trial，当前 Trial 至多到冻结超时；中断不自动重试，历史证据不覆盖。
18. 文本 patch、原始制品和单运行原始制品分别执行 256 KiB 警告、1 MiB patch 拒绝、50 MiB 单原始制品显式截断和 200 MiB 合计硬限制；二进制 patch 拒绝。
19. 到期原始制品只由可信 owner 的交互式本机维护逐对象清理；对象与数据库任一侧失败都能通过重复调用收敛，长期核心证据和删除审计不丢失。

## 8. 尚待技术核验

1. Harbor/Worker 是宿主机进程还是挂载 Docker Socket 的容器；先用不接 Web/数据库的本地 Codex 最小实验裁决。
2. 任务 01 的身份用例和两张身份表已实现，真实存储/恢复证据见[身份行动](../actions/2026-09-11-m1-owner-identity.md)，双轴评审的 HTTP/浏览器问题及修复验证见[独立修复行动](../actions/2026-09-11-m1-identity-review-fixes.md)。长期数据库部署及远程验收仍未完成；任务 02 邀请/成员亦已完成分层验收，见[成员行动](../actions/2026-09-11-m1-collaborator-invitations.md)。不复用执行凭据，也不新增独立 Auth 服务。
3. 真实 Trial 是否需要调整 256 KiB/1 MiB/50 MiB/200 MiB 默认阈值；调整产品行为前回到用户确认。
4. P2 才完成 `agent-exam.yaml`、Python 版本、依赖锁格式、Harbor 包装与 DeepSeek/Kimi 受控访问；不阻塞 Codex MVP 或 Aider/Claude Code 扩展。

## 9. 变更记录

- 2026-09-13：任务 12 深化 Artifact Store、Job Repository 和 Reporting Interface，落地有界原始证据、owner-only 本机清理、单侧失败恢复及 200/409/404/410 内容状态。
- 2026-09-09：依照总架构第 3.1 节标注后续 Judge/Human Review，移除它们对 M1 编排与报告的强制依赖；既有业务边界保留，未修改实现。

- 2026-09-01：创建候选 v0.1；明确公共对象、15 个模块的职责/输入/输出/错误/不变量/依赖/验证，以及跨模块保密和证据规则。
- 2026-09-02：同步闭卷主榜/开卷实验榜决定；新增评测策略对象，并要求 Run、Runner、Sandbox 和 Reporting 冻结赛道、网络及工具配置。
- 2026-09-03：用 Job Submission、Job Orchestrator 和深 `ExecutionBackend` 取代逐运行自研 Runner/Sandbox 主路径；Harbor 为主 Adapter，固定 Fork 独立判卷，并新增受控 Agent 源码审核模块。
- 2026-09-05：新增 Owner Approval 用例；远端提交初始为 `AWAITING_OWNER_APPROVAL`，只有评测机所有者批准后进入 `QUEUED`，Worker 不得绕过批准。
- 2026-09-05：把现有 Failure Judge 深化为 Failure/Quality 双用途 Judge，固定严格触发、输入清洗和失败不覆盖规则；确认首版自研 Agent 为 Python 进程 Interface，仅允许 DeepSeek/Kimi，真实 Key 不进入被测容器或业务数据流。
- 2026-09-05：确定 Codex 本地技术原型与平台 MVP 优先，自研 Agent 延至 P2；固定两角色邀请制、Quality 匿名双次反序比较、过程指标只展示、闭卷 MVP、任务快照、取消/手动重试、制品保留与大小限制。
- 2026-09-06：同步 M0 已实现的 Execution 领域/Port、Harbor NOP Docker Trial、结果映射与薄进程 Adapter 边界；保留真实进程 E2E、Codex/Fork 与 M1 契约为未完成。
