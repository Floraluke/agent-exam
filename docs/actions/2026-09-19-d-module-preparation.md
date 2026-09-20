# 2026-09-19 D 模块开工准备（Job 控制 + 证据与报告）

## 状态与情况说明

状态：In progress（2026-09-19 创建；本批只做只读梳理与文档交付，不改产品代码）。当前完成度：本地分支已建、本文档与三份清单已交付、行号抽查通过；**遗留**：远程分支 `xinyue-d-modules` 尚未建立（本机无 GitHub 凭据、GitHub 连接不稳定），见「自验证结果」第 4 条。

范围：只覆盖成员 D 负责的两个 Module——**Job 控制**与**证据与报告**——的开工准备。本批交付一份行动文档与三份清单（现状地图 / 接口清单 / 待办候选），为后续任务 02、03、04、05–07、08 的实施提供基础。

来源请求：刘欣悦（成员 D）于 2026-09-19 要求开始 D 的工作，并明确三条前置条件：
1. 开工前先在**远程仓库**建立本人分支；
2. 除本人分支外，**其他人的分支慎之又慎**（不 checkout、不推送、不合并、不删除）；
3. 必须**明确知道要创建什么文档**才能开始。

本行动的授权边界（成员 D 再次确认的红线）：

- 只允许修改本人分支 `xinyue-d-modules` 上属于 D 两个 Module 的文件；
- 涉及他人模块、公共 Interface、数据库 schema、共享文档时，必须先报告并取得确认；
- 不提交、不推送代码；不合并、不 rebase、不删除任何分支；不碰 `main`；
- 不调用真实模型、不下载大体量镜像、不安装依赖环境、不把任何密钥写入文件。

范围澄清（2026-09-19，成员 D 明确）：D 只按分工完成 **08（主责项）**；其余任务（02/03/04/05–07）中的参与交付属组内安排范围，未获安排时不做。远程分支改由成员 D 在 GitHub 网页手动创建（本机凭据推送方案已放弃，后台推送已于同日停止）。

当前事实（核对基准 `6dfa2be`，即本行动开始时的 `main`）：

- 本地分支 `xinyue-d-modules` 已建立（基于 `6dfa2be`）；远程分支**尚未建立**——2026-09-19 三次推送尝试分别被连接超时/连接重置打断，第 4 次到达认证环节后因本机无 GitHub 凭据失败。远端 `main`、`fengyy-fixweb`、`lly/dev` 指针未被改动。
- D 的两个模块已在 M1 任务 04–12 中实现，并有隔离环境验收记录（见 [`2026-09-12-m1-job-submission.md`](2026-09-12-m1-job-submission.md)、[`2026-09-12-m1-owner-approval.md`](2026-09-12-m1-owner-approval.md)、[`2026-09-12-m1-single-run-report.md`](2026-09-12-m1-single-run-report.md)、[`2026-09-12-m1-safe-evidence.md`](2026-09-12-m1-safe-evidence.md)、[`2026-09-12-m1-batch-progress.md`](2026-09-12-m1-batch-progress.md)、[`2026-09-13-m1-job-cancellation.md`](2026-09-13-m1-job-cancellation.md)、[`2026-09-13-m1-interruption-recovery.md`](2026-09-13-m1-interruption-recovery.md)、[`2026-09-13-m1-artifact-retention.md`](2026-09-13-m1-artifact-retention.md)、[`2026-09-13-m1-base-leaderboard.md`](2026-09-13-m1-base-leaderboard.md)）。这些记录证明"实现存在且有验收证据"，不等于本批重新验证。
- 扩展任务 01–08 仍为规划编号、未发布任务单（`.scratch/ui-catalog-providers/` 下没有 `issues/` 目录）；D 在其中的交付见 `docs/architecture/modules/TEAM_WORK_ALLOCATION.md` §5（`:859` 起）。
- 两个模块的架构文档各自声明："本轮没有重跑任何状态机、HTTP、浏览器或 PostgreSQL 测试"，历史验证分散在任务 04–13 行动文档（`docs/architecture/modules/job-control/ARCHITECTURE.md:86`、`docs/architecture/modules/evidence-and-reporting/ARCHITECTURE.md:86`）。

