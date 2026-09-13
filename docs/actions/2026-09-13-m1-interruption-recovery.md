# M1 中断恢复与新建重试行动记录

## 状态

In progress。用户已明确批准最小 `JobRepository.recover(RecoveryRequest)` Interface 及本记录中的收束、重试和访问语义。实现、分层验证和首轮双轴评审修复已完成；当前以 `2137e08` 为固定基准做最终 Standards/Spec 复审，尚未提前勾选任务验收。

## 情况说明

- Worker、宿主或 Harbor 中断后，现有 Job 会保留在 `PREPARING`、`EXECUTING`、`CANCEL_REQUESTED` 或 `FINALIZING`，但所有推进方法都要求尚未过期且版本匹配的 `JobLease`。复用 `fail()`/`finish()` 会绕过租约隔离或根本无法执行，现有职责不能安全承载过期租约收束。
- 权威规格要求旧 Job 不自动续跑、重新排队或调用模型；证据充分时只做幂等收束，证据不足、错配或损坏时明确记录 `INFRASTRUCTURE_INTERRUPTED`。所有者需要重试时必须创建关联的新 Job、重新冻结当前有效目录并重新批准。
- 已确认的最小变更是在既有 `JobRepository` 增加 `recover(RecoveryRequest) -> EvaluationJob`。它只在一个短事务内锁定过期 Job、终结未完成 Run、保留完成结果并使旧 Worker 的版本失效；不触碰 `ExecutionBackend`、`PatchEvaluator`、Harbor 进程或真实凭据。
- 不新增数据库表或顶层 Module。`evaluation_jobs` 只增加自引用 `rerun_of_job_id`；恢复审计继续使用既有不可变状态事件。应用层在既有 `job_lifecycle/` 增加恢复用例，手动重试复用并深化 `JobSubmission`。
- 已确认的访问语义：恢复与重试仅 owner；重试 Job 保留原 Job 的 `created_by`，因此原协作者仍可查询，新 Job 的首个事件以 owner 为 `actor_user_id`，并通过 `rerun_of_job_id` 关联旧 Job。普通 `POST /jobs` 不能伪造该关联。
- Judge/Review 不在本任务范围；不运行真实模型，不强杀真实容器，不自动扫描/续租/重试，不部署、不推送、不改机器或网络设置。

## 实施措施

1. 先以 HTTP 与内存 Repository 写红灯，固定 owner-only、租约尚有效冲突、过期后收束、重复恢复无重复事件、旧 Worker 失效和正文不能提权。
2. 在 `JobRepository` 增加唯一恢复事务：行锁后重新核对状态、租约和版本；已完成 Run/确定性结果保持不变，活跃 Run 记 `INFRASTRUCTURE_INTERRUPTED`，未开始 Run 记 `CANCELED`。
3. 若所有 Run 已终态，则只依现有可信结果收束；若有中断 Run，则有已完成结果时 Job 为 `COMPLETED_WITH_ERRORS`，否则为 `FAILED`。取消请求交叉场景保留 Run 的真实中断事实并把 Job 收束为 `CANCELED`，不改写已完成结果。
4. 增加 owner-only `POST /api/v1/jobs/{job_id}/recover` 空正文入口；重复调用返回同一已收束记录。Job 详情返回安全的租约到期时间、失败原因、事件和重试关联，页面显示中断阶段与“等待所有者收束”。
5. 增加 owner-only `POST /api/v1/jobs/{job_id}/retry` 空正文及 `Idempotency-Key`；只允许已由恢复流程收束且仍需重试的旧 Job。新 Job 重新查询任务/启用配置、冻结当前有效版本、生成全新 Job/Run/证据链并回到 `AWAITING_OWNER_APPROVAL`。
6. 用真实临时 PostgreSQL 验证租约竞争、重复恢复、旧 Worker 更新拒绝、完成结果不变和新旧 Job 关联；浏览器验证中断详情到新建重试。同步架构、数据模型、HTTP 与任务单。
7. 执行定向/完整后端、Ruff/mypy、Web typecheck/build、少量浏览器、规模与 diff 检查；最后以任务 09 关闭提交 `2137e08` 为固定基准并行做 Standards/Spec 评审，修复并复验。

## 需要修改的文件树

