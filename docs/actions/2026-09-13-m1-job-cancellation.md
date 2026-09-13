# M1 Job 取消流程行动记录

## 状态

Paused（额度阈值中断）。用户已确认通俗方案；实现与内存/静态验证已形成检查点，真实 PostgreSQL 已通过，浏览器、权威文档同步和双轴评审尚待完成。本任务以任务 08 关闭提交 `c8a5957` 为固定评审基准。

## 情况说明

- 权威任务为 [09-job-cancellation.md](../../.scratch/m1-platform/issues/09-job-cancellation.md)，对应规格故事 30、31、32、51；公开行为以 [HTTP_API.md](../interfaces/HTTP_API.md) 第 7.6 节和 [DATA_MODEL.md](../architecture/DATA_MODEL.md) 的 Job/Run 状态机为准。
- 协作者只能取消自己提交的 Job，所有者可取消任意 Job；身份来自可信会话。待批准、排队和尚未启动 Trial 的准备态直接收束为 `CANCELED`；执行态先进入非终态 `CANCEL_REQUESTED`。
- 固定 Harbor 本地实现会一次性把所有 Trial 协程交给单并发队列，公开 CLI 没有只撤销尚未开始 Trial 的入口。用户已确认在既有执行生命周期中增加最小协作式停止：平台记录取消后，当前 Trial 不受影响；每个后续 Trial 真正启动前读取停止信号并不再启动。
- 不新增数据库表、执行后端或平行执行链。深化既有 `evaluation_jobs`、Job Repository、Job execution、Harbor adapter/entry 和页面；不改变 `PatchEvaluator`，不删除或覆盖既有结果与证据。
- Judge/Review 保持不变；不运行真实模型、不强杀真实容器、不部署、不推送、不更改机器或网络设置。

## 实施措施

1. 先通过 HTTP seam 写红灯，固定授权、幂等、直接取消、终态冲突和可信审计字段；随后只实现使该切片通过的领域值、应用用例、Repository 事务和 route。
2. 通过真实临时 PostgreSQL 写取消与批准/领取竞争红灯，确保一个事务胜出、事件序列一致，取消后无法批准或领取。
3. 通过受控执行 adapter 写执行中红灯：取消只设置请求；当前 Run 保存真实结果；后续 `PENDING` Run 原子改为 `CANCELED`；Job 经 `FINALIZING` 收束为 `CANCELED`。
4. 在既有 `ExecutionProgressObserver` 增加最小停止查询，在 Harbor entry 与父进程之间使用本次证据目录内的私有停止标记；固定单并发队列只在 Trial 开始前检查，不终止活跃 Trial。
5. Web 明确显示“已请求取消，当前运行仍在收束”和“已取消”，只在允许状态提供按钮；浏览器覆盖请求受理到终态。
6. 同步架构、数据模型、模块契约和 HTTP 当前事实；执行定向/完整后端、Ruff/mypy、真实临时 PostgreSQL、Web typecheck/build、浏览器及规模检查。最后以 `c8a5957` 为基准并行做 Standards/Spec 评审、修复并复验。

## 需要修改的文件树

```text
apps/backend/src/eval_platform/
├─ domain/jobs/{models,cancellation}.py               # 状态、取消请求值与正文规范化
├─ application/
│  ├─ job_lifecycle/cancellation.py                   # 可信授权与取消 Application Service
│  ├─ ports/{repositories,execution}.py               # Repository 事务与执行停止 Interface
│  └─ execution/{batch,run_results}.py                 # 取消感知编排与结果保存
├─ adapters/
│  ├─ persistence/jobs/{schema,records,repository,cancellations,state_validation}.py
│  │                                                   # 同表字段、读回和原子取消事务
│  ├─ persistence/jobs/execution/                     # 领取、开跑、取消与最终收束事务
│  └─ execution/{harbor_entry,harbor/}.py              # 私有停止标记与 Trial 前协作检查
└─ delivery/http/
   ├─ app.py                                           # 既有装配
   └─ routes/jobs/{routes,schemas,cancel_schemas}.py   # 取消 route、请求和真实状态响应
apps/backend/tests/jobs/
├─ test_cancellation.py                               # HTTP/内存各阶段、授权与幂等
├─ cancellation/test_cancel_races.py                  # PostgreSQL 事务竞争
├─ support/cancellation.py                            # 内存 Repository 共用取消事务
└─ execution/{batch,cancellation,support}/             # 受控执行与 Harbor 停止协议
apps/web/src/
├─ features/jobs/{details,cancellation}.tsx            # 请求态/终态文案和控制
└─ lib/{contracts,job-client,job-shapes,jobs/}.ts      # 取消契约与拆分后的运行时解析
apps/web/tests/jobs.spec.ts                            # 浏览器请求到终态
docs/{architecture,interfaces}/                       # 当前状态机、Module Interface 与 HTTP 契约
.scratch/m1-platform/issues/09-job-cancellation.md     # 九号任务验收状态和证据
```

