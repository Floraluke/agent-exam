# 任务 03：对比报告、单次详情与目录管理动线（总行动）

> 状态：**进行中**（2026-09-20 建立）。
>
> 任务 DRI：**B（Web 与 HTTP）**。本文件是任务 03 的总行动；子行动的细节分别落在本目录下的独立文件中，本文只做汇总与指针，不复制子行动内容。
>
> 范围与验收以[执行计划第 5 节](../../../../../.scratch/ui-catalog-providers/plan.md)和[分层验收规范](../../../../../.scratch/ui-catalog-providers/verification.md)为准；对比矩阵的业务语义由[规格](../../../../../.scratch/m1-platform/spec.md) story 24–27 与 [Q12 覆盖行](../../../../../.scratch/ui-catalog-providers/verification.md)约束。

## 1. 情况说明

任务 03 要交付"先看对比、再看单次证据"的完整动线：跨批次"题目 × 配置"矩阵、单元格钻取到单次运行报告与安全证据，以及题库/配置/成员等独立导航。按[团队分工](../../TEAM_WORK_ALLOCATION.md)，B 负责矩阵与详情 UI，D 负责报告、证据与缺失语义，C 负责目录，A 负责成员与保留权限。

本次（2026-09-20）收到三项安排：记录共享环境验证结果、建立本 Module 工作文档结构、对任务 03 的接口实现做只读侦察并出计划。**未动任何 `.py` 文件**，未 commit/push。

## 2. 子行动

| 子行动 | 做什么 | 状态 | 证据/文件 |
|---|---|---|---|
| a. `03-comparison-api-spec` | 把 D 定稿的对比接口写进 `HTTP_API.md` §10.4 并提 PR | ✅ 契约已落笔；**PR 尚未创建**（`gh` 登录失败，待重试） | [契约行动](../../../../actions/2026-09-20-task03-comparison-api-doc.md)；分支 `task03/comparison-api-spec`，HEAD `a951a2a` |
| b. `03-comparison-api-impl` | 对比接口的 HTTP 实现 | ⚠️ **实现已由 D 交付**（路由/DTO/错误映射/OpenAPI/3 个契约用例，`bd47925`）；**B 侧复核与验证未完成** | [实现侦察行动](03-comparison-api-impl.md) |
| c. `03-comparison-ui` | 对比页 UI（列头、单元格、覆盖率、钻取） | ⬜ 未开始 | 依赖 b 的复核结论；无独立文件，待发布后新建 |

**与原始预期不同的一点**：子行动 b 不是"待开工的实现任务"。侦察确认该端点的 HTTP 翻译层已由 D 在 B 的 HTTP 层实现并经 B 批准，因此 b 剩余的是**复核、验证与必要的去重**（详见[实现侦察行动](03-comparison-api-impl.md)），而不是从零实现。

## 3. 规划文件树（任务 03；标"候选"的尚未创建）

```text
apps/backend/src/eval_platform/
  delivery/http/routes/jobs/
    report_comparisons.py        # 已存在（D 交付）：§10.4 的 DTO 与 /reports/comparisons 路由
    report_routes.py             # 已存在：§10.1 批次报告、§10.2 单次运行报告
    batch_schemas.py             # 已存在：§10.1 的 BatchOutcome 四档（任务 03 不改动）
apps/backend/tests/jobs/reporting/
  test_comparison_http.py        # 已存在（D 交付）：3 个契约用例
  test_matrix.py / test_compare_service.py / test_matrix_*.py   # 已存在：D 层的矩阵与渲染测试
apps/web/src/
  features/jobs/reporting/       # 候选：任务 03 的对比页 UI（实现地图标注为候选，任务 02 未创建）
  lib/job-client.ts              # 候选修改：新增对比接口的前端调用与形状校验
  lib/reporting-shapes.ts        # 候选新增：矩阵响应运行时校验（未知形状失败关闭）
apps/web/tests/                  # 候选：对比页浏览器用例
docs/interfaces/HTTP_API.md      # 已修改：新增 §10.4（子行动 a）
```