```text
apps/backend/src/eval_platform/
├─ domain/jobs/{models,execution,policy,factory}.py       # 重试关联、恢复请求、共享恢复判定与请求身份
├─ application/
│  ├─ job_lifecycle/recovery.py                           # owner 授权、恢复与手动重试用例
│  ├─ job_submission.py                                   # 复用目录校验并为原提交者重新冻结
│  └─ ports/repositories.py                               # 最小 recover Interface
├─ adapters/persistence/jobs/
│  ├─ recovery/{__init__,actions}.py                      # 过期租约原子收束及事件
│  ├─ {schema,publication,records,repository}.py          # 自引用字段、写入/读回与 Adapter 委托
├─ delivery/
│  ├─ jobs.py                                             # 运行时装配
│  └─ http/
│     ├─ app.py                                           # 注入既有单体路由
│     └─ routes/jobs/
│        ├─ routes.py                                     # 挂载恢复子路由
│        ├─ schemas.py                                    # 安全摘要字段
│        └─ lifecycle/{routes,schemas}.py                 # 空正文恢复/重试 HTTP
apps/backend/tests/jobs/
├─ recovery/{test_recovery_http,test_recovery_postgres,test_recovery_postgres_edges,test_retry,test_states}.py
│                                                          # 各阶段、竞争、持久化与幂等
├─ support/recovery.py                                    # 内存 Repository 恢复事务替身
├─ support/postgres_api.py                                # 共享真实 PG HTTP/Repository 装配
├─ test_postgres.py                                       # 复用装配后的既有 PG 提交/恢复回归
└─ {conftest,memory}.py                                   # 测试装配与端口实现
apps/backend/tests/identity/browser_server.py             # 环境门控的中断浏览器替身
apps/web/src/
├─ features/jobs/lifecycle/recovery.tsx                   # 中断说明、恢复和新建重试控件
├─ features/jobs/{details,submit}.tsx                     # 详情显示与既有页面接线
└─ lib/{contracts,job-client,jobs/shapes}.ts              # HTTP 类型、调用和运行时校验
apps/web/tests/{run-browser-tests.mjs,jobs/interruption-recovery.spec.ts}
                                                           # 子目录发现与中断到重试浏览器流
docs/{architecture,interfaces}/                          # 当前恢复契约和文件树
.scratch/m1-platform/issues/10-interruption-recovery.md  # 八项验收与证据
```

采用 Application Service、Repository、Ports/Adapters、Optimistic Concurrency（乐观并发）和 Idempotent Receiver（幂等接收）模式。恢复用例只表达授权与意图；Repository 是状态/租约/事件唯一事实源；PostgreSQL Adapter 隐藏行锁和事件写入；页面不获得 Worker 身份或容器控制能力。新增子目录是因为 `adapters/persistence/jobs/`、`delivery/http/routes/jobs/`、`tests/jobs/` 和 `web/tests/` 已达到 8 个直属文件，避免超过项目指标。

## 自验证方式与成功标准

- 有效租约、非活跃/非恢复终态、非 owner、未知 Job 均不改变状态；请求正文不能指定用户、Worker、状态、证据或重试来源。
- 过期租约恢复只接受行锁内当前版本；同一时刻的旧 Worker 更新或恢复只有一个合法结果，恢复提交后旧租约永远不能继续推进。
- 全部 Run 已有一致终态/确定性结果时不调用执行器或判卷器，只幂等完成 Job；任何活跃 Run 都不伪造结果，明确写基础设施中断，未开始 Run 取消。
- 重复恢复不增加事件、不覆盖结果/制品；损坏或错配的已有记录返回依赖错误并回滚，不部分写入。
- 手动重试生成全新 Job/Run ID、自引用旧 Job、重新冻结当前启用目录，保持原创建者访问范围并重新等待 owner 批准；旧 Job 永不改回队列。
- HTTP、真实临时 PostgreSQL、浏览器、完整回归、静态检查和规模检查全部实际运行；失败、跳过和未获授权的真实生命周期项如实记录。

## 自验证情况

