# M1 多题进度与部分失败行动记录

## 状态

In Progress。任务 07 已开始；用户已确认本行动中的最小 `ExecutionBackend` 进度通知方案。实现、验收和双轴评审尚未完成。

## 情况说明

- 权威任务为 [07-batch-progress.md](../../.scratch/m1-platform/issues/07-batch-progress.md)，固定评审基准为任务 06 关闭提交 `e72a40d`。
- 当前提交、批准、冻结矩阵和单 Run 报告已经存在，但基线 Worker、Repository 与编排器只允许 `trial_count=1`；后端仅在 Harbor 整批退出后返回全部结果，无法持久化逐 Trial 进度，也会在一个 Run 失败时提前结束整个 Job。
- 固定 Harbor `6af8d6e31eced13b93849cdf80feeadf24603d15` 提供 Trial 生命周期钩子，并逐 Trial写入 `config.json`/`result.json`；AgentExam 通过子进程 CLI 使用 Harbor，不能直接接入进程内钩子。因此生产 Adapter 把可信 Trial 文件生命周期规范化成受控通知，不能把日志文本当权威状态。
- 用户已确认最小方案：一个平台 Job 仍只创建一个 Harbor Job，`n_concurrent_trials=1`；既有 `ExecutionBackend.execute` 增加只传递受控 `started/finished` 身份的观察者 Interface，Job 编排器逐项持久化并判卷，后续失败保留先前可信结果。
- 任务 09、10 分别负责取消和中断恢复；本行动只验证错误 Worker、过期租约、重复/乱序通知、批内超时和部分结果，不预实现取消或完整崩溃接管。
- Judge/Review 模块、表、调用和实现保持不变；不运行真实模型、真实凭据或长期服务，不部署、不推送、不修改 Docker/WSL/代理/防火墙。

## 实施措施

1. 先用受控多 Trial Fake 写应用红灯，固定“一次后端调用、每个冻结 Run 恰好一次、逐 Run 开始/完成、重复和乱序拒绝、中间执行或判卷失败后继续、最终部分错误”的契约。
2. 深化既有执行 Port：新增最小 `ExecutionProgressObserver`，开始和结束通知都只携带冻结 `run_id`；同步返回值继续承载完整 `ExecutionTrialResult` 并用于最终身份闭合，避免新增异步框架。
3. 深化 Job Repository：一个 Job 租约携带当前 Job 版本；逐 Run 的开始、判卷、成功和失败各用短事务校验 Worker、租约、Job/Run 版本与单向状态，再追加持久化事件。
4. 改造 Job 编排器：一次构造完整矩阵请求并调用一次后端；按通知逐 Run 归档 patch、独立判卷和发布报告；单项失败只收束该 Run，全部通知闭合后才进入 `FINALIZING`，再按矩阵得到 `COMPLETED`、`COMPLETED_WITH_ERRORS` 或不可汇总的 `FAILED`。
5. Harbor Adapter 以每个 Trial 的受信配置身份映射冻结 Run，在子进程轮询周期检查结果文件并发出规范化通知；不解析 stdout/stderr 推断业务阶段。Fake 覆盖更细的乱序、重复与超时，真实 Harbor 不在本行动运行。
6. 扩展只读 Job 报告 HTTP 与批次页面，展示等待批准、排队、准备、执行、判卷、收尾和终态，以及任务/配置身份、成功、未解决、基础设施错误、未完成矩阵；已完成项可进入既有单 Run 报告。
7. 使用默认测试和专属临时 PostgreSQL 分层验收状态/事件重启一致性；Web 做 typecheck、build 和浏览器刷新/逐项导航。所有临时资源专属、无发布端口、无宿主挂载，按精确 ID 删除。
8. 以 `e72a40d` 为固定基准执行 Standards/Spec 双轴评审，修复后复评；关键节点仅显式暂存任务 07 文件并本地提交。

## 需要修改的文件树

以下是当前实现树；动态源码保持单文件不超过 200 行、每层目录不超过 8 个直接文件。

```text
apps/backend/src/eval_platform/
├─ application/
│  ├─ execute_job.py                         # 深应用服务；整批编排和最终收束
│  ├─ execution/{batch,completion}.py        # 通知编排、逐 Run 证据和结果归档
│  └─ ports/{execution,repositories}.py      # 进度观察者和批量状态事务契约
├─ domain/jobs/{execution,models}.py         # Job 租约、状态和批次报告值
├─ adapters/
│  ├─ execution/harbor/
│  │  ├─ {adapter,process_runner,result_mapper}.py # 单 Harbor Job、受控轮询和结果映射
│  │  └─ lifecycle/                          # 可信 Trial 文件观察、等待和清理
│  └─ persistence/jobs/
│     ├─ {repository,records,state_validation}.py # 接通并校验批次状态
│     └─ execution/                          # 领取、逐 Run、结果和最终化短事务
└─ delivery/http/routes/jobs/
   ├─ report_routes.py                       # 既有受保护 Job/Run 报告端点
   └─ {report_schemas,batch_schemas}.py      # 单 Run 与批次矩阵安全 DTO
apps/backend/tests/jobs/execution/
├─ batch/                                    # 多 Trial 编排、Harbor 观察与真实 PG
├─ test_reports_http.py                      # 身份范围、矩阵和中间态 HTTP
└─ support/                                  # internal_test 专用受控替身与内存仓储
apps/web/src/
├─ features/jobs/{details,batch-report}.tsx  # 批次阶段、矩阵和逐项入口
└─ lib/{contracts,batch-report-shapes}.ts    # 受控批次报告解析
apps/web/tests/job-batch.spec.ts             # 刷新后进度与逐项报告导航
docs/actions/2026-09-12-m1-batch-progress.md # 本行动唯一持续记录
.scratch/m1-platform/issues/07-batch-progress.md # 验收状态与证据
docs/architecture/{ARCHITECTURE,DATA_MODEL,MODULE_CONTRACTS}.md # 当前批次实现
docs/interfaces/{FRAMEWORK_INTERFACES,HARBOR_EXECUTION,HTTP_API}.md # 接口契约
```

