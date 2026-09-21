# Job 控制 Module

> 当前状态：M1 提交、批准、领取、批次推进、取消、恢复与保留协作已实现；长期 PostgreSQL 已部署，continuous 1–20 预设及旧库显式升级入口已落地。
> 权威范围：Job/Run 从创建到终态的控制职责和现实代码地图。精确状态与表约束以[数据模型](../../DATA_MODEL.md)为准。

## 1. 职责与非职责

本 Module 冻结一次评测请求，创建完整 Job×Run 矩阵，等待 owner 决定，把批准项发布到 PostgreSQL 队列，由单机 Worker 原子领取并推进状态；同时处理协作式取消、崩溃后人工恢复和显式新 Job 重试。

它不执行模型、不判断 patch 是否正确、不保存对象正文，也不自动审批、强杀当前 Trial、自动续跑或自动重试。

## 2. Interface 与不变量

- `JobSubmission`：校验目录项、规模/限制/赛道和幂等键，冻结快照并创建 `AWAITING_OWNER_APPROVAL` Job。
- `OwnerApproval`：只有 owner 能把待批 Job 原子变为 `QUEUED` 或 `REJECTED`。
- `JobCancellation`：待批/排队可直接取消；执行中只请求停止后续 Run。
- `JobRecovery`：按持久证据把过期 lease/中断状态收束，不自动重跑；用户重试会创建关联的新 Job 并重新等待批准。
- `JobRepository`：提交、决策、claim、lease、Run 状态、终态、报告索引和保留删除审计的 persistence seam。
- 当前正式队列只有 PostgreSQL；`FOR UPDATE SKIP LOCKED` 和 lease/advisory-lock 规则由 Adapter 隐藏。

精确错误、方法和状态迁移见[模块契约](../../MODULE_CONTRACTS.md)与[数据模型](../../DATA_MODEL.md)。

## 3. 当前 Implementation 文件树

```text
apps/backend/src/eval_platform/
  domain/jobs/
    models.py                         # Job/Run/事件值与错误
    snapshots.py                      # 任务、配置、限制、网络、工具冻结值
    policy.py                         # 提交规模、超时/lease 与恢复策略
    factory.py                        # 完整 Job×Run 矩阵和初始事件
    decisions.py                      # owner 批准/拒绝值与幂等摘要
    cancellation.py                   # 取消请求和值规范化
    execution.py                      # claim、lease、报告和制品索引值
  application/
    job_submission.py                 # 提交、冻结、幂等和查询
    owner_approval.py                 # owner 决定用例
    job_lifecycle/cancellation.py     # 协作取消用例
    job_lifecycle/recovery.py         # 中断收束与显式新 Job 重试
    job_lifecycle/retention.py        # owner 原始制品清理协作
    ports/repositories.py             # JobRepository Interface
  adapters/persistence/jobs/
    __init__.py                       # 建表入口与 continuous CHECK 显式幂等升级
    schema.sql                        # Job/Run/事件/结果/制品索引及约束
    repository.py                     # 聚合 PostgreSQL Job Repository Adapter
    publication.py                    # Job/Run/初始事件原子发布
    decisions.py / cancellations.py   # 决定与取消事务
    execution/                        # claim、lease、批次推进、结果与终态事务
    recovery/                         # 过期 lease 和中断状态恢复
    reporting/                        # Job/Run/排行榜读取模型
    retention/                        # 删除意图、确认与审计状态
    records.py / state_validation.py  # 数据库记录还原和不变量校验
  delivery/
    jobs.py                           # 显式 schema/continuous 升级/保留维护及 Job 用例装配
    job_presets.py                    # 可信批次、限制、网络和工具策略
    worker/main.py                    # 一次 claim 后委托 JobExecutor 的薄 Worker shell
    http/routes/jobs/                 # 提交、查询、决定、取消、恢复、报告 HTTP 翻译
apps/web/src/features/jobs/           # 提交、批准、详情、取消、恢复、报告和证据 UI
```

文件树中的目录项表示内部职责聚合，不是新的顶层 Module。`JobRepository` 虽实现较多方法，但调用者只通过同一持久化 seam 使用一致的 Job/Run 状态与事务规则。

## 4. 关键数据流

```text
协作者/owner 提交
  → 目录读取并冻结快照
  → PostgreSQL 原子创建 Job + 全部 Runs + 初始事件
  → owner 批准
  → QUEUED
  → Worker 原子 claim + lease
  → Execution/Evaluation 逐 Run 回调状态和证据索引
  → FINALIZING
  → COMPLETED / COMPLETED_WITH_ERRORS / FAILED / CANCELED
```

HTTP 返回并不触发长任务；FastAPI 和 Worker 通过 PostgreSQL 交接。所有者电脑关机时，已持久化的 Job 仍在库中，但不会继续执行或接受新请求。

## 5. 模式、依赖和深度

`JobRepository` 是应用与 PostgreSQL 之间的 seam；`PostgresJobRepository` 是 Adapter。状态机、锁、lease、事件序列和恢复判断隐藏在实现中，Web、HTTP 和 Worker 不各写一套 SQL。

取消与 claim 可能并发，因此 Job 读取事务使用 `REPEATABLE READ` 固定同一请求内的快照：取消请求不能在同一次业务判断中一半看到旧状态、一半看到新状态。并发最终仍由行锁、版本和状态前置条件裁决，不靠页面时序保证。

本 Module 依赖 Identity 提供 actor、Catalog 提供可冻结记录；执行 Module 依赖本 Module 的 claim/进度 Interface。Job Control 不依赖 Harbor 的配置格式或模型秘密。

## 6. 当前验证与缺口

历史动作与实际验证分散在任务 04–08、11–13 的行动文档中，当前状态总入口见 [`HANDOFF.md`](../../../../HANDOFF.md)。2026-09-20 的合并后修复已在隔离真实 PostgreSQL 验证旧三值约束升级、新四值约束幂等和未知约束失败关闭；共享长期库只读确认已经是四值且约束有效。HTTP 启动仍不自动迁移。

未完成项不等于 Module 重做：长期 PostgreSQL、启动/停止与重启后持久性验收已完成；备份恢复已由用户明确移出课设范围。`continuous` 允许 1–20 道，五道新题资格门禁和六题白名单也已完成；任务 04 当前等待人工确认。当前仍坚持一个重型 Job、每组合一次尝试、零自动重试。