采用 Application Service、Repository、Ports/Adapters 与 Cooperative Cancellation（协作式取消）模式。Job Repository 是状态与事务唯一事实源；执行进度 Interface 只暴露“还能否开始下一 Trial”，Harbor adapter 隐藏跨进程停止细节，HTTP 和 Web 不接触 Worker/Harbor 内部标记。

## 自验证方式与成功标准

- HTTP：协作者只取消自己的 Job，所有者可取消任意 Job；正文不能伪造身份；同幂等键同正文稳定重放，异正文冲突，其他重复或终态请求返回状态冲突。
- 事务：待批准/排队/无 Trial 启动的准备态直接 `CANCELED`，全部未启动 Run 同事务取消；取消与批准/领取只有一个结果，取消胜出后不可批准或领取，事件连续且审计人/时间/说明准确。
- 执行：`EXECUTING → CANCEL_REQUESTED` 不等于停止；当前 Trial 仍可在冻结超时内保存真实结果/失败证据；后续 Run 不进入 `RUNNING_AGENT`，改为 `CANCELED`；最终 Job 为 `CANCELED`。
- 安全：取消不覆盖既有 deterministic result、artifact 或已完成 Run，不使用请求正文身份，不删除证据，不自动重试或强杀当前 Harbor/模型进程。
- 页面：请求返回后展示“已请求取消/仍在收束”，最终才展示“已取消”；按钮状态、错误和重新读取均反映 HTTP 实际状态。
- 分层运行定向与完整 pytest、Ruff、mypy、真实临时 PostgreSQL、Web typecheck/build、Playwright 和 `git diff --check`；动态源码每文件不超过 200 行，受影响目录每层不超过 8 个直接文件。

## 自验证情况

- TDD 红灯已实际出现并驱动实现：取消 route 起初返回 `404`；准备态取消起初返回 `409`；执行中取消起初抛出 `JobStateConflict`；Harbor 父子停止协议起初分别因构造参数和缺少 controlled runner 失败。对应切片修复后均转绿。
- `apps/backend/tests/jobs -q`：`65 passed, 19 skipped, 2 warnings`。跳过项是需要外部 PostgreSQL/真实执行条件的既有分层测试，未冒充通过。
- 后端 `mypy src/eval_platform`：`Success: no issues found in 130 source files`。
- 后端 `ruff check src tests/jobs`：`All checks passed!`。
- Web `npm run typecheck`：通过；尚未运行生产 build 和 Playwright。
- 规模与补丁检查：本任务变更的 Python/TypeScript/TSX 源码均未超过 200 行；`git diff --check` 通过。Git 的 LF/CRLF 输出仅为工作区换行提示。
- 真实隔离 PostgreSQL+MinIO 首轮为 `1 failed, 83 passed, 2 warnings`：失败断言误把“批准先完成后，从 QUEUED 合法取消”视为不一致。数据库实际串行化正确；测试已改为固定两种合法事件序列（提交→取消，或提交→批准→取消），同时要求最终 Job/Run 均为 `CANCELED` 且返回值与事件吻合。
- 同一专属脚本复验为 `84 passed, 2 warnings in 28.46s`。三个容器均无发布端口、无宿主挂载；两轮都在 `finally` 中按唯一标签和精确 ID 删除，tmpfs 测试数据已移除，固定镜像和构建缓存按授权保留。
- 尚未完成：Web build、浏览器请求到终态、后端全量测试、权威架构/数据模型/接口同步、任务单八项验收回填，以及基于 `c8a5957` 的 Standards/Spec 双轴评审。

## 中断恢复点

- 2026-09-13 按用户要求约五分钟检查额度时，Codex 周期额度为已用 98%、剩余约 2%，因此自动停止新工作；两张可用 Full reset 均未使用。
- 已提交实现检查点 `d0cf278`（`feat: add cooperative job cancellation`）。该提交不是任务 09 验收完成点；其后只修正了 PostgreSQL 竞争测试契约和测试文件末尾空行，并更新本记录。
- 恢复时先核对 `git status/log/diff` 与额度，不 pull/reset/push；继续保留未暂存的混合旧文档、缓存与 framework/runtime。
- 下一验证顺序：Web `npm run build` → `npm run test:e2e -- jobs.spec.ts` → 默认完整后端测试 → Ruff/mypy/规模与 diff 复核。浏览器只使用既有合成服务，不运行真实模型。
- 验证通过后同步当前现场中的架构、数据模型、模块契约、HTTP 接口和任务单八项证据；随后以 `c8a5957` 为固定基准并行执行 Standards/Spec 评审，修复、复验、记录并本地提交。任务 09 全部完成前不进入任务 10。