已知未知项：

- 本机 GitHub 凭据未配置，远程分支创建待成员 D 处理后重试；
- owner 何时发布 01–08 任务单、D 的第一个正式任务编号，尚未确认。

明确排除项（本批不做）：

- 不修改任何产品代码、测试或配置；
- 不运行 `uv sync` / `npm ci` 等环境安装，因此**本批不产生"测试通过"的结论**；
- 不连接共享 PostgreSQL、不调用真实模型、不访问 MinIO。

## 一、现状地图（D 的两个模块）

### 1.1 Job 控制（`apps/backend/src/eval_platform/`）

| 位置 | 职责 | 关键不变量（位置） |
|---|---|---|
| `domain/jobs/models.py` | Job/Run/事件的不可变值与安全失败类别 | 11 种 Job 状态（`:23-35`）、7 种 Run 状态（`:36-44`）、`run_order_key` 确定性序（`:121-128`）、lease 字段（`:155-158`） |
| `domain/jobs/factory.py` | 从冻结输入构建待批 Job（纯函数） | 初始状态固定 `AWAITING_OWNER_APPROVAL`（`:37`）、笛卡尔积"一组合一 Run"（`:43-67`）、`attempt_index=1` |
| `domain/jobs/policy.py` | 服务端自有策略、恢复与租约计算 | 只有持久化 lease 过期才允许恢复（`:29-37`）；恢复结果**绝不回到可重跑态**（`:40-53`）；`maximum_agent_configurations=3`、`maximum_runs=60`（`:137-138`）；`max_retries`（`:116`） |
| `domain/jobs/snapshots.py` | 与 C 的冻结边界 | `TaskSnapshot.from_record` 重算 `problem_sha256`（`:58-76`）；`AgentSnapshot.from_record` 带指纹（`:92-106`） |
| `domain/jobs/execution.py` | E 的交接契约与只读报表值 | `ClaimedJob`（`:45-48`）；`ArtifactDeletionIntent` 审计不变量（`:59-76`）；`RunReport/JobReport`（`:110-125`）；由冻结 Run 还原执行输入并校验指纹（`:128-157`） |
| `application/job_submission.py` | 校验→冻结→落库，不执行 Agent | 幂等重放（`:83-85`）、上限校验（`:63-71`）、可见性范围（`:113-135`） |
| `application/owner_approval.py` | 仅授权与记录决策 | owner 校验（`:39-40`）、幂等键与正文哈希（`:41-52`） |
| `application/job_lifecycle/cancellation.py` | 取消授权+持久化 | 可见性判定（`:39-41`）、归一化（`:42`） |
| `application/job_lifecycle/recovery.py` | 显式恢复；恢复即收束 | 恢复不得续跑（`:25-30`）；重试必须已终态且存在 `INTERRUPTION_RECOVERED`（`:41-50`），并生成**全新 Job**（`:51-63`） |
| `application/job_lifecycle/retention.py` | 所有者驱动的到期清理 | 先验证、再确认、再删除、最后记账（`:36-51`） |
| `application/ports/repositories.py` | Job 仓储端口（对 E/B 的接口面） | `resolve_idempotency/create/decide/cancel/recover/claim/...`（`:58-147`） |
| `adapters/persistence/jobs/schema.sql` | 数据库层不变量 | `UNIQUE (created_by, idempotency_key_hash)`（`:54`）、`attempt_index = 1`（`:62`）、矩阵唯一 `UNIQUE (job_id, task_id, agent_configuration_id, attempt_index)`（`:87`）、`trial_count BETWEEN 1 AND 60`（`:22`）、COMPLETED 与 `resolved_summary` 等价（`:86`） |
| `adapters/persistence/jobs/repository.py` | PG 适配器，每方法一事务 | `claim` 为唯一 `ClaimedJob` 构造点（`:101-109`）；DB 失败不留半个矩阵（全程 `job_transaction`） |
| `adapters/persistence/jobs/publication.py` | 单事务发布 Job+矩阵+初始事件 | 幂等 `ON CONFLICT DO NOTHING`（`:32`）+ 正文不符即冲突（`:56-64`）；落库瞬间再次确认 C 侧快照未漂移（`:122-173`） |
| `adapters/persistence/jobs/state_validation.py` | 读路径全状态一致性（第二道防线） | 各状态 Run 子集约束（`:5-81`） |
| `adapters/persistence/jobs/execution/claims.py` | 队列领取 | **单重型 Job**：advisory lock + 已有活动 Job 即拒绝（`:15-26`） |
| `adapters/persistence/jobs/execution/cancellation.py` | 协作式取消 | 只取消 PENDING/PREPARING，其余不动（`:14-37`） |
| `adapters/persistence/jobs/execution/finalization.py` | 终态收束 | 取消优先（`:66-67`）；无失败→COMPLETED、混合→COMPLETED_WITH_ERRORS、全败→FAILED（`:95-100`） |
| `adapters/persistence/jobs/recovery/actions.py` | 只按持久化事实收束 | 未到期拒绝（`:34-35`）；**绝不重跑**，只写 `INTERRUPTION_RECOVERED`（`:50-66`） |
| `delivery/jobs.py`、`delivery/job_presets.py` | 本机 CLI 与版本化策略 | 装配唯一入口（`jobs.py:29-44`）；`default-single-host-v1` 并发 1、零重试（`job_presets.py:30-46`） |
| `delivery/http/routes/jobs/` | Job HTTP 适配器 | 幂等头约束（`routes.py:28-31`）、规范化文案（`batch_schemas.py:46-67`）、错误码唯一映射 `delivery/http/errors.py:82-105` |

