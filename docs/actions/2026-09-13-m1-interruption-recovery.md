# M1 中断恢复与新建重试行动记录

## 状态

In progress。用户已明确批准最小 `JobRepository.recover(RecoveryRequest)` Interface 及本记录中的收束、重试和访问语义。任务 09 已验收关闭；本任务对应 [10-interruption-recovery.md](../../.scratch/m1-platform/issues/10-interruption-recovery.md)，现在从 HTTP/内存 Repository 红灯开始。

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
├─ domain/jobs/{models,execution,policy,factory}.py       # 重试关联、恢复请求与幂等请求身份
├─ application/
│  ├─ job_lifecycle/recovery.py                           # owner 授权、恢复与手动重试用例
│  ├─ job_submission.py                                   # 复用目录校验并为原提交者重新冻结
│  └─ ports/repositories.py                               # 最小 recover Interface
├─ adapters/persistence/jobs/
│  ├─ recovery/{__init__,actions}.py                      # 过期租约原子收束及事件
│  ├─ {schema,publication,records,repository}.py          # 自引用字段、写入/读回与 Adapter 委托
│  └─ execution/{common,finalization}.py                  # 复用终态分类，不开放旧租约推进
├─ delivery/
│  ├─ jobs.py                                             # 运行时装配
│  └─ http/
│     ├─ app.py                                           # 注入既有单体路由
│     └─ routes/jobs/
│        ├─ routes.py                                     # 挂载恢复子路由
│        ├─ schemas.py                                    # 安全摘要字段
│        └─ lifecycle/{routes,schemas}.py                 # 空正文恢复/重试 HTTP
apps/backend/tests/jobs/
├─ recovery/{test_http,test_postgres,test_states}.py      # 各阶段、竞争、持久化与幂等
├─ support/recovery.py                                    # 内存 Repository 恢复事务替身
└─ {conftest,memory}.py                                   # 测试装配与端口实现
apps/web/src/
├─ features/jobs/lifecycle/recovery.tsx                   # 中断说明、恢复和新建重试控件
├─ features/jobs/{details,submit}.tsx                     # 详情显示与既有页面接线
└─ lib/{contracts,job-client,jobs/shapes}.ts              # HTTP 类型、调用和运行时校验
apps/web/tests/jobs/recovery.spec.ts                      # 中断详情到重试浏览器流
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
- 源码事务核对确认：`results.complete()` 在同一 PostgreSQL 事务中写入制品索引、`deterministic_results` 和 Run 的 `COMPLETED`/事件；事务失败会整体回滚。因此一致存储中“可信结果已落盘”必然对应终态 Run，恢复只需验证这些既有记录并收束 Job，不得重新调用 Evaluator。
- `RUNNING_AGENT`、`VERIFYING` 或其他活跃 Run 若没有上述完整事务结果，即使存在进程内返回值、孤立对象或 Harbor 残留也不能证明确定性结果；候选恢复会明确写 `INFRASTRUCTURE_INTERRUPTED`，不猜测或补造结果。
- `execution.common.current()` 明确拒绝 `now >= lease_expires_at`、Worker/版本/租约错配；现有 `fail()`、`start_finalizing()`、`finish()` 均依赖该检查，证明确需独立且受限的过期租约恢复事务，而不是复用正常执行入口。
- 用户已明确批准唯一新增 Interface 及上述最小语义；下一步用新红灯实现手动重试和 `rerun_of_job_id`，之后补真实 PostgreSQL 竞争验证。
