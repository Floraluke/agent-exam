# 2026-09-17 模块架构文档与所有者单机部署规划

## 状态与情况说明

**状态：Completed（持久化执行目标与关联文档已具体化；只完成文档及静态核对，产品实现和部署尚未开始）。**

用户要求依据现有架构文档和现实代码，在 `docs/` 中按模块建立当前架构权威文档，并说明五人组内协作时 PostgreSQL、MinIO、容器和模型凭据均留在所有者电脑上的实现方式，以及长期持久化是否应前移。

当前事实：M1 任务 01–13 已有现实实现；任务 13 曾在隔离临时 PostgreSQL/MinIO 中跑通正式 Job/Run、固定 Fork、持久化和页面，但这不等于长期服务已部署。现有远程方案是 Tailscale Serve 只暴露 Next.js；FastAPI、PostgreSQL、MinIO、Worker、Docker/Harbor 与模型秘密均应留在所有者机器。正式业务数据根目录已确认，长期版本、备份/恢复和重启验收尚未落实；最新选择由所有者单机架构维护。

本轮已确认的授权仅为规划和文档修改。明确排除：不修改产品源码、数据库表或接口，不启动/重启 PostgreSQL、MinIO、Docker、Web、API、Worker 或 Tailscale，不运行产品测试，不读取凭据，不调用模型，不迁移数据，不提交或推送。

首次交付将所有者单机长期运行写成候选。用户随后明确“确认”，接受将长期持久化、备份恢复和端口隔离放在 HTML 原型之后、真实组内使用和真实模型 API 之前；本次只同步规划并核对代码准备度，具体运行形态仍待收敛。

## 实施措施

1. 对照总架构、模块契约、数据模型、HTTP/Harbor/认证接口、远程接入与本机环境文档，并静态核对现实 Composition Root、应用用例、ports、Adapter、Web 客户端和目录结构。
2. 在 `docs/architecture/modules/` 建立一个索引和七份按职责聚合的模块文档；每份区分当前实现、Interface、Implementation、依赖方向、关键数据流、模式角色、验证证据、风险和候选变化。
3. 保留单一事实源：字段/状态仍由数据模型维护，HTTP 路由仍由 HTTP 接口维护，Harbor/Codex 细节仍由专题接口维护；模块文档只维护“当前模块怎样由现实代码组成及怎样协作”。
4. 为五人协作写出所有者单机候选拓扑、信任边界、运行角色、持久化/备份/恢复门禁及逐步落地顺序；明确“持久卷不是备份”和“所有者电脑离线即平台不可用”。
5. 首次交付更新总架构、模块契约、阅读路线、延期清单与交接入口的指针，不改写当时尚待确认的八项执行顺序；随后用户确认前移，追加 P 阶段和准备度核对，见本文末节。
6. 用户指出模块不应平铺为单个 Markdown。将七个模块改为各自目录下的 `ARCHITECTURE.md`，父层只保留索引；为以后在模块目录内增加数据流、部署或决定文档保留扩展位置，不凭空创建空文档。

完成标准：新模块目录不超过 8 个文件；所有路径有职责说明；当前事实和候选方案可区分；本地 Markdown 链接存在、代码围栏配对、`git diff --check` 通过；只做静态文档检查，不运行产品测试。

## 受影响文件树

```text
docs/
  actions/
    2026-09-17-module-architecture-and-owner-host-planning.md # 本轮范围、措施、文件树、静态验证和待决策记录
  architecture/
    ARCHITECTURE.md                    # 增加按模块当前架构入口；继续维护系统级决定与拓扑
    MODULE_CONTRACTS.md                # 说明契约与模块实现文档的权威分工并链接新索引
    READING_GUIDE.md                   # 把现实 M1 模块文档纳入阅读路线，替换只偏向 M0 的代码地图
    modules/
      README.md                        # 七个模块的导航、权威范围和依赖总览
      identity-and-membership/ARCHITECTURE.md   # 身份、会话、邀请、成员与 owner 本机维护
      catalog-and-configuration/ARCHITECTURE.md # 任务目录、不可变题目快照和固定 Agent 配置
      job-control/ARCHITECTURE.md               # 提交、批准、队列、取消、恢复与 Job/Run 状态
      execution-and-evaluation/ARCHITECTURE.md  # Worker、ExecutionBackend、Harbor、Codex 与固定 Fork
      evidence-and-reporting/ARCHITECTURE.md    # 证据发布、MinIO、报告、轨迹、保留和排行榜
      web-and-http/ARCHITECTURE.md              # Next.js、FastAPI、同源转发、权限翻译和页面分工
      owner-host-runtime/ARCHITECTURE.md        # 五人组所有者单机候选部署、持久化、备份恢复与上线门禁
HANDOFF.md                             # 记录文档成果、规划暂停点和最新确认
.scratch/persistence-deferred/spec.md  # 沿用旧路径维护已前移的 P 阶段范围，未获实施授权
```

