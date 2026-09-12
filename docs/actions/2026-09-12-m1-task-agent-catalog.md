# M1 任务 03：任务与 Codex 配置目录

## 状态与情况说明

- 状态：Blocked（最小接入草案已形成，等待新增结构及专属隔离验证范围批准；不是业务运行故障）。用户已明确继续使用 MinIO，不再询问是否换产品。任务 02 已完成，任务 03 尚未修改业务实现；源码测试候选、维护风险与适用边界见依赖总表第 2.3 节。
- 本行动对应[任务 03](../../.scratch/m1-platform/issues/03-task-agent-catalog.md)；与成员行动分开记录，之后同一任务的计划、实施和验证继续更新本文件。
- 已确认复用现有 Task Catalog、Agent Registry、Artifact Store 的规划职责，不新增顶层业务模块。现有账号/会话/邀请表不能承载固定任务、配置身份及原始快照索引；现有 SWE-Gym 适配器只从已校验本机数据读取任务，不是持久化目录。
- MinIO 上游维护/发行事实仍只在[依赖总表第 2.3 节](../dependencies/DEPENDENCIES.md#23-任务-03-对象存储依赖复核)维护。用户保留原产品与分层，不等于已确定具体旧版本、改用 AIStor 或批准安装；不会把本地文件替身当作真实对象存储验收。
- 任务 02–04 专属临时 PostgreSQL 已获许可，不重复索取。新对象存储的下载、构建、容器、账号或许可证操作尚未许可，未执行。业务新接口/表/目录仍需说明并确认；没有模型、邮件、真实用户、长期数据库、机器设置或推送操作。

## 实施措施

1. 已核对既有 task/agent/result 领域对象、SWE-Gym 适配器、目录任务、数据模型和 Artifact Store 契约。保留原始任务与 Agent 可见任务分离，不给普通 HTTP 暴露参考答案。
2. 已只读核对上游对象存储维护/发行事实及本机镜像可用性；先将发现和实际暂停点落盘，不先安装或替换产品。
3. 已收到“我们还是选择 miniO”：同步原架构继续采用 MinIO，关闭更换产品的提案与旧方向等待。后续只读核对 MinIO 的可固定版本、制品来源和适用部署边界，先说明具体风险，不重新询问是否换其他产品。
4. 提交最小结构草案：复用已有模块、深化实现，列出确需的 ports、数据库表和子目录及职责理由；同时明确固定任务可登记/可执行范围，再经批准进入 HTTP 红绿切片。当前 M0 仅登记固定单题环境，不能直接宣称批量题目都有可用镜像。
5. 实施阶段才执行 HTTP/少量浏览器、真实 PostgreSQL/获批对象存储单侧失败测试和双轴评审。任务 03 完成后才进入依赖它的任务 04，不先构造未确认的配置/提交契约。

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
   └─ architecture/ARCHITECTURE.md                     # 明确保留 MinIO 与原有分层
```

未新增生产模块、Interface、SQL 表或代码目录。沿用 ports/Adapter 的依赖方向：应用依赖抽象边界，存储产品由适配实现承接；目前只是规划定位，不声称已有正式 Artifact Store port。

## 自验证方式与成功标准

- 对照实际源码、任务验收和官方来源，明确已实现/规划/待确认，不用产品宣传代替维护状态或实验结果。
- 本轮文档的本地链接、锚点、代码围栏以及 `git diff --check` 应通过；任务 03 验收项保持未勾，任务 02 已完成不回退。
- Git 仅提交本行动、任务 03 及本次独立调研记录；已有混合文档增量保留工作区，不整批暂存。业务无变更，不因文档更新重跑模型或扩张外部验证。
- 后续实施成功标准仍按任务 03，包含原始快照与元数据发布一致、秘密隔离及真实双存储故障测试；当前不计为已运行。

## 自验证情况

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

### 任务 03 最小接入草案（候选，尚未批准/实施）

#### 能力与范围

- 目录能保存和分页查询多条固定任务/配置；首个正式种子仅采用现有已核验的 SWE-Gym Lite 单题和已确认 Codex 版本/模型/推理强度，不创建模拟正式条目、不下载更多任务镜像。更多真实任务必须先固定来源及环境；不把当前单题已核验等同整个题库可执行。
- 登录用户通过既有规划的四个查询端点查看任务/配置列表及详情；所有者通过受控登记入口选服务端预置身份，不提交任意 JSON、镜像、命令、URL 或宿主路径。配置可禁用且历史身份保留；重新登记同一禁用配置不隐式重新启用。
- 暂不实现 Job、批准、队列、报告/制品下载、全量题库同步或制品定时清理。限制模板的精确数值由任务 04 确认；任务 03 不伪造已存在的模板，未绑定时公开默认引用显式为空。

#### 必要新增与复用理由

| 项目 | 候选最小实现 | 为什么不能直接复用身份能力 |
|---|---|---|
| PostgreSQL 表 | `evaluation_tasks`、`agent_configurations`、`artifact_records`，只落任务 03 所需字段/关联，不预建 Job/Run/P2 表 | 账号/会话/邀请无法表达不可变任务身份、配置指纹及对象索引；三者均为已有数据模型规划的实体 |
| 应用与存储 Interface | TaskSource、TaskRepository、AgentConfigurationRepository、ArtifactStore；沿用规划的 `task_source.py`、`repositories.py`、`artifacts.py` 三个 port 文件 | 现有 `load()` 可作为 TaskSource 实现复用，但没有持久目录或对象存储 Interface；生产 PostgreSQL/MinIO 与合成测试 Adapter 分别满足同一接口，应用不见 SQL、SDK 或连接 |
| HTTP | 实现原规划的 GET tasks/详情、GET agent-configurations/详情；补所有者 POST tasks/register、POST agent-configurations、POST agent-configurations/{id}/disable | 现有身份/邀请端点不承担目录登记；正文仅接受受控预置 ID，复用当前 Cookie、Origin、可信身份和统一错误 |
| 初始化 | 独立本机目录结构升级命令，显式创建上述三表；启动 API 不建表/同步，重复执行失败且不覆盖数据 | 保持现有身份初始化行为，旧应用库需要明确升级入口，不能借一次登录隐式写结构 |
| 外部依赖 | MinIO Adapter 使用支持原子条件写的公开 S3 Python 客户端；具体锁定版本由官方接口/兼容核查确定 | 现有依赖没有 S3 客户端；不手写签名或依赖 SDK 私有方法，也不因使用 S3 协议而更换 MinIO 产品 |

Task Catalog 拥有登记/读取与发布一致性；Agent Registry 拥有固定配置与启用状态；Artifact Store 隐藏条件写、实际字节校验与对象错误。三个 Module 的 Implementation 深化，不新增顶层业务 Module、不修改 M0 ExecutionBackend/PatchEvaluator Interface。原 `connection.py` 的错误转换只认识身份错误，候选以兼容默认行为的内部参数化复用短事务，使目录故障不会被翻译为身份故障；不扩大为通用事务框架。

#### 双存储一致性与公开边界

1. 只从已校验的固定源加载 TaskBundle，核对公开字段与原始 JSON 的 SHA-256/大小；保留现有公开/隐藏字段分离，不自行解析第二套 SWE-Gym 字段。
2. 在私有 MinIO bucket 以内容寻址键条件写入，已存在时读取并验证实际字节一致；不能使用“先 HEAD 再普通 PUT”假装防并发覆盖，不能只信 ETag 或自报元数据。
3. 对象写入并验证完成后，以 PostgreSQL 短事务同时发布任务标准字段和制品索引；同身份同内容返回原记录，内容漂移明确冲突。对象 I/O 不占用数据库事务锁。
4. MinIO 先失败则不发布数据库；数据库失败或提交结果不确定时，不立即删除内容寻址对象，避免删除其他并发请求已引用的快照。未引用对象不经普通 API 暴露，留待带保护时间与数据库引用核对的本机维护处理；本任务不启动后台删除。
5. 普通查询仅用显式公开 DTO，原始快照不设 HTTP 下载入口，MinIO 凭据/对象管理入口不进浏览器。正式读取必须能检查对象缺失/内容不一致并返回安全错误；对象存储失效不能以空文件或半登记任务冒充成功。

#### 待批准的实施文件树

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
│  └─ runtime/                               # 候选测试辅助子目录，不新增顶层 infra
│     ├─ Dockerfile.minio / Dockerfile.tests  # 固定源码构建 MinIO、准备 Linux 测试依赖
│     └─ verify.ps1                         # 精确创建/核对/清理专属容器，无全局 prune
└─ identity/browser_server.py                # 修改：仅内部浏览器测试接入目录用例
apps/backend/pyproject.toml / uv.lock         # 修改：锁定公开 S3 客户端、打包目录 SQL
apps/web/src/
├─ features/catalog/                        # 新目录：目录浏览/详情与所有者受控登记
│  └─ tasks.tsx / agents.tsx                # 通过 HTTP，不直连 PostgreSQL/MinIO
├─ features/identity/session.tsx             # 修改：登录后接通目录，不代替后端权限
└─ lib/api-client.ts / contracts.ts / catalog-client.ts # 复用唯一 HTTP 请求入口与安全类型
apps/web/tests/catalog.spec.ts               # 新增：真实浏览器目录和协作者回归
```

本树是候选新增/修改范围，不是当前已有文件。当前只读计数：domain 6、application 3、ports 4、persistence 6、HTTP 7、routes 3、identity/membership 测试各 8、Web lib 3。按上述布局，新增直接目录均不超过 8 文件、动态源码目标不超过 200 行；不得先越限再用事后拆分解释。文档仍在本行动列出的已有事实源同步，新增 Interface/表/目录必须先获用户确认。

#### 分步验收

- HTTP 红绿切片：查询/受控登记 → 原始快照与身份不变 → 配置禁用/秘密隔离 → 空列表/筛选/安全错误；合成 Adapter 不替代应用授权和规则。
- 专属 PostgreSQL：任务和制品索引一起提交/回滚、重复/并发登记、禁用历史及初始化升级；已获任务 02–04 临时 PG 授权，仍不连接现有库。
- 获准后专属 MinIO：原子拒绝覆盖、同内容重入、GET 字节校验、丢对象/断流，以及 PostgreSQL/MinIO 单侧故障；合成凭据/数据、资源限额、精确清理。新调研发现旧 Docker 的发布回环端口限制，测试环境改为下节“不发布端口”的候选；尚未启动。
- 浏览器：所有者受控登记、协作者列表/筛选/详情、禁用可见；复跑身份/成员回归。静态、默认无模型测试、文档/树检查后，按固定提交做 Standards/Spec 双轴评审，修复及本地提交后才进入 04。

#### 专属对象存储验证环境（候选，待授权）

- MinIO 的固定 CE 源码测试候选见[依赖总表第 2.3 节](../dependencies/DEPENDENCIES.md#23-任务-03-对象存储依赖复核)，包括最后 release 后的条件写修复，但不关闭官方已知安全风险。本次仅使用合成数据验证 Adapter，不能据此批准 M1 长期或远程运行。
- 已记录的本机 Docker 为 27.5.1；官方提示低于 28.0.0 的回环发布端口可能从同一二层网络到达。实际本机可达性尚未验证，不能把一般性警告当作本机漏洞已复现；也不能只靠 `-p 127.0.0.1` 声称隔离。出处由本机 Docker 文档维护。
- 候选使用三个专属容器：MinIO 以 `--network none` 建立只有回环的网络命名空间；专属 PostgreSQL 与 Linux 测试器共享该空间，只经其中的 127.0.0.1 交互。全部不发布宿主端口，不使用 host 网络、Docker socket、宿主敏感目录、真实账号或凭据；不修改代理、Docker/WSL、防火墙或现有容器/卷/网络。
- 构建阶段需要联网获取经核验的官方 MinIO 固定源码、官方 Go/Python 构建镜像及锁定依赖；执行前分别固定身份与摘要，不能直接用 latest。构建与无网络运行分开，限制构建资源并核对磁盘余量，不能给运行中的测试服务打开联网。
- 完成/失败均核验完整容器 ID/标签再删除，仅清理专属测试数据；保留原有镜像与资源，不用全局 prune。构建产物和可复用缓存的实际保留范围另记，不把“容器删除”冒称所有下载缓存消失。
- 技术前提若不能满足，停止该验证并报告，不静默退回宿主发布端口或升级机器。此环境仍是候选，不是已执行步骤。
