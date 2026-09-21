# AgentExam 规划与接续交接

> 更新：2026-09-20；工作区：`E:\9.1agent_exam`。
>
> 当前停点（2026-09-20）：最小本地持久化 P1–P4、扩展任务 01 和扩展任务 02 均已完成。D 的 continuous 1–20、跨批次比较后端和 cancel/claim 竞态修复已合入 `main`；这些后端前置不等于任务 03 Web 对比页、任务 04 五道新题或任务 08 已完成。不得据此自动启动剩余范围或真实模型调用。
>
> 最新进展（13:54）：Windows 最后启动时间确认晚于重启前检查点；项目未随系统或 Docker 自动启动。正式启动后清单 SHA-256、5 类业务记录和 9 个对象全部一致；随后只删除清单指定对象、随机数据库和清单。最终状态复核为初始化完成、PostgreSQL/AIStor 运行、活动 Job 为 0、停止标记 false；Worker 与模型未启动。
>
> Web/HTTP 进展：任务 02 当时的 31 项清单与 OpenAPI 对账仍是历史验收事实。当前 FastAPI 已注册 32 个端点，新增 `GET /api/v1/reports/comparisons` 并写入 HTTP §10.4；Web 尚无对应客户端、页面或按钮，继续遵守“后端未提供则不造交互、尚未接线则不冒充完成”。
>
> 后续决定（2026-09-20）：用户明确按五人课设只使用 owner 电脑上的一套 PostgreSQL，五人共用 `agentexam_admin` 管理员账号直连；不建立只读库、分角色数据库账号或每人独立数据库。当前实际 tailnet 入口已核对为 `sss.tail03c757.ts.net:55432 → 127.0.0.1:55432`。因部分组员无法下载 Tailscale，用户决定增加同一可信物理局域网 `owner当前IPv4:55432` 直连；本轮只改文档，Compose、防火墙和容器未修改，所以局域网入口尚未实施或验证。两条路径的 Navicat 步骤见 [`TEAM_POSTGRESQL_CONNECTION.md`](docs/operations/TEAM_POSTGRESQL_CONNECTION.md)；MinIO、原始 FastAPI、Docker、Worker 和模型秘密仍不开放，不做路由器转发或公网发布。
>
> 团队分工（2026-09-18）：七个 Module 已按五人 A–E 建立唯一 DRI、上下游交接和 52/55/54/55/56 小时初始工时基线；M1-14 与扩展 01–08 已映射负责人，入口见 [`TEAM_WORK_ALLOCATION.md`](docs/architecture/modules/TEAM_WORK_ALLOCATION.md)。该文档已补齐七个 Module 的当前 JSON 交接示例，并区分实际 HTTP、内部 dataclass 表示和运维状态；除 A 是 owner 外其余姓名待填。任务 01–02 已完成；分工完成不等于 03–08 已发布或已取得真实模型调用授权。
>
> 当前状态：分支 `main`，本地与 `origin/main` 的已提交基线均为 `beed93f`；合并后审查修复仍是未提交工作树增量。2026-09-20 只读确认共享长期库的 `evaluation_jobs_batch_preset_check` 已包含 `continuous` 且有效，活动 Job 为 0，没有重复执行 ALTER。课设继续采用“不做备份恢复”的已确认范围。另一设备负向和整个 MVP 仍未验；本轮未推送。
>
> 本文是当前恢复入口，不替代专题事实源。新窗口若只收到“恢复上下文”或同义要求，读完后只汇报已恢复并等待，不把历史计划当作新授权。历史架构讨论、迁移和逐轮探针保留在对应行动记录，不再全文复制到交接中。

先按AGENTS阅读docs/agents的任务/标签/领域约定，再读[模块架构索引](docs/architecture/modules/README.md)和当前[执行计划](.scratch/ui-catalog-providers/plan.md) → [规格](.scratch/ui-catalog-providers/spec.md) → 按阶段读[实现地图](.scratch/ui-catalog-providers/implementation-map.md)与[验证规范](.scratch/ui-catalog-providers/verification.md)。扩展任务 01–02 已完成；03–08 仍待逐项发布，不能把任务 02 完成当成允许自动开始任务 03。原规划历史见[规划行动](docs/actions/2026-09-17-ui-catalog-provider-planning.md)，本轮模块/单机规划见[行动文档](docs/actions/2026-09-17-module-architecture-and-owner-host-planning.md)，持久化范围见[已前移的 P 阶段规格](.scratch/persistence-deferred/spec.md)。