模块关系与设计模式：业务依赖保持 `Web/CLI → delivery → application → domain/ports ← Adapter`。PostgreSQL Repository、MinIO Artifact Store、Harbor Execution Backend 和 SWE-Bench Patch Evaluator 是各 seam 上的 Adapter；`create_runtime_app()`、`create_runtime_worker()` 是 Composition Root。新文档不创造新的运行时 Module 或 Interface。

## 自验证方式

- 静态检查新旧 Markdown 的相对链接目标、标题与代码围栏。
- 检查 `docs/architecture/modules/` 直接文件数不超过 8，且文件树中的每个路径都有职责注释。
- 定向搜索“已实现/候选/未部署/未运行”表述，人工核对没有把临时测试环境写成长期服务；首次交付将前移标为候选，用户确认后的版本同步为已确认、未实施。
- 运行 `git diff --check`，核对最终变更路径；确认 `git diff -- apps/backend apps/web` 无本轮产品源码变化。
- 不运行 Python/TypeScript 测试、构建、容器或模型；历史运行证据只引用既有行动记录。

## 自验证情况

首次版本把七份文档平铺在 `modules/` 下；用户指出每个模块应有自己的文档目录。已改为父层仅保留 `README.md`，下设 7 个模块目录，每个目录当前各有一份 `ARCHITECTURE.md`。这为以后按模块增加数据流、部署或决定文档留出位置，同时没有创建无内容的占位文档。现实代码内容、候选状态和八项计划边界不变。

目录调整后重新检查本行动列出的 14 份 Markdown：相对文件链接缺失 0，未配对代码围栏 0；`modules/` 直接文件 1 个、模块目录 7 个，每个模块目录直接文件 1 个。定向搜索确认旧的平铺文件链接为 0，最终树与行动文件树一致。

最终 `git diff --check` 退出 0，仅输出工作区既有 LF/CRLF 提示；`git diff -- apps/backend apps/web` 无输出，确认没有产品源码修改。没有运行 Python/TypeScript 测试、构建、数据库、MinIO、Docker、Tailscale 或模型，也没有读取秘密、迁移数据、提交或推送。

创建 `docs/architecture/modules/` 及其七个子目录时普通沙箱受到文件系统 ACL 限制；随后只对这些已授权文档目录执行受控目录创建，未放宽父目录或修改机器设置。该次交付停在持久化优先级决定，后续确认见下节。

## 2026-09-17：确认持久化前移与代码准备度核对

状态：Completed（确认同步与静态准备度核对完成；P 阶段未实施）。用户确认前移，并询问是否已经做好全部持久化代码准备。继续使用本行动记录同一规划的反馈；本轮只读代码并更新文档，不执行产品、测试、容器、模型或数据迁移。

已核对：PostgreSQL Repository/SQL、MinIO Adapter、显式初始化入口、Worker 装配及 `run_once`、JobRecovery、制品保留、两份隔离存储验收脚本与任务 13 历史行动。结论是业务持久化基础已有，长期运营代码/配置未齐；临时测试采用 tmpfs，不能当持久部署模板。Job 状态恢复与数据库备份恢复是不同能力。

实施措施：记录前移已确认；在现有八项计划中插入独立 P 持久化阶段，保留 01–08 编号以免已有引用失效；在所有者单机模块补充带源码依据的准备度表；同步规格、验证入口、索引、总架构和 Handoff。新版本数据约束会在长期库建立后继续变化，因此显式升级/回退是本阶段必须准备的能力。

本次追加文件树：

