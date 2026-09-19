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
| 扩展任务 01–08 的正式计划 | [`.scratch/ui-catalog-providers/plan.md`](../../.scratch/ui-catalog-providers/plan.md) |

**规则：** 某项事实一旦成为项目级结论（别人也要用它），必须提升到上表对应的权威文档，并在本目录只留链接。不要在本目录复制字段表、路由表或数据库表结构，否则会出现两份会各自过期的事实。

## 分类

| 目录 | 放什么 |
|---|---|
| [`01-plan/`](01-plan/) | 计划书、阶段拆分、待确认事项 |
| [`02-environment/`](02-environment/) | 本地开发环境（PostgreSQL、Python、前端依赖）的搭建与复现步骤 |
| [`03-progress/`](03-progress/) | 进度日志，按日期追加，只记事实与实际结果 |
| [`04-issues/`](04-issues/) | 已记录的问题：现象、证据、处理过程、遗留风险 |

## 当前状态

- 计划书：[`01-plan/PLAN.md`](01-plan/PLAN.md)
- 本地环境：阶段 0 已完成；数据库实时运行状态只在 [`02-environment/LOCAL_SETUP.md`](02-environment/LOCAL_SETUP.md) 维护
- 未决问题：见 [`04-issues/KNOWN_ISSUES.md`](04-issues/KNOWN_ISSUES.md)
- 对应行动记录：[初始环境搭建](../actions/2026-09-18-lly-local-dev-environment.md)、[阶段 0 两库隔离与验收](../actions/2026-09-19-stage0-local-development-plan.md)
