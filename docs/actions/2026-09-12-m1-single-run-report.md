# M1 任务 06：单题执行与最小报告

## 状态与情况说明

- 状态：Complete。固定开工/评审基准为 `4944ce6`；任务 06 的 11 项验收全部完成，Standards 与 Spec 修复后复评均无 findings。M1/MVP 尚未完成，下一项为任务 07。
- 对应[任务 06](../../.scratch/m1-platform/issues/06-single-run-report.md)与 M1 规格故事 23、24、26–28、35–38、41、47、51。当前切片只执行一个已批准、且恰好含一个 Run 的 Job；多组合批次在任务 07 前保持排队并明确显示开发期限制。
- 本任务深化已规划的 Job Orchestrator、Worker Shell、Job/Run Repository、Artifact Store、Reporting，以及既有 Execution Backend / Patch Evaluator ports；`deterministic_results` 是权威数据模型已规划且本任务首次需要的结果表，`artifact_records` 在既有表内扩展 Run 所有者和受控证据类型，不建立平行执行或存储系统。
- Worker 领取使用 PostgreSQL 短事务、事务级 advisory lock 和 `FOR UPDATE SKIP LOCKED`：同机全局最多一个活跃重型 Job。领取后以 Worker 身份、未过期租约和行版本推进状态；租约长度取冻结 Agent 墙钟上限、Evaluator 墙钟上限与 300 秒收尾余量之和，阶段边界续租，不在外部执行期间持有数据库锁。任务 10 才实现中断恢复，过期租约本任务不自动重排或重跑。
- 首轮执行/判卷只用受控 `internal_test` Adapter；真实 HTTP 身份/用例、真实临时 PostgreSQL 和 MinIO 仍走生产 ports。真实 Codex、Harbor、模型凭据、长期服务、远程部署、机器设置和推送不在本行动范围，也不把合成闭环称为真实 M1 运行验收。
- Judge、Judge 表、Review 表或调用均不创建、不修改；M1 报告只返回兼容空值。现有混合旧文档、缓存、framework/runtime 和暂存区状态保持隔离。

## 实施措施

1. 先以 HTTP 和应用测试固定单 Run 领取、双 Worker 竞争、错误 Worker/租约/版本拒绝、多组合不领取，以及 `QUEUED → PREPARING → EXECUTING → FINALIZING → COMPLETED/FAILED` 与 Run 状态事件。
2. 在既有 Repository Interface 内增加领取、阶段推进、失败收束和报告查询；PostgreSQL Adapter 用短事务写状态、版本和追加事件。Worker Shell 只管理领取/租约生命周期并调用一个深的 Job Orchestrator，不包含判卷或业务分支。
3. Job Orchestrator 从冻结 Job 快照构造既有 `ExecutionJobRequest`，验证返回的一一对应 Run、后端身份和平台 Artifact Store 中的 patch 字节，再调用既有 `PatchEvaluator`。Harbor reward、模型文本或无可信 Fork 报告都不能写确定性结果。
4. 扩展既有 MinIO Artifact Store 的受控 Run 证据：最终文本 patch、Fork 报告与测试输出按 Run/类型/哈希组成不可变对象键，读取时复核类型、大小和 SHA-256。对象先成功写入并读回，数据库再在结果事务内发布元数据；任一单侧失败不进入完整终态。
5. 新增只读 Reporting 用例和 Job/Run 报告 HTTP；沿现有 Job 权限隐藏他人资源。Web 从 Job 进入 Run 报告，只显示确定性摘要、过程指标和允许发布的证据元数据；原始配置、原始结果、私密轨迹正文不自动公开。
6. 按 TDD 逐片记录红灯和绿灯；运行默认回归、Ruff/mypy、Web typecheck/build、浏览器，以及专属无发布端口/无宿主挂载的真实 PostgreSQL+MinIO 集成。完成后以 `4944ce6` 为固定基准并行执行 Standards/Spec 双轴评审，修复、复核、限定文件本地提交，不推送。