测试位置：`apps/backend/tests/jobs/`（提交/幂等 `test_http.py`、`test_security.py`、`test_concurrency.py`；批准 `test_approval.py`；取消 `cancellation/`；恢复 `recovery/`；领取与编排 `execution/`；Worker `runtime/`）。

### 1.2 证据与报告（`apps/backend/src/eval_platform/`）

| 位置 | 职责 | 关键不变量（位置） |
|---|---|---|
| `domain/artifacts.py` | 封闭制品词汇表 | 公开制品与 raw 制品集合不相交（`:55`、`:62`） |
| `domain/result.py` | 制品引用/用量/结果值对象 | 制品不可变 + SHA-256 形态（`:49-52`）；删除审计三字段同生同灭（`:63-69`）；文件名不得含路径（`:56-60`）；completed 必有 patch（`:130-134`） |
| `domain/leaderboard/models.py` | 排行榜比较域与汇总 | 结果身份与 run 状态一致（`:78-83`）；**指标是 value+coverage 对**（`:94-109`） |
| `domain/leaderboard/policy.py` | 去重/分母/分类/并列策略 | 区分 false/基础设施失败/未完成/缺失/unknown（`:125-130`）；未开始不计入分母（`:28-36`）；全量分母（`:73-76`）；**缺失即 None，绝不填 0**（`:135-145`）；不可比 scope 独立排名（`:43-63`） |
| `domain/leaderboard/query.py` | 查询值与稳定游标 | 游标不可伪造（`:44-50`） |
| `application/reporting/service.py` | 受保护的报告查询服务 | 无权与不存在收敛 404（`:98-100`、`:142-144`）；**MinIO 正文与 PG 索引摘要一致**（`:131-139`）；对象键必须归属本 run 前缀（`:132-137`） |
| `application/reporting/evidence.py` | 公开证据视图 | 只暴露公开制品（`:80-81`）；公开文本先过脱敏校验（`:86`、`:123`）；轨迹行封闭 schema（`:129-151`） |
| `application/reporting/leaderboard.py` | 只读排行榜服务 | 未启用赛道显式拒绝（`:17-18`） |
| `application/ports/artifacts.py` | 制品端口 | 协议级明文声明不可变/回读校验/缺失即不可用（`:23-28`） |
| `adapters/artifacts/minio.py` | MinIO 适配器 | 摘要回读（`:36-39`、`:60`）；缺失不等于空（`:70-84`）；只删经字节校验的 live raw（`:112-131`） |
| `adapters/artifacts/policy.py` | durable 制品身份白名单 | object_key 形态 `runs/{uuid}/{type}/{sha256}`（`:74`）；long_term 与 raw_30d 互斥（`:37-52`） |
| `adapters/artifacts/bounded.py` | 有界读取 | 仍哈希全部字节（`:33-34`）；截断 marker 固定（`:20-26`） |
| `adapters/persistence/jobs/reporting/rows.py` | 聚合前校验 | 官方执行身份不可漂移（`:27-31`）；结果身份与 run 状态一致（`:92-107`） |
| `adapters/persistence/jobs/reporting/validation.py` | 冻结证据 fail-closed | 快照与目录表逐字段相等（`:44-77`）；agent 指纹可重算（`:98-135`） |
| `adapters/persistence/jobs/retention/records.py` | 可审计的过期清理 | CAS 全字段匹配 + owner + active（`:50-58`）；无 verified 审计即拒（`:134-135`） |
| `delivery/http/routes/artifacts.py`、`artifact_schemas.py`、`leaderboard/` | 制品/轨迹/排行榜 HTTP | 只有 GET 无 DELETE（`artifacts.py:86-96`）；**报告不泄漏 object_key**（`artifact_schemas.py:13-29`）；content_status 四态显式（`:55-61`）；quality_tiebreak 恒为 None（`leaderboard/schemas.py:80`） |