- 第一片 TDD 红灯已出现：新增恢复 HTTP 测试为 `3 failed`，三项都因端点不存在返回 404，分别覆盖过期收束、有效租约冲突/幂等重放、owner-only 与伪造控制字段。
- 第一片绿灯为 `3 passed, 2 warnings`。已实现 owner-only 空正文恢复入口、内存/生产 Repository 的过期租约原子收束、活跃 Run 基础设施中断、待运行取消、重复恢复无新事件，以及 Job/Run 安全失败字段；同组 Ruff 已通过。
- 第二片 TDD 红灯为 `3 failed`，三项都因重试端点不存在返回 404，固定了仅 owner、必须先恢复收束、禁止正文伪造来源以及 `Idempotency-Key` 幂等语义。
- 第二片绿灯为 `6 passed, 2 skipped`：手动重试会创建全新 Job/Run，保留原提交者 `created_by` 访问范围，以 owner 记录首事件，通过 `rerun_of_job_id` 关联旧 Job，并重新进入 `AWAITING_OWNER_APPROVAL`；普通提交的请求摘要保持兼容。两个跳过项是仅在真实 PostgreSQL 环境运行的持久化测试。
- 定向静态检查已通过：Ruff 无告警；mypy 覆盖 `136` 个源码文件并通过。
- 首次真实临时 PostgreSQL/MinIO 套件没有进入测试执行：新增恢复用例与既有用例同名为 `test_http.py`、`test_postgres.py`，pytest 收集时报 import mismatch。已把新文件改为唯一名称；本次专属容器和 tmpfs 均精确清理，不把它记为通过。
- 改名后的真实套件首次执行为 `94 passed, 1 failed`。失败揭示内存取消测试替身仍为取消中的 Run 合成 `BATCH_*` 失败码，而生产 PostgreSQL 路径会清空它；已修正替身，并把变化中的 `lease_expires_at` 限定为详情字段，避免幂等取消摘要随心跳漂移。本次环境同样已精确清理。
- 修正后真实隔离套件为 `95 passed, 2 warnings in 36.32s`。其中新增 PostgreSQL 用例验证：过期恢复原子提交、重复恢复只产生一个收束事件、旧 Worker 不能再推进；以及 Run 结果已提交但 Job 尚未终结的合成崩溃，恢复只根据持久化结果到达 `COMPLETED`，不改变结果或重新执行。三个容器均无宿主端口、无宿主挂载，结束后已按专属标签精确删除并移除 tmpfs；镜像和构建缓存保留。
- 新增多 Run 和取消交叉状态测试与既有恢复/重试组共 `8 passed, 2 warnings`：已完成 Run 保持原对象，活跃 Run 记 `INFRASTRUCTURE_INTERRUPTED`，未开始 Run 取消；有取消请求时 Job 收束为 `CANCELED`，但 Run 的中断事实保留。两项新增测试第一次即通过，是对现有算法的边界刻画，不冒称经历了产品代码红灯。
- 浏览器红灯先经历两项测试设施修正：原测试运行器不发现子目录且嵌套输出目录创建失败，已改为递归发现并使用扁平结果目录；测试控制请求最初因缺少同源/写请求头被拒绝，已按真实 HTTP 安全边界补齐。设施就绪后的产品红灯为 `1 failed`：页面找不到“中断恢复”区域和“不自动续跑”提示。
- 页面绿灯为 `1 passed (10.8s)`，Web `tsc --noEmit` 通过。环境门控的浏览器替身只在 `AGENTEXAM_IDENTITY_BROWSER_TEST=1` 时提供暂停/合成过期能力；真实页面经后端 HTTP 完成 owner 收束和新建重试，验证不同 Job ID、旧 Job 关联、URL 切换和重新等待批准，且不显示 Worker 身份。
- 本片 Ruff 已通过；源代码和测试文件均未超过项目的 200 行指标，`submit.tsx` 为 195 行。真实 PostgreSQL 新增的并发恢复和损坏证据回滚用例尚待下一次隔离套件执行，因此当前不记为通过。
- 第二轮真实隔离套件为 `97 passed, 1 failed, 2 warnings in 36.16s`，三个专属容器和 tmpfs 已精确清理。并发恢复测试已通过；失败发生在损坏证据夹具的目标断言前：夹具把 Job 改回 `FINALIZING` 并删除结果行，却保留了原 `COMPLETED` Job 事件，通用读取门禁先因状态/事件不一致返回 `JobUnavailable`。下一轮只修正夹具，使唯一损坏点为“COMPLETED Run 缺少确定性结果”，不放宽生产读取或恢复校验。
- 修正夹具后的真实隔离套件为 `98 passed, 2 warnings in 35.41s`。两个并发恢复事务均读回同一 `FAILED` 结果且只有一条 `INTERRUPTION_RECOVERED` 事件；过期 Worker 更新仍被拒绝。单一损坏点测试确认 `COMPLETED` Run 缺少 `deterministic_results` 时 HTTP 返回 503，Job 保持 `FINALIZING`、事件数不变，没有部分收束。三个专属容器均无宿主端口/挂载，结束后已精确删除并移除 tmpfs；镜像和构建缓存保留。
- 完整后端回归为 `348 passed, 70 skipped, 2 warnings in 45.25s`。70 项跳过均有显式环境门禁，其中任务 10 的 PostgreSQL/MinIO 项已由上一条专属套件实际通过；未运行真实 Codex、Harbor、网络、真实凭据或其他未授权探针。全仓 Ruff 通过，mypy 为 `Success: no issues found in 136 source files`。
- Web 首次 `next build` 未进入编译，因沙箱拒绝写系统用户 `AppData` 的 Next.js 配置临时文件；把本次进程的 `APPDATA` 指向仓库内 `runtime/tests/next-appdata` 并关闭遥测后，生产构建成功，4 个静态页面生成完成。现有 `%USERPROFILE%` 缓存未删除，机器设置未改变。
- 完整浏览器回归递归执行 8 个规格文件，共 `18 passed`。每份规格使用新合成后端；新增中断恢复动线通过，既有目录、身份安全、登录、成员、提交/批准/取消、多 Run 报告和安全证据流程也全部通过。没有真实模型或 Harbor 调用。
- 双轴评审前自查补强页面的逐 Run 解释：已完成项明确显示结果保留，失败项显示后端安全摘要中的中断阶段，未开始项显示已取消；不展示 Worker 身份。补强后 Web typecheck 再次通过，单项浏览器复验为 `1 passed (10.0s)`。
- 规模复核覆盖相对固定基准 `2137e08` 的全部 Python/TypeScript/JavaScript 变更：动态源码均不超过 200 行，所有受影响目录直属文件均不超过 8 个。共享 PG 测试夹具在格式化后达到 205 行，已把可复用的 HTTP/Repository 装配下沉到既有 `tests/jobs/support/postgres_api.py`；最终辅助文件 103 行、原测试 118 行，support 目录 3 个直属文件。全仓 Ruff check 和 format-check 均通过。
- 源码事务核对确认：`results.complete()` 在同一 PostgreSQL 事务中写入制品索引、`deterministic_results` 和 Run 的 `COMPLETED`/事件；事务失败会整体回滚。因此一致存储中“可信结果已落盘”必然对应终态 Run，恢复只需验证这些既有记录并收束 Job，不得重新调用 Evaluator。
- `RUNNING_AGENT`、`VERIFYING` 或其他活跃 Run 若没有上述完整事务结果，即使存在进程内返回值、孤立对象或 Harbor 残留也不能证明确定性结果；候选恢复会明确写 `INFRASTRUCTURE_INTERRUPTED`，不猜测或补造结果。
- `execution.common.current()` 明确拒绝 `now >= lease_expires_at`、Worker/版本/租约错配；现有 `fail()`、`start_finalizing()`、`finish()` 均依赖该检查，证明确需独立且受限的过期租约恢复事务，而不是复用正常执行入口。
- Standards 首轮指出生产 PostgreSQL 恢复与内存测试替身重复维护状态集合、Run 转换和 Job 汇总；Spec 首轮指出 `COMPLETED_WITH_ERRORS` 不能幂等重放、取消已进入 `FINALIZING` 后会丢失取消意图、结果证据只检查“有无行”以及缺少恢复与旧 Worker 的真实并发。均属于已批准边界，无需新增业务选择。
- 评审修复先形成可复现红灯：纯领域恢复函数尚未存在时测试收集报 ImportError；接线前状态测试为 `2 failed, 2 passed`，分别证明部分成功重放返回 409、FINALIZING 取消被误收束为 FAILED。随后把租约资格、Run 转换和 Job 汇总下沉到既有 `domain/jobs/policy.py`，生产 Adapter 与内存替身共用；取消判断读取持久化 `cancel_requested_by`，部分成功终态纳入幂等读回。定向组转为 `10 passed, 2 warnings`。
- 新增真实 PostgreSQL 边界第一次为 `101 passed, 4 failed`：摘要错配、Harness revision 错配和不可能的结果布尔组合都被错误返回 200；取消用例本身还未让 Worker 持久化协作停止，无法合法进入 FINALIZING。生产查询随后核对 `resolved_summary`、冻结 `swe_bench_fork_revision` 及 `resolved ⇒ patch_successfully_applied ⇒ patch_exists`；测试夹具改为通过 `start_run` 的取消准入结果收束 Run，没有绕过生产状态机。
- 修复后的专属 PostgreSQL/MinIO 套件为 `105 passed, 2 warnings in 38.72s`：三类错配都返回 503 且事务无部分写入，FINALIZING 保留取消意图，恢复与持旧租约 Worker 同时争锁时只有恢复成功。容器无宿主端口/挂载，三个专属容器与 tmpfs 已精确清理，镜像/构建缓存保留。
- 评审修复后的完整后端为 `350 passed, 75 skipped, 2 warnings in 44.24s`；新增 5 个跳过均为已由专属环境通过的 PG 边界，其他跳过仍是显式外部探针门禁。mypy 再次覆盖 136 个源码文件并通过，Web typecheck 通过，Ruff check/format-check 通过。
- 最终浏览器单项首次因旧结果目录 `.last-run.json` 的 Windows EPERM 未进入产品断言；精确删除该任务结果目录后，第二次又因沙箱无法重建目录退出，沙箱外首次运行再发现前一次异常留下的 3100 端口进程。仅终止该合成测试 Node 进程并重建精确目录后，`interruption-recovery.spec.ts` 为 `1 passed (10.2s)`；没有真实模型、Harbor 或凭据调用。
- 当前实现和权威契约已同步，下一步只做双轴最终复审、回填八项任务验收并提交关闭记录；复审通过前不进入任务 11，也不提前宣称任务 10 完成。
