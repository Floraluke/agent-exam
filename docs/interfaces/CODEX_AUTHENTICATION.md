# Codex 与自研 Agent 模型凭据约定

> 状态：认证政策已确认；第四场真实单题的认证使用与正常清理已核对，完整生命周期/输出保护仍按第 6 节收尾
> 权威范围：Codex 原型认证方式、新增Codex第三方API规划、自研Agent的DeepSeek/Kimi凭据所有权，以及多人协作时的秘密边界。
>
> 反向导航：[`ARCHITECTURE.md`](../architecture/ARCHITECTURE.md) 只维护全局决定，[`DEPENDENCIES.md`](../dependencies/DEPENDENCIES.md) 只维护版本状态，[`HARBOR_EXECUTION.md`](./HARBOR_EXECUTION.md) 只维护执行映射，[`FRAMEWORK_INTERFACES.md`](./FRAMEWORK_INTERFACES.md) 只维护上游 CLI 接口；认证事实发生变化时必须回到本文更新。

## 1. 先用一句话理解

项目可以共享非秘密配置，但任何人都不得共享自己的 `auth.json`、API Key 或 Token。正式评测所需凭据只由评测机所有者在本机可信秘密配置中管理。

`auth.json` 和 DeepSeek/Kimi API Key 都不是普通配置，应按密码级敏感信息处理。Codex 的固定 Harbor Adapter 当前需要在 Trial 生命周期内使用 `auth.json`；P2 自研 Agent 则明确不得取得 DeepSeek/Kimi 真实 Key，两条路径不能混为同一种注入方式。自研路径尚未验证不阻塞 Codex MVP。

## 2. 已确认的原型选择

首个真实 Codex 原型采用以下配置：

```text
Agent：Codex CLI
模型提供方：OpenAI / ChatGPT
认证方式：运行机器所有者本人的 ChatGPT Pro auth.json
执行位置：运行机器所有者控制的单机 Harbor 临时 Trial 容器
```

OpenAI 官方文档区分两类本地认证：使用 ChatGPT 登录以使用订阅权益，或使用 API Key 按 API 用量计费：

- <https://learn.chatgpt.com/zh-Hans/docs/pricing>
- <https://learn.chatgpt.com/docs/auth>

固定版本 Harbor 的 Codex Adapter 支持通过 `CODEX_AUTH_JSON_PATH` 指定本机 `auth.json`，并在运行时把文件上传到 Trial 容器：

- <https://github.com/harbor-framework/harbor/blob/6af8d6e31eced13b93849cdf80feeadf24603d15/src/harbor/agents/installed/codex.py#L1380-L1391>

这只能证明 Harbor 技术上支持该接入方式，不代表可以共享个人 ChatGPT 账号凭据。

## 3. 多人协作规则

### 3.1 可以共享

- 本文档和其他项目文档。
- 环境变量名称，例如 `CODEX_AUTH_JSON_PATH`。
- 不含个人目录的示例路径，例如 `<your-codex-home>/auth.json`。
- Agent、模型提供方、模型名、超时和资源限制等非秘密配置。
- 脱敏后的失败日志。

### 3.2 禁止共享

- 任何人的真实 `auth.json` 文件或文件内容。
- ChatGPT 登录 Token、Refresh Token、Cookie 或会话信息。
- OpenAI、Kimi、DeepSeek 等平台的真实 API Key。
- 包含上述内容的截图、终端输出、数据库记录、MinIO 制品或聊天消息。

OpenAI 的个人账户供创建者本人使用，不能把账户凭据交给其他人：

- <https://openai.com/es-US/policies/row-terms-of-use/>

### 3.3 协作者怎样工作

有两种允许的方式：

1. **只在统一评测机执行正式真实评测**：协作者可以远端提交冻结的评测选择，但 Job 初始必须为 `AWAITING_OWNER_APPROVAL`；评测机所有者通过可信会话批准后才进入本机 `QUEUED`，随后只能由本机 Worker 执行。远端提交和批准都不携带或读取 `auth.json`、DeepSeek/Kimi Key，协作者不需要取得评测机所有者的凭据。
2. **协作者在自己机器开发或冒烟测试**：协作者只能使用自己获授权的账号或 Key，并保存在自己的未跟踪秘密配置中；这类结果不是本项目正式评测机产生的正式排行证据。

项目当前为单机架构，因此第 1 种方式是默认方案。

## 4. P2 Kimi 与 DeepSeek 的边界

自研 Agent 已降为 P2，只保留扩展接缝；其首版模型提供方只允许 DeepSeek 或 Kimi。评测所有者在源码审核通过后，从这两个已登记提供方中生成 Agent Configuration；提交者不能上传 Key、填写任意提供方/Base URL 或要求运行时回退。例如：

