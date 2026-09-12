# M1 任务 03：任务与 Codex 配置目录

## 状态与情况说明

- 状态：Completed。2026-09-12 完成目录、真实隔离存储验收、HTTP/Web 回归和双轴评审；P2 摘要漂移已修复并复核，架构与数据模型同步。可选页面去重未纳入。固定 CE 只用于隔离合成验证，不是长期/远程部署基线；维护风险见依赖总表第 2.3 节。
- 本行动对应[任务 03](../../.scratch/m1-platform/issues/03-task-agent-catalog.md)；与成员行动分开记录，之后同一任务的计划、实施和验证继续更新本文件。
- 已确认复用现有 Task Catalog、Agent Registry、Artifact Store 的规划职责，不新增顶层业务模块。现有账号/会话/邀请表不能承载固定任务、配置身份及原始快照索引；现有 SWE-Gym 适配器只从已校验本机数据读取任务，不是持久化目录。
- MinIO 上游维护/发行事实仍只在[依赖总表第 2.3 节](../dependencies/DEPENDENCIES.md#23-任务-03-对象存储依赖复核)维护。已批准固定 CE 源码候选的隔离合成验证，不改用 AIStor、不作为长期/远程部署批准，也不把本地文件替身当作真实对象存储验收。
- 任务 02–04 专属临时 PostgreSQL 及下方 MinIO 获取、构建、容器与精确清理范围已获许可；执行前仍查证具体构建输入身份。三张表、四个 Interface 和下方子目录已批准。没有模型、邮件、真实用户、长期数据库、机器设置或推送操作。

## 实施措施

1. 已核对既有 task/agent/result 领域对象、SWE-Gym 适配器、目录任务、数据模型和 Artifact Store 契约。保留原始任务与 Agent 可见任务分离，不给普通 HTTP 暴露参考答案。
2. 已只读核对上游对象存储维护/发行事实及本机镜像可用性；先将发现和实际暂停点落盘，不先安装或替换产品。
3. 已收到“我们还是选择 miniO”：同步原架构继续采用 MinIO，关闭更换产品的提案与旧方向等待。后续只读核对 MinIO 的可固定版本、制品来源和适用部署边界，先说明具体风险，不重新询问是否换其他产品。
4. 最小结构已批准：复用已有模块，按下方树开展 HTTP 红绿切片；同步架构、数据模型、模块和 HTTP 契约。当前仅登记固定单题环境，不能直接宣称批量题目都有可用镜像。
5. 逐步执行 HTTP/少量浏览器、真实 PostgreSQL/MinIO 单侧失败测试和双轴评审，记录失败与限制。任务 03 完成后才进入任务 04，其精确规模与限制数值仍需确认。

## 当前实际修改的文件树

```text
E:/9.1agent_exam/
├─ .scratch/m1-platform/issues/03-task-agent-catalog.md # 已确认产品与恢复开工状态，不改验收语义
├─ HANDOFF.md                                         # 当前恢复点，不沿用旧方向等待
└─ docs/
   ├─ actions/2026-09-12-m1-task-agent-catalog.md       # 本行动；与任务 02 分开
   ├─ dependencies/DEPENDENCIES.md                     # 对象存储上游事实唯一维护位置
   ├─ research/2026-09-12-minio-m1-baseline.md           # 本次官方来源调研，候选不等于已固定依赖
   ├─ operations/LOCAL_DOCKER_ENVIRONMENT.md             # 记录官方端口发布限制与实测边界，不改机器设置
   ├─ interfaces/HTTP_API.md                            # 随切片同步受控登记、公开字段与安全错误
   └─ architecture/
      ├─ ARCHITECTURE.md                                # 已批准的分层、文件树及实现状态
      ├─ DATA_MODEL.md                                  # 目录三表、不可变关联与实际字段
      └─ MODULE_CONTRACTS.md                            # 已批准四个 Interface 的契约
```

上述为先行文档增量；当前已新增下方已批准树中的领域、应用/四个 ports、数据库/MinIO Adapter、交付层和 catalog 测试目录，以及 MinIO 构建 Dockerfile；Web 和其余隔离测试脚本也已落地。依赖方向保持应用依赖抽象边界，生产/合成 Adapter 实现同一 Interface，真实存储实测结果在下节维护，不据此声称长期部署已完成。

## 自验证方式与成功标准

- 对照实际源码、任务验收和官方来源，明确已实现/规划/待确认，不用产品宣传代替维护状态或实验结果。
- 本轮文档的本地链接、锚点、代码围栏以及 `git diff --check` 应通过；任务 03 仅在对应实测与评审完成后勾选，任务 02 已完成不回退。
- Git 按任务 03 实际新增/修改的明确允许集合本地提交；已有混合文档增量保留，不整批暂存。评审基准为实施前 `1563c66`；不运行模型或推送。
- 成功标准按任务 03，包含原始快照与元数据发布一致、秘密隔离及真实双存储故障测试；实际已运行/跳过记录如下。

## 自验证情况

## Standards

- 固定评审范围 `1563c66...62ea681`。P2：PostgresTaskRepository 读取未核对 problem_sha256，正文与摘要不一致时仍成功，违反数据模型第 4.1 节和模块契约第 6.2 节。评审者纯内存调用确认；已按确认的 HTTP/真实存储边界新增故障注入用例并修复。实测列表、详情和重复登记都安全返回 503；原 Standards 评审者只读复核确认覆盖原问题、未发现新缺陷。
- P3（可选判断）：两个目录页面的请求代次、忙碌/错误与详情失效代码重复。不是硬违规；未经确认不扩大本轮重构，后续可评估局部共享请求状态处理。

## Spec

- 同一固定范围未发现任务 03 的规格遗漏、未经授权扩展或可复现实现错误。三表、四个 Interface、固定种子、限制引用暂空及隔离 CE 测试均属于已批准方案。

双轴评审计数：Standards 1 项 P2、1 项可选 P3；Spec 0 项。评审者未重跑容器或完整测试，原测试属于沿用证据；下方另记修复后的实际验证。

### 2026-09-12 实施进展与本轮实际验证

后续结果（覆盖下方较早的“待执行”快照）：

- 修复后 `verify.ps1`：55 passed、2 warnings，33.73 秒；scope catalog-7231804e88e14d759b3cfc4aaf91bc15，driver sha256:2162edefcc51562f3a2ad3c405699f4e4b107efae8b6a92b7c38fc7e6e69cd24。真实 PG 正文损坏经 HTTP 列表/详情/重入全部安全失败，目录及身份/成员 PG 回归通过。三个专属容器与 tmpfs 已精确删除；未连接现有服务或运行模型。
- 修复后全后端 `python -m pytest -q -p no:cacheprovider --tb=short`：274 passed、47 skipped、2 warnings，25.86 秒；新增跳过是 PG 故障用例，已在上项显式开启通过。`ruff check src tests`、`ruff format --check src tests` 通过（130 文件），`mypy src` 通过（74 源文件）。Web 没有再修改，沿用本轮前段的 11 项浏览器、typecheck/build 证据，不冒称修复后重跑。
- 收尾文档检查：10 份 Markdown、247 条本地链接、77 处锚点、围栏/空白/diff 通过，暂存区为空，任务 03 八项验收完成。只读资源复核 catalog-test 容器为 0，现有容器/卷/网络仍 18/15/5；四场专属测试的数据已清理，镜像与缓存保留。
- 原 Standards 评审者只读复核确认原 P2 已覆盖，未重跑容器。任务 03 验收据本行动的实测与双轴评审完成；可选 P3 不扩大重构，MinIO 安全部署、全量题库、M1 后续能力和完整 M0 验收未借此完成。

- 评审修复红灯：在真实 PostgreSQL 注入正文与摘要不一致后，经 HTTP 列表实际返回 200 而非预期 503；本场 54 passed、1 failed、2 warnings，35.35 秒。scope catalog-b577a9de12624362bb256111aa3dd8fe 的三个容器及 tmpfs 已精确删除。随后在任务 Repository 统一读出边界增加摘要比对，列表、详情、同身份重入共用；架构与数据模型同步，后续绿灯见上项。
- 修复验证准备曾尝试禁网构建，因构建网络模式改变导致依赖层缓存未命中而失败；原授权允许构建联网，因此恢复原命令后成功（driver sha256:01197454104ae315b4d95b0f138340e27833acb8b0840f29e63b316be1296f05），未改机器设置或运行容器隔离策略。
- 任务 03 实现检查点 `62ea681`（feat: implement M1 task and Codex catalogs with isolated storage acceptance）精确提交 46 个允许文件，暂存集合与允许集合一致、暂存 diff 通过，提交后暂存区为空。混合旧权威文档继续保留工作区，没有推送。双轴评审固定为 `1563c66...62ea681`，两路只读评审已完成，结论及修复见上节。
- 离线 wheel 构建成功（runtime/tools/catalog-wheel-check/agentexam_backend-0.1.0-py3-none-any.whl）；默认沙箱首次直接打开 ZIP 被拒绝，属于检查权限失败，不是包资源缺失。经授权只读重试成功，确认身份 SQL、邀请 SQL、catalog/schema.sql 均已包含；没有安装到系统、联网或发布。

- 检查点前文档校验：10 份 Markdown、247 条本地链接、77 处锚点、围栏/空白/diff 检查通过，暂存区为空；任务验收暂不勾选，等待独立评审。只读资源收尾：catalog-test 标签容器 0，现有容器/卷/网络为 18/15/5；只删除了两场各自的精确合成容器，保留既有资源及新建镜像/缓存。

- 隔离后的默认 `npm run test:e2e` 全部通过：catalog 2/11.1 秒、identity-security 6/14.3 秒、identity 2/9.2 秒、membership 1/10.6 秒，共 11 项；每个文件使用新启动的合成后端，结果分文件保存在 runtime/tests/identity-browser-results。随后 npm run typecheck、npm run build 均通过，Next 编译 3.0 秒；不把构建当作已部署。动态新增/修改源码均不超 200 行；domain 7、ports 7、HTTP 8、catalog 测试 8、runtime helper 3、Web lib 4 个直接文件，未使用事后拆分或新增指标例外。

- 完整浏览器首次 9 passed、2 failed（32.3 秒）：新增目录登录叠加既有用例超过同进程 60 秒 10 次预算，后续错误密码/成员测试收到真实 429。不是修改产品限流的理由。新增既有 tests 目录内的 run-browser-tests.mjs，配合 package.json 将每个 .spec.ts 文件放入独立启动/收尾的合成后端；不新增目录或放宽生产规则，既有测试目录 4 个用例文件加此编排文件仍不超 8。默认命令继续发现全部测试文件。

- MinIO 源码构建完成：go mod verify 通过，构建 379.4 秒；自建镜像与构建输入身份由依赖总表第 2.3 节维护。仅是已批准隔离测试构建，版本输出 DEVELOPMENT.GOGET，不冒称官方发布或安全风险已关闭。
- 新增 apps/backend/.dockerignore，限制构建上下文只含 pyproject/uv.lock/src/tests；原目录 5 文件，加此配置不超 8，未新增结构边界。Dockerfile.tests 固定 Python 与 uv 制品后按锁构建，未发送 .venv、私有 runtime 或宿主配置。
- 专属集成第一次：scope catalog-087421da6b8f4ed181b6bae4d5e7f9fd，47 passed、1 failed、2 warnings，29.06 秒。新存储检查通过，旧身份跨进程恢复因目录配置在启动时过早强制校验失败；不是数据库事务或 MinIO 运行故障。修正为首次使用目录时才验证专属配置，缺失目录配置仍安全失败，不阻断原有登录。该场 3 个容器及 tmpfs 均已精确清理。
- 第二次专属集成：scope catalog-4527372dd1bc419198e98dcecbeb86a0，driver image sha256:4f9314a04eaedb67bfe948c9b55c88a1708bb44ba8bb8f54eb0a6d1eb3f52835。运行 catalog 全组及 identity/test_postgres_identity.py、membership/test_postgres.py、membership/test_postgres_rollback.py：54 passed、2 warnings，33.99 秒；包含目录 PG 并发/回滚/重建/筛选分页、MinIO 条件写/重入/缺失/损坏，以及真实双存储单侧失败。MinIO network none，另两容器共享其网络空间；逐容器断言无发布端口/宿主挂载、有只读根与资源限制，3 个容器及 tmpfs 已清理；镜像和构建缓存保留。没有连接现有服务或运行模型。
- SDK 错误测试曾揭示 ClientError 不属于 BotoCoreError，缺失对象错误未正确转换；加入显式转换后相关 4 项客户端检查通过。不是“模拟服务通过”冒充真实 MinIO；上项另有真实服务证据。
- 首个浏览器目录测试先因页面未实现失败；接线后 1 passed，11.0 秒。多条摘要浏览器测试随后发现 Array.map 将数组索引误当详情标志，已按同一红绿测试修正；完整浏览器回归正在运行。所有浏览器数据/账号合成，不产生正式成绩。
- 默认全后端：274 passed、46 skipped、2 warnings，25.30 秒；46 跳过为未启用的 M0 重型与身份/成员/目录外部集成，不能计为通过（其中本次单独启用范围见上项）。Ruff check/format 全部通过，131 文件；mypy 75 源文件通过。真实模型、重型 M0 生命周期和正式部署均未运行。

- 已记录用户批准并解除 needs-info；执行 implement/tdd，沿已确认 HTTP 和外部存储 Interface 开展切片。任务与配置登记的首个测试分别以 404 失败后转绿；非法查询测试发现未知/重复参数被忽略，收紧后通过。PostgreSQL/MinIO 测试首次因 Adapter 尚不存在而在收集阶段失败，不能称为真实存储行为已验证。
- 当前局部检查：`python -m pytest -q -p no:cacheprovider tests/catalog --tb=short` 为 26 passed、3 skipped、2 warnings，4.81 秒；3 跳过为尚未启用的专属 PG。Ruff check 经格式/导入修正通过，mypy 74 源文件通过；此前 SQL 组合类型和测试夹具导入静态错误已修正。未执行当前全量回归、Web 或独立评审。
- 构建准备：Docker Hub 摘要查询连接超时；官方 ECR 的 Go 查询曾 429，延后一次查询成功，Go/Python 两个官方固定摘要镜像已拉取。没有改变代理、Docker/WSL 或宿主端口。
- PyPI 核验 boto3 1.43.93 支持当前 Python。首次 uv 默认缓存因跨磁盘临时文件失败；用本次命令的项目缓存路径及 copy 模式后 lock/sync 成功，现有直接依赖版本不变。缓存位于 runtime/tools/uv-cache，非全局配置更改。
- MinIO 官方固定源码归档已下载至 runtime/tools/minio-build-7aac2a2c/minio.tar.gz，24,227,422 bytes，SHA-256 为 71794c2df26aad0cc99e8421c58b7aa2dd55969f979b0e7d1e931042e9fabcd6。已读取其 go.mod；Dockerfile 构建核验摘要通过，正在下载模块/构建，尚未声称镜像或运行验收成功。
- 构建命令指定 3 GiB/2 CPU 参数，Go 并行度 2、GOMEMLIMIT=2GiB、GOTOOLCHAIN=local；运行测试环境仍未创建。开工 E 盘可用约 12.8 GB；镜像/缓存保留，尚未执行清理，也未推送。

- 代码核对：已有 EvaluationTask / EvaluatorTaskData / TaskBundle 分离公开与隐藏任务，AgentConfiguration 可冻结关键配置并计算指纹，ArtifactRef 包含哈希/大小；本机 SWE-Gym 读取仍不是目录数据库。架构规划的 task_source/artifacts port 尚未落成，不凭规划树调用不存在的接口。
- 官方核对：MinIO 社区仓库明确归档和停止维护；其 AIStor Free 链接实际跳转至许可证下载入口。不能据旧 README 的产品称谓推断已获得可部署许可证。两次猜测产品/文档地址打开失败，随后改用官方现有链接定位；失败不是本机网络或服务故障，不据此改代理。
- 本机只读 `docker image ls --filter reference=*minio*` 没有结果；未拉取/构建或启动对象存储。PostgreSQL 清理与运行结果仍只由任务 02 行动维护。
- 上轮文档实查：10 份 Markdown、224 条本地链接、59 处锚点、围栏及 `git diff --check` 均通过；局部补丁因标题/上下文不匹配被拒绝，核对实际内容后只补未生效段落，未覆盖既有增量。当时产品方向尚待确认；用户后续已明确保留 MinIO，不能继续沿用旧 Blocked 状态。

### 用户确认保留 MinIO 后的同步

- 本次只更新同一任务 03 行动、任务单、架构、依赖与交接五文件，不另开同一行动的重复文档。业务源码、数据库、容器和依赖安装没有变化，未运行模型或推送。
- 完成标准：五文件对“保留 MinIO、方向已确认、精确版本/新结构/外部验证尚未定案”的描述一致。实际检查：5 份 Markdown、177 条本地链接、41 处锚点、围栏与 `git diff --check` 全部通过；任务 03 验收项仍全部未勾。此次没有重跑业务测试或上游维护检查，历史运行结果与维护证据不冒称本次实测。

### MinIO 版本与最小接入方案核对

- 用户同意继续核对固定版本与最小接入方案。使用 research 技能的有界调研代理，只读官方来源并写上述单份调研记录；主代理核对既有模块、领域值、数据与 HTTP 契约，负责方案收束和审批边界。不下载可执行制品、不安装依赖或启动容器，不实施新表/接口/目录。
- 核对目标：候选版本有官方出处与不可变身份；说明社区版维护及已知安全限制，制品来源无法证实就明确未知。最小结构草案复用已有职责、保持单文件/目录指标，明确原始快照与公开视图分离及双存储失败语义。
- 完成检查：已读取官方调研及关键安全/端口发布原文，具体产品仍为 MinIO；已对照现有代码、数据/HTTP/模块契约及直接目录计数检查候选方案。7 份 Markdown、201 条本地链接、59 处锚点、围栏、尾空白及 diff 检查通过，包含新增未跟踪调研文件的逐行检查；业务源码无差异、暂存区为空、任务 03 验收项未勾。候选不视为用户已批准或实际验收；构建、安装、容器与业务测试均未执行。

### 任务 03 最小接入方案

2026-09-12 用户已批准以下方案；尚未运行的验证仍不算通过。

#### 能力与范围

- 目录能保存和分页查询多条固定任务/配置；首个正式种子仅采用现有已核验的 SWE-Gym Lite 单题和已确认 Codex 版本/模型/推理强度，不创建模拟正式条目、不下载更多任务镜像。更多真实任务必须先固定来源及环境；不把当前单题已核验等同整个题库可执行。
- 登录用户通过既有规划的四个查询端点查看任务/配置列表及详情；所有者通过受控登记入口选服务端预置身份，不提交任意 JSON、镜像、命令、URL 或宿主路径。配置可禁用且历史身份保留；重新登记同一禁用配置不隐式重新启用。
- 暂不实现 Job、批准、队列、报告/制品下载、全量题库同步或制品定时清理。限制模板的精确数值由任务 04 确认；任务 03 不伪造已存在的模板，未绑定时公开默认引用显式为空。

#### 必要新增与复用理由

| 项目 | 已实施最小实现 | 为什么不能直接复用身份能力 |
|---|---|---|
| PostgreSQL 表 | `evaluation_tasks`、`agent_configurations`、`artifact_records`，只落任务 03 所需字段/关联，不预建 Job/Run/P2 表 | 账号/会话/邀请无法表达不可变任务身份、配置指纹及对象索引；三者均为已有数据模型规划的实体 |
| 应用与存储 Interface | TaskSource、TaskRepository、AgentConfigurationRepository、ArtifactStore；沿用规划的 `task_source.py`、`repositories.py`、`artifacts.py` 三个 port 文件 | 现有 `load()` 可作为 TaskSource 实现复用，但没有持久目录或对象存储 Interface；生产 PostgreSQL/MinIO 与合成测试 Adapter 分别满足同一接口，应用不见 SQL、SDK 或连接 |
| HTTP | 实现原规划的 GET tasks/详情、GET agent-configurations/详情；补所有者 POST tasks/register、POST agent-configurations、POST agent-configurations/{id}/disable | 现有身份/邀请端点不承担目录登记；正文仅接受受控预置 ID，复用当前 Cookie、Origin、可信身份和统一错误 |
| 初始化 | 独立本机目录结构升级命令，显式创建上述三表；启动 API 不建表/同步，重复执行失败且不覆盖数据 | 保持现有身份初始化行为，旧应用库需要明确升级入口，不能借一次登录隐式写结构 |
| 外部依赖 | MinIO Adapter 使用支持原子条件写的公开 S3 Python 客户端；具体锁定版本由官方接口/兼容核查确定 | 现有依赖没有 S3 客户端；不手写签名或依赖 SDK 私有方法，也不因使用 S3 协议而更换 MinIO 产品 |

Task Catalog 拥有登记/读取与发布一致性；Agent Registry 拥有固定配置与启用状态；Artifact Store 隐藏条件写、实际字节校验与对象错误。三个 Module 的 Implementation 深化，不新增顶层业务 Module、不修改 M0 ExecutionBackend/PatchEvaluator Interface。原 `connection.py` 的错误转换只认识身份错误，以兼容默认行为的内部参数化复用短事务，使目录故障不会被翻译为身份故障；不扩大为通用事务框架。

#### 双存储一致性与公开边界

1. 只从已校验的固定源加载 TaskBundle，核对公开字段与原始 JSON 的 SHA-256/大小；保留现有公开/隐藏字段分离，不自行解析第二套 SWE-Gym 字段。
2. 在私有 MinIO bucket 以内容寻址键条件写入，已存在时读取并验证实际字节一致；不能使用“先 HEAD 再普通 PUT”假装防并发覆盖，不能只信 ETag 或自报元数据。
3. 对象写入并验证完成后，以 PostgreSQL 短事务同时发布任务标准字段和制品索引；同身份同内容返回原记录，内容漂移明确冲突。对象 I/O 不占用数据库事务锁。
4. MinIO 先失败则不发布数据库；数据库失败或提交结果不确定时，不立即删除内容寻址对象，避免删除其他并发请求已引用的快照。未引用对象不经普通 API 暴露，留待带保护时间与数据库引用核对的本机维护处理；本任务不启动后台删除。
5. 普通查询仅用显式公开 DTO，原始快照不设 HTTP 下载入口，MinIO 凭据/对象管理入口不进浏览器。正式读取必须能检查对象缺失/内容不一致并返回安全错误；对象存储失效不能以空文件或半登记任务冒充成功。

#### 实际实施文件树

```text
apps/backend/src/eval_platform/
├─ domain/catalog.py                         # 新增：目录记录与安全错误；复用 task/agent/result 值
├─ application/
│  ├─ task_catalog.py / agent_registry.py    # 新增：授权、登记/读取、不变性用例
│  └─ ports/
│     ├─ task_source.py                      # 新增：固定任务输入；SWEGymTaskSource 已有 load 实现
│     ├─ repositories.py                     # 新增：目录发布/查询、固定配置持久化
│     └─ artifacts.py                        # 新增：不可变写入与验证读取，不暴露 SDK
├─ adapters/
│  ├─ persistence/connection.py              # 修改：复用短事务，保留身份默认错误行为
│  ├─ persistence/catalog/                  # 新子目录：避免既有 6 文件直接目录膨胀
│  │  ├─ __init__.py / schema.sql           # 新增：显式目录升级入口与三表约束
│  │  └─ tasks.py / agents.py               # 新增：任务+制品索引短事务，配置登记/禁用
│  └─ artifacts/                            # 既有规划的新目录：不同于 M0 本机证据校验
│     ├─ __init__.py / config.py            # 新增：包入口和仅后端可见的 MinIO 连接配置
│     └─ minio.py                           # 新增：公开 S3 客户端、条件写和校验
└─ delivery/
   ├─ catalog.py / catalog_presets.py        # 新增：显式本机初始化、服务端受控固定种子
   └─ http/
      ├─ app.py / errors.py                 # 修改：组装目录与安全错误，沿用身份/Origin
      ├─ catalog_schemas.py                 # 新增：公开白名单、受控登记请求
      └─ routes/catalog.py                  # 新增：四查询与三管理端点的翻译
apps/backend/tests/
├─ catalog/                                 # 新目录：既有身份/成员目录各已 8 文件
│  ├─ __init__.py / conftest.py / memory.py  # 合成外部存储、固定任务与共享夹具
│  ├─ test_http.py / test_security.py        # 调用者可见流程、权限、隐藏字段和错误
│  ├─ test_postgres.py / test_minio.py / test_consistency.py # 真实持久化、不可变与双侧故障
│  └─ runtime/                               # 测试辅助子目录，不新增顶层 infra
│     ├─ Dockerfile.minio / Dockerfile.tests  # 固定源码构建 MinIO、准备 Linux 测试依赖
│     └─ verify.ps1                         # 精确创建/核对/清理专属容器，无全局 prune
└─ identity/browser_server.py                # 修改：仅内部浏览器测试接入目录用例
apps/backend/pyproject.toml / uv.lock         # 修改：锁定公开 S3 客户端、打包目录 SQL
apps/backend/.dockerignore                   # 新增：构建上下文代码/测试/锁白名单
apps/web/src/
├─ features/catalog/                        # 新目录：目录浏览/详情与所有者受控登记
│  └─ tasks.tsx / agents.tsx                # 通过 HTTP，不直连 PostgreSQL/MinIO
├─ features/identity/session.tsx             # 修改：登录后接通目录，不代替后端权限
└─ lib/api-client.ts / contracts.ts / catalog-client.ts # 复用唯一 HTTP 请求入口与安全类型
apps/web/tests/catalog.spec.ts               # 新增：真实浏览器目录和协作者回归
apps/web/tests/run-browser-tests.mjs          # 新增：每个用例文件使用独立合成后端
apps/web/package.json                        # 修改：默认浏览器命令接入上述编排
```

上述树已实际落地，包含构建上下文白名单与浏览器编排。开工计数：domain 6、application 3、ports 4、persistence 6、HTTP 7、routes 3、identity/membership 测试各 8、Web lib 3。按上述布局，新增直接目录均不超过 8 文件、动态源码目标不超过 200 行；不得先越限再用事后拆分解释。文档在上方已有事实源同步，超出此范围的新结构仍须确认。

#### 分步验收

- HTTP 红绿切片：查询/受控登记 → 原始快照与身份不变 → 配置禁用/秘密隔离 → 空列表/筛选/安全错误；合成 Adapter 不替代应用授权和规则。
- 专属 PostgreSQL：任务和制品索引一起提交/回滚、重复/并发登记、禁用历史及初始化升级；已获任务 02–04 临时 PG 授权，仍不连接现有库。
- 已完成专属 MinIO：原子拒绝覆盖、同内容重入、GET 字节校验、丢对象及双存储单侧故障；SDK 流失败另作受控边界检查。采用下节不发布端口方案和合成数据，资源已精确清理。
- 浏览器：所有者受控登记、协作者列表/筛选/详情、禁用可见；复跑身份/成员回归。静态、默认无模型测试、文档/树检查后，按固定提交做 Standards/Spec 双轴评审，修复及本地提交后才进入 04。

#### 专属对象存储验证环境

2026-09-12 已按本节授权完成构建输入核验、隔离验证与清理；结果见自验证情况。

- MinIO 的固定 CE 源码测试候选见[依赖总表第 2.3 节](../dependencies/DEPENDENCIES.md#23-任务-03-对象存储依赖复核)，包括最后 release 后的条件写修复，但不关闭官方已知安全风险。本次仅使用合成数据验证 Adapter，不能据此批准 M1 长期或远程运行。
- 已记录的本机 Docker 为 27.5.1；官方提示低于 28.0.0 的回环发布端口可能从同一二层网络到达。实际本机可达性尚未验证，不能把一般性警告当作本机漏洞已复现；也不能只靠 `-p 127.0.0.1` 声称隔离。出处由本机 Docker 文档维护。
- 实际使用三个专属容器：MinIO 以 `--network none` 建立只有回环的网络命名空间；专属 PostgreSQL 与 Linux 测试器共享该空间，只经其中的 127.0.0.1 交互。全部不发布宿主端口，不使用 host 网络、Docker socket、宿主敏感目录、真实账号或凭据；不修改代理、Docker/WSL、防火墙或现有容器/卷/网络。
- 构建阶段需要联网获取经核验的官方 MinIO 固定源码、官方 Go/Python 构建镜像及锁定依赖；执行前分别固定身份与摘要，不能直接用 latest。构建与无网络运行分开，限制构建资源并核对磁盘余量，不能给运行中的测试服务打开联网。
- 完成/失败均核验完整容器 ID/标签再删除，仅清理专属测试数据；保留原有镜像与资源，不用全局 prune。构建产物和可复用缓存的实际保留范围另记，不把“容器删除”冒称所有下载缓存消失。
- 技术前提若不能满足，停止该验证并报告，不静默退回宿主发布端口或升级机器。此环境已完成本行动限定验证，未批准长期部署。
