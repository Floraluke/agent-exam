# C 模块（目录与配置）开发计划书

> **状态：准备阶段，产品开发未开工。** 扩展任务 01–08 尚未在本仓库发布独立 issue；「分工完成」不等于开工授权。本计划书不构成产品实施授权、镜像与数据下载授权或真实模型调用授权。
>
> 维护人：LYQ（成员 C 占位代号）　日期：2026-09-20
>
> 权威边界：本计划只做**归集与排期**。业务规则、接口、字段、表结构一律以上级权威文档为准（见第 6 节），本文件不复制它们。

## 1. 我负责的范围

分工依据：[团队分工文档](../../architecture/modules/TEAM_WORK_ALLOCATION.md) 第 1 节与第 5 节。

| 项目 | 内容 |
|---|---|
| 长期负责职责模块（Module） | 目录与配置（`catalog-and-configuration`）——代码主责 |
| 任务直接负责人（DRI） | 04 五道新题合格入库 + 1–20 连续规模 |
| 参与任务 | 03 的目录管理动线、05–07 的提供方受控配置、08 的冻结目录回归 |
| 工时基线 | 54 h（03:4 / 04:30 / 05–07:14 / 08:6） |

工时估算不含软件与镜像下载、等待用户确认、真实模型运行、外部限流和评审返工；每完成一个任务重新估算，偏差超过 8 h 需提出调平方案。

我负责模块的当前代码地图见[目录与配置模块架构](../../architecture/modules/catalog-and-configuration/ARCHITECTURE.md)；`TaskCatalog`、`AgentRegistry` 的输入输出与错误边界见[模块契约](../../architecture/MODULE_CONTRACTS.md)第 6.2、6.3 节。

## 2. 四条硬约束（先认清，能省很多返工）

1. **任务 04 尚未获得开工授权。** 扩展计划第 1 节第 5 条与第 5.2 节写明：01–08 仍是规划编号，未发布独立 issue；任务未发布、用户未安排之前不提前修改后续任务代码。执行顺序是 `01 → 02 → 03 → 04`，我的 04 排在 `03`（B 主责）之后。
2. **镜像与数据需要下载授权。** 任务 04 的资格验证要在容器里跑三种补丁，需要题目镜像。计划明确「没有下载范围授权时不拉镜像」，并要求先列本地缓存/缺失镜像、磁盘需求和下载来源。
3. **本机（开发机）不具备真实运行条件。** 本机没有 `framework/`、`runtime/`、`infra/data/`、`infra/volumes/`，没有固定 Parquet 数据快照，Docker Desktop 未运行。参考 E 模块的结论：真实执行链与固定镜像只在组长的机器上，本机只适合写代码、跑单元与契约测试、用合成目录验证边界。
4. **隐藏数据与秘密不进入任何共享位置。** 题目的 gold patch、测试名单、判卷字段不得出现在做题侧、HTTP、网页、日志或共享数据库的操作记录里；提供方 Key 只由组长在本机私有文件管理。

## 3. 任务 04 的分工边界

任务正文与步骤见[扩展执行计划第 6 节](../../.scratch/ui-catalog-providers/plan.md)，验收要求见[分层验收规范](../../.scratch/ui-catalog-providers/verification.md)（需求覆盖表 Q5、Q7 归 04）。本计划只记录**谁做什么**：

| 事项 | 主责 | 我的位置 |
|---|---|---|
| 题目目录、preset、规模版本 | **C（我）** | 主实现与收口 |
| 参考/空/错误补丁的固定 Fork 资格验证 | E | 组织交接、收口证据 |
| Job 快照与最多 60 Runs 兼容 | D | 提供受控目录与预设 |
| HTTP options 与三步向导 | B | 提供新预设组合，与其对接口 |
| 磁盘与长期 schema 变更窗口 | A | 提出需求，不改 schema 前先取得确认 |

## 4. 我要交付的两半

1. **题库**：五道 mypy 新题逐个通过资格门禁后进入受控白名单，同时保留旧题身份与 M0 单题入口；候选不足或不合格时从同一固定集合选替补并重走门禁，凑不满五道就停下汇报。
2. **规模（已由 D 实现，我的剩余边界待确认）**：`continuous(1–20)` 预设与相关用例已由成员 D 于 2026-09-20 实现并合入上游 `main`——`delivery/job_presets.py` 新增 `BatchPreset("continuous", 1, 20)`（既有 `demo`/`quick`/`standard` 区间未改），并新增 `tests/jobs/scale/test_continuous_preset.py` 与 `tests/jobs/reporting/test_matrix_rehearsal.py`。这部分原按分工算在「规模版本」名下，现由 D 按其 08 与 04 的 D 侧交付完成。**我的剩余部分需与组长和 D 确认**，至少涉及：受控选项的契约同步（D 明确留给 B 在 `docs/interfaces/HTTP_API.md` 补记）、`0/4 配置`、重复 ID、未知/停用条目的拒绝用例归属，以及规模版本与目录侧 preset 的关系。详见 [ISSUE-05](../04-issues/KNOWN_ISSUES.md)。

实施步骤、计划文件树与测试设计已写入[任务 04 行动文档](../../actions/2026-09-19-task-04-catalog-candidates-and-scale.md)，不在本计划重复。

## 5. 我需要的上游条件

1. 任务 04 的任务单发布与开工授权。
2. 题目镜像与数据集的下载授权，以及磁盘配额。
3. 任务 03 完成（B 主责），执行顺序才轮到 04。
4. 组长机器上的 Fork 判卷能否为我所用，以及由谁跑（E 主责，需要约定交接方式）。

## 6. 权威文档索引

| 需要什么 | 去哪里 |
|---|---|
| 全项目架构 | [`docs/architecture/ARCHITECTURE.md`](../../architecture/ARCHITECTURE.md) |
| 我负责模块的架构 | [`catalog-and-configuration/ARCHITECTURE.md`](../../architecture/modules/catalog-and-configuration/ARCHITECTURE.md) |
| 模块契约与稳定错误 | [`MODULE_CONTRACTS.md`](../../architecture/MODULE_CONTRACTS.md) |
| 表结构与对象键 | [`DATA_MODEL.md`](../../architecture/DATA_MODEL.md) |
| HTTP 路由与请求/响应 | [`HTTP_API.md`](../../interfaces/HTTP_API.md) |
| 团队分工 | [`TEAM_WORK_ALLOCATION.md`](../../architecture/modules/TEAM_WORK_ALLOCATION.md) |
| 扩展任务计划与验收 | [`.scratch/ui-catalog-providers/`](../../.scratch/ui-catalog-providers/) |
| 共享数据库连接 | [`TEAM_POSTGRESQL_CONNECTION.md`](../../operations/TEAM_POSTGRESQL_CONNECTION.md) |