```text
docs/actions/2026-09-17-module-architecture-and-owner-host-planning.md # 当前确认、核查与静态验证
docs/actions/2026-09-17-ui-catalog-provider-planning.md                # 原规划行动追加已确认依赖指针
docs/architecture/modules/owner-host-runtime/ARCHITECTURE.md         # 准备度事实源与前移状态
docs/architecture/modules/catalog-and-configuration/ARCHITECTURE.md # 纠正 catalog CLI 只有 init-db 的职责描述
docs/architecture/modules/README.md                                 # 前移已确认的模块状态
docs/architecture/ARCHITECTURE.md                                    # 全局阶段依赖同步
.scratch/persistence-deferred/spec.md                               # 保留旧路径，改为前移阶段清单
.scratch/ui-catalog-providers/plan.md                                # P 阶段及 06/07 前置
.scratch/ui-catalog-providers/spec.md                                # 新确认与独立部署范围指针
.scratch/ui-catalog-providers/verification.md                        # P 验收来源与真实调用前置
HANDOFF.md                                                         # 移除已获确认的重复问题
```

修改前验证标准：上述文档链接存在、围栏配对、无仍把优先级写成待确认的活动说明；P 位于 01 后且为正式组内使用/06/07 的前置；新模块路径保持；产品源码差异为空，`git diff --check` 通过。历史验证不冒充本轮重跑。

实际结果：11 份本次相关 Markdown 的 284 个本地文件链接均存在，代码围栏配对、无尾随空白；定向搜索没有发现仍将前移优先级作为待确认问题的活动说明。人工核对计划表、P 小节、06/07 前置、规格及 Handoff 一致；原任务 14 远程验收未被误标为通过。`git diff --check` 退出 0，`git diff -- apps/backend apps/web` 无输出；既有混合文档变更及 `%USERPROFILE%` 未跟踪缓存保留。

两次多文件补丁曾返回上下文匹配失败，但回读发现前部文件已部分落盘；未按返回状态假定整批成功，也未盲目重复，逐文件核对并补齐余项后完成上述验证。`git status` 对用户级 ignore 文件有权限警告，但未阻止仓库状态读取；未改变该权限。

未运行任何产品测试、构建、数据库/对象存储/容器/网络探针或真实模型；没有迁移、秘密读取、提交或推送。下一步仍为规划审阅，准备度缺口只在所有者单机模块第 10 节维护，不另建重复的实现清单。

## 2026-09-17：课设最小方案与容量盘点

状态：Completed（盘点与规划同步完成，不表示部署完成）。用户通过逐项 Grill 确认手动一键启停、启动后后台运行且不随开机自动启动；硬盘故障恢复目标为最多丢失最近 24 小时数据。用户随后说明主要担心本机容量，项目只是五人课设、预期数据不多，并确认先盘点本机占用和确定数据位置、云存储暂列可选。简单备份与恢复仍保留，异机副本去向未定，不能把本机导出或云可选等同于已满足故障恢复目标。

本轮只读文件系统元数据并同步已确认规划，不修改产品、不创建数据目录、不读真实运行正文/秘密，不运行 Docker/WSL/服务/测试/模型，不删除、移动、压缩、迁移或上传数据，不提交/推送。按 grilling 技能把有边界的项目目录容量和既定 VHDX 文件元数据盘点交给只读子代理；主代理核对盘符容量并负责文档，子代理不得修改文件。

实施措施：

1. 以现有文件系统元数据核对盘符余量、项目各目录逻辑文件长度和历史指定 VHDX 的当前长度；不遍历其他私人目录、不启动 Docker 查询镜像。
2. 本机动态值只在环境文档维护，区分逻辑长度、物理占用、共享资源和无法判断的可回收空间；文件系统扫描不能替代 Docker 镜像/卷盘点。
3. 所有者单机模块维护已确认课设约束，规格、P 计划和 Handoff 只做相应状态同步和指向；不替用户选择尚未确认的数据目标路径、清理范围或备份去向。

本轮实际修改范围（无新增产品目录、Interface、表或设计模式）：

```text
docs/actions/2026-09-17-module-architecture-and-owner-host-planning.md # 同一规划的确认、盘点方法与验证记录
docs/operations/LOCAL_DOCKER_ENVIRONMENT.md                          # 最新磁盘/目录元数据事实及检查边界
docs/architecture/modules/owner-host-runtime/ARCHITECTURE.md         # 课设运行约束、候选容量方案和剩余决定
.scratch/persistence-deferred/spec.md                               # 已确认启停/恢复目标与可选云的任务状态
.scratch/ui-catalog-providers/plan.md                                # P 阶段落实最小方案，不取消必要持久化门禁
HANDOFF.md                                                         # 最新确认、恢复入口与下一停点
```

自验证方式：检查以上 Markdown 的本地链接、围栏、空白和状态一致性；确认没有将云方案、数据目录、清理或迁移写成已授权/已实施；`git diff --check` 及产品源码 diff；回读行动结果。容量只读命令失败和未覆盖部分须明示，不重跑产品测试。

