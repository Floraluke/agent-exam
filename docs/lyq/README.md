# lyq 的模块文档（目录与配置）

本文件夹是陆泳倩（lyq）的个人模块文档目录。按团队会议要求建立：每位成员在 `docs/` 下建自己的文件夹，存放模块架构、输入输出契约、接口和进度/history。

## 我负责什么

- 长期 Module：**目录与配置**（Catalog and Configuration）。内部是两块：Task Catalog（可信题目目录）和 Agent Registry（固定 Agent 配置）。
- 当前任务 DRI（直接负责人）：**任务 04 五道新题入库与 1–20 连续规模**。
- 还参与：任务 03 的目录动线、任务 05–07 的提供方受控配置、任务 08 的冻结目录回归。

## 这个文件夹放什么

| 文件 | 内容 |
|---|---|
| `MODULE_ARCHITECTURE.md` | 我负责模块的架构：职责、Interface、文件树、数据流 |
| `CONTRACTS.md` | 输入输出契约：能接收什么、返回什么、什么情况报错 |
| `INTERFACES.md` | 接口清单：HTTP 端点和模块内部 Interface |
| `PROGRESS.md` | 进度与 history：做到哪一步、卡在哪、下一步 |

## 这里不是权威来源

按项目规则「同一事实只设一个权威来源」，本文件夹是**我个人的视图和工作记录**，不复制权威正文。要看准确字段、错误码、表结构和路由，去这些地方：

- 模块契约：[MODULE_CONTRACTS.md](../architecture/MODULE_CONTRACTS.md) 第 6.2、6.3 节
- 数据模型：[DATA_MODEL.md](../architecture/DATA_MODEL.md)
- HTTP 接口：[HTTP_API.md](../interfaces/HTTP_API.md)
- 本模块架构：[catalog-and-configuration/ARCHITECTURE.md](../architecture/modules/catalog-and-configuration/ARCHITECTURE.md)
- 全项目架构：[ARCHITECTURE.md](../architecture/ARCHITECTURE.md)
- 团队分工：[TEAM_WORK_ALLOCATION.md](../architecture/modules/TEAM_WORK_ALLOCATION.md)
- 扩展计划与任务：[.scratch/ui-catalog-providers/plan.md](../../.scratch/ui-catalog-providers/plan.md)

如果本文件夹和权威文档不一致，以权威文档为准，并回来修正本文件夹。