测试位置：`apps/backend/tests/jobs/artifacts/`（限额、清理、HTTP 状态）、`apps/backend/tests/jobs/execution/`（证据发布、存储、报告 HTTP）、`apps/backend/tests/leaderboard/`（策略、HTTP、真实 PG）。

## 二、接口清单（对 B / C / E / A）

**对 B（Web/HTTP）——请求与响应 DTO**

| 交接物 | 位置 |
|---|---|
| `JobRequest` / `CancelRequest` / `OwnerDecisionRequest` / 生命周期空体 | `routes/jobs/schemas.py:13`、`cancel_schemas.py:11`、`decision_schemas.py:11`、`lifecycle/schemas.py:4` |
| `JobSummary` / `JobDetail` / `JobPage` | `routes/jobs/schemas.py:70`、`:115`、`:183` |
| `JobOptionsResponse` / `JobReportResponse` | `routes/jobs/batch_schemas.py:18`、`:97` |
| `RunReportResponse`（= `RunReport` 的 DTO） | `routes/jobs/report_schemas.py:65`；领域类型 `domain/jobs/execution.py:111` |
| 制品索引 / 轨迹 / 下载 | `routes/artifacts.py:55`、`:73`、`:86` |
| 排行榜 | `routes/leaderboard/routes.py:32` |
| 路由挂载与错误处理 | `delivery/http/app.py:77`、`:117-120`；错误码唯一映射 `delivery/http/errors.py:82-105` |
| 幂等头契约 | `routes/jobs/routes.py:28-31`、`lifecycle/routes.py:14-17` |

**对 E（执行与判卷）**

- 交接对象：`ClaimedJob`（`domain/jobs/execution.py:45-48`），唯一构造点 `adapters/persistence/jobs/repository.py:109`（`claim` 与 `JobLease` 一起）。
- 消费入口：`application/execute_job.py:48`（`JobExecutor.execute`）→ `start_execution`（`:50`）→ `_request`（`:72-95`）把冻结 Run 还原为执行请求（`restore_public_task`/`restore_agent`，`domain/jobs/execution.py:128-157`）。
- 执行期回调契约：`application/ports/repositories.py:87-118`（start_run→finish_run_execution→start_verifying→complete/fail→start_finalizing→finish）。
- 报告侧读回：`adapters/persistence/jobs/execution/reports.py:19`。

**对 C（目录与配置）**

- 读取入口：`application/job_submission.py:86-93`（Task 走 `TaskCatalog.get`，Agent 走 `AgentRegistry.get`）。
- 冻结点（唯一）：`domain/jobs/snapshots.py:58-76`（Task）与 `:92-106`（Agent），在 `job_submission.py:86-98` 调用、`factory.py:43-67` 写入 Run、`publication.py:66-86` 落库。
- 防漂移双向校验：落库瞬间 `publication.py:122-173`；读时 `records.py:41-46`、`:64-65`；排行榜路径 `reporting/validation.py:44-77`。
- 边界要点：Job 侧只读 C 的目录与制品；`AgentSnapshot` 刻意剔除凭据值（`snapshots.py:88`）。