采用 Ports/Adapter、Repository、Application Service（应用服务）与 Observer（观察者）模式。Observer 只跨执行 Port 传递经过适配的领域事件；所有能改变权威状态的校验和幂等性仍在 Repository 事务内，Harbor 文件或通知本身不能直接改数据库。

## 自验证方式与成功标准

- 执行契约：一个平台 Job 只调用一次后端并只产生一个 Harbor Job；请求含完整冻结矩阵，`n_concurrent_trials=1`；每个 `(task, agent, attempt=1)` 恰好一次。
- 状态安全：HTTP 可观察 Job 的批准/排队/准备/执行/收尾/终态和 Run 的等待/准备/Agent/判卷/终态；安全说明不泄漏日志、路径或凭据。刷新与新 Repository 实例恢复相同事件序列。
- 幂等与租约：未知 Run、错误 Job、错误 Worker、过期租约、陈旧版本、完成后重复、结束先于开始和跨 Run 污染均不能推进或倒退；合法重复只能安全忽略且不得追加重复事件/结果。
- 部分结果：中间 Trial 执行失败、判卷失败、超时或存储失败时，先前结果与证据保持可读；后续 Run 继续处理；矩阵明确区分 `resolved`、`unresolved`、`infrastructure_error`、`incomplete`。至少存在可信结果时 Job 以 `COMPLETED_WITH_ERRORS` 收束；完全不可汇总才使用 `FAILED`。
- 证据门禁：只有 patch 与 Fork 报告/输出均成功写入、读回并在数据库事务关联后，Run 才能完成；Job 只在所有 Run 已进入终态后完成或部分错误。
- 分层验证：定向 pytest、默认完整 pytest、Ruff format/check、mypy、真实临时 PostgreSQL、Web typecheck/build、Playwright 浏览器刷新与逐项导航、文件/目录指标、`git diff --check` 和资源残留核对均按实际输出记录。

## 自验证情况

- 应用层第一轮红灯：三 Run 测试得到 `1 failed, 2 warnings`，原因是旧内存仓储只允许 `trial_count=1`；随后接通整批领取、一次后端调用、逐 Run 事务与独立判卷。
- 状态契约第二轮红灯：将四个部分结果断言改为权威 `COMPLETED_WITH_ERRORS` 后得到 `4 failed, 3 passed, 2 warnings`，证实旧实现错误收束为 `FAILED`；修正领域 Literal、SQL 约束、最终化、HTTP 和页面后，同组得到 `7 passed, 2 warnings`。
- 当前受控后端回归（批次编排、Harbor 观察者、单题兼容、领取、HTTP、Harbor Adapter/进程清理）为 `28 passed, 2 warnings in 7.23s`。另增 2×2 多配置顺序红灯，先证明随机 Run ID 会打乱 Harbor 的 task×agent 次序，再统一应用、内存和 SQL 顺序后得到 `7 passed`；无 Trial ID 的外层超时红灯也已修复为保留 `EXECUTION_TIMED_OUT`。
- 最终真实临时 PostgreSQL + MinIO 为 `54 passed, 2 warnings in 19.19s`；测试驱动镜像 `sha256:53f7e62b...f9f88b`，PostgreSQL/MinIO 使用既有固定摘要，三个专属容器无发布端口和宿主挂载，脚本确认精确 ID 与 tmpfs 数据均删除，镜像/缓存按授权保留。
- Web 最终 `typecheck`、生产 `build` 通过（编译 1237 ms）。浏览器首次复跑因默认系统 Playwright 缓存缺少 Chromium，在创建浏览器前失败；随后只把测试进程指向项目已有固定缓存，未下载或改机器设置，得到 `1 passed (10.0s)`、用例本体 2.4 秒；3100/8875 无监听，测试时钟文件不存在。此前普通沙箱 `EPERM` 失败及精确进程清理仍保留为真实失败记录。
- 默认后端首次因清理模块拆分后的旧私有导入在测试收集阶段失败；修正测试导入后第二次发现 `_run` 新 Observer 参数使旧位置断言偏移；两项兼容修复后完整结果为 `312 passed, 63 skipped, 2 warnings in 37.11s`。63 项是未启用的真实 PG/MinIO、Docker、Harbor、Fork 等门控检查，不能计为通过；本任务 PG/MinIO 已由上项专属脚本单独覆盖。
- Ruff format 检查 201 个文件、Ruff check 全部通过；mypy 对 119 个源码文件通过。涉及目录直接文件数均不超过 8，动态源码均不超过 200 行。
- 当前基线固定为 `e72a40d`；权威架构/数据/接口现场已同步。关键提交、差异检查和双轴评审仍待完成，不能把以上分层结果冒充任务验收结束。
