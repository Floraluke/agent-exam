# LLY 开发过程文档

> 维护人：LLY（五人分工中的成员 E 占位代号，负责「执行与判卷」Module）
> 建立日期：2026-09-18

本目录归集 **E 模块负责人的开发过程材料**：计划、本地环境搭建记录、进度日志和问题记录，目的是让开发过程可追溯、便于交接与复盘。

## 这个目录不放什么（重要）

项目已有权威文档，同一事实只在**一处**维护。以下内容必须写在权威位置，本目录只用链接引用：

| 事实类型 | 权威位置 |
|---|---|
| 系统架构、模块边界、依赖方向 | [`docs/architecture/`](../architecture/) |
| HTTP 路由与请求/响应 | [`docs/interfaces/HTTP_API.md`](../interfaces/HTTP_API.md) |
| 表结构、状态机、对象键 | [`docs/architecture/DATA_MODEL.md`](../architecture/DATA_MODEL.md) |
| 本机部署与运维事实 | [`docs/operations/`](../operations/) |
| 已实施行动的过程与证据 | [`docs/actions/`](../actions/) |
| 团队分工与任务归属 | [`TEAM_WORK_ALLOCATION.md`](../architecture/modules/TEAM_WORK_ALLOCATION.md) |
| 扩展任务的规格、计划、实现地图与验收规范 | [`.scratch/ui-catalog-providers/`](../../.scratch/ui-catalog-providers/)：[规格](../../.scratch/ui-catalog-providers/spec.md)、[计划](../../.scratch/ui-catalog-providers/plan.md)、[实现地图](../../.scratch/ui-catalog-providers/implementation-map.md)、[验证规范](../../.scratch/ui-catalog-providers/verification.md) |
| 扩展任务单（01、02 已发布） | [`.scratch/ui-catalog-providers/issues/`](../../.scratch/ui-catalog-providers/issues/)：[01 可点击 HTML 原型](../../.scratch/ui-catalog-providers/issues/01-clickable-html-prototype.md)、[02 A 版角色工作台与提交审批闭环](../../.scratch/ui-catalog-providers/issues/02-role-workbench-submission-approval.md) |

**规则：** 某项事实一旦成为项目级结论（别人也要用它），必须提升到上表对应的权威文档，并在本目录只留链接。不要在本目录复制字段表、路由表或数据库表结构，否则会出现两份会各自过期的事实。

## 分类

| 目录 | 放什么 |
|---|---|
| [`01-plan/`](01-plan/) | 计划书、阶段拆分、待确认事项 |
| [`02-environment/`](02-environment/) | 本地开发环境（PostgreSQL、Python、前端依赖）的搭建与复现步骤 |
| [`03-progress/`](03-progress/) | 进度日志，按日期追加，只记事实与实际结果 |
| [`04-issues/`](04-issues/) | 已记录的问题：现象、证据、处理过程、遗留风险 |

## 当前状态

- **第三块实施计划（准备件，新会话据此开工）**：[`01-plan/STAGE1_PROXY_SERVICE_PLAN.md`](01-plan/STAGE1_PROXY_SERVICE_PLAN.md)（`service.py` 与接线的流水线顺序、文件树、分片 S6a–S6e、取证规则、阻塞与风险；S10/S11 等 T2）
- 阶段 1 实施方案：[`01-plan/STAGE1_IMPLEMENTATION_PLAN.md`](01-plan/STAGE1_IMPLEMENTATION_PLAN.md)（文件树、S1–S11 分片、逐片验证与机器归属、待授权清单；**S3–S7 与 T1 已实施，S2/`service.py`/S8–S9 未做；T2 待窗口**）
- 计划书：[`01-plan/PLAN.md`](01-plan/PLAN.md)
- 阶段 1 测试设计：[`01-plan/STAGE1_PROXY_TEST_DESIGN.md`](01-plan/STAGE1_PROXY_TEST_DESIGN.md)（准备性设计，05 未开工，不代表已授权或已运行）
- 阶段 1 设计冻结底稿：[`01-plan/STAGE1_PROXY_DESIGN_FREEZE.md`](01-plan/STAGE1_PROXY_DESIGN_FREEZE.md)（数值部分负责人已确认；机制候选；**T1 已证成、T2 未证**）
- 阶段 1 负责人交付要求：[`01-plan/TASK05_OWNER_DELIVERY.md`](01-plan/TASK05_OWNER_DELIVERY.md)（负责人已回填 9 项决定；**6 项前置 3/6，总判定仍 STOP**）
- 负责人只读核对（填充版）：[`01-plan/TASK05_OWNER_DELIVERY_FILLED.md`](01-plan/TASK05_OWNER_DELIVERY_FILLED.md)（第 0–6 节为首次核对当时状态，第 7 节为后续回执；原文未改，仅加一行归档说明）
- 负责人决定与授权回执：[`01-plan/TASK05_OWNER_ACTION_REQUIRED.md`](01-plan/TASK05_OWNER_ACTION_REQUIRED.md)（**9 项已全部拍板，第 7 项选 A 保守上界**；资源范围已确认但**本轮无执行窗口、不运行探针**）。三份构成"请求 → 回复 → 回执"配对
- 扩展任务进展：P、任务 01、任务 02、任务 04 已完成；03 无独立任务单但 B 在推进；**05 正在本机实施：S3–S7 已实现并有测试（`pytest tests/providers` 67 passed / 1 skipped），T1（纯 Docker 层拓扑）已在本机证成；S2、`service.py`、S8–S9 未做**。E 模块主责 05、06、07，配合 04 与 08，详见[计划书第 1、3 节](01-plan/PLAN.md)
- 任务 05 本机实施进度与证据：[本机实施行动](../actions/2026-09-21-task05-local-implementation.md) 第"自验证情况"节（含 T1 探针 run 02 的原始记录；探针本体在 `.gitignore` 排除的 `runtime/prototype/t05-topology-20260921-02/`）
- 本地环境：阶段 0 已完成；数据库实时运行状态只在 [`02-environment/LOCAL_SETUP.md`](02-environment/LOCAL_SETUP.md) 维护
- 未决问题：见 [`04-issues/KNOWN_ISSUES.md`](04-issues/KNOWN_ISSUES.md)
- 对应行动记录：[初始环境搭建](../actions/2026-09-18-lly-local-dev-environment.md)、[阶段 0 两库隔离与验收](../actions/2026-09-19-stage0-local-development-plan.md)、[归档计划文档与同步 origin/main](../actions/2026-09-21-file-plan-docs-and-sync.md)、[阶段 1 测试设计准备](../actions/2026-09-21-stage1-proxy-test-design.md)、[起草任务 05 任务单](../actions/2026-09-21-draft-task-05-issue.md)、[组长机器执行预案](../actions/2026-09-21-task05-owner-machine-runbook.md)、[任务 05 设计冻结](../actions/2026-09-21-task05-design-freeze.md)、[任务 05 负责人侧交付要求](../actions/2026-09-21-task05-owner-delivery.md)、[归档负责人回复与修复断链](../actions/2026-09-21-task05-owner-response-filing.md)、[待负责人回执文档](../actions/2026-09-21-task05-owner-round2.md)、[归档负责人回执与 B 对齐](../actions/2026-09-21-task05-owner-receipt-and-b-alignment.md)、[任务 05 实施方案与 Docker 前提变更](../actions/2026-09-21-task05-implementation-plan.md)、[本机实施开工（S3–S7 与 T1）](../actions/2026-09-21-task05-local-implementation.md)、[fengyy 侧任务 05 负责人文档同步](../actions/2026-09-21-feng-sync-task05-owner-docs.md)
