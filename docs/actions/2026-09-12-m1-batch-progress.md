# M1 多题进度与部分失败行动记录

## 状态

Complete。任务 07 的 8 项验收全部完成；以 `e72a40d` 为固定基准的 Standards/Spec 双轴终审及 P2 定向复核均 PASS、无剩余 findings。M1/MVP 尚未完成，下一项为任务 08。

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
5. Harbor Adapter 以每个 Trial 的受信配置身份映射冻结 Run，在子进程轮询周期检查结果文件并发出规范化通知；不解析 stdout/stderr 推断业务阶段。Job 汇总缺失时仍保留可验证的逐 Trial 结果，未知、重复或损坏 Trial 形成协议警告；异常退出前精确清理本 Job 的 Harbor 项目。Fake 覆盖乱序、重复、超时和部分协议结果，真实 Harbor 不在本行动运行。
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
├─ domain/jobs/{execution,models,policy}.py  # Job 租约、整批预算、状态和批次报告值
├─ domain/result.py                          # 后端结果及安全不透明引用约束
├─ application/reporting/service.py          # official 报告范围门禁与证据复核
├─ adapters/
│  ├─ execution/harbor/
│  │  ├─ {adapter,process_runner,result_mapper}.py # 单 Harbor Job、异常清理和部分结果映射
│  │  └─ lifecycle/                          # 可信 Trial 文件观察、等待和清理
│  └─ persistence/jobs/
│     ├─ {repository,records,state_validation}.py # 接通并校验批次状态
│     └─ execution/                          # 领取、逐 Run、结果和最终化短事务
└─ delivery/http/routes/jobs/
   ├─ report_routes.py                       # 既有受保护 Job/Run 报告端点
   └─ {report_schemas,batch_schemas}.py      # 单 Run 与批次矩阵安全 DTO
apps/backend/tests/jobs/execution/
├─ batch/                                    # 多 Trial、租约、清理、存储失败、HTTP 与真实 PG
├─ test_reports_http.py                      # 身份范围、矩阵、中间态与 internal_test 隔离
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
- 安全补强采用红灯固定后再实现：旧租约在三 Run 默认预算下仅 3900 秒，新增完整后端/判卷/收尾预算后为 10920 秒；Harbor 汇总缺失、部分 Trial、宿主路径引用、Observer 异常清理、对象存储中段失败、HTTP 中间态、协议警告和 `CANCELED` 汇总都各有失败测试证明缺口，修复后的组合定向回归为 `24 passed, 2 warnings`，协议警告子集为 `7 passed`。
- internal-test 报告隔离先得到预期红灯 `200`（本应 404），随后生产 `JobReporting` 固定只发布 `official`；专用浏览器/PG 测试装配才显式注入内部范围，报告回归为 `6 passed`。2×2 报告顺序也先证明随机 Run ID 会打乱矩阵，现按 task→agent→run 排序。
- 本轮最终隔离 PostgreSQL + MinIO 验证为 `173 passed, 2 warnings in 38.86s`。测试驱动镜像为 `sha256:66747d7f...68306`，PostgreSQL/MinIO 固定镜像分别为 `sha256:5cce759a...a6b6`、`sha256:922042a6...aba8`；三个专属容器无发布端口、无宿主挂载。清理前数据库无 `identity_*` 临时行且 MinIO bucket 列表为空；随后按精确容器 ID 删除并确认名称不存在，镜像/缓存按授权保留。第一次把宿主路径契约测试误纳入容器范围导致收集失败、下一次因 PG 测试装配未显式启用内部报告得到 1 个失败，均如实保留，修正范围/装配后才得到上述结果。
- Web `typecheck`、生产 `build` 通过（编译 997 ms）。浏览器普通沙箱首次因不能删除专属结果目录中的 `.last-run.json` 得到 `EPERM`；使用同一项目内浏览器缓存重跑后五组共 12 项全部通过，其中任务 07 的批量进度刷新与逐项报告导航为 `1 passed`。结束后 3100/8875 无监听，测试时钟文件不存在；未下载浏览器或改机器设置。
- 最终默认后端为 `322 passed, 63 skipped, 2 warnings in 30.23s`；63 项是未启用的真实 PG/MinIO、Docker、Harbor、Fork 等门控检查，不能计为通过，本任务 PG/MinIO 已由上项专属脚本单独覆盖。mypy 对 119 个源码文件通过，Ruff check 通过；Ruff format 首次指出 `batch_schemas.py` 需要机械换行，格式化后 205 个文件通过，相关 HTTP 回归为 `7 passed, 2 warnings`。全部动态源码不超过 200 行，六个受影响目录分别为 4/8/7/7/7/8 个直接文件；`git diff --check` 无错误，仅显示 Windows 工作区既有 LF→CRLF 提示。
- 当前基线固定为 `e72a40d`；权威架构/数据/接口现场已同步租约预算、报告范围、后端引用和 Harbor 部分结果契约。实现提交为 `978d17e`，终审修复提交为 `a4f1581`。
- Spec 终审指出 `CANCELED` 项虽计入“未完成”，页面却没有报告入口。新增拒绝 2 Run 的浏览器断言先得到期望 2、实际 0 的红灯；加入终态入口后，实际点击又以页面 `JOB_NOT_FOUND` 证明浏览器测试内存仓储未像生产 PostgreSQL 一样组合无确定性结果的最小 Run 报告。最终统一三个 Run 终态、让测试 Repository 返回所有 Run 报告，并验证取消项可打开“本次没有形成确定性成绩”。中间一次直接 Playwright CLI 因不符合项目 runner 的动态文件约定得到 `No tests found`，一次将 Next build 与 dev 并行导致验证互扰，随后均改回既有 runner 串行执行。最终后端定向 `13 passed, 2 warnings`、Web typecheck/build、Ruff 及浏览器 `1 passed (10.0s)` 通过；最后一次完整后端仍为 `322 passed, 63 skipped, 2 warnings in 30.07s`。

## 双轴评审结论

| 评审轴 | 初审 | 修复后复核 | 残余风险 |
|---|---|---|---|
| Standards | PASS，无 findings | Spec P2 小改定向复核仍 PASS | `application/execution/batch.py` 已到 200 行，Harbor 与批次测试目录各到 8 个直接文件；后续扩展前先拆分 |
| Spec | 1 个 P2：`CANCELED` Run 无法从矩阵进入最小报告 | PASS，无 P0/P1/P2/P3 findings | 未重跑真实 Harbor/模型；取消和过期租约恢复属任务 09/10；长期部署、远程双机和最终真实闭环未验收 |

两路评审都读取了 `e72a40d` 到当前未提交现场及权威文档，不只审阶段提交。Judge/Review 没有修改或调用；63 项门控跳过仍明确不计为通过。