自验证情况：6 份文档的 192 个本地文件链接存在、围栏配对且无尾随空白；`git diff --check` 通过，当时产品源码 diff 为空。容量来源与读取失败/跳过情况在本机环境第 2.1 节记录。后续用户确认正式业务数据规划放 `D:\AgentExamData`、故障可在一天内人工恢复，并要求停止过细的运维 Grill。D/E dockerdata 专项只读检查确认当前 Docker 配置与注册路径在 E，D 只剩约 0.88 GiB 归档和空目录；未删除任何文件，归档用途仍未知。

## 2026-09-17：最小持久化行动指南与 P1 Worker 代码准备

状态：Superseded（被下一节“执行目标具体化”替代；本节保留当时拟定方案，不是已实现清单）。用户明确要求“出一版行动指南然后开始”，并要求先说明耗时。已先告知整个最小范围粗估 2–4 小时，遇 Docker/WSL 权限或挂载问题可能延至半天，非完成保证。实际只创建了指南并阅读源码；尚未进入以下候选 Worker 改动。

授权与排除：可编写指南、修改相关代码并做不调用模型的局部验证。不得因此启动真实 Worker、读取真实模型凭据、领取已有队列、连接既有库、创建正式 D 盘目录、迁移 Docker、删除 D/E 内容或运行真实模型；正式环境变更须另说明具体影响。没有提交/推送授权。

实施措施：

1. 把最小范围、分步交付、成功标准、风险停点和粗估放在本模块 `ACTION_GUIDE.md`，不增加业务模块/Interface/表或产品目录。
2. P1 仅深化现有 Worker delivery：保留默认一次 claim，增加显式 `--watch --stop-file <absolute-path>`；仅顺序重复既有 `run_once`，空队列等待，停止标记阻止下一轮领取，当前 Job 正常收束；异常立即退出且不自动重试，Ctrl+C 属于中断而非优雅完成。
3. 在既有目录增加内部命令实现和单测，不把 polling/命令解析塞进业务用例；runtime 继续唯一装配生产 Adapters。为遵守 200 行上限，将命令壳从已有 runtime 拆到同目录 command.py，不新增公共业务接口。
4. 先运行新增假 Worker 测试取得失败信号，再实现并运行局部回归、Ruff 和 Mypy；不运行 Docker、浏览器、框架或模型测试。自查后按固定基准对本切片作双轴检查；旧混合文档不当本轮源码增量。
5. 同步运行模块、执行模块、P 规格/计划、Handoff 与行动实际结果。部署配置、统一启停及备份恢复留在指南后续步骤，不把 P1 冒充整个持久化完成。

固定基准：`19a0b63b66f77c3c860e0bffa8f2905757de321d`；开工时 `git diff -- apps/backend apps/web` 为空，旧混合文档、未跟踪缓存和 framework/runtime 全部保留。本轮未新增提交，评审必须包括工作区和新增文件，不能只比较空的提交区间。

当时拟定切片文件树（仅 ACTION_GUIDE.md 与本行动落盘，其余源代码/测试文件未改或未建）：

```text
docs/actions/2026-09-17-module-architecture-and-owner-host-planning.md # 同行动的实施范围、变化和验证
docs/architecture/modules/owner-host-runtime/
  ACTION_GUIDE.md                 # 新增：整项最小持久化步骤与当前完成度
  ARCHITECTURE.md                 # 已确认 D 盘/恢复目标与 Worker 准备度
docs/architecture/modules/execution-and-evaluation/ARCHITECTURE.md # Worker 命令的现实职责与边界
apps/backend/src/eval_platform/delivery/worker/
  runtime.py                     # Composition Root；构造现有 Worker 并交给命令壳
  command.py                     # 新增内部 Implementation：一次/循环模式、等待、停止和安全错误
apps/backend/tests/jobs/runtime/
  test_worker_command.py         # 新增：假 Worker 的默认、顺序、空闲、停止、失败与参数边界
.scratch/persistence-deferred/spec.md  # 当前最小实施授权与尚未完成项
.scratch/ui-catalog-providers/plan.md  # 独立 P1 代码准备已开始，其余阶段不自动开工
HANDOFF.md                        # 最新授权、P1 进度与正式部署边界
```