**对 A（身份与成员）**

- `AuthenticatedActor` 可见性：`job_submission.py:113-135`（owner 可跨 `created_by`，协作者强制 scope）。

**当前冻结点说明**：以上形状来自 M1 已验收实现，属于**冻结契约**；扩展任务 02/03/04 若要改动其中任何一项，按"契约先于联调"由提供方 D 先更新 `docs/interfaces/HTTP_API.md` 与 `docs/architecture/MODULE_CONTRACTS.md`，再通知 B/E。

## 三、待办候选（D 参与的交付）

> 说明：01–08 **不是 D 一个人的任务**。任务 DRI 分别是：01/02/03 = B，04 = C，05/06/07 = E，**08 = D（主责）**；其余任务里 D 只是参与方，交付的是下表"D 的交付"列出的那一片。M1-14 由 A 主责、D 配合。另：任务 01/02 已由 owner 完成（见下"外部输入更新"），02 中"D 的契约"交付已随之完成。

| 任务 | D 的交付 | 现在能否独立开工 | 依赖 | 预估 |
|---|---|---|---|---|
| 02 两角色首页、列表、提交/审批 | 提交、审批、取消/恢复**契约** | 契约设计可先做；产品代码等任务单 | 01 原型确认（按计划）；与 B/E 对齐 | 8h |
| 03 对比报告、详情、目录管理 | 报告、证据和**缺失语义** | 否（真依赖） | 02 的会话/导航壳 | 12h |
| 04 五道新题与 1–20 规模 | Job **快照**、最多 60 Runs、兼容 | **技术上无依赖**（文档原话："技术上不依赖新 UI"） | 按节奏排在 UI 后；需 C 的 preset 配合 | 10h |
| 05–07 提供方接入 | 额度、状态、证据接法 | 技术上无硬依赖，按节奏 | 05 安全门禁；E 主责 | 11h |
| 08 冻结矩阵与全量回归 | 12 Run 矩阵、状态/报告、验证清单与总结（**主责**） | 否（真依赖） | 03、04、06、07 已验收 | 14h |
| M1-14 私有双机协作验收 | 配合 Job/报告证据 | 已发布、进行中 | A 主责，需与 A 对 | — |

建议顺序（若获准提前开工）：**02 的契约部分 → 04 的 Job 快照/规模 → 03 的报告语义 → 05–07 的额度与证据 → 08**。理由：前三者在 D 的模块内可自证，且不需要真实模型或外部环境；08 必须最后做。

