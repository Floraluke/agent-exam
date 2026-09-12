# M1 任务 04：提交并冻结评测 Job

## 状态与情况说明

- 状态：Blocked（待必要方案确认，不是技术故障）。本行动只完成开工核对与候选方案，尚未修改任务 04 业务代码、建表或执行其测试。
- 用户已授权依次实施、评审和修复任务 02–04；任务 03 已在 `3302084` 完成收尾。已有任务是每个行动各自一份记录，本行动不复用[目录行动](2026-09-12-m1-task-agent-catalog.md)。
- 对应[任务 04](../../.scratch/m1-platform/issues/04-job-submission.md)。现有身份、邀请、Task Catalog、Agent Registry 和存储 Adapter 已实现；Job Submission 及批次存储仍只有规划，不能把 M0 的本机执行请求当作持久 Job。
- HTTP 为主要验收入口、少量浏览器接线、真实临时 PostgreSQL 事务验证已获确认。模型、Harbor 执行、真实凭据、长期数据库、远程部署、机器设置和推送不在本行动范围。
- 本轮需确认精确批次/资源预置及必要新增结构；完整方案如下。未经确认不把候选写成已生效规则。

## 实施措施

1. 已核对[数据模型](../architecture/DATA_MODEL.md#44-evaluation_jobs)、[HTTP Job 契约](../interfaces/HTTP_API.md#7-job-api)、[模块契约](../architecture/MODULE_CONTRACTS.md#64-job-submission)与已有代码、目录计数。
2. 用户确认后，沿预先同意的 HTTP/真实存储 Interface 逐片红绿实现：受控选项与提交校验 → 原子 Job/Run 快照 → 幂等/并发 → 刷新查询与浏览器。
3. 同步架构实际文件树、数据表/约束、HTTP 输入输出与错误，不预建批准/执行/报告的空壳；关键实现检查点本地提交，固定以本行动开工前 `3302084` 为评审基准。
4. 运行静态、完整默认测试、真实 PG 集成和少量浏览器；按 code-review 进行独立 Standards/Spec 评审并修复，最后勾选任务单。任务 04 结束即停止，不自动进入任务 05。

## 待确认的最小方案

### 产品行为与固定预置（候选）

- 批次规模沿现有候选锁定：demo 为 1–3 题、quick 为 5 题、standard 为 10–20 题；每批最多 3 个启用的 Codex 配置，每个组合只尝试一次，最大 60 条 Run。题目与配置去重后计数；空选择、规模不符、非法覆盖在创建前拒绝。
- 当前正式受控种子仍只有任务 03 的单题/单配置；较大矩阵只用独立合成数据验证。页面不能把未登记任务补成假正式数据，也不因有规模选项就宣称已有 20 道可执行题。
- 第一份只读限制预置拟沿用 M0 已运行的单题上限：Agent 900 秒、1 CPU、4096 MiB 内存、8192 MiB storage 配置；独立判卷 300 秒、1 CPU、4096 MiB；单并发、零自动重试。PID、patch/日志/原始制品阈值复用现有受控值；不让用户自填资源。历史出处见[真实单题行动](2026-09-05-m0-codex-harbor-implementation.md#2026-09-08第四次授权的固定真实单题)。
- 以上只是提交时冻结的初始上限，不是多题性能承诺或磁盘硬限额全部生效的证明；真正执行前仍按[资源规则](../interfaces/HARBOR_EXECUTION.md#12-单机资源规则)核验实际峰值和限制执行能力。本任务不启动执行来验证它。
- 限制、闭卷网络和工具策略均为服务端版本化预置；前端只选 ID。暂不新增限制模板表或管理页面，Agent 的可空默认限制引用保持为空，Job 明确携带所选预置 ID 与快照；不为配置目录虚造外键绑定。
- 协作者只能查询自己提交的 Job，所有者可查全部；他人不可见记录使用 404。应用身份仍来自可信会话，内部测试范围只由服务端测试装配决定，客户端不能用标记绕过批准。

### 必要结构与复用理由（候选）

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

仅本行动、任务单和权威文档指针已修改；以下代码树全部是候选，等待批准后才创建。每文件目标不超过 200 行，每层直接文件不超过 8。

```text
apps/backend/src/eval_platform/
├─ domain/jobs/                             # 候选新目录：批次不可变值及提交策略，不依赖框架
│  ├─ __init__.py                           # 包入口
│  ├─ models.py                             # Job/Run/快照值与安全错误
│  └─ policy.py                             # 固定规模、限制、闭卷策略与正文规范化
├─ application/job_submission.py            # 候选新增：授权、校验、提交/查询用例
├─ application/ports/repositories.py        # 候选修改：增加最小 JobRepository Interface
├─ adapters/persistence/jobs/               # 候选新目录：PostgreSQL 批次 Adapter
│  ├─ __init__.py / schema.sql              # 显式升级与四表最小约束
│  ├─ records.py                           # 冻结值序列化/读出完整性
│  ├─ repository.py                        # 幂等创建与查询的 Repository
│  └─ publication.py                       # 同一事务插入组合/事件并复核目录状态
└─ delivery/
   ├─ jobs.py / job_presets.py              # 候选新增：本机升级/组装和可信配置，非模型凭据
   └─ http/
      ├─ app.py / errors.py                 # 候选修改：组装提交用例和安全错误
      └─ routes/jobs/                       # 候选新目录：避免 HTTP 根目录超过 8 文件
         ├─ __init__.py / routes.py         # 路由入口与 HTTP 翻译
         └─ schemas.py                     # 受控选择与安全输出 DTO
apps/backend/tests/jobs/                    # 候选新目录：最多 8 个直接文件
├─ __init__.py / conftest.py / memory.py     # 合成外部存储、可信身份与夹具
├─ test_http.py / test_security.py           # 提交/刷新、权限和任意输入拒绝
├─ test_postgres.py / test_concurrency.py    # 真实持久化、回滚、幂等和并发
└─ runtime/verify.ps1                        # 候选子目录：复用固定官方镜像、隔离 PG/测试器、精确清理
apps/backend/tests/identity/browser_server.py # 候选修改：仅内部浏览器装配提交用例
apps/backend/pyproject.toml                 # 候选修改：打包新 SQL，不新增依赖
apps/web/src/
├─ features/jobs/                           # 候选新目录：通过 HTTP 提交和刷新
│  ├─ submit.tsx / controls.tsx             # 受控选择、组合数与确认界面
│  └─ details.tsx                          # 冻结内容与等待批准状态
├─ features/identity/session.tsx             # 候选修改：登录后接入页面
└─ lib/job-client.ts                        # 候选新增：复用唯一 HTTP request，运行时校验 DTO
apps/web/tests/jobs.spec.ts                 # 候选新增：真实浏览器提交→等待批准→刷新
docs/actions/2026-09-12-m1-job-submission.md  # 已新增：本任务独立行动
.scratch/m1-platform/issues/04-job-submission.md # 已修改：必要待决项，不预勾验收
HANDOFF.md                                  # 已修改：恢复入口与授权边界
docs/architecture/{ARCHITECTURE,DATA_MODEL}.md # 已修改：当前阶段与候选指针；批准后维护实际树/表
docs/architecture/MODULE_CONTRACTS.md         # 候选同步：实际 Interface 与不变量
docs/interfaces/HTTP_API.md                  # 候选同步：实际 schema/错误/预置，只维护一处
```

## 自验证方式与成功标准

- 当前只检查文档链接/锚点/围栏、diff 与候选目录计数；任务 04 所有验收项保持未勾。
- 实施时 HTTP 检查：合法组合和安全 DTO、所有非法/禁用/越权/超限选择、幂等重复/冲突、刷新读取、内部测试不能绕过批准；调用执行或凭据路径应使测试失败。
- 真实 PG 检查：重建应用后快照不变、全部组合和初始事件一起提交、注入写入故障整笔回滚、并发同键只生成一批、禁用与提交竞态结果一致。使用已批准合成临时库；断言通过公共 HTTP/Repository，不用内部函数调用次数冒充行为验证。
- 浏览器少量检查：登录后选择已登记项、组合数、提交等待批准、刷新恢复，以及协作者/所有者可见性；不做假进度或假成绩。
- 全量默认后端、Ruff/mypy、Web typecheck/build、浏览器和文档检查均记录真实输出；未启用的重型/外部检查如实记跳过。双轴评审和修复后才完成任务并本地提交；不推送。

## 自验证情况

- 文档核对已完成：12 份 Markdown、259 条本地链接、84 处锚点、围栏/空白与 git diff --check 通过；首次发现历史单题引用锚点不匹配，按真实标题修正后通过。任务 04 九项验收全部未勾，标签 needs-info；未创建候选业务目录。
- 目录指标复核：任务 03 的 36 个动态代码文件均不超过 200 行，检查的 9 个直接目录均不超过 8 文件；任务 04 候选布局已避开满额 HTTP/测试目录。该检查不代表任务 04 代码已存在。
- 本轮仅新行动与任务单拟精确本地提交；架构、数据和 HANDOFF 等混合旧文档已同步于工作区，不整批暂存，不覆盖原有改动。
- Pending：任务 04 尚未实现，业务验收未运行。任务 03 的通过证据只作已完成依赖，不计为任务 04 通过。
- 当前可控暂停点：等待以上候选方案批准，尤其是精确规模/资源预置、访问范围、四表和新 Interface/子目录。既有临时 PG 与本地提交授权不重复申请。