持久化前移和本次执行已获确认，不再重复询问优先级。业务读写 Adapter 与本地生命周期已落地；备份恢复明确移出课设范围。准备度由[所有者单机模块第 10 节](docs/architecture/modules/owner-host-runtime/ARCHITECTURE.md#10-当前代码准备度2026-09-18-实际核对)维护。已确认的根目录、手动启停及无备份风险由[课设运行约束](docs/architecture/modules/owner-host-runtime/ARCHITECTURE.md#11-已确认的课设运行约束2026-09-17)维护，云存储仍只是未来可选。

面向项目所有者的分步阅读入口：[项目阅读路线](docs/architecture/READING_GUIDE.md)。它帮助把代码放回模块地图，不替代第 3、4 节开发者必读要求，也不表示恢复实施或运行测试。

用户已另行确认所有开发项目主动使用“项目可控性汇报”：个人 [AGENTS](C:/Users/YINGYI/.codex/AGENTS.md) 指向 [project-control-report](C:/Users/YINGYI/.codex/skills/project-control-report/SKILL.md)。这是个人层面的说明规则，不扩展业务实施授权；换机器须另行恢复，不能由本仓库 Git 推断已安装。

当前 M1 范围的权威入口是[总架构第 3.1 节](docs/architecture/ARCHITECTURE.md#31-m1-交付边界2026-09-09-已确认)，本次独立同步记录见[行动文档](docs/actions/2026-09-09-m1-judge-deferral.md)。旧 MVP 决策和 M0 出口提案保留历史，不覆盖这一已确认调整。

当前交付与验收展开见[M1 规格](.scratch/m1-platform/spec.md)，制定过程与验证见[规格行动记录](docs/actions/2026-09-11-m1-platform-spec.md)。规格不是已实现清单；其标签不替代真实执行授权。

正式任务从[01：所有者登录与本机恢复](.scratch/m1-platform/issues/01-owner-login-recovery.md)开始；完整顺序、依赖和文档检查见[任务发布行动](docs/actions/2026-09-11-m1-ticket-publication.md)。父规格中的拆分待确认是发布时快照，当前批准状态以本入口及任务记录为准。

## 1. 目标与当前阶段

既有目标是完成 **Codex-only MVP（最小可用平台）**。交付顺序不变：先完成不带网页的本机技术原型 M0，再进入包含网页、账号、批准、队列和存储的 M1。Aider/Claude Code 后续接入，自研 Agent 属于 P2；具体业务规则见第 3 节权威文档。

当前 **M0核心闭环通过、M1任务01–13验收完成、14部分验收有证据但未关单；扩展任务 01–02 已完成，MVP仍未完成**。任务13证据在[同任务行动](docs/actions/2026-09-13-m1-local-real-acceptance.md)，任务14正向完成及首次启动/浏览器失败原因在[同任务行动](docs/actions/2026-09-14-m1-private-remote-acceptance.md)。后者末尾仍含早期“待验证”快照，恢复时逐项对账，不忽略中间已有正向证据，也不把它扩大成全部通过。本轮没有重新启动/核验这些服务。扩展任务 02 的范围与验证只由[实施行动](docs/actions/2026-09-18-ui-workbench-implementation.md)维护。M0剩余差距见[Harbor验收对账](docs/interfaces/HARBOR_EXECUTION.md#暂停后的验收对账2026-09-08)。

| 能力 | 已有事实 | 不能据此推断 |
|---|---|---|
| 固定 SWE-Gym 题目与补丁 | 第四场真实 Codex 生成 1,225-byte 补丁；实际公开任务字节与固定快照一致，补丁三份实际文件哈希相同 | 整个 mypy 项目或所有题目均通过 |
| Harbor 执行与独立判卷 | 第四场真实 Agent → 补丁 → 固定 Fork，patch_applied=true、resolved=true，有原始报告和轨迹 | 已实现网页、账号、批准、队列和存储 |
| Codex 安装与保护 | 第四场实际 UID 65534、模型命令/文件修改、正常清理已核对；第三场 Agent 超时清理证据保留 | Token 刷新、完整崩溃/强杀或全面输出保护已验收 |
| 正式入口与网络 | 限定 DNS 修正已接入；第四场当前账号/模型连接和真实工具执行可用，原有拒绝检查保留 | IPv6、所有长连接/故障或全面网络防护已通过 |
| 产品与远程协作 | 任务 01–11 已验收；基础排行榜的真实 PG、完整浏览器和双轴终审均通过 | 局部通过就是整个 M1 可用，或临时测试通过就是已部署长期数据库/MinIO |

实现与逐轮验证的唯一记录是 [M0 行动记录](docs/actions/2026-09-05-m0-codex-harbor-implementation.md)。前两次模型前失败、第三次 DNS 超时均保留；第四场已完成真实回复、工具执行、补丁和独立判卷。取证不显示认证内容，源登录文件仍由所有者本机私有保存；假值测试中的“Token 泄漏”不是用户账号泄漏，本场有限秘密形态 0 命中也不等于全面保护。

### 1.1 上一窗口的开发历程索引

以下只提供恢复顺序，具体改动、命令、失败和验证仍以行动记录对应段落为准：

1. 从“假值测试已有、正式入口尚未接线”接续：在既有适配层接入固定离线安装、非 root/PATH、私有凭据上传与 Factory 注册；详见“正式 Codex 入口接线”。
2. 前两场在模型调用前失败：第一场误把版本输出前的提示当作版本行，修正为核对最后一条非空行；第二场启动构造误用不存在的 Windows 包路径，纠正为已校验的固定 Linux 包，未放宽校验。
3. 第三场因 Docker 外部 DNS 转发被侧车规则拦住而超时，无模型回复、有效补丁或判卷；获批后仅在现有网络适配层加入限定 DNS 修正，通过无凭据红绿及拒绝对照，未改代理或上游。
4. 第四场单独获授权，真实 Codex 完成固定题、收集补丁，独立 Fork 判卷通过；本场私有输出与清理检查完成，未自动发起第五场。
5. 源码/测试/文档提交为 `729dd88`；首次 push 被平台拦截，用户明确确认目的地和范围后推送成功，发布记录提交为 `a011b78`。该拦截已解除，不是当前开发阻塞；随后用户要求暂停并整理本次交接。

## 2. 当前阻塞与授权边界

当前持久化范围 P1–P4 和 UI 扩展 02 已经完成；新题和模型 API 扩展仍是规划阶段。任何扩展都不是恢复旧 M0 或任务 14 的许可。下表历史技术缺口仅供按分支查阅；当前目标、技术门禁和下一停点以第 6 节为准。

| 类型 | 当前缺口 | 恢复动作与事实源 |
|---|---|---|
| 开发进展 | 任务01–13已收尾；14已有正向真实流程，仍未关单；扩展 02 已完成 | 当前无自动续做目标；14留在原行动，不自动恢复，03 未发布 |
| 数据库验证 | 长期 PostgreSQL/AIStor 已部署并完成跨重建、整机重启持久性验收；2026-09-20 只读确认 Job preset 约束已包含 continuous | 业务库只做明确授权的维护；测试继续使用专属随机库并精确清理，不能把测试迁移直接跑到共享库 |
| 当前评审结果 | 任务13相对 `5e39632` 的最终Standards/Spec均为0 findings/PASS；扩展 02 的 Standards hard findings 均关闭、Spec PASS | 任务14尚未完成双轴终审；扩展 02 只保留已记录的 URL 分散判断项，不扩展重构 |
| 接入准备 | 任务 03 三张规划内表、必要 Interface/子目录已落地，隔离验证通过；不等于正式部署 | 版本候选/风险见[依赖总表第 2.3 节](docs/dependencies/DEPENDENCIES.md#23-任务-03-对象存储依赖复核)，结构和不发布端口的专属测试方案见[已实施方案](docs/actions/2026-09-12-m1-task-agent-catalog.md#任务-03-最小接入方案)；实际构建、合成运行与精确清理见行动，不部署长期服务 |
| 已修复的基础设施阻塞 | Docker 外部 DNS 转发已用限定 UDP53 例外接通；未知 resolver 配置在 nft 前拒绝，固定上游未改，双哈希已记录 | 见[执行接口的限定 DNS 适配](docs/interfaces/HARBOR_EXECUTION.md#限定-dns-适配2026-09-08)；不要重复申请该授权或重做已通过的 DNS 修正 |
| 技术验收 | 第四场真实模型路径已可用；具体 FlClash 路由、IPv6、长连接/故障及 DNS/ICMP 外部范围仍有未验收项 | 先读 [Harbor 接口](docs/interfaces/HARBOR_EXECUTION.md#第四次授权运行真实补丁与独立判卷通过2026-09-08)；保留本场通过结果，不扩大为完整网络保护 |
| 技术验收 | 真实模型命令/文件修改和正常清理已核对；完整外层强杀/崩溃、上传中断及真实 Token 刷新未全部验收 | 先读 [认证接口](docs/interfaces/CODEX_AUTHENTICATION.md#第四次真实单题通过2026-09-08) 第 6.2、6.3 节；按必要范围收尾，不把全部 P2 对抗要求加入 MVP |
| 授权边界 | 限定 DNS 修正和第四次真实运行均已获授权且完成；本场成功，没有第五场 | 不重复询问已批准事项，不自动新跑单题或批量评测；如确需另一次真实调用，先说明目的/额度/剩余风险再取得对应许可 |
| 阶段例外的条件 | 用户已允许暂缓本机私有原始输出的全面清洗；代码以 0700 创建每次原型目录，实际真实目录仍须在运行前后核对权限 | 按认证接口第 6.2 节落实；这不是全面保护已经实现，也不是对外发布含秘密输出的许可 |

最新已确认输出政策的唯一事实源是 [认证接口第 6.2 节](docs/interfaces/CODEX_AUTHENTICATION.md)：仅所有者私有保存、不经共享目录/同步/下载接口发布、不送外部 Judge 的原始输出可暂缓全面清洗；对外提供前仍须保护秘密，凭据隔离与容器清理保留。该决定不授权真实模型使用或剩余网络风险豁免。**此边界、内部目录整理和首轮固定配置都无需重复询问。**

假值四场景已经证明原生日志、session、轨迹、错误报告及 patch 可能带入合成秘密。相关测试以“能检测到刻意泄漏”为部分成功条件，故 `4 passed` 不能表述为“防泄漏通过”。审计明确记录 `full_output_protection_passed=false`。详细观察只在认证事实源维护。

## 3. 权威文档必读顺序

### 3.1 开始修改前必须阅读

以下文档必须完整阅读；M0 行动记录较长，按表中指定段落读完，处理对应问题前再读相应历史实验，避免强制装载全部旧窗口记录。

| 顺序 | 文档 | 目的 |
|---|---|---|
| 1 | [AGENTS.md](AGENTS.md)、本文 | 协作规则、最小修改原则、当前目标与授权 |
| 2 | [CONTEXT.md](CONTEXT.md) | 领域词汇，尤其 Job/Run、M0 技术原型与 MVP 的区别 |
| 3 | [总架构](docs/architecture/ARCHITECTURE.md) | 模块边界、依赖方向、关键数据流、规划文件树；规划不等于实现 |
| 4 | [模块契约](docs/architecture/MODULE_CONTRACTS.md) | Execution Backend、Patch Evaluator 等输入输出与错误边界 |
| 5 | [Harbor 执行接口](docs/interfaces/HARBOR_EXECUTION.md) | 固定执行链、补丁契约、M0/M1 验收及第 13.1 节网络事实 |
| 6 | [Codex 认证接口](docs/interfaces/CODEX_AUTHENTICATION.md) | 凭据所有权、当前私有绑定门槛、假值检查与最新受限输出政策 |
| 7 | [框架接口](docs/interfaces/FRAMEWORK_INTERFACES.md) | SWE-Gym、固定 Fork 和 Harbor 的实际入口，避免凭印象调用 |
| 8 | [依赖总表](docs/dependencies/DEPENDENCIES.md) | 固定版本、模型/推理配置、数据和镜像身份；第 2.1 节固定离线安装输入 |
| 9 | [MVP 决策记录](docs/actions/2026-09-05-mvp-priority-product-decisions.md) | 用户已确认的范围与交付顺序；当时环境/未实现状态是历史快照 |
| 10 | [M0 行动记录](docs/actions/2026-09-05-m0-codex-harbor-implementation.md) | 必读“状态与情况说明”，以及“下一窗口交接整理”“进度说明与已确认输出边界同步”“已批准的 Codex 内部目录整理”“完整假凭据 Trial 接线”“完整假凭据 Trial 结果与暂停点”；继续读“正式 Codex 入口接线”“第三次授权的固定真实单题”“已授权的限定 DNS 适配”“第四次授权的固定真实单题”“用户授权提交与推送”“暂停开发与 handoff 上下文恢复整理”和“放缓开发后的权威文档同步”全部段落 |

完成阅读的标准：能从文档和源码指出当前真实入口何时允许/拒绝、哪些设置已接线或只存在测试里、哪些是已确认政策、哪些是未验证事实；有冲突先查明并同步，不以历史记录覆盖最新专题事实源。

### 3.2 按工作分支追加必读

- 做 Docker、网络或资源探针前，读 [本机 Docker 环境](docs/operations/LOCAL_DOCKER_ENVIRONMENT.md)、[DNS/ICMP 风险评估](docs/research/2026-09-07-dns-icmp-risk-assessment.md) 及 Harbor 第 13.1 节。风险报告是证据和分析，不自动构成政策授权。
- 改动 Harbor 适配或考虑替代方案前，读 [Harbor ADR](docs/adr/0001-use-harbor-as-execution-backend.md)，并核对依赖总表中固定的本地上游源码；不要无依据切换后端或修改第三方仓库。
- M0 验收后进入 M1 前，完整读 [HTTP API](docs/interfaces/HTTP_API.md)、[数据模型](docs/architecture/DATA_MODEL.md)、[远程接入](docs/operations/REMOTE_TEAM_ACCESS.md)，再按既定范围规划实现。
- 接续任一M1旧任务时，完整阅读[M1规格](.scratch/m1-platform/spec.md)、对应任务单和同任务行动；先读docs/agents下任务/标签/领域约定，HTTP、数据模型和相关模块契约也必须读。任务09/10均为历史已完成，不再按其旧停点阻断当前规划。
- 接续UI/题库/API规划时，完整阅读当前扩展规格、计划、同一规划行动和按阶段的实现地图/验证规范。修改业务实现前仍须读本节权威文档及第4节相关源码；新增题目/提供方不能只看文件树。预算/地区/固定CLI探针事实从[研究](docs/research/2026-09-17-codex-provider-config-and-budget.md)取得，真实调用前重核会变化的官方资料。
- 只有实际处理 P2/后备执行路径时读 [Runner 协议](docs/interfaces/RUNNER_PROTOCOL.md)；P2 凭据提供方和包装细节不阻塞当前 Codex 原型。
- 只有出现迁移/沙箱问题时读 [路径迁移记录](docs/actions/2026-09-04-workspace-path-migration.md)。旧路径是历史事实，迁移没有根治所有 Windows 沙箱故障。

## 4. 核心代码与测试必读

以下清单必须实际打开阅读，包含本轮整理后的新路径；不是只核对文件存在。目录均为现有实现，不能照规划树另造一套平行代码。

| 顺序 | 必读文件 | 必须理解的关系 |
|---|---|---|
| 1 | [原型入口](apps/backend/prototype_codex_harbor_e2e.py) | 现有 ExecutionBackend → patch 校验 → PatchEvaluator 编排；单题约束、证据文件、真实调用门禁及 CLI 的 check-only 模式 |
| 2 | [执行 port](apps/backend/src/eval_platform/application/ports/execution.py)、[判卷 port](apps/backend/src/eval_platform/application/ports/evaluator.py) | 业务与适配器的边界；其引用的 [task](apps/backend/src/eval_platform/domain/task.py)、[agent](apps/backend/src/eval_platform/domain/agent.py)、[result](apps/backend/src/eval_platform/domain/result.py) 领域对象也须读 |
| 3 | [SWE-Gym Adapter](apps/backend/src/eval_platform/adapters/tasks/swe_gym.py)、[collect 脚本](apps/backend/src/eval_platform/adapters/tasks/collect_patch.sh) | 冻结任务与隐藏字段分离、生产任务渲染、相对固定 base commit 收集补丁 |
| 4 | [Harbor Adapter](apps/backend/src/eval_platform/adapters/execution/harbor/adapter.py)、[配置映射](apps/backend/src/eval_platform/adapters/execution/harbor/config_mapper.py)、[正式引导入口](apps/backend/src/eval_platform/adapters/execution/harbor_entry.py) | ExecutionBackend 的 Adapter 实现；配置/身份、只清理本 Job；固定 Codex 私有绑定才注册，任意配置/缺项失败关闭 |
| 5 | [Codex 兼容类](apps/backend/src/eval_platform/adapters/execution/codex/agent.py)、[权限策略](apps/backend/src/eval_platform/adapters/execution/codex/policy.py)、[安装输入](apps/backend/src/eval_platform/adapters/execution/codex/install.py)、[私有上传](apps/backend/src/eval_platform/adapters/execution/codex/uploads.py) | 固定上游窄继承、默认拒绝凭据绑定；安装/权限输入如何合作；上传代理仅承接两个固定目标，不是新增业务模块 |
| 6 | [patch 校验](apps/backend/src/eval_platform/adapters/execution/harbor/artifacts.py)、[Fork Adapter](apps/backend/src/eval_platform/adapters/evaluation/swe_bench.py) | 完整性校验不等于秘密检测；独立判卷而非信任 Agent 自述 |
| 7 | [完整假值测试](apps/backend/tests/test_codex_trial.py)、[Job 驱动](apps/backend/tests/codex_trial_probe.py)、[合成 CLI 夹具](apps/backend/tests/codex_trial_fixture.py) | 测试怎样注入离线安装、非 root/PATH 和假认证，哪些断言故意要求发现泄漏；模型命令是替身，固定 CLI 只做无模型操作 |
| 8 | [编排契约](apps/backend/tests/contract/test_m0_pipeline.py)、[无模型串联测试](apps/backend/tests/integration/test_m0_pipeline_integration.py) | 现有编排的成功/失败与原型标记；复用已有闭环，避免绕开接口另写脚本 |

开始修改相应实现前还必须读：

- 网络： [network.py](apps/backend/src/eval_platform/adapters/execution/network.py)、[preflight.py](apps/backend/src/eval_platform/adapters/execution/preflight.py)、[网络契约](apps/backend/tests/contract/test_execution_network.py)、[网络实测](apps/backend/tests/integration/test_harbor_network.py) 与其夹具。
- 运行/输出/清理： [process_runner.py](apps/backend/src/eval_platform/adapters/execution/harbor/process_runner.py)、[process_evidence.py](apps/backend/src/eval_platform/adapters/execution/harbor/process_evidence.py)、[redaction.py](apps/backend/src/eval_platform/adapters/execution/redaction.py)、[result_mapper.py](apps/backend/src/eval_platform/adapters/execution/harbor/result_mapper.py)、[result_values.py](apps/backend/src/eval_platform/adapters/execution/harbor/result_values.py)；对应 [秘密测试](apps/backend/tests/test_secret_safety.py)、[强杀清理测试](apps/backend/tests/integration/test_harbor_timeout_cleanup.py)。
- 安装与权限： [test_codex_policy.py](apps/backend/tests/test_codex_policy.py)、[test_codex_guard.py](apps/backend/tests/test_codex_guard.py)、[test_codex_uploads.py](apps/backend/tests/test_codex_uploads.py)、[安装契约](apps/backend/tests/contract/test_codex_installation.py) 及它们实际调用的 probe 文件。
- 判卷内部： [process.py](apps/backend/src/eval_platform/adapters/evaluation/process.py)、[fork_entry.py](apps/backend/src/eval_platform/adapters/evaluation/fork_entry.py)、[判卷映射](apps/backend/src/eval_platform/adapters/evaluation/result_mapper.py)、[五类真实判卷测试](apps/backend/tests/integration/test_swe_bench_integration.py)。

### 4.1 M1 接续必须追加的现有实现

以下均是已存在的代码，先实际阅读公共调用和错误处理；不得只看文件树，也不得按旧任务 04 快照另造平行实现。

- 身份与会话：[HTTP 组装](apps/backend/src/eval_platform/delivery/http/app.py)、[统一错误](apps/backend/src/eval_platform/delivery/http/errors.py)、[身份用例](apps/backend/src/eval_platform/application/identity.py)、[成员用例](apps/backend/src/eval_platform/application/membership.py)；沿用可信 Actor、Cookie/Origin 和统一请求入口。
- 目录与快照：[目录用例](apps/backend/src/eval_platform/application/task_catalog.py)、[配置用例](apps/backend/src/eval_platform/application/agent_registry.py)、[已有 Repository ports](apps/backend/src/eval_platform/application/ports/repositories.py)、[目录领域值](apps/backend/src/eval_platform/domain/catalog.py)。
- 数据库：[短事务](apps/backend/src/eval_platform/adapters/persistence/connection.py)、[目录 SQL](apps/backend/src/eval_platform/adapters/persistence/catalog/schema.sql)、[任务 Repository](apps/backend/src/eval_platform/adapters/persistence/catalog/tasks.py)、[配置 Repository](apps/backend/src/eval_platform/adapters/persistence/catalog/agents.py)。理解读出摘要/指纹验证、默认限制引用为空、显式升级、不把对象 I/O 放入事务。
- 装配与页面：[固定种子](apps/backend/src/eval_platform/delivery/catalog_presets.py)、[目录路由](apps/backend/src/eval_platform/delivery/http/routes/catalog.py)、[目录 HTTP 客户端](apps/web/src/lib/catalog-client.ts)、[题目页](apps/web/src/features/catalog/tasks.tsx)、[配置页](apps/web/src/features/catalog/agents.tsx)及[会话页](apps/web/src/features/identity/session.tsx)；复用唯一 request，不另造平行请求链。
- 测试与隔离：[目录 HTTP](apps/backend/tests/catalog/test_http.py)、[PG 测试](apps/backend/tests/catalog/test_postgres.py)、[双存储/漂移回归](apps/backend/tests/catalog/test_consistency.py)、[PG 夹具](apps/backend/tests/identity/conftest.py)、[隔离验证辅助](apps/backend/tests/catalog/runtime/verify.ps1)、[浏览器后端](apps/backend/tests/identity/browser_server.py)、[浏览器编排](apps/web/tests/run-browser-tests.mjs)。理解显式开关、合成账号和精确清理；恢复阅读不等于自动运行这些脚本。
- Job 生命周期与取消：[提交](apps/backend/src/eval_platform/application/job_submission.py)、[批准](apps/backend/src/eval_platform/application/owner_approval.py)、[取消](apps/backend/src/eval_platform/application/job_lifecycle/cancellation.py)、[执行编排](apps/backend/src/eval_platform/application/execute_job.py)、[Repository](apps/backend/src/eval_platform/adapters/persistence/jobs/repository.py)及其 `execution/` 内部实现。任务 09 还必须读 [Harbor control](apps/backend/src/eval_platform/adapters/execution/harbor/lifecycle/control.py)、取消 HTTP/竞争/编排测试和当前 Web Job 页面。

## 5. Git、环境与测试快照

### Git 与必须保留的增量

**2026-09-17 持久化开工前快照（不是当前 HEAD）：** 当时 HEAD/main/本地 origin/main=`19a0b63`（task14真实私有流程记录），左右差异0/0，暂存区为空，13 份既有已跟踪文档为 dirty，另有旧规划文档与缓存。随后持久化配置和 Worker 控制已新增本地检查点，当前以第 6 节、实施行动及实际 git log 为准；未重新联网核验远端。下方 2026-09-08/12 的提交数和授权也只作历史证据。

历史 2026-09-08 交接开始时 `main` 工作树干净，HEAD 与本地 `origin/main` 均为 `a011b78f78457e0ba11bb4c74bdecbff49b40678`。上一轮已实际推送并独立查询远端确认该哈希；当轮只读本地 Git，不重新 fetch、pull 或查询远端。`729dd88` 是 M0 实现/真实结果文档提交，`a011b78` 是发布记录提交，均已上传至原有 `origin/main`。

本次 2026-09-12 交接实查：`main` 比本地 `origin/main` 超前 12 个提交，HEAD 为 `3274e18`（任务 04 草案），之前依次是 `3302084`（目录评审修复）、`62ea681`（目录实现）、`1563c66`（目录方案）。暂存区为空，但工作树有混合旧文档增量及未跟踪阅读/行动文档；根目录和 Web 下 `%USERPROFILE%/` 缓存均保留。没有业务源码未提交差异，本次仅改 HANDOFF 与新交接记录，不提交或联网查询远端。恢复时重新读本地 Git，不能沿用上方历史“干净”结论。

任务 04 草案行动的提交哈希回填在工作区；其余架构、数据、模块、接口、依赖和旧行动含先前增量，不整批暂存。新窗口对任务 04 关键节点本地提交仍获授权，但须逐项核对实际所属范围。当前交接证据见[独立交接记录](docs/actions/2026-09-12-m1-task04-handoff.md)。

2026-09-08 的增量包括原有 [8 份文档同步](docs/actions/2026-09-05-m0-codex-harbor-implementation.md#2026-09-08放缓开发后的权威文档同步)、阅读指南和相关导航，当时共 9 个文档路径。此后新增数据图中文说明、M0 出口提案和[当前范围同步](docs/actions/2026-09-09-m1-judge-deferral.md)等增量；精确状态以本地 Git 为准，不沿用旧数量。恢复时用 `git status --short --branch`、`git log -4 --oneline`、`git diff` 核对并保留现场，不用远端覆盖。runtime/framework 不在主仓库中，clone 不能恢复完整环境与原始证据。

2026-09-11 新建本地配置检查点 `bee4d6c`，仅包含 `AGENTS.md` 的技能入口、三个 `docs/agents/` 配置和本次配置行动记录；未推送。随后 `2290973` 成功提交 M1 规格、14 份任务单及两份对应行动记录，共 17 个 Markdown 文件；暂存检查通过、提交后暂存区为空。已混合此前增量的总架构、交接等文档未整批加入这些提交，精确范围见[任务发布行动](docs/actions/2026-09-11-m1-ticket-publication.md)。任务 01 的实施另见[身份行动](docs/actions/2026-09-11-m1-owner-identity.md)，不要把旧文档增量自动混入新提交。

身份实现本地检查点为 `b15f062`（`feat: checkpoint M1 owner identity and isolated database tests`），仅包含身份源码/测试、Web、包清单/锁、任务 01 与本行动记录，共 43 文件；不是“任务 01 已完成”的标签。提交后暂存区为空，没有推送。架构、数据、模块、HTTP、依赖及本交接文档在工作区已同步身份事实，但混合此前用户增量，未整批加入此检查点；仅看 Git 提交将缺少这些最新契约增量，正式评审须同时读取当前权威文档。根目录及 Web 下的 `%USERPROFILE%/` 缓存路径均未暂存。

随后本地修复检查点为 `777f67a`（`fix: align identity HTTP errors and verify browser security`），包含 9 个明确源码/测试文件、任务 01 及[独立修复行动](docs/actions/2026-09-11-m1-identity-review-fixes.md)，共 11 文件。实际暂存集合与允许集合逐项一致，暂存 diff 检查通过，提交后暂存区为空；没有 amend 或推送。旧混合文档及缓存继续保留在工作区，权威文档已同步但不在此次提交内；工作树不是干净状态。任务 01 的验收判断见任务单，检查点不代表 M1/MVP 完成。

已推送的实现范围包括：

- 完整假凭据 Trial 测试、非 root 上传和固定 Factory 参数兼容修复。
- 用户已批准的 `execution/codex/{agent,policy,install,uploads}.py` 内部整理及所有相关导入；Git 中旧 `codex_agent.py`、`codex_install.py`、`codex_policy.py` 的删除标记是移动/等价拆分，不是实现丢失。
- 固定离线安装、正式任务 UID/PATH、私有运行绑定、Factory 注册、原型 `codex` 类型及对应测试/文档同步。
- 本次已批准的 `network.py` 限定 DNS 适配、原始/生效哈希、未知配置拒绝，以及现有网络契约/探针的回归增量。

保留全部现有文件和缓存；已完成的发布只包含源码、测试和文档，不包含真实认证、原始运行补丁/日志/判卷输出。该批次提交/push 授权已执行完毕，不延伸到本轮交接或后续自动推送；不因换窗口而重用旧授权。

本轮额外写入的个人汇报技能和个人 AGENTS 位于主仓库之外，不计入上述 9 个 Git 文档路径；准确范围、既有行动技能检查和验证限制见[M0 行动记录](docs/actions/2026-09-05-m0-codex-harbor-implementation.md#2026-09-08全局项目可控性汇报技能)。未修改 `F:\.codex` 备份或现有 action-document 副本。

### 环境与证据

- `framework/` 与 `runtime/` 被主仓库忽略，但含固定源码、依赖环境、题目/镜像安装缓存和实验记录。恢复时核对依赖身份并复用；不要无理由重建 Harbor/Fork 环境。Harbor 首次 Windows 源码编译曾耗时约 275 分钟。
- WSL 更新、UAC 确认和内核预检此前已完成。第三次运行的预检、实际容器与收尾查询均成功访问 Docker；历史全局资源计数仍不是当前状态。若恢复时访问 named pipe 被拒绝，先区分权限错误与引擎停止。
- FlClash 和校园网背景见运维文档；第四场实际模型访问已成功，但具体代理路由及完整网络边界未全部验收。未经对应授权不重启 WSL/Docker、不更改系统代理、防火墙或现有容器。清理只定位对应 Trial，不能全局 prune。
- 证据根为 `runtime/prototype/`。旧 runtime 脚本可能仍使用整理前的导入，重跑使用跟踪测试的新路径；旧证据保留，不批量改写历史记录。

2026-09-12 本地验收收尾提交 `e00408d`（`test: complete M1 membership PostgreSQL acceptance`）仅含任务 02 和成员行动两文件；任务 03 开工/待决记录提交 `f48c41b`（`docs: record M1 catalog storage decision gate`）仅含任务 03 和其新行动两文件。两次暂存集合均与允许范围一致、暂存 diff 检查通过、提交后暂存区为空。权威文档同步仍保留混合旧增量于工作区；没有新业务代码、没有推送。

任务 03 最小接入草案及官方调研本地检查点为 `1563c66`（`docs: prepare MinIO catalog integration proposal`），仅含任务 03、同一行动和调研记录三文件；已核对精确暂存范围、暂存 diff，通过后提交且暂存区为空。该提交时草案尚待批准；用户后续已允许实施，不代表已有新表/Interface/容器或业务测试；旧混合权威文档增量继续保留工作区，没有推送。

任务 03 的实现检查点为 `62ea681`，双轴评审固定 `1563c66...62ea681`；后续 P2 正文摘要校验修复已完成真实红绿验证及原评审者只读复核。最新默认测试、真实 PG/MinIO、浏览器和精确容器清理只由[目录行动](docs/actions/2026-09-12-m1-task-agent-catalog.md)维护，不重复复制数字。混合旧权威文档继续保留工作区，未整批提交或推送。

### M1 当前验证与 M0 历史测试

任务 01 的首次实现、真实 PostgreSQL 集成与容器清理证据在[身份行动](docs/actions/2026-09-11-m1-owner-identity.md#自验证情况)，后续错误契约修复、最新默认回归和 HTTPS 浏览器结果在[独立修复行动](docs/actions/2026-09-11-m1-identity-review-fixes.md#自验证情况)。后者没有重跑数据库。下表仅保留 M0 历史证据，不代表当前身份源码的最近测试。

任务 02 的默认回归、浏览器、双轴评审/修复及新增真实 PG 验收单独维护于[成员行动](docs/actions/2026-09-11-m1-collaborator-invitations.md)。任务 02 评审固定点为 `777f67a`；验收完成以行动和任务单为证，不以检查点代替测试。混合旧增量的权威文档继续保留工作区，不整批混入源码检查点，评审须读取现场文档。

任务 02 实现检查点 `166ccf4`（`feat: checkpoint M1 collaborator invitations pending database acceptance`）已按允许集合精确提交 31 文件；不包含混合旧文档、缓存或测试凭据，没有推送。Standards/Spec 已完成 `777f67a...166ccf4` 静态评审；刷新缺陷已修复、全量浏览器/构建通过，并经原 Standards 评审者针对性复核；可选校验去重未纳入。结论和证据在同一成员行动维护。

任务 02 修复检查点为 `b9efc6b`（`fix: clear invitation token on explicit refresh and record M1 review`），仅含成员页面、对应浏览器测试、任务 02 和成员行动四文件；允许集合与暂存集合一致、diff 检查通过，没有推送。2026-09-12 用户允许专属临时 PG 后已补齐实测，成员行动 Completed、任务 02 验收项全勾选；旧 needs-info 授权等待已解除。

| 检查 | 最近已记录结果 | 解释 |
|---|---|---|
| Ruff check / format --check | 通过；68 文件已格式化 | 本次 DNS 修改后的检查 |
| mypy | 36 源文件通过 | 同一轮静态检查 |
| 默认 pytest | 194 passed、19 skipped，11.51 秒 | DNS 修正后的结果；19 项为未启用的重型检查，不能计为通过 |
| 固定 Harbor 网络回归 | 原始策略 1 failed / 24.56 秒；修正后 1 passed / 42.01 秒 | 同一 DNS 断言红→绿；既有拒绝与精确清理通过，不代表模型通过 |
| 无凭据追加边界 | 9 个守卫场景、受控 UDP 正负例、两个主机根路径 TLS/证书完成 | HTTP 均 403，无模型/账号验证；首次测试断言错误及全部清理证据保留 |
| 第四场真实 Codex → Fork | completed、patch_applied=true、resolved=true；Harbor Trial 167.15 秒 | 真实 1,225-byte 补丁/ATIF/独立原始报告；本场隔离与清理已核对，不代表所有生命周期通过 |
| 生产 Guarded Codex 离线安装 | 1 passed，12.15 秒；真实 Harbor 无模型回归通过 | 固定镜像、network none/deny-all、假认证；无 curl/npm 回退和模型调用，精确资源残留为 0 |
| 新生产 UID/PATH 下完整假认证 success Trial | 1 passed、3 deselected，38.09 秒 | 合成模型/补丁，只证明接线和自然清理；首次夹具顺序失败已保留 |
| 单独启用的完整假值 Docker Trial | 更早一轮 4 passed，156.44 秒 | 成功、报错、超时、patch 带假值；不是全面防泄漏通过 |

实际命令和实验偏差见 M0 行动记录“已批准的 Codex 内部目录整理”“完整假凭据 Trial 结果与暂停点”。完整假值证据位于 `runtime/prototype/codex-full-trial-20260907-06/`；认证接口第 6.2 节说明审计文件与结论。

第三次运行的真实证据位于 `runtime/prototype/m0-real-codex-20260907-03/`：执行 timed_out / AgentTimeoutError、resolved=null、无有效 patch/判卷、usage=null；该场清理证据保留。无凭据 DNS 证据位于 `runtime/prototype/m0-dns-{red,green,light,boundary}-20260908-*/`，各次网络探针的四类资源均为空；该 DNS 验证阶段没有调用模型，之后第四场才单独获授权运行。固定 Linux 包仍在 `runtime/prototype/m0-codex-install-20260907-01/codex-0.153.0-linux-x64.tgz`；预检和运行必须复用同一构造及同一个已校验绑定，不能再次凭记忆拼写启动命令。

最新真实证据为 `runtime/prototype/m0-real-codex-20260908-04/`，同名 `-launch.py` 和 `-audit.py` 在其父目录，分别为本次同一 check/run 构造和限定审计。真实补丁 SHA-256 为 `d5fefec345eb335c9b17d6305037ef47214c56d265f1ca11175c88c90d3ad09d`，独立原始 report 的 SHA-256 为 `cf943803a6e2d818b446afdecb32d41b9e8c706ae36b00b279ae6a5ecf6cc1ec`；具体路径由 execution.json/evaluation.json 引用。该轮没有生产源码变更，未重跑前轮轻量或四场假值测试。

证据阅读注意：`audit-final.json` 是本场限定收尾检查，不能当作全面安全认证；`audit-live.json` 写入时容器已自然结束，空数组不是运行中快照。实际运行中 inspect/top 的观察及 Windows Linux 链接、CRLF 比对造成的检查偏差见第四场行动记录。本次交接没有重读私有原始输出或重跑测试；如下一窗口只看到 Git 文档，应说明证据是沿用记录而非刚刚重新验真。

以下是后续获准验证时的轻量命令参考，工作目录为 `apps/backend`；不是本次恢复后自动执行的步骤：

```powershell
.venv/Scripts/ruff.exe check src tests prototype_codex_harbor_e2e.py
.venv/Scripts/ruff.exe format --check src tests prototype_codex_harbor_e2e.py
.venv/Scripts/mypy.exe src prototype_codex_harbor_e2e.py
.venv/Scripts/python.exe -m pytest -q -p no:cacheprovider --tb=short
```

重型测试先读各测试中的显式开关和依赖，使用全新证据目录，不盲目执行整组。完整假值开关为 `AGENTEXAM_RUN_CODEX_TRIAL_PROBE=1`；这不是实际模型运行开关。

## 6. 当前接续顺序与验收

### 最新确认与当前停点（2026-09-20）

`main` 的 `beed93f` 已包含 D 的 14 个提交：continuous 预设、比较报告端点/矩阵、cancel/claim 竞态修复及其验证记录。合并后审查发现并修复：旧库没有可执行升级入口、比较 query 未严格拒绝未知/重复参数、跨仓库同名 `task_instance_id` 会合并、DTO/渲染重复派生汇总、`routes/jobs/` 超过直属文件上限，以及 HTTP/数据/模块文档未同步。共享库已经由他人升级，本轮只读核验，不重复改库；隔离临时 PostgreSQL 验证升级路径后已精确删除测试库和角色。最终测试结论以[合并后修复行动](docs/actions/2026-09-20-post-merge-review-fixes.md)为准。

任务 03 的后端比较端点已经存在，但 Web 对比页没有实现；任务 04 仍缺五道新题资格入库，任务 08 仍缺真实冻结矩阵全流程。当前不因这些后端前置而改写任务状态或自动继续。

### 历史停点（2026-09-18）

用户已在 `fengyy-fixweb` 分支完成扩展任务 01 的选型：`runtime/prototype/ui-workbench-20260918-01/` 中三种离线假数据 Web 布局通过静态/浏览器检查，最终选择纯 A「侧栏工作台」，不混入 B/C。获授权的任务 02 已把该结构重写为正式 Next.js 工作台，连接现有会话、目录、Job、审批/取消/恢复、成员、报告/证据和排行榜 HTTP Interface；新建向导、服务端筛选/不透明游标、URL 恢复和 390/360 手机菜单已完成。最终 32 条全量浏览器测试、TypeScript、生产构建、双轴评审通过，31 项 API 文档与实时 OpenAPI 差异为 0。未运行真实 Worker/模型，任务 03 未授权。

当前工作状态为 completed 并已到换窗停点：取消备份后的最小本地持久化 P1–P4 已完成，当前没有自动续做的目标。随机数据库 `ae_persist_reboot_9777563a`、9 个随机对象及不含凭据的 `D:\AgentExamData\control\reboot-acceptance.json` 先通过重启前读回；用户完成 Windows 整机重启后，系统启动时间、清单 SHA-256、项目未自启状态均得到独立核对。正式启动后 5 类业务记录和 9 个对象逐项一致，随后只删除清单指定对象、随机数据库和清单。最终只读状态为初始化完成、PostgreSQL/AIStor 运行、活动 Job 为 0、停止标记 false；真实 Worker/模型调用仍未授权。

收尾时 Codex Windows `elevated` 沙箱因自身残留 runtime staging 路径校验失败；重开仍复现。用户按 OpenAI 官方后备方案临时切换到 `unelevated` 后，普通命令与项目补丁恢复。它是本机 Codex 工具状态，不是 AgentExam 产品故障或项目能力；后续若恢复 `elevated`，应先确认 Codex 运行时问题已修复。

生命周期公共入口为 `Initialize-AgentExam.ps1`、`Start-AgentExam.ps1`、`Stop-AgentExam.ps1`、`Get-AgentExamStatus.ps1`。启动只启动存储且不初始化/不启动 Worker；停止先写停止标记，再连续确认主库无活动 Job，超时保留服务运行。日常命令和限制见[行动指南](docs/architecture/modules/owner-host-runtime/ACTION_GUIDE.md#owner-日常操作)。

真实持久化验收使用同一 D 盘 bind mount 中的随机隔离数据库及正式私有 bucket 随机对象键：账号、题目、配置、已完成 Job/Run、报告和全部对象在正常启停、两容器删除/重建及 Windows 整机重启后均一致，测试样本已精确清理。该结果不等于另一设备 LAN/tailnet/公网负向、五人远程入口或整个 MVP 已通过。

#### 已结束的历史路径

暂停时的 AIStor 许可接线红灯已稳定复现并完成最小实现；随后固定镜像模板也完成独立红绿。当前 `infra/tests/test_compose_config.py` 为 10 passed，Ruff lint/format 通过。两个固定摘要镜像已实际拉取并用无网络、只读临时容器核对版本；尚未把版本检查冒充许可证加载、D 盘落盘或长期服务部署。

用户已发布持续目标并确认部署目录与验收边界。[模块索引](docs/architecture/modules/README.md)维护七个模块目录；[所有者单机架构](docs/architecture/modules/owner-host-runtime/ARCHITECTURE.md)维护约束与准备度，[行动指南](docs/architecture/modules/owner-host-runtime/ACTION_GUIDE.md)维护四项交付及验收标准，[实施行动](docs/actions/2026-09-17-minimal-local-persistence.md)维护本次证据、剩余门禁和检查点。原 01–08 编号保留，不自动领取其他阶段。

历史“指南然后开始”当时未实施 Worker，已被当前 P1–P4 数据优先顺序替代。用户随后实际发布目标，允许相关代码、配置、文档及无模型测试；但之后明确暂停，恢复前不得继续实施或测试。D 盘写入、专属容器部署、重启等须精确说明和审批。不读真实模型凭据、不消费真实队列、不改共享 Docker/WSL/全局网络、不推送。用户追加“重要节点本地提交”覆盖早先不提交文字；只暂存本目标明确文件，保留旧混合改动。

现有 `infra/compose.yaml`、无秘密 `.env.example`、正式初始化/生命周期入口和真实 Compose/存储测试；Worker 命令层的默认单次/显式循环、停止标记和失败退出已通过假 Worker 测试。D 盘实际部署、AIStor Free 服务端许可有效性、固定镜像身份、最小权限、跨容器重建、Windows 整机重启和本机非回环端口负向均已验证；备份恢复已明确移出范围，不再列为缺失功能。另一设备端口负向仍归原任务 14。

用户先前条件为“漏洞如果不严重就用”。官方通告 High/8.8 与固定 CE 源码核对不满足条件，因此没有批准旧 CE 承载正式数据；用户随后明确采用 AIStor Free 修复版。当前只核对官方许可和版本，不代用户注册、接受条款或下载软件；研究证据由[MinIO 调研](docs/research/2026-09-12-minio-m1-baseline.md)维护，不再重复发行方向选择。

本地配置检查点 `477c281`：仅提交三份新增 infra 配置/测试及本次实施行动，共四文件；无推送。配置回归 8 passed、Ruff lint/format 和暂存 diff 检查通过；该切片当时不是 P1–P4 完成标记。后续实际部署和验收结果由最新实施行动及 `af0c1cb` 维护，不把早期选型确认当部署证据。

后续安全切片：正式发行版等待期间，只推进已授权且与发行版无关的 Worker 命令控制；24 项 Worker/配置组合检查通过，后端 162 源码类型检查通过。当前 venv 无安装后的 `agentexam-worker.exe`，源码模块帮助已验证；统一启动时需明确 `PYTHONPATH`/运行环境，不擅自安装包。命令层不是完整进程管理或持久化交付；标记检测和数据库 claim 不具原子性，精确语义与失败/红绿记录见实施行动。

Worker 检查点为 `d069511`，仅 command/runtime/新测试/本行动四文件；`c00ca8a` 仅记录当时的选型停点，无推送。工作区权威文档仍保留旧混合规划。该选型停点现已解除，但确认发行方向不能代替用户亲自接受许可条款和取得 Free 许可证。

AIStor 官方核对检查点为 `35a62a6`，仅本次持久化行动和原 MinIO 调研两文件，无推送；其他权威文档及检查点结果回填保留工作区。当时 8 份文档链接/diff 检查通过，未运行服务；后续已新增 D 盘私有许可文件和权限验证，详见实施行动。恢复时复用现有许可，不重复领取/选型研究；普通沙箱写私有路径可能附加 ACL，后续须使用明确审批的 owner 操作并复核权限。

额度规则：持续目标执行期间每半小时检查实际账户限额，剩余 1–4% 时先精确本地提交并报告停止。整机重启后的最近一次读数为 `PrimaryRemaining=12`，未创建模型请求且未触发停工阈值；本目标完成后不再安排后台轮询。接口限制由实施行动开头唯一维护，不把错误或 goal token 数当百分比。

课设最小方案、手动启停和正式业务数据根目录已经确认，云存储只作未来可选；用户随后明确取消备份与恢复，并接受误删、损坏或 D 盘故障可能导致全部业务数据丢失。精确规则由所有者单机模块第 1.1 节维护。用户要求停止过细的运维 Grill，不重问这些选择。已有容量快照见[本机环境第 2.1 节](docs/operations/LOCAL_DOCKER_ENVIRONMENT.md#21-课设容量只读盘点2026-09-17)；随后 D/E dockerdata 专项只读检查及其限制见[规划行动](docs/actions/2026-09-17-module-architecture-and-owner-host-planning.md)，未删除数据。

### 接续顺序

1. 完整读 AGENTS、HANDOFF 及第 3/4 节当项文档/源码，再核对本地 git status/log/diff；保留混合旧增量、全部缓存与 framework/runtime，不 pull/reset/push。若用户只要求恢复上下文，完成这些只读步骤后停下等待新任务，不自动实施或运行测试。
2. 先阅读模块架构、行动指南与最新持久化实施行动，核对目标状态；若用户当轮改为只读/停止则遵从。不因旧任务14未关单恢复机器变更。
3. P1–P4 本地持久化已完成，不自动重做整机重启、重新制造验收样本或恢复已取消的备份方案。原任务 14 的另一设备远程负向仍独立未完，只有用户安排该任务时才继续。
4. 任务 02 的实现、验证、双轴评审和文档已经关闭。当前停止，不自动进入任务 03。
5. 后续严格按各项前置/步骤/验收/停止条件推进。API代理方向和本机私有文件已确认；精确拓扑、计量和固定CLI工具循环仍需验证，不回退真Key进做题容器或协议桥。
6. 真实API阶段重新核验官方模型/地区/价格、账户资格与预算，取得相应调用授权；历史ChatGPT三次许可不覆盖新提供方。人民币费用为条件性估算，不自动充值或扩大Run次数。
7. 每项完成更新同项行动、相关权威文档、任务与本交接；做所需验证与双轴评审后停下。需要新的业务选择/Module/Interface/表或范围扩展时另请用户决定。

### 已有证据与未做事项

- 任务13已经关闭；任务14已有正向真实双角色流程，未完项仍由[原行动](docs/actions/2026-09-14-m1-private-remote-acceptance.md)维护。新范围完成不等于原任务14或整个MVP全部通过；也不把owner自提交自批准误写成产品禁止。
- 已有禁外网假配置探针5/5，固定CLI `0.153.0`；首次环境/权限/路径失败和清理证据唯一见[研究6.1](docs/research/2026-09-17-codex-provider-config-and-budget.md#61-固定-cli-配置探针)。它只证明请求路由/配置拒绝，不证明真实供应商、代理隔离或新题已通过。
- 本次获准只读检查确认 Docker Server 27.5.1，旧任务14两容器为 Exited；未重跑探针、启动或改动任何容器。不据此声明旧环境健康。
- 部署未新增业务 Module/Interface/表；正式 D 盘主库已有 11 表，AIStor 私有 bucket/最小应用权限、重复初始化和真实对象权限通过。生命周期 3 项组合加 1 项停机竞态测试、跨重建合成验收、一次 Windows 整机重启和本机非回环端口负向通过；未运行真实 Worker、模型或推送。
- P1–P4 已有本机实际证据，实现检查点为 `af0c1cb`，重启前文档检查点为 `3ed4dca`。另一设备访问、完整产品回归与整个 MVP 不得由本轮结果冒充完成；整机重启验收不需自动重复。
- 历史额度重置/运行次数不作当前余额事实。新增实际额度检查见上方，未兑换、重置或发起模型请求。

## 7. 历史提示词（2026-09-12，已执行，不作为当前恢复指令）

以下代码块只保留当时交接证据；其中任务号、提交数和“停止在任务 04”的要求都已失效，恢复时必须使用第 6 节。

```text
请在 E:\9.1agent_exam 恢复 AgentExam，并继续完成任务 04。

先完整阅读 AGENTS.md 和 HANDOFF.md，再按 HANDOFF 第 3、4 节完成必读；第 4.1 节是当前任务必须追加的已有身份/目录/事务/页面/测试源码，不能只看文件树。读规格/任务前遵守 docs/agents/issue-tracker.md、triage-labels.md 和 domain.md。所有后续工作按 HANDOFF 第 6 节执行。

最新用户已明确确认 docs/actions/2026-09-12-m1-job-submission.md 中的最小方案，包括精确规模/最多三个配置、初始资源模板、访问范围、四张规划内表、必要 Interface 和子目录。上一窗口只因上下文已满而被要求“只写 handoff”，不是方案未批准。该行动的 Blocked/候选、任务单 needs-info 和架构/数据模型的待批文字是尚未回填的旧快照；先同步确认状态，再直接实施，不重复询问同一授权。详细方案以该行动为准，本提示不另复制规则。

当前 M0 核心真实单题通过、完整验收未完；M1 任务 01–03 已验收并处理评审问题，任务 04 尚未实现、九项验收全部未完成，MVP 未完成。任务 03 实现提交 62ea681、评审修复 3302084；当前 HEAD 3274e18 是任务 04 草案提交，不是实现。沿现有任务 04 行动持续记录，不新建第二份同任务行动，也不复用旧 M0/目录/本次交接记录。

核对本地 git status/log/diff，保留全部混合旧文档、未跟踪阅读/行动文档、%USERPROFILE% 缓存以及 framework/runtime。暂存区此前为空，origin/main 本地记录仍为 a011b78，当前 main 超前 12 个提交；新窗口重新核对，不 pull/reset/push。权威架构/数据/接口有未提交增量，评审必须读取现场，不只看提交。

使用 implement/tdd 按已确认 HTTP 主入口、少量浏览器、真实临时 PG 的分层验收逐片实现。沿 codebase-design 深化已有 Job Submission/Job Repository，不改 M0 ExecutionBackend/PatchEvaluator。创建只保存冻结 Job、全部 Run 和初始事件，立即返回等待所有者批准，不启动 Harbor、模型或读取真实凭据。保持受控配置、幂等/事务/越权/内部测试隔离；随代码及时同步架构、数据模型和接口。

临时 PG 与合成验证、精确清理、关键节点本地提交已有授权；保持专属隔离，不连接现有库或更改机器设置。MinIO 保留，固定 CE 的证据仅支持隔离合成测试，不批准长期/远程部署。现有真实存储和浏览器证据由任务 03 行动维护，恢复时不要冒称刚刚重跑。具体新测试按任务 04 行动记录成功、失败和跳过。

完成实现后按 code-review 以 3302084 为固定基准分别做 Standards/Spec 评审，修复、验证并记录。关键节点只提交明确属于本任务的文件，不能 git add . 混入旧改动。任务 04 验收全部完成后汇报并停止，不自动进入任务 05。不运行真实模型、不重做 M0 网络/凭据实验、不部署长期服务、不改 Docker/WSL/代理/防火墙、不推送。

沟通用清晰中文，按 project-control-report 主动报告模块、结果、证据及待决事项；相同任务的计划/实施/验证更新同一行动，新独立行动另建记录。遵守单文件/目录指标及最小修改。已批准事项无需重复确认，真正新增的业务/架构/外部操作选择再请用户决定。
```

## 8. 建议使用的技能

- `project-control-report`：用户已确认为所有开发项目的个人默认汇报要求；位置见本文开头指针。它负责开始、重要变化和结束时的主动说明，输出格式在技能内唯一维护，不要求用户每次点名。
- `action-document`：实际修改项目文件前使用；本项目入口为 [.agents/skills/action-document/SKILL.md](.agents/skills/action-document/SKILL.md)。用户已明确要求每次新行动新建记录，仅同次行动内持续更新。
- `to-spec` / `to-tickets` / `implement`：用户指定 Spec 分任务工作流。当前本机文件位于个人 skills 下，先实际读取，不因未列在自动技能目录就宣称已丢失；本地配置入口已在 `AGENTS.md`，继续技能要求的测试边界和拆分确认。不得未获允许就发布 GitHub Issues 或安装插件。
- `prototype`：用户安排01时读取，使用静态HTML和假数据比较结构；本轮仅计划，不开始制作。`grilling`只用于新增业务歧义，一次一问，不重复Q1–Q14。
- `tdd` / `codebase-design` / `code-review`：获安排实施时分别用于红绿切片、深化既有模块与双轴评审；使用前完整读取技能及指定参考。code-review要求独立评审时才按技能委派，不把本交接当额外委派授权。
- `handoff` / `writing-for-agents`：按用户明确要求维护现有根HANDOFF，不另建临时副本；本轮范围和验证在同一规划行动。下窗口先看用户是否已发布具体目标；没有新安排就不自动恢复实施。
- `diagnosing-bugs`：实际需要诊断失败时再使用；先区分基础设施、题目失败与检查脚本偏差，不因交接而重新启动实验。

优先用当前会话实际提供的技能调用方式；若只提供文件入口，就完整读取相应 SKILL.md。找不到时说明缺失并按项目文档恢复，不假设存在名为 Skill 的工具；本次没有新建或修改任何技能。