**2026-09-19 外部输入更新**：冯颖怡发来更新后的规划文件夹（本机路径 `C:\Users\Admin\Documents\xwechat_files\wxid_rsj6khrsk6vm22_3eb8\msg\file\2026-09\ui-catalog-providers\ui-catalog-providers\`），含更新后的 `spec.md` / `plan.md` / `implementation-map.md` / `verification.md` 与新增的 `issues/`。据其核对：

- **任务 01（可点击 HTML 原型）与任务 02（A 版角色工作台与提交审批闭环）均已完成**：两份任务单全部验收项勾选、状态为 `ready-for-human`；任务 02 记录 32 条浏览器回归、类型检查、生产构建、31 项 API 对账与双轴评审完成。
- **03–08 仍未发布、未授权实施**：更新后的 `plan.md` 首部与任务 02 的 Comments 均明确写明"任务 03 未发布、未授权"。
- 本工作区副本（`6dfa2be`）**尚未包含**这批新文件；它们属共享计划区，不复制进本分支，等 owner 推送/合并后按正常拉取获取。
- 对 D 的影响：分工表里"D 在 02 的契约交付"已由 owner 在任务 02 中一并完成；下一个可能发布、且含 D 交付的是 **03（报告、证据与缺失语义，B 主责）**，目前仍待发布。

## 实施措施

1. 建立本人分支 `xinyue-d-modules`（本地已完成；远程推送待 GitHub 凭据与网络恢复后重试）。
2. 创建本行动文档，并把只读梳理的三份清单写入（本批交付）。
3. 只读核对：抽查本文件引用的关键行号与源文件一致。
4. 下一步（需成员 D 批准后另开本行动的后续批次）：产出"第一个代码增量提案"，精确到文件、测试与验证命令。

完成标准：本文件行号可核对；`git status` 只显示新增本文档；产品代码零改动。

## 受影响文件树

本批只新增一个文档，不改动任何其他文件：

```text
docs/actions/2026-09-19-d-module-preparation.md   # 本行动文档（新增）；D 模块现状地图、接口清单、待办候选
```

不改动（本批明确排除）：`apps/backend/src/eval_platform/**`（产品代码）、`apps/backend/tests/**`（测试）、`docs/architecture/**`、`docs/interfaces/**`、`.scratch/**`（owner 的计划区）、`main` 及任何他人分支。

## 自验证方式

本批为文档批次，验证方式如下（全部为只读命令）：

1. `git status --short`：预期只出现 `?? docs/actions/2026-09-19-d-module-preparation.md`（外加工具自身的 `.zcode/`），无任何已跟踪文件被修改。
2. `git branch --show-current`：预期 `xinyue-d-modules`；`git rev-parse HEAD`：预期 `6dfa2bee285e71e073b0286370b7e24257b367ad`。
3. 行号抽查：对本文引用的以下位置逐一打开核对——`domain/jobs/policy.py:20-37`、`:137-138`；`domain/jobs/execution.py:45-48`；`adapters/persistence/jobs/repository.py:101-109`；`adapters/persistence/jobs/schema.sql:62`、`:87`；`application/reporting/service.py:131-139`；`domain/leaderboard/policy.py:125-130`、`:135-145`。
4. 远端核对（网络可用时）：`git ls-remote --heads origin` 确认 `main`、`fengyy-fixweb` 指针不变。

说明：本批**不运行**测试套件（未安装依赖环境，且不在授权范围内），因此不产生任何"测试通过"结论；上文引用的既有验收结论来自对应行动文档，未在本批重新执行。

## 自验证结果

完成时间：2026-09-19（本批）。逐项实测：

1. `git status --short` 实测输出：

   ```text
   ?? .zcode/
   ?? docs/actions/2026-09-19-d-module-preparation.md
   ```

   `.zcode/` 是工具自身产生的会话目录，与本行动无关、不纳入任何提交。除两者外**没有任何已跟踪文件被修改**——产品代码零改动，结论成立。

2. 分支与基点：`git rev-parse --abbrev-ref HEAD` → `xinyue-d-modules`；`git rev-parse HEAD` → `6dfa2bee285e71e073b0286370b7e24257b367ad`，与开始时的 `main` 相同。
   偏差说明：本机 git 不支持 `git branch --show-current`（版本较旧），改用 `git rev-parse --abbrev-ref HEAD` 达到同一验证目的。

3. 行号抽查（`rg`/`sed` 实测，全部与本文引用一致）：
   - `domain/jobs/execution.py:46` `class ClaimedJob`；
   - `adapters/persistence/jobs/repository.py:101` `def claim`、`:109` `ClaimedJob(record, lease)`（唯一构造点）；
   - `application/reporting/service.py:102` `def _verify`、`:131-139` 对象键前缀校验与 `read_verified` 回读；
   - `domain/leaderboard/policy.py:66` `_row`、`:125` `_classification`、`:133` `_metrics`；
   - `domain/result.py:27` `class ArtifactRef`；`domain/leaderboard/models.py:94` `class MetricSummary`。
   - 由本人直接阅读核对的项：`domain/jobs/policy.py:20-37`（恢复策略）、`:137-138`（上限 3 配置 / 60 Run）；`adapters/persistence/jobs/schema.sql:62`（`attempt_index = 1`）、`:86`（COMPLETED 与 `resolved_summary` 等价）、`:87`（矩阵唯一）。

4. 远端核对：**未完成**。过程中 `git ls-remote --heads origin` 成功过一次（当时读到 `main = 6dfa2be`、`fengyy-fixweb = 6dfa2be`、`lly/dev = 469ba1d`，三者均未被本行动改动）；其后的三次 `git push` 与最终核对均被连接超时/重置打断，第 4 次到达认证环节后因本机无 GitHub 凭据失败。**远程分支 `xinyue-d-modules` 尚未建立**，为唯一遗留项。

5. 测试：**未运行**（未安装依赖环境，且不在本批授权范围）。本文引用的既有验收结论来自 M1 任务 04–13 的行动文档（每篇均为 `Completed`，并记录专属 PG/MinIO 用例数），本批未重新执行，因此不产生任何新的"测试通过"结论。

遗留与下一步：

- 远程分支创建：改由成员 D 在 GitHub 网页从 `main` 新建 `xinyue-d-modules`（本地同名分支已存在且基点相同，不冲突）；
- 成员 D 的范围：只做 **08（主责）**；其前置（03、04、06、07 验收）未满足前不实施；
- 08 执行预案已追加于下节（草稿，待任务发布后确认）。

## 环境与基线（2026-09-19 追加）

为具备"改完代码能立刻自验证"的能力，在本机（D 分支、无产品代码改动）完成开发环境准备：

1. 安装 `uv`（`python -m pip install --user uv`，版本 `0.12.17`；可随时用 `pip uninstall uv` 卸载）。说明：依赖总表中另固定 `0.12.10` 供部署工具链使用；本次为开发环境，依赖版本仍由 `uv.lock` 严格锁定。
2. 执行 `uv sync --locked --no-python-downloads`，建立 `apps/backend/.venv`（`.gitignore` 已忽略，不进提交）。
3. 运行后端全量测试（默认门禁；需显式启用的专属 PostgreSQL/MinIO/Docker 用例自动跳过）：

   ```text
   2 failed, 386 passed, 82 skipped, 2 warnings in 51.02s
   ```

4. 两个失败的逐条核查（读源码确认，非推测）：均位于 `apps/backend/tests/contract/test_execution_network.py`——
   - `:109` 需要运行 `framework/harbor/.venv/Scripts/python.exe`；
   - `:129` 需要 `git -C framework/harbor show <revision>:...`。
   共同原因是本机未恢复固定上游源码 `framework/harbor`（`DEPENDENCIES.md` 第 7 节指定的恢复路径）。属**环境缺口，非代码缺陷**，与 D 的两个模块无关。
5. D 模块测试（`tests/jobs/`、`tests/leaderboard/`）本次全部通过；跳过项为需显式启用的专属 PG/MinIO/Docker 用例，与既有行动文档口径一致。

结论：D 已具备本地"改动 → 立即验证"能力；唯一缺口是需要上游 Harbor 源码的两个契约测试（如后续需要，按 `DEPENDENCIES.md` 第 7 节恢复 `framework/harbor`，属只读参考，不影响他人分支）。

### 本机数据库与集成测试（2026-09-20 追加，参照 `lly/dev` 的已验证做法）

在成员 E（`lly/dev`，2026-09-19 提交）已公开的本机环境方案基础上，本机补齐了**不依赖 Docker、不依赖 Tailscale、不需要数据库密码**的数据库能力：

- 安装便携版 PostgreSQL **15.14** 到 `D:\pgsql`（解包自官方 `postgresql-15.14-1-windows-x64-binaries.zip`，320,461,864 字节，MD5 `48218bceef0b293898f76566b8500a8d`，与下载源元数据一致）；
- 数据目录 `D:\pgsql\data`，仅监听 `127.0.0.1:55432`，回环信任认证；
- 建立两库：`agentexam_identity_test`（测试控制库，`CREATEDB`）与 `agentexam_dev`（日常开发库）；
- 用项目自带入口装 schema：`AGENTEXAM_DATABASE_URL=<dev dsn> owner init-db` → `agentexam_dev` 实测 **11 张表**；
- 开启数据库门禁后跑全量：**2 failed / 438 passed / 36 skipped（101.15 秒）**；相比默认基线（2 / 392 / 82）**多出 46 个真实 PostgreSQL 用例并全部通过**（Job 存储与状态事务、Run 报告、排行榜、目录冻结校验、成员事务等），失败集合不变（仍是缺 `framework/harbor` 的 ISSUE-04）；
- 运行方式（进程级环境变量，不写入系统或仓库）：

  ```text
  AGENTEXAM_TEST_DATABASE_URL=postgresql://agentexam_identity_test@127.0.0.1:55432/agentexam_identity_test
  AGENTEXAM_RUN_IDENTITY_POSTGRES=1
  → cd apps/backend && <上述变量> ./.venv/Scripts/python.exe -m pytest -q
  ```

- 已知限制：便携版不是 Windows 服务，**重启电脑后需手动启动**：

  ```text
  D:\pgsql\bin\pg_ctl.exe -D "D:/pgsql/data" -l "D:/pgsql/data/pg_ctl-start.log" -o "-p 55432 -c listen_addresses=127.0.0.1" start
  ```

- 下载的安装包保留在 `D:\pgsql-binaries.zip`（320 MB），确认无需保留后可删除。

## 08 执行预案（草稿；待任务发布后确认）

依据：`plan.md` 第 10 节（08 冻结矩阵与全量回归）与任务映射表（D 主责：12 Run 矩阵、状态/报告、验证清单与总结）。以下为**待确认草稿**，不是已批准的实施计划。

- **矩阵**：6 题 × 2 个新 API 配置 = 12 个 Run，连同 06/07 两个烟测共 14 次真实 Run；每次一次尝试、**零自动重试**、并发 1。
- **逐 Run 记录**：终态（Job/Run 状态与事件）、确定性结果（补丁应用、FAIL_TO_PASS/PASS_TO_PASS、resolved）、可获得用量与费用、轨迹/证据引用、基础设施失败与题目失败分开、清理证据。
- **统计口径**：分母为完整矩阵（含未完成与基础设施失败）；**缺失/未知不得写成 0**；报告要能区分"未通过"与"未运行/基础设施失败"。
- **回归清单（按 `verification.md`）**：默认后端、Web 类型检查与生产构建、浏览器动线、隔离真实存储、代理与固定 Fork 回归；旧 ChatGPT 链用合成数据回归，不消耗真实 auth。
- **评审与收口**：双轴（Standards/Spec）评审 → 修复 → 定向重验（必要时全量）；逐项列"通过/失败/跳过/延期"；M1-14 未关单时不得宣布整个 MVP 完成。
- **停止条件**（照抄计划）：超额风险、未知 usage、泄漏或计量状态丢失时按代理合同关闭；真实失败不自动补满；不为挑好看结果而复跑。
- **开工前必须重新确认**：模型型号/价格/预算、真实调用授权、五道新题与六题集合冻结。

### 08 记录模板（草稿；发布后按此填写）

任务步骤与验收标准的权威来源是 [`plan.md` 第 10 节](../../.scratch/ui-catalog-providers/plan.md)；本节只提供**记录骨架**，不复制任务步骤。

每个 Run 一行；**缺失/未知一律留空并标注"缺失"，不写 0**。

| # | 题目 instance_id | 配置 | Run 状态 | 终态 | resolved / FAIL_TO_PASS / PASS_TO_PASS | 用量与费用 | 基础设施失败码 | 证据引用（patch/报告） | 清理确认 | 备注 |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | | | | | | | | | | |
| 2 | | | | | | | | | | |
| … | | | | | | | | | | |
| 12 | | | | | | | | | | |

批次级汇总（与矩阵渲染的覆盖率一致）：

- 配置 A：有结论 __/6；缺失 __；通过 __；未通过 __；基础设施失败 __；未完成 __
- 配置 B：有结论 __/6；缺失 __；通过 __；未通过 __；基础设施失败 __；未完成 __
- 口径：分母 = 完整矩阵（含缺失）；不得把缺失计入"未通过"，也不得从分母扣除。
- 报告生成：用本分支原型的 `application/reporting/matrix.py` + `matrix_markdown.py` 把两批报告渲染成 Markdown 对比表，粘贴进验收报告。
