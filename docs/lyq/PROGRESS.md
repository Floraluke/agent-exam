# 进度与 history：目录与配置（lyq / 成员 C）

## 1. 我的任务

| 项 | 内容 | 工时 |
|---|---|---|
| 长期 Module | 目录与配置（Task Catalog + Agent Registry） | — |
| **当前任务 DRI** | **任务 04：五道新题合格入库 + 1–20 连续规模** | 30 h |
| 参与 | 任务 03 目录动线 | 4 h |
| 参与 | 任务 05–07 提供方受控配置 | 14 h |
| 参与 | 任务 08 冻结目录回归 | 6 h |
| 合计 | | 54 h |

分工依据：[TEAM_WORK_ALLOCATION.md](../architecture/modules/TEAM_WORK_ALLOCATION.md) 第 4.2、5、6 节。任务正文见 [.scratch/ui-catalog-providers/plan.md](../../.scratch/ui-catalog-providers/plan.md) 第 6 节。

## 2. 时间线

| 日期 | 发生了什么 |
|---|---|
| 2026-09-12 | M1 任务 03 完成，目录与配置模块落地（当时由 A 主责）。这是本模块的前身，现在库里那一道题和一个 Codex 配置就是它留下的 |
| 2026-09-17 | 扩展规划文档建立（角色化 UI、至少五道新题、DeepSeek/Kimi 接入、连续规模） |
| 2026-09-18 | 五人分工确定，我成为目录与配置 DRI、任务 04 任务 DRI |
| 2026-09-19 | 我克隆仓库到本机；建立任务 04 行动文档；补出任务 04 的测试设计；推送开发分支 |
| 2026-09-20 | 按会议要求建立个人分支 `lyq` 和个人文档文件夹 `docs/lyq/` |

## 3. 现在卡在哪（2026-09-20）

这些都不是我能自己解决的，需要上游或组长给条件：

1. **任务 04 没有发布任务单**。项目规则写明：分工不等于开工，任务未发布、没人安排之前不能改后续任务的代码。
2. **任务 03 还没完成**。执行顺序是 01 → 02 → 03 → 04，03 由 B 主责（对比报告、详情、目录管理动线）。01 和 02 已完成。
3. **没有镜像和数据的下载授权与磁盘配额**。任务 04 的资格验证要在容器里跑，需要先拉题目镜像；规则明确写了没授权不许拉镜像。
4. **仓库文档落后于组长手上那版**。组长 2026-09-19 给的更新版里，`plan.md`、`spec.md`、`implementation-map.md` 都已更新（写明任务 01、02 已完成），并新增了 `issues/01`、`issues/02` 两份任务单，但这些还没推到仓库。仓库看到的还是 09-17 草案版。
5. **本机跑不了验证**。我这台机器没有 `framework/`、`runtime/`、`infra/data/`、`infra/volumes/`，没有固定 Parquet 数据快照，Docker Desktop 也没运行。

## 4. 我能做、已经在做的准备

- 读自己模块的代码和权威文档（不需要授权）。
- 准备任务 04 的测试设计——已写进行动文档：[2026-09-19-task-04-catalog-candidates-and-scale.md](../actions/2026-09-19-task-04-catalog-candidates-and-scale.md)。
- 用 Navicat 连共享 PostgreSQL，直接看目录三张表（`tasks`、`task_artifacts`、`agent_configurations`）的现状。连接方法见 [TEAM_POSTGRESQL_CONNECTION.md](../operations/TEAM_POSTGRESQL_CONNECTION.md)。

## 5. 下一步

1. 向组长确认三件事：更新版文档什么时候推到仓库；镜像与数据的下载授权和磁盘配额；任务 04 任务单什么时候发布。
2. 连数据库，看目录三张表里那一道题和一个配置的实际记录。
3. 等任务 03 验收完成后开工。开工第一步按项目规则锁定当时的 HEAD 基线，并更新行动文档。
4. 数据库观察结果和确认到的授权，回来补进本文件。

## 6. 注意

- 行动文档里引用的「前项状态」会随文档同步而变化。文档一同步，先回读 [plan.md](../../.scratch/ui-catalog-providers/plan.md) 再动工。
- 验收规范里写的命令工作目录是组长的机器路径（`E:\9.1agent_exam\apps\backend`）。我的克隆在 `C:\Users\陆泳倩\Desktop\agent-exam`，将来执行 `verify.ps1` 一类脚本时路径要对齐，不要照抄。
- 目录与本模块的权威事实以 `docs/architecture/` 和 `docs/interfaces/` 为准，本文件夹只做个人视图和进度记录。

## 7. 本文件夹变更记录

| 日期 | 变更 |
|---|---|
| 2026-09-20 | 建立本文件夹（README、MODULE_ARCHITECTURE、CONTRACTS、INTERFACES、PROGRESS），对应个人分支 `lyq` |