## 需要修改的文件树

以下为当前实际文件树；没有不存在的 `features/runs` 目录。新增路径均属于权威架构已规划的 Module/表/页面职责。动态源码保持每文件不超过 200 行、每层目录不超过 8 个直接文件。

```text
apps/backend/src/eval_platform/
├─ domain/
│  ├─ jobs/{models,factory,snapshots}.py # Job/Run 生命周期、冻结工厂与快照恢复
│  ├─ jobs/execution.py                  # 租约、Run 结果、制品索引和报告值
│  └─ result.py                          # 执行、确定性结果与 patch 校验值
├─ application/
│  ├─ execute_job.py                    # 深 Module；单 Run 执行、判卷、证据和收束
│  ├─ execution/evidence.py             # 旧本地 Adapter 引用到长期证据的规范化发布
│  ├─ reporting/service.py              # 授权后复核证据正文并组合只读报告
│  ├─ job_submission.py                 # 仅保留冻结提交/查询，不混入 Reporting
│  └─ ports/{repositories,artifacts}.py # 深化既有领取/推进/报告与受控证据契约
├─ adapters/
│  ├─ persistence/jobs/
│  │  ├─ execution/                     # 为遵守每层 8 文件指标归拢 Worker 持久化细节
│  │  │  ├─ claims.py / common.py       # 原子领取、租约/版本检查和事件追加
│  │  │  └─ results.py / reports.py     # 原子结果发布与只读报告恢复
│  │  ├─ {repository,records,publication}.py # 接通同一 port、恢复记录与发布快照
│  │  └─ schema.sql                     # 领取/结果字段、事件和规划内结果表
│  └─ artifacts/{local,minio}.py         # 受限本地来源读取与长期对象完整性存储
├─ delivery/
│  ├─ worker/main.py                    # 单机并发 1 Worker Shell
│  └─ http/routes/jobs/{report_routes,report_schemas}.py # 受保护报告端点/DTO
apps/backend/tests/
├─ jobs/execution/{test_claims,test_orchestrator}.py # 领取与单 Run 编排
├─ jobs/execution/{test_postgres_execution,test_storage}.py # 真实 PG/MinIO 分层验收
├─ jobs/execution/{test_reports_http,test_evidence_publication}.py # HTTP 与旧 Adapter 桥
├─ jobs/execution/support/              # 仅 internal_test 的后端、判卷、仓库替身
└─ identity/browser_server.py           # 浏览器门禁下装配 internal_test Worker/报告
apps/web/src/
├─ features/jobs/{details,report}.tsx   # Job 到 Run 入口与最小可信报告
└─ lib/{contracts,job-client,job-shapes,report-shapes}.ts # 契约、请求和失败关闭解析
apps/web/tests/jobs.spec.ts              # 浏览器提交→批准→合成执行→报告接线
docs/actions/2026-09-12-m1-single-run-report.md # 本行动唯一执行记录
.scratch/m1-platform/issues/06-single-run-report.md # 标签、验收和真实证据
docs/architecture/{ARCHITECTURE,DATA_MODEL,MODULE_CONTRACTS}.md # 当前实现子集
docs/interfaces/HTTP_API.md              # 报告形状、空值、安全与错误契约
```

设计继续使用 Ports/Adapter、Repository、Composition Root，并在 Worker Shell 与 Job Orchestrator 之间使用 Application Service（应用服务）分层：Shell 只负责进程生命周期，Orchestrator 隐藏一次运行的完整业务流程，PostgreSQL/MinIO/Harbor/Fork 细节分别留在 Adapter 后面。

## 自验证方式与成功标准

