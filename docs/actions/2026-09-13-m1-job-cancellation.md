# M1 Job 取消流程行动记录

## 状态

Completed。用户已确认的取消方案、主实现、分层验证、两轮双轴评审及八项验收均已完成。本任务以任务 08 关闭提交 `c8a5957` 为固定评审基准；评审修复提交为 `02eb391`。

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
├─ cancellation/test_cancel_states.py                 # HTTP/内存各阶段、授权与幂等
├─ cancellation/test_cancel_races.py                  # PostgreSQL 事务竞争
├─ support/cancellation.py                            # 内存 Repository 共用取消事务
└─ execution/
   ├─ cancellation/                                   # 取消期间编排与 HTTP 行为
   ├─ batch/                                          # 批次阶段和报告 HTTP
   └─ support/{memory_cancellation,memory_reports}.py # 内存停止与报告辅助
apps/web/src/
├─ features/jobs/{details,cancellation}.tsx            # 请求态/终态文案和控制
└─ lib/{contracts,job-client,job-shapes,jobs/}.ts      # 取消契约与拆分后的运行时解析
apps/web/tests/jobs.spec.ts                            # 浏览器请求到终态
docs/{architecture,interfaces}/                       # 当前状态机、Module Interface 与 HTTP 契约
.scratch/m1-platform/issues/09-job-cancellation.md     # 九号任务验收状态和证据
```

采用 Application Service、Repository、Ports/Adapters 与 Cooperative Cancellation（协作式取消）模式。Job Repository 是状态与事务唯一事实源；执行进度 Interface 只暴露“还能否开始下一 Trial”，Harbor adapter 隐藏跨进程停止细节，HTTP 和 Web 不接触 Worker/Harbor 内部标记。`application/job_lifecycle/` 和 `web/src/lib/jobs/` 创建时各自父目录已达 8 个直属文件，因此保留必要子目录；这不是为未知未来功能预留层级。

## 自验证方式与成功标准

- HTTP：协作者只取消自己的 Job，所有者可取消任意 Job；正文不能伪造身份；同幂等键同正文稳定重放，异正文冲突，其他重复或终态请求返回状态冲突。
- 事务：待批准/排队/无 Trial 启动的准备态直接 `CANCELED`，全部未启动 Run 同事务取消；取消与批准/领取按行锁串行化为合法一致序列，取消提交后不可批准或领取，事件连续且审计人/时间/说明准确。
- 执行：`EXECUTING → CANCEL_REQUESTED` 不等于停止；当前 Trial 仍可在冻结超时内保存真实结果/失败证据；后续 Run 不进入 `RUNNING_AGENT`，改为 `CANCELED`；最终 Job 为 `CANCELED`。
- 安全：取消不覆盖既有 deterministic result、artifact 或已完成 Run，不使用请求正文身份，不删除证据，不自动重试或强杀当前 Harbor/模型进程。
- 页面：请求返回后展示“已请求取消/仍在收束”，最终才展示“已取消”；按钮状态、错误和重新读取均反映 HTTP 实际状态。
- 分层运行定向与完整 pytest、Ruff、mypy、真实临时 PostgreSQL、Web typecheck/build、Playwright 和 `git diff --check`；动态源码每文件不超过 200 行，受影响目录每层不超过 8 个直接文件。

## 自验证情况

- TDD 红灯已实际出现并驱动实现：取消 route 起初返回 `404`；准备态取消起初返回 `409`；执行中取消起初抛出 `JobStateConflict`；Harbor 父子停止协议起初分别因构造参数和缺少 controlled runner 失败。对应切片修复后均转绿。
- `apps/backend/tests/jobs -q`：`65 passed, 19 skipped, 2 warnings`。跳过项是需要外部 PostgreSQL/真实执行条件的既有分层测试，未冒充通过。
- 后端 `mypy src/eval_platform`：`Success: no issues found in 130 source files`。
- 后端 `ruff check src tests/jobs`：`All checks passed!`。
- Web `npm run typecheck`：通过。生产 build 首次在编译前因沙箱拒绝 Next.js 用户级配置写入而 `EPERM`；只对当前进程设置 `NEXT_TELEMETRY_DISABLED=1` 后通过，Next 编译 3.0 秒，没有更改机器配置。
- 规模与补丁检查首轮脚本误报“无超过 200 行”；Standards 复核实际发现 `harbor_entry.py` 206 行、`test_http_stages.py` 201 行和 `memory.py` 204 行。评审修复已下沉 Harbor control 配置、压缩测试签名并拆出内存取消/报告辅助；最终规模和 `git diff --check` 须在复验后回填。
- 真实隔离 PostgreSQL+MinIO 首轮为 `1 failed, 83 passed, 2 warnings`：失败断言误把“批准先完成后，从 QUEUED 合法取消”视为不一致。数据库实际串行化正确；测试已改为固定两种合法事件序列（提交→取消，或提交→批准→取消），同时要求最终 Job/Run 均为 `CANCELED` 且返回值与事件吻合。
- 同一专属脚本复验为 `84 passed, 2 warnings in 28.46s`。三个容器均无发布端口、无宿主挂载；两轮都在 `finally` 中按唯一标签和精确 ID 删除，tmpfs 测试数据已移除，固定镜像和构建缓存按授权保留。
- 浏览器 `jobs.spec.ts` 首轮为 1 failed / 3 passed：旧批准用例把冲突刷新后的实际状态硬编码为五秒内 `COMPLETED`，任务 09 为稳定命中 `EXECUTING` 增加的合成延迟使正确页面停在执行中。改为验证已离开待批且批准审计可见后，第二轮再次 1 failed / 3 passed，暴露旧用例仍断言任务 08 前的证据文案。同步为已验收的“安全证据/轨迹只含可观察事件”后，最终 `4 passed in 19.8s`；包含执行中取消从请求态到最终 `CANCELED`。3100/8875 无监听，测试时钟不存在，未下载浏览器或运行真实模型/Harbor。
- 默认完整后端首轮为 `1 failed, 337 passed, 66 skipped, 2 warnings`：旧上传测试按 `_run` 私有位置参数索引取 bundle 路径，新增 control 参数使索引漂移。测试改为通过公开 `execute()` 可观察的暂存目的地验证，定向 `1 passed`；完整复验为 `338 passed, 66 skipped, 2 warnings in 32.82s`。66 项是未启用的外部 PG/MinIO/Docker/Harbor/Fork 门控；任务 09 的 PG 已由专属脚本覆盖。
- 权威 `ARCHITECTURE.md`、`DATA_MODEL.md`、`MODULE_CONTRACTS.md`、`HTTP_API.md` 和 `HARBOR_EXECUTION.md` 已按现场同步取消状态、审计/幂等字段、Repository/Observer Interface、Harbor ready/permit/stop 协议及固定 revision 私有绑定风险；过期租约恢复仍明确留给任务 10。由于这些文件含此前未提交增量，终审必须读取整个现场，最终提交也只暂存可明确归属任务 09 的补丁。
- 最终静态复核中，mypy 对 130 个源码文件通过、Web typecheck 通过、动态源码无超过 200 行；Ruff 首次发现浏览器合成服务 1 处导入排序和 7 个任务文件未格式化，机械修正后 `ruff check src tests` 与 `ruff format --check src tests` 均通过（221 文件已格式化）。旧“取消未落地/取消路由未注册”文字检索无命中。目录检查发现 `tests/jobs` 因新增取消主测试达到 9 个直接文件，已把该文件移入既有 `tests/jobs/cancellation/` 并改为唯一 basename，使父目录恢复为 8 个；移动后回归待执行。
- 收尾状态：Spec 与 Standards 最终复审均 PASS；任务单八项验收已回填。评审修复已提交为 `02eb391`，本行动记录和任务单的关闭事实由后续文档提交保存。
- 首轮双轴评审已完成但未通过。Spec 发现两项 P1：执行态取消在 Job 收束后以同键重放会错误返回当前 `CANCELED`，而非首次 `CANCEL_REQUESTED`；取消若在结果对账首次状态采样后提交，未启动 Run 可能被结果缺失分支写成 `FAILED`。Standards 发现恢复文档/接口页头仍是旧快照、3 个 Python 文件超过 200 行，并指出用户取消与 Worker 停止的持久化更新重复；两个单文件子目录属于父目录 8 文件上限下的必要分层，须补充设计理由而非扁平化。
- 评审修复采用测试先行：新增“执行态首次受理状态在最终收束后仍原样重放”和“结果对账采样后取消仍只取消未启动 Run”两条红灯；随后让 Repository 原子区分失败与协作式停止，统一未启动 Run 取消写入，并把 Harbor control 配置下沉到既有生命周期模块。修复后重新执行全部分层验证和 Standards/Spec 复审。
- 两条新增回归首次运行均失败：重放得到 `CANCELED` 而非 `CANCEL_REQUESTED`，竞争窗口中的 Run 全部变为 `FAILED`；修复后定向复验为 `4 passed, 2 warnings`。生产 Repository 由第一条取消事件恢复首次受理状态；结果缺失事务在行锁内观察 `CANCEL_REQUESTED` 时复用统一的未启动 Run 取消写入，应用层按真实落盘状态区分失败与停止。
- 评审修复后的 Jobs 定向回归为 `67 passed, 19 skipped, 2 warnings`，mypy 对 130 个源码文件通过，Ruff 修正一处新导入排序后通过。真实隔离 PostgreSQL+MinIO 首轮修复复验为 `86 passed`；补入 PostgreSQL 版“对账停止+最终收束后重放”后再验为 `87 passed, 2 warnings in 27.72s`，三容器仍无发布端口/宿主挂载并已精确清理。
- 默认完整后端最终复验为 `340 passed, 67 skipped, 2 warnings in 40.18s`；新增 PostgreSQL 项在默认环境按设计跳过，已由专属真实存储脚本覆盖。Web typecheck 通过，生产 build 通过（编译 972ms）。浏览器第一次受运行证据文件 `EPERM` 阻断，第二次因未指向项目已有固定浏览器缓存而 4 项均在 launch 前失败；设置进程级 `PLAYWRIGHT_BROWSERS_PATH=runtime/tools/playwright` 后同一 `jobs.spec.ts` 为 `4 passed in 20.1s`，未下载浏览器。
- 最终静态复验：`ruff check src tests`、`ruff format --check src tests`（223 文件）和 mypy（130 个源码文件）均通过；受影响 Python/TypeScript/TSX 无超过 200 行，受影响目录无超过 8 个直属文件，`git diff --check` 仅有 Git 的 LF/CRLF 工作区提示。

## 额度中断与恢复记录

- 2026-09-13 按用户要求约五分钟检查额度时，Codex 周期额度为已用 98%、剩余约 2%，因此自动停止新工作；两张可用 Full reset 均未使用。
- 用户随后明确要求先用完剩余约 2%，再使用一张 Full reset 继续；该授权只覆盖一次重置，已成功兑换；另一张保留且没有再次兑换授权。
- 恢复验证与文档同步后额度为已用 99%、剩余约 1%；先保存本地重要节点，再兑换已授权的一张重置。
- 已提交实现检查点 `d0cf278`（`feat: add cooperative job cancellation`）。该提交不是任务 09 验收完成点；其后只修正了 PostgreSQL 竞争测试契约和测试文件末尾空行，并更新本记录。
- 恢复时先核对 `git status/log/diff` 与额度，不 pull/reset/push；继续保留未暂存的混合旧文档、缓存与 framework/runtime。
- 以 `c8a5957` 为固定基准的 Spec 复审与 Standards 最终复审均 PASS。Standards 最后一轮只要求移除本记录的一处过期“尚未完成”描述，修正后定点确认通过，未发现新的高置信问题。
- 任务 09 已完成并停止在清晰提交边界；下一步按用户已授权的顺序进入任务 10，另建同任务唯一行动记录。
