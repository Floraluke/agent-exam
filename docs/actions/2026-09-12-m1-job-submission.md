# M1 任务 04：提交并冻结评测 Job

## 状态与情况说明

- 状态：Completed。用户已明确批准本行动记录的精确规模/最多三个配置、初始资源模板、访问范围、四张规划内表、必要 Interface 与子目录；旧 Blocked 只是上一窗口尚未回填的快照。任务 04 实现检查点为 `5b585b4`，独立双轴评审的有效问题已修复、复核并完成最终分层验收；没有进入任务 05。
- 用户已授权依次实施、评审和修复任务 02–04；任务 03 已在 `3302084` 完成收尾。已有任务是每个行动各自一份记录，本行动不复用[目录行动](2026-09-12-m1-task-agent-catalog.md)。
- 对应[任务 04](../../.scratch/m1-platform/issues/04-job-submission.md)。现有身份、邀请、Task Catalog、Agent Registry 和存储 Adapter 已复用；Job Submission、四张提交子集表与 Web/HTTP 入口现已实现。它们只保存等待批准的持久 Job，仍不能把 M0 本机执行请求或任务 05 的批准/执行能力混入本轮。
- HTTP 为主要验收入口、少量浏览器接线、真实临时 PostgreSQL 事务验证已获确认。模型、Harbor 执行、真实凭据、长期数据库、远程部署、机器设置和推送不在本行动范围。
- 本轮按下方已确认方案直接实施；临时 PG、合成验证、精确清理和关键节点本地提交沿用既有授权，不重复询问。

## 实施措施