- 领取与状态：待批准、拒绝、已领取和多组合 Job 不可领取；两个 Worker 同时竞争最多一个成功且全局最多一个活跃；错误 Worker、过期租约和陈旧版本不能推进；所有状态与事件可重启恢复，外部执行时没有长事务。
- 编排：一次平台 Job 只构造一次含一个 Run 的 `ExecutionJobRequest`，只消费同 Run 的返回；后端失败、缺少 patch、身份/哈希/大小/格式错误与 Fork `EvaluationError` 均形成安全基础设施失败，不能形成伪 `resolved=false`。
- patch：空补丁沿既有判卷契约；大于 256 KiB 保留警告，大于 1 MiB、非 UTF-8、NUL/二进制标志或非 Git diff 拒绝且绝不截断；报告中的 patch 身份与不可变对象一致。
- 存储：真实 MinIO 覆盖条件写、哈希/大小校验、缺失/损坏/不可用；真实 PostgreSQL 覆盖领取并发、事务回滚、确定性结果唯一和重启查询。对象或数据库任一侧失败时 Job/Run 不宣告完整成功。
- HTTP/Web：真实身份和资源范围；Job 报告可进入唯一 Run 报告；正常未解决与基础设施失败分开展示；只返回受控摘要和证据元数据；`judge_analyses=[]`、`human_review=null`、`quality_tiebreak=null`、`review_status=NOT_REQUIRED`，不存在 Judge/Review 调用或表。
- 全量：默认 pytest、Ruff、format、mypy、Web typecheck/build、完整浏览器、专属存储验收、文档链接/围栏/diff、文件/目录指标和残留资源均按实际输出记录；未运行、失败或跳过不记为通过。

## 自验证情况