修改前成功标准：默认命令行为保持；已有停止标记时不装配、不领取；循环只顺序调用既有 shell，空队列不忙等；停止请求不开始下一轮且不创建重试 Job；循环/配置异常退出 2、诊断不泄漏异常正文，Ctrl+C 退出 130；无效参数在装配前拒绝。局部测试/静态检查输出实际核对；文档链接/围栏/文件行数和目录文件数合规。新源码不超过 200 行，每个被加文件的现有目录仍不超过 8 文件。

实际结果：已创建最初版指南并阅读现有 Worker/存储/初始化入口，没有实施候选循环命令。最新只读核对 `git -c core.safecrlf=false diff --name-only -- apps/backend apps/web` 无输出；候选 command.py 和 test_worker_command.py 均不存在。未运行单测、Ruff、Mypy、容器或模型；原计划中的红绿验证与双轴评审未执行，不能称 P1 已完成。

## 2026-09-17：持久化执行目标具体化

状态：Completed（目标准备完成，不表示持久化实现完成）。用户最新要求“你把持久化具体化给我，我把它设成目标执行吧”。本轮只更新目标说明及关联文档，不替用户创建目标，不实施产品代码、不运行产品测试或服务。沿用同一行动，停止先做 Worker 的旧推进顺序，改为先明确真正的数据落盘与验收。

实施措施：

1. 改写已有 ACTION_GUIDE 为可交给下一次执行的目标：长期 PG/MinIO、显式初始化、手动启停、备份恢复及合成验证；每项列可观察的成功标准与失败停点。
2. 把 Worker 循环放回启停配套；数据落盘和重建保留先于队列消费。说明代码完成、部署验证、本机备份和异机防灾是不同结果。
3. 同步已确认数据路径与一天人工恢复目标，删除活动文档仍把它们写成待决定的描述。配置版本、目录子布局由后续技术核对收敛，不强行新增业务模块或泛化迁移系统。
4. 更新规格、计划和 Handoff 的唯一入口；注明当前仅目标文档完成，没有把未来 D 盘写入、真实 Worker/模型或机器变更自动授权。

本轮受影响文件树（全部为既有文档修改）：

```text
docs/actions/2026-09-17-module-architecture-and-owner-host-planning.md # 范围、旧方案替代关系及实际验证
docs/architecture/modules/owner-host-runtime/
  ACTION_GUIDE.md                 # 最小持久化执行目标、交付顺序与验收标准的唯一维护处
  ARCHITECTURE.md                 # 已确认根目录/恢复目标及现实准备度
.scratch/persistence-deferred/spec.md # 阶段状态、执行指南指针和未完成门禁
.scratch/ui-catalog-providers/plan.md  # 具体目标入口，不擅自启动其他阶段
HANDOFF.md                       # 最新目标准备停点，防止恢复过期 Worker 实施计划
```

模块关系不变：现有 Repository/ArtifactStore Adapter 负责业务存取，部署与维护入口负责它们的生命周期；Worker 仍复用已有单次执行，不新增业务 Interface、表或顶层 Module。本轮不创建候选部署目录。

自验证方式：检查上述 Markdown 本地链接、围栏、尾随空白；检查目标/当前事实不混写，已确认目录与恢复耗时不再作为活动待决问题；运行 `git diff --check`，核对产品源码 diff 仍为空，候选 Worker 新文件仍不存在。只做静态文档检查，不能当部署验证。

自验证情况：6 份实际修改文档的 185 个本地文件链接均存在，围栏配对且无尾随空白；`git -c core.safecrlf=false diff --check` 无错误。产品源码 diff 无输出，候选 Worker command.py 和 test_worker_command.py 均不存在；模块目录仍只有 ARCHITECTURE.md、ACTION_GUIDE.md 两个文件。定向搜索及人工核对确认根目录/恢复耗时已确认、旧 P1 进行中已替代；旧决策历史保持并注明后续替代，不作为活动待决。

最后复查 `git diff --check` 退出 0。产品目录状态仍显示既有两个 `%USERPROFILE%` 未跟踪缓存目录，全部保留；Git 用户级 ignore 文件的权限警告仍存在，未修改权限，不把本轮无产品改动描述为整个工作区干净。

实际文件范围与本节树一致，没有新增部署目录、业务代码、Interface 或表；未运行任何产品测试、容器、模型或网络验收，没有本轮磁盘盘点、D 盘创建/迁移/删除、凭据读取、目标创建、提交或推送。文档检查通过不代表长期存储、备份恢复或端口隔离已通过。下一步由用户发布目标；未获新安排不自动执行。