1. 已核对[数据模型](../architecture/DATA_MODEL.md#44-evaluation_jobs)、[HTTP Job 契约](../interfaces/HTTP_API.md#7-job-api)、[模块契约](../architecture/MODULE_CONTRACTS.md#64-job-submission)与已有代码、目录计数。
2. 沿已确认的 HTTP/真实存储 Interface 逐片红绿实现：受控选项与提交校验 → 原子 Job/Run 快照 → 幂等/并发 → 刷新查询与浏览器。
3. 同步架构实际文件树、数据表/约束、HTTP 输入输出与错误，不预建批准/执行/报告的空壳；关键实现检查点本地提交，固定以本行动开工前 `3302084` 为评审基准。
4. 运行静态、完整默认测试、真实 PG 集成和少量浏览器；按 code-review 进行独立 Standards/Spec 评审并修复，最后勾选任务单。任务 04 结束即停止，不自动进入任务 05。

## 已确认的最小方案

### 产品行为与固定预置

- 批次规模沿现有候选锁定：demo 为 1–3 题、quick 为 5 题、standard 为 10–20 题；每批最多 3 个启用的 Codex 配置，每个组合只尝试一次，最大 60 条 Run。题目与配置去重后计数；空选择、规模不符、非法覆盖在创建前拒绝。
- 当前正式受控种子仍只有任务 03 的单题/单配置；较大矩阵只用独立合成数据验证。页面不能把未登记任务补成假正式数据，也不因有规模选项就宣称已有 20 道可执行题。
- 第一份只读限制预置 `default-single-host-v1` 沿用 M0 已运行的单题上限：Agent 900 秒、1 CPU、4096 MiB 内存、8192 MiB storage 配置；独立判卷 300 秒、1 CPU、4096 MiB；单并发、零自动重试。PID、patch/日志/原始制品阈值复用现有受控值；不让用户自填资源。历史出处见[真实单题行动](2026-09-05-m0-codex-harbor-implementation.md#2026-09-08第四次授权的固定真实单题)。
- 以上只是提交时冻结的初始上限，不是多题性能承诺或磁盘硬限额全部生效的证明；真正执行前仍按[资源规则](../interfaces/HARBOR_EXECUTION.md#12-单机资源规则)核验实际峰值和限制执行能力。本任务不启动执行来验证它。
- 限制、闭卷网络和工具策略均为服务端版本化预置；前端只选 ID。暂不新增限制模板表或管理页面，Agent 的可空默认限制引用保持为空，Job 明确携带所选预置 ID 与快照；不为配置目录虚造外键绑定。
- 协作者只能查询自己提交的 Job，所有者可查全部；他人不可见记录使用 404。应用身份仍来自可信会话，内部测试范围只由服务端测试装配决定，客户端不能用标记绕过批准。

### 必要结构与复用理由

| 新增内容 | 最小职责 | 为什么现有能力不能承载 |
|---|---|---|
| 四张规划内表：evaluation_jobs、evaluation_runs、job_state_events、run_state_events | 保存待批准批次、所有组合的冻结快照与创建事件 | 目录记录描述“可选什么”，不描述“谁在何时提交了哪一批”；账号/邀请不能承担评测生命周期 |
| JobRepository 的原子创建/幂等重入/查询 Interface | 一次事务处理 Job、Run、创建事件、幂等及并发登记状态复核 | 单条 Task/Agent Repository 没有跨记录批次事务；复用现有 connection 短事务实现，生产 PG 与合成 Adapter 满足同一 Interface |
| 原规划 POST /jobs、GET /jobs、GET /jobs/{id}；补 GET /job-options | 提交、刷新及获取服务端规模/限制预置 | 现有任务/配置列表不包含全局组合规则；由同一服务端规则生成选项，避免前后端各维护一套数字 |
| 下方 jobs 子目录 | 分开领域值、持久化、HTTP DTO、页面和测试职责 | HTTP 直接目录已有 8 文件，已有身份/成员/目录测试目录均达 8；不能继续平铺或先越限再拆分 |

创建过程复用 Task Catalog 的完整性读取及 Agent Registry；对象 I/O 不放进数据库事务。创建事务内复核已登记身份和配置启用状态，冻结任务/配置/框架版本/策略/限制，并同时插入全部 Run 和初始事件。幂等范围为可信提交者 + 哈希后的键，相同规范化正文返回原 Job，不同正文冲突；重复请求不能受随后配置禁用影响而创建第二批。

Job 初始为 AWAITING_OWNER_APPROVAL，Run 初始为 PENDING。HTTP 不调用 ExecutionBackend、PatchEvaluator、凭据解析或模型。显式本机升级建表，启动 API 不迁移；只建立当前提交所需字段，不提前实现 Worker 领取、批准/拒绝、取消、执行结果或 Judge 表。

设计模式仍为 ports/Adapter、Repository 和 Composition Root：Job Submission 应用只依赖小型抽象，PostgreSQL Adapter 隐藏 SQL/事务，交付层组装；不新增顶层业务 Module、外部框架依赖或独立服务，不改 M0 执行/判卷 Interface。

## 需要修改的文件树

下列结构已按批准方案实际落地；每文件目标不超过 200 行，每层直接文件不超过 8。没有新增批准、Worker、执行或报告空壳。

```text
apps/backend/src/eval_platform/
├─ domain/jobs/                             # 已新增：批次不可变值及提交策略，不依赖框架
│  ├─ __init__.py                           # 包入口
│  ├─ models.py                             # Job/Run/快照值与安全错误
│  └─ policy.py                             # 固定规模、限制、闭卷策略与正文规范化
├─ application/job_submission.py            # 已新增：授权、校验、提交/查询用例
├─ application/ports/repositories.py        # 已修改：增加最小 JobRepository Interface
├─ adapters/persistence/jobs/               # 已新增：PostgreSQL 批次 Adapter
│  ├─ __init__.py / schema.sql              # 显式升级与四表最小约束
│  ├─ records.py                           # 冻结值序列化/读出完整性
│  ├─ repository.py                        # 幂等创建与查询的 Repository
│  └─ publication.py                       # 同一事务插入组合/事件并复核目录状态
└─ delivery/
   ├─ jobs.py / job_presets.py              # 已新增：本机升级/组装和可信配置，非模型凭据
   └─ http/
      ├─ app.py / errors.py                 # 已修改：组装提交用例和安全错误
      └─ routes/jobs/                       # 已新增：避免 HTTP 根目录超过 8 文件
         ├─ __init__.py / routes.py         # 路由入口与 HTTP 翻译
         └─ schemas.py                     # 受控选择与安全输出 DTO
apps/backend/tests/jobs/                    # 已新增：7 个直接文件
├─ __init__.py / conftest.py / memory.py     # 合成外部存储、可信身份与夹具
├─ test_http.py / test_security.py           # 提交/刷新、权限和任意输入拒绝
├─ test_postgres.py / test_concurrency.py    # 真实持久化、回滚、幂等和并发
└─ runtime/                                 # 已新增：Dockerfile.tests/verify.ps1，隔离 PG 与精确清理
apps/backend/tests/identity/browser_server.py # 已修改：仅内部浏览器装配提交用例
apps/backend/pyproject.toml                 # 已修改：打包新 SQL/本机升级命令，不新增依赖
apps/web/src/
├─ features/jobs/                           # 已新增：通过 HTTP 提交和刷新
│  ├─ submit.tsx / controls.tsx             # 受控选择、组合数与确认界面
│  └─ details.tsx                          # 冻结内容与等待批准状态
├─ features/identity/session.tsx             # 已修改：登录后接入页面
└─ lib/job-client.ts                        # 已新增：复用唯一 HTTP request，运行时校验 DTO
apps/web/tests/jobs.spec.ts                 # 已新增：真实浏览器提交→等待批准→刷新
docs/actions/2026-09-12-m1-job-submission.md  # 已新增：本任务独立行动
.scratch/m1-platform/issues/04-job-submission.md # 已修改：必要待决项，不预勾验收
HANDOFF.md                                  # 已修改：恢复入口与授权边界
docs/architecture/{ARCHITECTURE,DATA_MODEL}.md # 当前阶段、实际树与表的权威同步
docs/architecture/MODULE_CONTRACTS.md         # 实际 Interface 与不变量
docs/interfaces/HTTP_API.md                  # 实际 schema/错误/预置，只维护一处
```

## 自验证方式与成功标准

- 开工时只完成文档链接/锚点/围栏、diff 与规划目录计数；任务 04 所有验收项保持未勾，实施后逐项回填。
- 实施时 HTTP 检查：合法组合和安全 DTO、所有非法/禁用/越权/超限选择、幂等重复/冲突、刷新读取、内部测试不能绕过批准；调用执行或凭据路径应使测试失败。
- 真实 PG 检查：重建应用后快照不变、全部组合和初始事件一起提交、注入写入故障整笔回滚、并发同键只生成一批、禁用与提交竞态结果一致。使用已批准合成临时库；断言通过公共 HTTP/Repository，不用内部函数调用次数冒充行为验证。
- 浏览器少量检查：登录后选择已登记项、组合数、提交等待批准、刷新恢复，以及协作者/所有者可见性；不做假进度或假成绩。
- 全量默认后端、Ruff/mypy、Web typecheck/build、浏览器和文档检查均记录真实输出；未启用的重型/外部检查如实记跳过。双轴评审和修复后才完成任务并本地提交；不推送。

## 自验证情况

- 2026-09-12 TDD 首个红灯：运行 `.venv\\Scripts\\python.exe -m pytest tests/jobs/test_http.py -q`，收集阶段因 `eval_platform.application.job_submission` 尚不存在而失败（exit 1）。该失败符合先固定公开 HTTP 行为再补实现的预期，不记为通过。
- 首片绿色：同一 HTTP 用例在补齐受控选项、冻结提交、内存 Repository 与查询 DTO 后为 `2 passed`（2 个上游弃用警告）；响应确认 `AWAITING_OWNER_APPROVAL`、`internal_test`、初始 Job/Run 事件及不返回测试凭据引用。
- 第二片红绿：安全/范围用例首次为 `4 passed, 1 failed`，失败点是 Job 列表尚未拒绝未知 query；补上与既有目录一致的未知/重复 query 检查后，`tests/jobs` 为 `7 passed`（2 个上游弃用警告）。已覆盖任意字段/资源覆盖拒绝、空/未登记/禁用/规模错误、去重、3 配置/60 Run 上限、禁用后幂等重放、同键异文冲突、协作者 404 隔离和 owner 全局可见。
- 第二片局部 mypy 通过；Ruff 首跑仅发现测试 import/行长问题，修正后局部 Ruff 通过。组合命令的最终进程码来自末项 mypy，故不把中途 Ruff 失败冒称整组首跑通过。
- 真实 PG 红灯：新增公开 Repository/HTTP 的恢复、整批回滚、同键并发和提交/禁用竞态测试后运行，收集阶段因 `eval_platform.adapters.persistence.jobs` 尚不存在而 2 errors（exit 1）；尚未启动或连接任何数据库。
- 真实 PG 绿色：新增四表 SQL、显式 `agentexam-jobs init-db`、PostgreSQL Repository 的幂等发布/目录行复核/读出完整性和正式 HTTP 组装后，默认门禁运行 `7 passed, 4 skipped`；4 项跳过均为未设置专属 PG 开关，不能计为真实数据库通过。
- 经既有授权运行 `tests/jobs/runtime/verify.ps1`：先核对任务 03 测试基镜像 `sha256:2162edef...cd24` 与固定 PostgreSQL 镜像 `sha256:5cce759a...a6b6`，使用 `--network=none` 无网络构建当前测试镜像 `sha256:ed201d9e...bbba`。PostgreSQL 容器为 `network=none`，测试器仅共享其网络命名空间；两者均无发布端口、无宿主挂载、只读根、受限 CPU/内存/PID，数据仅在 tmpfs。实际结果 `11 passed`（2 个上游弃用警告，6.36s）；恢复、回滚、并发同键和提交/禁用竞态均通过。
- 清理证据：脚本只按本次随机标签和精确容器 ID 删除测试器 `0a108f1e...e2ebf` 与 PostgreSQL `3d47e34e...708e80`，末尾复核无同标签容器；tmpfs 数据已删除，本地镜像/构建缓存按授权保留。未连接现有数据库、未发布端口、未更改机器设置。
- 浏览器红灯取证：首次普通沙箱运行因无权创建既有结果目录而未到页面；提升后未设置项目缓存路径，Playwright 找不到机器级浏览器，未下载任何内容。按依赖文档复用只读核实存在的 `runtime/tools/playwright/chromium_headless_shell-1243` 后，真实 Next→FastAPI 测试到达页面并在 30.1s 超时：缺少“提交评测/刷新可提交选项”入口，符合实现前红灯。前两次异常遗留的本次 3100/8875 测试服务经命令行核实后只终止对应 PID；第三次由 Playwright 正常收束。
- 浏览器绿色：沿唯一 `request` 客户端补齐服务端选项读取、已登记任务/启用配置选择、组合数、受控提交和详情恢复；合成浏览器后端只在既有门禁下装配 `internal_test` JobRepository。`npm run typecheck` 通过；复用项目 Playwright 缓存运行 `jobs.spec.ts` 为 `1 passed`（19.0s），实际验证登记→选择→组合数 1→提交等待批准→整页重载从后端列表恢复→显式刷新，页面不展示假成绩。
- 第一轮完整默认后端为 `282 passed, 51 skipped, 2 warnings`（27.09s）；跳过项包括需显式门禁的旧 Docker/真实 PG/MinIO/M0 集成及 4 项 Job PG，用上方独立专属 PG 的 11 项通过补充任务 04 数据库证据，不把其余跳过冒称通过。`mypy src` 为 87 个源文件无问题，Ruff check 通过；首次 format check 指出 5 个新增文件需格式化，执行 Ruff 格式化后 check 与 format check 均通过（150 文件）。
- 完整浏览器回归按测试文件隔离启动后端，累计 `12 passed`：目录 2、身份安全 6、登录 2、Job 1、成员 1；各组 8.1–13.9s，测试进程正常收束。Web typecheck 再次通过。首次普通沙箱 build 仅因 Next 无权创建本机配置临时文件而失败；禁用遥测并提升权限后 `next build` 编译、类型检查、4 个静态页面生成及构建 trace 全部通过，首页 7.88 kB、首载 110 kB。该构建不是部署。
- 首次局部 Ruff 发现 1 处超长行与 2 处 import 顺序问题，已修正后局部 Ruff 通过；首次局部 mypy 发现 DTO 的四处显式转换/返回类型问题，已修正，待重跑。文件行数实查：本片 6 个主要 Python 文件为 61–193 行，均未超过 200 行。
- 开工前文档核对历史记录：当时 12 份 Markdown、259 条本地链接、84 处锚点、围栏/空白与 `git diff --check` 通过；首次发现历史单题引用锚点不匹配，按真实标题修正后通过。该时点任务 04 尚未实现、九项未勾且标签为 needs-info，现状已由本节顶部和任务单后续记录取代。
- 开工前目录规划历史记录：任务 03 的 36 个动态代码文件均不超过 200 行，检查的 9 个直接目录均不超过 8 文件；任务 04 候选布局避开了满额 HTTP/测试目录。实际落地结构与最新指标见上方文件树和最终复验记录。
- 本轮新行动与任务单已精确本地提交为 `3274e18`，暂存范围核对与暂存 diff 通过、提交后暂存区为空；架构、数据和 HANDOFF 等混合旧文档已同步于工作区，不整批暂存，不覆盖原有改动。
- 当前：任务 04 已实现并完成首轮分层验证、固定基准双轴评审、评审修复与最终全量复验；任务 03 的通过证据只作已完成依赖，不计为任务 04 通过。
- 2026-09-12 恢复窗口已回填用户批准：精确规模/资源预置、访问范围、四表和新 Interface/子目录均已确认；当前无方案授权阻塞。既有临时 PG 与本地提交授权不重复申请。

## 独立双轴评审与修复

- 固定基准 `3302084`，评审差异包含草案 `3274e18` 与实现 `5b585b4`；暂存区为空。Standards 与 Spec 子代理分别只读检查提交差异，并按恢复要求同时读取现场未提交的架构、数据、模块和 HTTP 权威增量。
- Standards 报告 3 项：行动当前态与历史快照冲突、数据/HTTP 首页状态与正文冲突、Web `jobOptions` 只校验数组外壳后强制转型。Spec 报告 3 项，其中权威状态冲突重合，另有页面刷新按随机 UUID 首项恢复、非 UUID 目录 ID 可能进入真实 PG 并误报 503。十二类坏味道基线未发现需报告项，无新增业务或架构授权事项。
- TDD 红灯：新增 HTTP 非 UUID 用例得到 404 而非 422（`1 failed, 2 passed`）；新增浏览器精确 Job URL 和嵌套选项畸形用例均失败（URL 参数为 null，错误提示缺失）。
- 修复：Job 创建 DTO 使用 UUID 列表并在进入应用/Repository 前规范为字符串；页面用 URL `job` 参数保存并按精确 ID 从详情端点恢复；`jobOptions` 对批次、限制模板和全局上限逐字段运行时校验；同步四份权威文档当前态。
- 局部绿灯：HTTP/安全 `9 passed`，Web typecheck 通过；浏览器第一次修复运行中精确恢复已通过，畸形 DTO 行为也已正确报错但测试选择器与 Next 自带 alert 重名，收紧为页面 `p[role=alert]` 后 `2 passed`。
- 原 Standards 评审者复核三项均 resolved，原 Spec 评审者复核刷新身份、非法 ID、权威状态三项均 resolved；两者均未发现修复直接引入的阻断问题。复核为静态只读，测试证据由下方独立命令提供。

## 最终自验证与收尾

- 专属真实 PostgreSQL：重建无网络测试镜像 `sha256:291e643a...aaf3d`，固定 PG 镜像仍为 `sha256:5cce759a...a6b6`；无发布端口、无宿主挂载，PG 为 `network=none`，测试器只共享其网络命名空间。结果 `14 passed, 2 warnings`（7.90s），覆盖显式迁移、恢复、原子回滚、并发幂等、禁用竞态、快照稳定和非 UUID 422。精确删除测试器 `70328c1e...94ef`、PG `d4025b50...7e45` 及 tmpfs 数据，标签复核无残留；镜像/构建缓存按授权保留。
- 默认后端全量：`283 passed, 52 skipped, 2 warnings`（26.30s）。52 个跳过均为需显式开关的旧 PostgreSQL/MinIO/Docker/M0 外部检查，其中本任务的 5 个默认 PG 跳过已由上方专属真实 PG 覆盖；未把其余跳过冒称通过。两个 warning 是 FastAPI/Starlette 测试客户端的上游弃用提示。
- 静态与构建：Ruff check 通过，150 个 Python 文件 format check 通过，mypy 检查 87 个源文件无问题；Web typecheck 通过，Next 生产构建完成 4 个静态页面，首页 8.25 kB、首载 111 kB。构建仅生成本地产物，没有部署。
- 浏览器全量：复用项目现有 Playwright 缓存，无下载；累计 `13 passed`（目录 2、身份安全 6、登录 2、Job 2、成员 1）。Job 覆盖选择/计数/提交等待批准、URL 精确身份、整页重载从后端恢复、显式刷新和畸形嵌套选项失败关闭；各临时服务正常收束，3100/8875 无监听残留。
- 文档与结构：本任务 6 份规格/行动/架构/接口 Markdown 的 104 个本地链接均可解析、代码围栏成对，`git diff --check` 通过；动态代码均不超过 200 行，新增直接目录文件数为 3/5/3/7/3，均不超过 8。任务单九项已逐项勾选，权威架构、数据、模块和 HTTP 当前态一致。
- 收束残留检查：首个组合命令已打印文档/结构成功结果，但末项 `Get-NetTCPConnection` 在没有匹配项时令总进程码为 1，因此不把该组合码冒称全绿；改为显式数组判定后输出 `No listeners on 3100 or 8875`、exit 0。专属 Docker 标签的提升权限只读复核无输出，确认没有任务 04 容器残留。
- 评审修复检查点 `e35d4cd`：提交前暂存区逐项核对为 9 个任务 04 文件，共 143 insertions/21 deletions；未暂存 HANDOFF、混合权威文档、旧行动、缓存或其他未跟踪文件，未推送。实现检查点仍为 `5b585b4`。
- 遗留边界：任务 05 的批准/拒绝/取消/领取/执行路由仍不存在；本任务未读取真实模型凭据、未运行模型或 Harbor、未连接既有数据库、未部署长期服务，也未更改 Docker/WSL/代理/防火墙或推送。M0 完整验收、M1/MVP 后续任务和 52 个需独立开关的非任务 04 外部检查保持原状态。