- 第一片应用红灯：`pytest tests/jobs/execution/test_orchestrator.py -q` 在收集期按预期因 `eval_platform.application.execute_job` 尚不存在失败（1 error，2 个既有框架弃用 warning）。测试已经固定一个 `QUEUED` 单 Run 经 Worker、ExecutionBackend、Artifact Store、PatchEvaluator 到分层报告的完整边界；尚未实现生产代码。
- 第一片合成绿灯：单 Run 编排与三项领取边界为 `4 passed / 2 warnings`；Job 只发出一次单 Run Execution 请求并调用一次 Evaluator，错误 Worker、陈旧 Job/Run 版本、到期租约、重复领取和多组合领取均被拒绝。相关 Job 与既有 patch/Harbor 单元回归为 `35 passed / 9 skipped / 2 warnings`；9 项是未开启真实 PostgreSQL 门禁，不能记为通过。首次 Ruff 指出测试残留一个未用 import，mypy 同时准确显示生产 PostgreSQL Adapter 尚未实现扩展 port、HTTP 状态 DTO 尚未扩展；本节点尚不提交。
- PostgreSQL 领取红灯：任务 06 专属脚本首次普通沙箱因无 Docker daemon 权限在任何容器创建前失败；按既有授权提升后，以测试镜像 `sha256:ae3674d...e344e` 和固定 PostgreSQL 镜像启动随机标签隔离批次，取得 `28 passed / 1 failed / 2 warnings`。唯一失败为生产 `PostgresJobRepository` 尚无 `claim`，符合 TDD 预期；PostgreSQL `bc0fbc2d...b6f4` 与测试器 `fe0477d8...3731` 均无发布端口/宿主挂载，结束后按精确 ID 删除，tmpfs 数据删除、镜像/缓存保留。
- PostgreSQL 领取第一次实现后，扩展表约束暴露两个真实问题：参数化元组不能直接用于该 `ANY` 查询，且 owner 拒绝产生的 Run 事件不应被误当 Worker 事件；批次为 `26 passed / 3 failed / 2 warnings`，所有隔离资源照常删除。改为固定状态白名单查询并允许 `JOB_REJECTED` 的可信无 Worker 事件后，专属批次为 `29 passed / 2 warnings`，测试镜像 `sha256:d0cc370...57da6`；容器 `b7193bbd...e10a` 与 `5237ae56...3d5` 已精确删除。
- 结果事务红灯：新增从真实 PG 领取、用受控执行/判卷替身形成证据，再由新 Repository 实例恢复报告的测试；专属批次为 `29 passed / 1 failed / 2 warnings`，唯一失败是生产 Adapter 尚无 `complete`，符合预期。测试镜像 `sha256:8bd50b7...28095`；容器 `8193b4a1...1ad3` 与 `ee6106bb...7efc4` 已精确删除。
- 结果事务绿灯：在同一短事务写 Run 制品索引、唯一确定性结果、过程指标、Run 终态和 Job `FINALIZING → COMPLETED` 事件；新 Repository 重启后恢复结果、3 个制品索引和资源指标。专属批次最终 `30 passed / 2 warnings`（13.38 秒），测试镜像 `sha256:6740e74...07a70`；PostgreSQL `5d7fad92...8101a` 与测试器 `fa79194f...25d67` 无端口/宿主挂载，已精确删除，tmpfs 数据删除。
- 第一提交点前检查：任务 06 合成及相关 Job/patch/Harbor 回归 `35 passed / 11 skipped / 2 warnings`；11 项均是本次命令未开启的 PostgreSQL 门禁，其中任务 06/既有 Job PG 已由上方 30 项专属批次覆盖。Ruff 与 mypy（101 个源文件）通过；所有新增/修改动态源码均不超过 200 行。HTTP 报告、真实 MinIO、浏览器和完整回归仍待后续切片。
- 第一实现提交为 `62a246c`（`feat: add single-run execution core`），只纳入任务 06 的领域、编排、Worker、PostgreSQL 和相应测试/任务记录；未混入既有脏文档、缓存或 framework/runtime，也未推送。
- HTTP/报告切片先取得真实提交→批准→Worker→Job/Run 报告 `1 passed / 1 failed`：未知 Run 的测试期 Repository 将缺失错误误报为租约冲突，HTTP 返回 500 而非安全 404；修正测试 Adapter 与生产 `JobNotFound` 契约一致后，报告与相关 Job HTTP 为 `17 passed / 2 warnings`，Ruff、mypy（104 个源文件）通过。随后补入“他人协作者 404、创建者与 owner 200”，报告定向测试为 `3 passed / 2 warnings`。响应确认不含对象键，并固定 `judge_analyses=[]`、两个 null 和 `NOT_REQUIRED`。
- MinIO 切片红灯为 `test_storage.py` 首次 `1 failed / 2 warnings`：既有 Store 只允许题目快照，按预期拒绝 Run 制品。扩展为受控 `runs/{run_id}/{type}/{sha256}` 类型/内容类型/上限后，单元及既有 MinIO 目录回归 `5 passed / 2 skipped / 2 warnings`；2 项是未开启真实 MinIO 门禁。
- 专属真实 PG+MinIO 验收使用测试镜像 `sha256:e140470...00b81`、固定 PostgreSQL `sha256:5cce759...a6b6`、固定 MinIO `sha256:922042...aba8`，最终 `35 passed / 2 warnings`（15.24 秒）。它覆盖双 Worker 领取、真实不可变写/读/删除后明确缺失、结果重启恢复，以及 MinIO 三对象已写后数据库触发器失败：Job/Run 收束为 `FAILED`，确定性结果和制品索引均未发布，三只对象仅成为可定位孤儿而非报告结果。MinIO `ea2ee8...c12b`、PG `28dbc7...6110`、测试器 `49bc7e...e23e` 均无端口和宿主挂载，已按精确 ID 删除，tmpfs 数据删除、镜像/缓存保留。
- 补丁/失败分类边界新增测试后先因误把 Worker 的 `run_once=True` 理解成“执行成功”而出现 `4 failed`；该返回值实际只表示“成功领取并处理过一个 Job”。保持生产契约并修正断言后 `7 passed / 2 warnings`：空补丁、256 KiB 警告且不截断、非 diff、二进制、超过 1 MiB、Agent 失败和正常未解决均分开验证；补丁警告同时纳入 Run 持久化，重启报告可恢复。
- Web 报告新增完整执行状态、失败关闭解析、单 Run 入口、确定性摘要/过程指标及受保护证据索引；页面只显示证据元数据，不显示对象键、私密轨迹或凭据引用。typecheck 通过；首次 build 因 Next.js 用户级配置缓存写入被沙箱拒绝，提升后仍遇到跨文件系统 rename，最终仅在进程内设置 `NEXT_TELEMETRY_DISABLED=1` 后生产 build 通过（编译 1.368 秒），没有修改机器配置。
- 浏览器第一次普通沙箱在写 `.last-run.json` 前失败；提升后服务能启动，但 Playwright 默认缓存缺少 Chromium 1243，3 项均在创建浏览器前失败。查明项目已有精确缓存 `runtime/tools/playwright/{chromium,chromium_headless_shell}-1243` 后，仅为测试进程设置 `PLAYWRIGHT_BROWSERS_PATH`，`jobs.spec.ts` 最终 `3 passed`（14.1 秒）：覆盖 owner 提交/批准/内部 Worker/报告、过期页面冲突刷新、协作者不可决定与拒绝、畸形契约失败关闭。测试结束后 3100/8875 无监听，测试时钟文件不存在；未下载浏览器、未启动真实模型或 Harbor。
- 第二提交点前重跑专属 PG+MinIO 为 `42 passed / 2 warnings`（16.95 秒），其中新增断言确认超过 256 KiB 的 patch 字节数与 `PATCH_SIZE_WARNING` 可由全新 PostgreSQL Repository 恢复。测试镜像 `sha256:22da7a9...902ac`；MinIO `fd5d47e...04281`、PG `caa956a...f0404`、测试器 `7f21629...f30a4` 已按精确 ID 删除，tmpfs 数据删除，未留下容器。
- 第二实现提交为 `2b64ef3`（`feat: expose protected single-run reports`），显式暂存 31 个任务 06 HTTP/报告/存储/Web/测试文件；旧混合文档、缓存和 framework/runtime 未进入提交，未推送。
- 收尾后端全量为 `303 passed / 60 skipped / 2 warnings`（30.33 秒）。60 项均是默认关闭的 PostgreSQL、MinIO、Docker、Fork、Harbor 或 Codex 门禁；任务 06 的 PG+MinIO 已由上方专属 42 项覆盖，其余不冒称本轮通过。Web 全量浏览器按文件隔离新后端，共 14 项通过：catalog 2、identity-security 6、identity 2、jobs 3、membership 1；结束后 3100/8875 无监听、测试时钟不存在。typecheck、生产 build、Ruff format/check 和 mypy 均通过。
- 规模/结构检查：从固定基准到现场的 Python/TypeScript/JavaScript 动态文件均不超过 200 行；application/domain/jobs/HTTP jobs/persistence jobs/persistence execution/测试 execution/测试 support/Web jobs/Web lib 的直接文件数依次为 8/7/6/6/5/7/5/5/7，均不超过 8；`git diff --check` 与本行动涉及文档围栏配对通过。
- 双轴评审期间主执行者自查发现 PostgreSQL 报告恢复把 Run 级 `PATCH_SIZE_WARNING` 误挂到所有 Harness 制品；应只属于 patch。已在 `reports.py` 限定 `agent_patch` 并给真实 PG 用例增加非 patch 无警告断言。另把公开 HTTP `process_metrics` 从宽泛字典收紧为 Pydantic DTO，并将 Run/Job 状态、受控制品类型和脱敏状态收紧为枚举；OpenAPI 测试确认不含 `object_key`。这些修复的针对性验证与评审结论待下方继续记录。
- 固定基准 Spec 初评发现四个真实断点：冻结执行契约被错误硬编码、既有 Harbor/Fork 本地引用无法进入 MinIO、对象正文丢失后报告仍冒充完整、空补丁替身可返回矛盾成功。已改为使用 Run 冻结版本；新增受限本地 `ArtifactReader` 与 `EvidencePublication`，只把 patch/报告/测试输出规范化为长期对象；`JobReporting` 在授权后复核全部结果证据；确定性结果新增 patch/应用/解决不变量，空补丁为三项 false。针对性合成验证为 `13 passed / 2 warnings`，HTTP 缺失对象返回 `503 DEPENDENCY_UNAVAILABLE`。
- Standards 初评指出非法 `in-progress` 标签、行动树过期、Submission/Reporting 职责混合及 Web 状态列表重复。任务标签已恢复为合法 `ready-for-agent`；Reporting 移至独立应用子目录；Job/Run/制品/脱敏状态改为 `contracts.ts` 单一定义；本节改为实际文件树。另一次误用 Windows PowerShell 5 运行验收脚本，在创建容器前因 finally 查询未创建对象被宿主当成终止错误；镜像构建成功且标签核对无残留，随后改用 PowerShell 7 重跑同一脚本。
- 修复后的专属真实 PostgreSQL+MinIO+HTTP 验收为 `46 passed / 2 warnings`（17.21 秒），测试镜像 `sha256:1bea9b4...1c0377`。新增路径先从真实 PG 恢复 `COMPLETED` 报告并成功读取三项 MinIO 证据，再删除一个精确对象，报告立即变为 `503`，不再返回完整结果。MinIO `3baab094...c0d161`、PostgreSQL `15edd5a7...d72d02`、测试器 `aeac6a9e...c2cbe` 均无发布端口或宿主挂载，已精确删除，tmpfs 数据清理，镜像/缓存保留。复评与最终全量回归见下三项，均已完成。
- 评审修复后的默认后端全量为 `306 passed / 61 skipped / 2 warnings`（33.97 秒）；新增的第 61 项跳过是必须由专属 PG+MinIO 门禁开启的真实报告失败关闭用例，该用例已包含在上方 46 项通过中，其余门禁仍不冒称通过。Web `typecheck` 和生产 `build` 通过（编译 1.176 秒）。浏览器全套第一次在普通沙箱清理 Playwright 自身 `.last-run.json` 时因 `EPERM` 退出，未形成业务失败；沿既有授权提升重跑后 catalog 2、identity-security 6、identity 2、jobs 3、membership 1，共 14 项全部通过。结束后 3100/8875 无监听、测试时钟不存在、`agentexam.jobs-test` 标签无容器残留。
- 最终静态检查过程中，首次 `ruff format --check` 准确指出刚加强的 Reporting 条件式尚需格式化；同组 Ruff 规则检查、mypy（109 个源文件）和 13 项针对性测试均通过。执行 Ruff 格式化后再次 `format --check` 为 186 个文件全部符合。该格式变化不改变行为；双轴复评正在读取当前现场。
- 固定基准 Spec 初评的 4 项 P1 全部修复，targeted 复评无 findings；评审确认冻结版本实际进入既有 Harbor mapper、本地 Harbor/Fork 引用安全归档、真实对象丢失后报告失败关闭、空 patch 三项 false，且 Judge/Review 未被实现或调用。Standards 初评的非法标签、行动树、职责混合、重复状态常量及 201 行测试文件全部修复；最后一项把测试文件严格压缩为 200 行，Ruff 与 13 项定向测试复验通过，targeted 复评无 findings。
- 任务 06 完成结论：11 项验收全部有实现与证据；所有成功、失败与跳过均按实际记录。当前没有任务 06 遗留阻塞；真实 Codex/Harbor 并未在本任务重跑，长期服务、远程部署和 Judge/Review 仍在授权边界外。下一任务只按任务 07 规格深化批量进度与收束。