后端路由层目前**已经超过**项目"每层文件夹默认不超过 8 个文件"的指标：`routes/jobs/` 现有 9 个 `.py` 文件（`__init__.py`、`batch_schemas.py`、`cancel_schemas.py`、`decision_schemas.py`、`report_comparisons.py`、`report_routes.py`、`report_schemas.py`、`routes.py`、`schemas.py`）加 `lifecycle/` 子目录，共 10 个条目。这是**既有状态**（`report_comparisons.py` 随 D 的实现加入时形成），不是任务 03 造成的。任务 03 **不新增后端文件**，因此不加剧该偏差；但按项目规则，超指标需要单独说明理由、风险与拆分评估并取得确认——本次只如实记录，**未擅自拆分或移动任何文件**。Web 侧新增文件按职责放入 `features/jobs/reporting/`，不继续平铺。

## 4. 验证方式

1. **契约一致性**：`HTTP_API.md` §10.4 的字段与 D 的实现逐项对照；运行 `apps/backend/tests/jobs/reporting/test_comparison_http.py` 复核形状与错误族。该测试使用内存替身装配，**不需要真实 PostgreSQL**（依据见[实现侦察行动](03-comparison-api-impl.md)）。
2. **矩阵语义**：空选择、非 UUID、超 20、无会话、无权、`internal_test`、`missing` 语义、五档映射逐项覆盖；`missing` 的 `resolved` 必须为 `null`、不并入未通过、不写成 0。
3. **回归**：`apps/backend` 的 `ruff`/`mypy`/定向 pytest；Web 侧 `npm run typecheck`、`npm run build`、浏览器回归。命令与工作目录以[分层验收规范第 3 节](../../../../../.scratch/ui-catalog-providers/verification.md)为准；**默认跳过的真实存储/容器用例逐项列 skipped，不算通过**。
4. **UI 完成后**：矩阵在桌面/手机均可读可钻取；零用量与未知明确不同；页面权限不变；既有 UI 动线无功能丢失。

## 5. 自验证情况

- 本文件建立时任务 03 **未进入代码修改阶段**，因此尚无本轮实现类验证结果；本文的验证方式都是**计划**，不是已执行结论。
- 已执行并记录的只读核对：§10.4 与实现字段的静态对照（20/20 命中）、契约测试文件与夹具性质的确认、路由注册位置的确认。均见[实现侦察行动](03-comparison-api-impl.md)。
- 共享环境（PostgreSQL `15432`）当前**连不上**，但按侦察结论不阻塞本接口的本地测试；该结论的影响面与限制见[实现侦察行动](03-comparison-api-impl.md)。

## 6. 未验证项与待确认项

| 项 | 说明 |
|---|---|
| 契约测试实际运行 | 本次只读，未运行 pytest；需在 `apps/backend` 环境执行后回填结果 |
| 实时 OpenAPI 计数 | §2.1 已改为 32；未启动应用读取实时 OpenAPI 复核 |
| `ComparisonOutcome` 与 `MatrixCell` 的重复声明 | **已决定暂不收敛**（2026-09-20）；是否把 `MatrixCell` 提升为跨模块公开 Interface 待 D 回答（见[侦察行动](03-comparison-api-impl.md)与[进展与未决项](../progress.md)） |
| D 文档的两处失真 | 提案 §2 的 `coverage` 字段、§4 的未知/重复参数 400；属 D 维护，**只报告不擅改**（报告原文见[进展与未决项](../progress.md)） |
| 后端依赖环境与测试 | 本机无 `uv`，环境未恢复，契约测试**未运行**；见[侦察行动](03-comparison-api-impl.md) |
| 对比页 UI 的契约行 | 按实现地图 2.1 节门槛，写代码前须先补逐控件契约行 |
| 任务 03 的正式 issue | `.scratch` 当前无 `03-*` 任务单；是否发布需 B 确认 |
