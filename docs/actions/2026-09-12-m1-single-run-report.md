# M1 任务 06：单题执行与最小报告

## 状态与情况说明

- 状态：In Progress。固定开工基准为 `4944ce6`；任务 05 已完成，任务 06 的 11 项验收尚未实现。
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

以下是实施前规划；执行中按实际变化更新。新增路径均属于权威架构已规划的 Module/表/页面职责。动态源码保持每文件不超过 200 行、每层目录不超过 8 个直接文件；若接近指标先拆入已有职责子目录。

```text
apps/backend/src/eval_platform/
├─ domain/
│  ├─ jobs/models.py                    # 扩展可持久化 Job/Run 生命周期摘要
│  └─ jobs/execution.py                 # 新增：租约、Run 结果、制品索引和报告值
├─ application/
│  ├─ execute_job.py                    # 新增：深 Module；单 Run 执行、判卷、证据和收束
│  └─ ports/{repositories,artifacts}.py # 深化既有领取/推进/报告与受控证据契约
├─ adapters/
│  ├─ persistence/jobs/
│  │  ├─ schema.sql                     # 扩展既有四表并新增规划内 deterministic_results
│  │  ├─ execution/                     # 新增：为遵守每层 8 文件指标归拢 Worker 持久化细节
│  │  │  ├─ claims.py / common.py       # 原子领取、租约/版本检查和事件追加
│  │  │  └─ results.py / reports.py     # 原子结果发布与只读报告恢复
│  │  ├─ repository.py                  # 接通扩展的同一 Repository port
│  │  └─ records.py                     # 恢复和校验执行期/终态 Job/Run
│  └─ artifacts/minio.py                # 扩展受控 Run 证据，不改变任务快照规则
├─ delivery/
│  ├─ worker/main.py                    # 新增：单机并发 1 Worker Shell
│  └─ http/{app.py,routes/...}          # 注入 Reporting；Job/Run 报告端点和安全 DTO
apps/backend/tests/
├─ jobs/execution/...                   # 新增子目录以保持 jobs 层 8 文件；单 Run、双 Worker与存储测试
└─ identity/browser_server.py           # 仅浏览器门禁下装配 internal_test Worker/报告
apps/web/src/
├─ features/jobs/...                    # Job 到 Run 报告入口及开发期限制
├─ features/runs/...                    # 新增：最小可信 Run 报告视图
└─ lib/{contracts,job-client,...}.ts     # 报告契约、请求与失败关闭解析
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