```text
codex-openai-chatgpt-pro
team-agent-a-kimi-fixed-model
team-agent-a-deepseek-fixed-model
```

`codex-openai-chatgpt-pro` 使用第 2 节的 Codex 认证路径；后两项是同一自研源码的两个独立配置，不能混分。每项评测结果必须记录实际 Agent、模型提供方、模型名和认证类型。一次 Trial 开始后不得静默切换提供方；失败后如需换提供方，必须创建新的配置和新的 Trial。

DeepSeek/Kimi 真实 Key 只由评测机所有者在本机可信秘密配置中保存。被测 Python Agent 只使用由现有 Execution Backend/LLM Provider Implementation 提供的受控、可撤销单次运行访问能力，不能读取提供方 Key。这里不新增顶层业务 Module；受控访问采用宿主进程还是可信侧车、怎样经过 FlClash/VPN、怎样限制模型/Token/预算以及怎样阻断绕过，均留到 P2 原型裁决。

在正式写入具体 Kimi/DeepSeek 模型 ID、外部接口参数或兼容声明前，必须查阅各平台官方文档并完成真实调用测试。

### 4.1 Codex 第三方 API 扩展规划（2026-09-17）

用户现要求保留 Codex 并接入 DeepSeek 与 Kimi 开放平台按量 API，业务正文见[扩展规格](../../.scratch/ui-catalog-providers/spec.md)，确认历史见[规划行动](../actions/2026-09-17-ui-catalog-provider-planning.md#已确认的产品决定)。这是新增规划路径，不是启用上述 P2 自研 Agent；当前只有 ChatGPT auth 路径的历史实现证据。

凭据所有者、公开请求不含秘密、执行前所有者批准与固定配置身份继续适用。用户已在 Q10 选择 B：独立可信代理持有真实 Key，做题容器只取得与单个 Run 绑定的有限访问令牌。该方向包含必要内部子目录、短命可信进程与私有网络的规划，不包含立即实施或真实调用；真实 Key 不进入做题容器。现有 Harbor 网络侧车没有密钥托管或认证头注入能力，需要新增现有 Execution Adapter 的内部 Implementation；不能把 P2 候选或同用户文件权限当成已完成的秘密隔离。

最小机制设计（已写入[计划05–08](../../.scratch/ui-catalog-providers/plan.md)，待拆分审阅和无秘密技术验证，不宣称实现）：

1. Worker 仍只领取已批准 Job；到达某个 Run 时，由现有执行 Adapter 启动该 Trial 专属代理，绑定固定提供方、模型、截止时间和受控额度。用户委托设定的首轮地区/额度初值见[配置与预算研究第 2–5 节](../research/2026-09-17-codex-provider-config-and-budget.md)，不是当前已生效的执行限制。提交/批准 HTTP 不读 Key。
2. 首版采用 owner 在评测机本地填写的受限私有配置文件，位于 Git 工作树之外，不放仓库 `.env`、共享或同步目录；网页不录入、查看或更换 Key，只管理非秘密配置身份。执行时由可信本机组件读取，再以不进入参数、日志或镜像层的私有输入流交给可信代理，仅在代理内存中使用。此入口已由 Q13 确认；精确文件路径、格式、所有者/权限拒绝条件和固定代理镜像仍须在实施计划中明确。本轮不创建私有密钥文件或访问真实秘密；受限文件本身不替代被测容器隔离与泄漏测试。
3. Codex 的受控用户级 `$CODEX_HOME/config.toml` 指向私有 Responses 入口，`env_key` 引用随机 Run 令牌；服务端保存令牌与允许模型、期限、预算的对应关系，容器自行改配置不能扩大权限。每 Run 可包含多轮请求，因此令牌不是只能调用一次 HTTP 的一次性码。固定 CLI 已验证还支持 `-c` 覆盖配置，所以安全限制必须由代理和网络执行，不能只信任 TOML 文件或题目仓库配置。
4. 代理验证令牌和请求策略，只转发允许的路径、模型与工具；剥离客户端认证头，使用固定真实 Key 向对应供应商 HTTPS 发送请求并流式返回。拒绝任意 URL/重定向/模型覆盖/超限请求，关闭秘密与正文日志。不做 Chat/Responses 协议转换。
5. 做题容器与代理隔离 PID、文件系统和秘密；做题侧只通私有入口，代理侧才有受控供应商出网，不发布宿主端口或挂载 Docker socket。现有主容器与网络侧车共享网络命名空间，不能原样照搬后宣称防绕过；具体 Compose 拓扑须以直连拒绝、宿主隔离和正常模型请求正对照验证。
6. Run 正常结束、失败或超时后撤销令牌、关闭代理并精确清理资源；代理故障时停止该条模型访问，不回退直连或自动续跑。Job 的协作式取消语义不变：不以代理机制擅自强杀当前 Trial。期限为撤销提供兜底，崩溃残留与清理失败必须单独验收。

额度是有限授权，不是绝对安全或精确账单保证：临时令牌泄漏仍可能消耗该 Run 的允许额度；流式中断或用量缺失时须保守占用预算并停止新增调用，不能把未知计费当作零。Token/请求/金额首值与推导见研究第4–5节；[实现地图第5节](../../.scratch/ui-catalog-providers/implementation-map.md#5-05-开工必须冻结的安全候选)列出私有文件、拓扑与保守账本候选。固定计量、并发预留、重启丢失时失败关闭仍须验证，未通过不得放行真实矩阵。该新路径仅覆盖本轮第三方 API，不顺带重构既有 ChatGPT auth。

本轮核对公开文档与源码，并完成禁外网/假令牌的固定 CLI 配置探针，准确能力与限制见[研究第 6.1 节](../research/2026-09-17-codex-provider-config-and-budget.md#61-固定-cli-配置探针)。未读取真实 Key、充值或调用供应商；旧 ChatGPT auth 单题/三次运行许可不覆盖新提供方。B 的方向已批准，精确技术细节仍需收敛；真实供应商兼容、代理假 Key 泄漏对照、越权/绕过拒绝、故障和生命周期尚未验证。配置探针的容器清理通过不替代代理生命周期验收。

## 5. 实现时的强制安全约束

- 只向经过检查的 SWE-Gym-Lite 原型任务注入个人 `auth.json`。
- 不把任何凭据文件或 Key 复制进镜像层，不提交 Git，不写入 PostgreSQL 或 MinIO。
- `CODEX_AUTH_JSON_PATH` 只保存在执行节点本机、未跟踪的秘密配置中；执行节点在启动受控 Codex Trial 时解析它，既不把真实路径写入 Job，也不返回给对外接口。
- DeepSeek/Kimi Key 只保存在评测机所有者控制的本机可信秘密配置中；精确保存机制仍待确认，但不得使用仓库 `.env`、提交者输入或可被被测容器挂载的普通文件。
- 公开 Job 请求、`ExecutionJobRequest` 和 PostgreSQL 只保存非秘密的提供方、认证类型、逻辑凭据配置身份与 Agent Configuration 身份，不接收凭据文件、Key 内容或真实宿主路径。
- P2 `agent-exam.yaml` 不声明 Key、自定义提供方/Base URL、代理、宿主路径或 shell 命令；自研 Agent 只选择所有者已登记的 DeepSeek/Kimi 配置。
- 所有者批准只授予该 Job 进入本机执行队列的资格；它不把凭据附加到 Job，也不在 HTTP 请求生命周期内启动 Agent。Worker 真正建立受控 Trial 时才从本机秘密配置解析凭据引用。
- P2 自研 Agent 被测进程及其容器环境、命令行和文件系统不得出现 DeepSeek/Kimi 真实 Key；若实现需要访问令牌，只能签发与单个 `run_id`、固定提供方/模型、预算和有效期绑定的可撤销能力，且必须像秘密一样脱敏和清理。
- Trial 使用临时容器；结束后销毁容器及其可写层。
- 制品收集明确排除 `$CODEX_HOME`、Harbor secrets 目录、任何 `auth.json`、提供方 Key 和运行时访问令牌。
- stdout、stderr、轨迹和异常信息进入存储前执行凭据脱敏；M0 仅所有者本机私有原始输出的受限阶段例外见第 6.2 节“本机保存与对外访问边界”。
- M0 首次实测只检查认证状态并运行一个真实任务，然后人工检查容器销毁和受控本机证据目录；接入 M1 后再检查 PostgreSQL/MinIO 全部制品。
- 未通过凭据泄露检查前，不允许批量运行，也不允许对不可信用户开放。

## 6. 尚待实测，不伪装成已确认

### 6.1 2026-09-07 风险评估发现

- **固定源码事实**：上述 `run()` 把登录文件上传到 `/tmp/codex-secrets/auth.json`，在指定 Agent 用户时改为该用户所有，并从 `$CODEX_HOME/auth.json` 链接过去；随后用 `--dangerously-bypass-approvals-and-sandbox` 运行 Codex。目录命名和容器外层隔离不能证明同一用户的仓库进程读不到文件。是否采用额外读取隔离仍是实现/验收问题，不因此更改已确认认证方式。
- **方法级合成验证**：固定 Harbor `Trial._scrub_jobs_dir()` 只搜集敏感环境变量的值做文本替换；已验证它可以抹除合成环境变量值和合成文件路径，但不会自动解析该文件内的假 Token。项目 `process_evidence.write_log()` 同样原样保存假 Token。完整证据、来源与优先级见 [风险评估](../research/2026-09-07-dns-icmp-risk-assessment.md)；这不是实际登录信息泄露，也没有执行完整 Trial。
- **待验收边界**：成功/失败/超时清理、文件内 Token（含刷新后的值）、日志/轨迹/patch 和可写挂载中的秘密覆盖都尚未通过。网络封禁不能代替这些检查；仅排除名为 `auth.json` 的文件也不能证明内容未被复制进其他输出。当前真实入口继续关闭，本次评估没有授权读取真实凭据或接受剩余风险。

### 6.2 2026-09-07 假凭据安全收尾

状态：用户已授权假值检查及现有适配层内的小修；日志能力已增强、独立沙箱读取限制有正反对照、专属容器清理已验证。**完整 Harbor Trial 凭据安全未通过**，不包含真实认证或网络剩余风险豁免。

| 项目 | 本轮证据 | 能证明 / 不能证明 |
|---|---|---|
| 凭据读取正对照 | 固定任务镜像，UID 65534，同用户创建的假 `auth.json` 为 0600；直接路径和 `$CODEX_HOME/auth.json` 链接均可读 | 仅靠同用户权限及目录名不足以隔离读取；没有真实凭据 |
| Codex 沙箱拒绝读取 | 固定 CLI `0.153.0` 的 `codex sandbox -- <command>` 配合权限 profile：根目录只读、题目目录可写、两个假凭据目录 deny；题目读写正常，两条凭据路径均不可读 | 独立 Linux 沙箱命令对照通过；没有增加 capability 或关闭 seccomp，也不是完整 Codex 模型会话/Harbor Trial |
| 已知值日志脱敏 | `run_bounded_process(..., redactions=(...))` 将仅驻内存的值交给内部 `Redactor`，双流在落盘前替换；启动异常返回值也处理 | 已传入的完整值跨分块、超时/失败和日志上限测试通过；不会自动发现认证文件内/刷新后的 Token，不抵御任意编码 |
| 正常/报错/超时清理 | 三个独立禁网假凭据容器，分别返回 0/7/124；测试 finally 显式调用生产精确 Compose 清理 helper，标签资源复核为空 | 证明该 helper 能移除这三种测试容器及其可写层；不证明完整 Harbor 的每条退出路径均已接线、挂载目录无残留 |

首次沙箱调用误用了旧式 `codex sandbox linux ...`：退出 101，未执行读取程序，不能算拒绝读取通过。读取本包帮助后改为上述实际命令，复测退出 0，包含题目读写正对照及两条 `credential-denied`。CLI 还提示临时目录下不能创建 PATH aliases；直接调用沙箱成功不能代替后续完整工具链兼容性验证。

复现证据为忽略目录 `runtime/prototype/credential-boundary-20260907-01/`（三种结束路径及首次命令失败）和 `...-02/`（命令纠正后读取对照）；专用脚本为同级 `credential-boundary-probe.py` / `credential-fixture.py`。全部使用现有缓存镜像、`--pull=never --network none`、无挂载、去全部 capability、禁止提权和资源限额；本轮未改上游、代理或网络放行规则。

上述日志小修的准确测试数量和命令见 [行动记录](../actions/2026-09-05-m0-codex-harbor-implementation.md#2026-09-07-假凭据检查与日志小修)。它只处理传入的已知完整值；当前 NOP Adapter 仍不提供真实秘密列表，不能说所有 Trial 已自动脱敏。

#### 下一阶段：固定 Harbor 启动兼容（同日）

用户要求解释日志实现并继续后，新增了现有 Execution Adapter 内部的权限与 Agent 兼容实现（最初名为 `codex_policy.py` / `codex_agent.py`，经用户批准已归拢为 `execution/codex/policy.py` / `agent.py`），**仍是待完整集成的兼容实现，不是已开放的 Agent**：

- `permission_config()` 生成固定本地权限：题目目录和临时目录可写，凭据目录、CODEX_HOME、日志和 `/proc` 禁止访问；禁止仓库命令联网，关闭审批升级和 Web 搜索。它不是模型进程的端点控制，不能代替已有容器网络策略。官方 [权限说明](https://learn.chatgpt.com/docs/permissions) 提醒旧 sandbox 配置/参数会覆盖 profile，因此兼容层不混用这两套配置。
- `guarded_codex_class()` 窄继承固定上游 Codex，复用原 `run()`，仅接受已核对的启动/辅助命令。它移除启动处的 bypass 与 nvm shell 初始化，保留模型/effort/Web 关闭配置和原始指令正文；命令结构不匹配时在执行前拒绝，不做全文字符串替换。部署时仍须提供已验证的预装 CLI PATH。
- 该阶段兼容类要求显式非 root 数值 UID，不读取宿主环境中的 API Key、强制登录或 Base URL；真实凭据解析刻意返回 `CODEX_CREDENTIAL_BINDING_NOT_READY`。测试子类只返回自行生成的假文件。**当时未修改上游源码、未注册到生产 AgentFactory，`harbor_entry` 仍拒绝非 NOP；后续状态见本节较后的正式入口接线。**
- 外层 finally 覆盖上游配置上传之前/期间的失败，以及运行失败和取消；清理失败不再被该外层吞掉。固定 Harbor 方法契约使用不执行命令的 RecordingEnvironment，验证正常、配置上传失败、运行失败、注入取消、清理失败五种路径；这是方法调用/清理尝试证据，不是完整 Trial 资源销毁证明，也不是墙钟超时实测。

独立 Docker 对照发现固定 CLI 在不存在的题目 `.codex` 拒绝访问路径上启动失败。仅移除 `/proc` 拒绝或 `/tmp` 可写均未解决；预建空 `.codex` 目录后保持全部限制即可运行。兼容层因此增加目录准备并拒绝工作目录/`.codex` 是符号链接；没有放宽 deny、增加 capability 或修改 seccomp。复测使用生产生成的同一 profile 和准备命令：题目读写通过、两条假凭据读取拒绝、凭据目录写入拒绝、安全配置改写拒绝。PATH aliases 的临时目录警告仍存在，不代表完整工具链可用。

证据保存于 `runtime/prototype/codex-guard-20260907-01/`（失败）、`...-02/`（单变量定位）、`...-03/`（修复后完整对照）；三轮专属容器均清理且复核无残留。准确命令与检查结果见 [兼容接线行动记录](../actions/2026-09-05-m0-codex-harbor-implementation.md#2026-09-07-固定-harbor-启动兼容接线)。

上述阶段结束时仍未完成 Job、非 root 和输出接线；后续实际进展见下节，不能把独立沙箱对照当成完整安全验收。

#### 完整假凭据 Harbor Trial 取证及上传兼容（同日）

该次假值取证结束时状态：**假值生命周期及泄漏正对照通过，完整输出保护未通过**。当时生产 `harbor_entry` 仍拒绝非 NOP，默认认证解析仍报 `CODEX_CREDENTIAL_BINDING_NOT_READY`。该轮没有读取真实认证文件、调用模型或修改上游源码。

`tests/test_codex_trial.py` 通过显式开关启动固定 Harbor Job/Trial，复用生产 `build_job_plan()` 和结果 mapper。仅测试进程把 AgentFactory 的类替换为兼容类子类；该子类只提供自行生成的假认证文件和离线 CLI 输入。会调用模型的 `codex exec` 由明确的合成程序替代，真正的固定 CLI `0.153.0` 只运行 `--version` 与 `sandbox --`。合成刷新是测试程序更新假 Token，**不是实际 ChatGPT 刷新验证**。

实际修正：

- 固定 AgentFactory 自动传入空 `extra_env`；兼容类现在只接受空映射和明确关闭的 `web_search`，仍拒绝非空环境覆盖和其他 Web 模式。
- 上游以 root 上传后执行 `chown`，在项目 `CapDrop=ALL` 下实际失败。`execution/codex/uploads.py` 内的 `CodexUploads` 复用 Harbor Compose 输入流，让明确的非 root UID:GID 独占创建文件（0600）；仅允许两个固定认证/配置目标，输入上限 64 KiB，正文与宿主路径不进入 argv，失败仅返回通用错误。兼容类把已核对的上游 `chown` 命令替换为所有者/权限断言，不增加 capability。上传代理最初与安装实现同文件，现已按用户批准等价拆分，行为未改。
- 该阶段测试渲染的固定任务在构建时赋予 UID 65534 工作目录所有权，Agent 和 collect 均显式使用 `65534:65534`；安装与伪 `exec` PATH 由测试 setup 提供。**在该次取证结束时这些设置尚未接入生产，后续已按本节较后的正式入口接线更新**。`--version` 的 PATH aliases 警告原样保留；版本行正确、沙箱对照通过，不代表完整模型工具链已通过。

增强后的四场完整试验使用已有侧车空白名单配置，不是 Docker `network none`。实际主容器去全部 capability、禁止提权、PID=64、内存=2 GiB；存在 `/logs/agent`、`/logs/verifier`、`/logs/artifacts` 三个可写宿主挂载，不能沿用前一轮“无挂载”的结论。

| 场景 | 生命周期结果 | 输出审计结果 |
|---|---|---|
| 正常结束 | 完成并返回非空假补丁；两条凭据路径的直接读取正对照及沙箱拒绝对照通过 | 假原值、刷新后值及刷新令牌出现在 `codex.txt`、session 和标准 `trajectory.json` |
| 主动报错 | 上游 `NonZeroAgentExitCodeError`，mapper 为 `agent_failed` | 除上述输出，`exception.txt` 和 Trial `result.json` 也带有假值 |
| 真实墙钟超时 | 上游 `AgentTimeoutError`，mapper 为 `timed_out` | 日志/session/标准轨迹仍带有假值 |
| 假 Token 写入 patch | mapper 当前仍为 `completed` 并返回 patch 引用 | 两份 patch 收集副本都带假值，证明大小/哈希校验不是秘密准入检查 |

四场均在容器销毁前检查两个凭据目录已消失；Harbor 自然结束后、测试宿主兜底清理之前，专属容器/网络/卷查询均为空。随后兜底 helper 复核并清理本轮带精确标签的资源/构建镜像。测试合成输入和诊断证据刻意保留，不能说所有宿主文件都被删除。完整 Codex 外层强杀/崩溃路径、上传过程被中断及真实 Token 刷新仍未通过。

证据：`runtime/prototype/codex-full-trial-20260907-06/` 各案例的 `container-boundary.json`、`probe-observations.json`、`natural-cleanup.json`、`output-audit.json`。审计显式写入 `full_output_protection_passed=false`；测试通过表示生命周期与已知漏洞正对照可复现，**不表示防泄漏通过**。前五轮的失败与覆盖局限见 [行动记录](../actions/2026-09-05-m0-codex-harbor-implementation.md#2026-09-07-完整假凭据-trial-结果与暂停点)。

完整输出保护尚未实现；`execution/codex/` 内部整理已获批并完成，用户已确认以下受限阶段例外，不再把目录整理或同一边界的重复确认记为阻塞。政策确认不代表安全验收通过；该阶段真实入口尚未开放，后续接线状态见本节较后的更新。

#### 本机保存与对外访问边界（2026-09-07 用户已确认）

用户说明 PostgreSQL/MinIO 部署在自己的电脑，并已确认下述本机私有输出与对外发布的区别；没有同意把含凭据结果提供给协作者。项目当前 M0 代码仍写入本机 runtime 文件，尚未接入 PostgreSQL/MinIO；不能把本机已有服务当作本项目持久化已实现。

物理位置与可见范围是两件事：规划中的 [轨迹和制品 API](./HTTP_API.md#9-trajectory-与-artifact-api) 会经后端把允许访问的内容返回浏览器；即便数据源在本机，内容仍可能被队友读取。Judge 请求也可能把输入发送到外部模型服务，服务程序在本机不改变这一点。

已确认政策：M0 **仅所有者本机私有保存、不经共享目录/同步/下载接口发布、不送入外部 Judge** 的原始输出，可以暂缓全面清洗；对外显示、下载、分享或送 Judge 前仍须过滤秘密；被测仓库进程不能读取凭据及容器清理继续保留。这是第 5 节“进入存储前脱敏”的受限阶段例外，不取消凭据文件排除、禁止提交秘密或批量运行门槛。

授权与实现状态：此项确认仅调整输出保护的阶段优先级，**不是读取真实登录文件、调用模型或接受剩余网络风险的授权**。真实运行前仍须核实证据目录确为所有者私有，并另行取得实际凭据使用与单题调用授权。本轮仅同步文档，没有实现或验证新的访问限制，也没有开放真实凭据绑定。

#### 正式运行入口接线（2026-09-07，接线完成时尚未真实调用）

当前代码状态已晚于上面的历史假值取证：既有 `HarborExecutionAdapter` 可以由可信本机构造器显式接收固定 Codex 归档和所有者登录文件引用，逐次把完整校验后的离线 bundle 放入该次 0700 原型目录；这两个引用只进入受控 Harbor 子进程环境，不进入 `ExecutionJobRequest`、Harbor Job JSON、公开任务或 Adapter 的 `repr`。`harbor_environment()` 仍不复制同名或其他宿主认证环境变量，缺少任一显式绑定都会失败关闭。

`harbor_entry.py` 现在只接受原 NOP 或唯一固定 Codex 配置 `0.153.0` / `openai/gpt-5.6-terra` / `medium` / Web 关闭；固定配置缺少私有绑定时报 `CODEX_CREDENTIAL_BINDING_NOT_READY`，配置不一致在导入 Harbor/创建容器前拒绝。入口重新核验 bundle manifest 及 8 个文件 SHA-256，再把由闭包绑定的 `GuardedCodex` 注册到固定 `AgentFactory`；路径不写入 Agent kwargs。兼容类只返回显式绑定的普通非符号链接文件，不再读取 ambient API Key/Base URL；未绑定类继续保持原拒绝行为。

生产安装上传到 `/opt/agentexam-codex`，固定 PATH 指向其 `bin` 与 `codex-path`；版本不等于 `0.153.0` 即失败，不调用上游 curl/npm 安装分支。正式任务渲染现在把 Agent 和 collect 都固定为 `65534:65534`，镜像构建时把 `/testbed` 交给同一 UID:GID。一次固定镜像、`network none`、假认证的生产安装契约已验证真实 CLI 版本/帮助、无 curl/npm 回退、非 root 和精确容器清理；另一次完整禁网假认证 success Trial 验证新的生产 UID/PATH 与合成补丁/自然清理协作。后者第一次因测试替身覆盖后才检查版本而失败，调整为覆盖前检查后通过；两次都没有调用模型，不能证明账号、真实 Token 刷新或真实工具链。

原型编排现在允许显式 `codex` 类型，但没有新增自动发现登录文件的 CLI 参数，也没有默认打开网络；调用方必须构造上述私有绑定和精确 `network_hosts`。因此“代码存在可调用接缝”不等于“已经得到账号使用许可”：预检和取证只检查认证元数据，获授权的真实运行由私有上传层读取并通过 stdin 传输文件，不向聊天/Git 显示其内容。每场真实单题前仍须向所有者说明固定输入、额度、端点/剩余网络风险、0700 本机证据与清理检查，并单独取得授权；失败不自动重试。实际运行状态以下方最新记录为准，M0 尚未完成。

#### 首次真实 Trial（模型前失败并修复，2026-09-07）

用户随后分别授权首次真实单题和缺失登录时的人工 ChatGPT 登录。固定宿主 Codex CLI `0.153.0` 在本次 M0 专属的私有 `CODEX_HOME` 中完成浏览器登录，生成普通非符号链接且大小受限的 `auth.json`；代码与取证只检查文件元数据和 CLI 的 `Logged in using ChatGPT` 状态，没有读取、输出或写入 Git 的令牌内容。首次 `m0-real-codex-20260907-01` 使用固定任务、模型、推理强度和 `auth.openai.com` / `chatgpt.com` 候选主机，但在 Agent setup 的离线版本核验阶段终止，尚未上传凭据或发出模型请求。

结构化结果为 `agent_failed` / `CODEX_OFFLINE_INSTALL_FAILED`，无 trajectory、usage、可接纳 patch 或 Fork 判卷；本场专属 Compose 容器、网络、卷和镜像残留均为 0。真实 Harbor 无模型复现证明版本命令成功返回两条非空行，第二行才是固定 `codex-cli 0.153.0`；原实现复用上游首行解析器而误判。现有 `GuardedCodex.install()` 现要求成功输出的最后一条非空行精确等于固定版本，不放宽包 SHA-512、逐文件 SHA-256、PATH 或在线安装禁令。最小回归经历红灯后通过，真实 Harbor deny-all、假认证、覆盖空 `run()` 的原路径也通过，且无模型调用、资源残留为 0。

该场属于认证后、模型前的基础设施失败，不是题目未修好，也不构成 M0 完成。依据不自动重试规则，修复只做无模型验证；原始输出阶段例外和全部秘密边界继续适用。

#### 第二场真实 Trial（启动输入错误，2026-09-07）

用户另行授权第二场固定单题。两次 import-only 启动错误没有创建原型运行；纠正构造方式后，`m0-real-codex-20260907-02` 在 Execution Adapter 准备离线输入时，因调用层误把归档指向不存在的 Windows `.zip`，由生产 `prepare_codex_bundle()` 以 `CODEX_PACKAGE_INVALID` 失败关闭。该路径发生在 Harbor 配置、Job、容器和凭据上传之前，因此没有认证文件副本、模型请求、usage、patch 或 Fork 判卷。

正确固定输入仍是所有者本机忽略目录中的 `codex-0.153.0-linux-x64.tgz`，普通文件、129,210,185 bytes，SHA-512 与生产常量一致；不是缓存损坏或校验实现缺陷。第二场证据根关闭 ACL 继承，且不存在 `execution.json`、`evaluation.json`、Harbor 配置或 jobs 目录。旧授权已使用；如需继续真实闭环必须重新取得所有者授权，不得把这次模型前失败自动重试。

#### 第三次授权运行（DNS 阻塞后超时，2026-09-07）

用户明确授权第三次运行 `m0-real-codex-20260907-03`。本次先让同一构造代码的 check/run 两种模式校验实际绑定的固定 Linux 归档、接口、任务和认证元数据，再调用现有原型一次。安装与真实凭据上传成功到达 Codex 会话，运行中独立观察到 Codex 进程 UID=65534、主容器去全部能力且禁止提权，证据根为所有者私有。Agent 未能解析官方主机，900 秒后由 Harbor 以 `AgentTimeoutError` 结束；没有模型回复、完成的 turn、工具执行或可用 usage，不能将 null 用量当作已核实的零账单。网络原因及最小诊断对照见[执行接口](./HARBOR_EXECUTION.md#第三次授权运行dns-转发失败2026-09-07)。

本场没有有效补丁或 Fork 判卷。结束后独立查询确认专属容器、网络、卷、镜像残留均为 0，运行目录内没有 `auth.json` 副本，请求和 Job 配置不含认证源目录标记；原型根 ACL 继承关闭且由当前所有者持有。认证源仍保留在先前的项目私有登录目录。10 份 Trial 输出的限定常见秘密形态扫描为 0 命中，原始内容没有在聊天展示或送外部 Judge；该检查不等于全面输出保护。本场仍未产生真实工具的凭据读取拒绝对照或 Token 刷新证据，既有假值结果不能据此升级为完整安全验收。

本次实际运行授权不包含自动再次运行，第三场生产网络规则没有被诊断临时修改。运行身份、摘要哈希、诊断偏差及清理证据见[M0 行动记录](../actions/2026-09-05-m0-codex-harbor-implementation.md#2026-09-07-第三次授权的固定真实单题)。

2026-09-08 后续：用户已另行批准限定 DNS 修正，已在现有网络适配层接线并完成无凭据 DNS/HTTPS、拒绝对照和清理验证，详见[执行接口](./HARBOR_EXECUTION.md#限定-dns-适配2026-09-08)。本轮没有读取登录文件、运行 Codex 或产生模型用量；限定网络修改的授权不扩展为第四场模型运行或全面网络风险豁免。未知项仍按下节维护。

#### 第四次真实单题通过（2026-09-08）

用户另行授权的 `m0-real-codex-20260908-04` 已结束：现有私有上传层使用同一个项目登录文件，固定 Codex 实际完成模型回复、命令执行和文件修改，补丁由本机固定 Fork 独立判卷通过。执行/判卷结果见[执行接口](./HARBOR_EXECUTION.md#第四次授权运行真实补丁与独立判卷通过2026-09-08)，不再把实际账号/模型路径描述为完全未经验证。

运行前仅核验认证元数据/父目录受限 ACL；真实使用只经过既有私有绑定和 stdin 上传，未在聊天/Git 显示令牌。运行中独立 Docker top 观察实际 codex/code-mode 进程 UID=65534，inspect 核对去能力、禁止提权和原定挂载范围；模型工具已实际执行。结束后精确 Harbor 四类资源为空，Fork 双身份标签容器为空；本场根的 auth.json 副本数为 0，request/Job config 不含认证源目录标记。原型根由本机所有者持有，ACL 继承关闭；源登录文件保留。

收尾有限秘密形态检查覆盖本场 44 个文本/JSON/patch/diff 文件，0 命中、无超大文件跳过，明确不跟随 1 个 Fork Linux 目录链接。该检查不代表全面保护；本轮没有主动诱导真实工具读取令牌、没有真实 Token 刷新或编码外传验收。原始输出继续仅本机所有者私有保存、不送外部 Judge，既有阶段例外不扩大。Harbor 的美元 cost 字段为估算，不是已核实的 ChatGPT 账单。

第四场授权已使用且本场成功结束，不自动发起第五场；M1、批量评测和对外输出仍须遵守现有门槛。具体证据及审计脚本的 WinError 1920/换行比对偏差见[M0 行动记录](../actions/2026-09-05-m0-codex-harbor-implementation.md#2026-09-08第四次授权的固定真实单题)。

### 6.3 其他尚待实测项

- 当前 Codex CLI 与固定 Harbor Adapter 组合能否稳定刷新 ChatGPT 登录 Token。
- 第四场正常结束、第三场 Agent 超时已有真实清理证据；完整外层强杀/崩溃、上传中断等路径仍未全部实测。
- Harbor 生成的完整日志与轨迹是否可能包含认证信息。
- P2 Kimi/DeepSeek 的精确模型 ID、外部接口与平台 Python 进程 Interface 是否兼容。
- P2 受控模型访问采用宿主进程还是可信侧车，以及短期访问能力的签发、限额、撤销和清理方式。
- P2 Docker Desktop 下能否证明被测容器既没有取得 DeepSeek/Kimi Key，也不能绕过受控路径直连提供方、宿主或任意公网；这些问题不阻塞 M0/M1 Codex。
