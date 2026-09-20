# LYQ 开发过程文档

> 维护人：LYQ（五人分工中的成员 C，负责「目录与配置」Module）
> 建立日期：2026-09-20

本目录归集 **C 模块负责人的开发过程材料**：我负责模块的个人视图、计划、进度日志和问题记录，目的是让开发过程可追溯、便于交接与复盘。

目录结构参照成员 E 已建立的 [`docs/LLY/`](../LLY/) 约定。

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
| 我负责模块的权威架构 | [`catalog-and-configuration/ARCHITECTURE.md`](../architecture/modules/catalog-and-configuration/ARCHITECTURE.md) |

**规则：** 某项事实一旦成为项目级结论（别人也要用它），必须提升到上表对应的权威文档，并在本目录只留链接。不要在本目录复制字段表、路由表或数据库表结构，否则会出现两份会各自过期的事实。

## 分类

| 目录 | 放什么 |
|---|---|
| [`01-plan/`](01-plan/) | 我负责范围的计划书、阶段拆分、待确认事项 |
| [`02-module/`](02-module/) | 我负责模块的架构、输入输出契约、接口的**个人视图**；正文仍在权威文档 |
| [`03-progress/`](03-progress/) | 进度日志，按日期倒序追加，只记事实与实际结果 |
| [`04-issues/`](04-issues/) | 已记录的问题：现象、证据、处理过程、遗留风险 |

## 当前状态

- 长期 Module：**目录与配置**（Task Catalog 题目目录 + Agent Registry 配置目录）
- 当前任务 DRI：**任务 04 五道新题入库与 1–20 连续规模**
- 状态：**准备阶段，产品开发未开工**。任务 04 尚未发布独立 issue，按项目规则不提前修改后续任务代码
- 计划书：[`01-plan/PLAN.md`](01-plan/PLAN.md)
- 未决问题：[`04-issues/KNOWN_ISSUES.md`](04-issues/KNOWN_ISSUES.md)
- 对应行动记录：[任务 04 行动文档](../actions/2026-09-19-task-04-catalog-candidates-and-scale.md)

## 日常 git 操作

仓库有两个远端：`upstream` 是团队仓库（`anphuchoang5-sys/agent-exam`），`origin` 是我自己的 fork（只作快照，不作为交付目标）。我个人的工作分支是 `lyq`。

```bash
git branch                 # 看当前在哪个分支，应该是 lyq
git fetch upstream         # 拉取团队最新提交（不动我的工作区）
git rebase upstream/main   # 把我的提交挪到团队最新之上
git status                 # 看改了哪些文件
git add <文件>              # 把改动放进待提交区
git commit -m "说明"        # 提交
git push                   # 推到团队仓库的 lyq 分支，PR 会自动更新
```

注意事项：

- 本仓库已配置 `http.proxy` 走本机代理（原因见 [ISSUE-01](04-issues/KNOWN_ISSUES.md)），所以上面这些命令能正常联网；若代理端口变了需要改配置。
- 不要在没有明确授权时 `git push` 到 `main`；合并由组长在 PR 页面操作。
- 写文档前先确认事实来源：能查代码的查代码，需要人类判断的（业务规则、范围）先问组长。

