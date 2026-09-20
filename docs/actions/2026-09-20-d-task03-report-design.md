# 2026-09-20 D：任务 03 报告语义设计草案（对比矩阵与"缺失"）

## 状态与情况说明

状态：**候选 / 待确认**（2026-09-20 起草）。这是 D 在任务 03 中的交付切片（报告、证据与缺失语义）的**接口设计草案**；不实现、不改路由、不改公共契约，等任务 03 发布并经相关方确认后再动产品代码。

来源请求：成员 D 于 2026-09-20 要求继续完成属于 D 的任务；本稿是对 03 中 D 部分的事前设计。

范围：跨批次"题目 × 配置"对比矩阵的语义、缺失档的 HTTP 表现、指标聚合口径；证据钻取复用现有接口，不重新设计。

## 现状盘点（2026-09-20 本机核对，全部有代码依据）

| 事实 | 位置 |
|---|---|
| 现有报告端点只有两个：`GET /api/v1/reports/runs/{run_id}`、`GET /api/v1/reports/jobs/{job_id}`，**没有跨批次对比端点** | `delivery/http/routes/jobs/report_routes.py:22-29` |
| 批次报告 DTO `JobReportResponse` 每个 Run 带 `outcome` 四档：resolved / unresolved / infrastructure_error / incomplete，**没有"缺失"档** | `delivery/http/routes/jobs/batch_schemas.py:15`、`:78`、`:116-124` |
| 单 Run 详情已有：`RunReportResponse`（含 deterministic_result / process_metrics / artifact_links） | `delivery/http/routes/jobs/report_schemas.py:65` |
| 证据钻取已有：制品索引 / 轨迹分页 / 正文下载 | `delivery/http/routes/artifacts.py:55`、`:73`、`:86` |
| 指标聚合已有可复用模式：`MetricValueResponse = value + coverage`，缺失不写 0 | `delivery/http/routes/leaderboard/schemas.py:40-42` |
| 冻结身份校验已有：快照与目录逐字段比对、指纹重算（可用于对比矩阵的分组身份） | `adapters/persistence/jobs/reporting/validation.py:44-77`、`:98-135` |
| D 的矩阵原型已实现五档语义并有测试 | `application/reporting/matrix.py`、`tests/jobs/reporting/test_matrix.py`（本分支） |

## 设计草案

### 1. 单元格语义（五档）

复用原型 `matrix.py` 的分类口径，并映射到 HTTP：

| 语义 | 判定（实现依据） | HTTP 表现 |
|---|---|---|
| resolved | Run COMPLETED 且 `resolved_summary=True` | 现有 `BatchOutcome.resolved` |
| unresolved | Run COMPLETED 且 `resolved_summary=False` | 现有 `BatchOutcome.unresolved` |
| infrastructure_error | Run FAILED | 现有 `BatchOutcome.infrastructure_error` |
| incomplete | 其余非终态（取消/未完成） | 现有 `BatchOutcome.incomplete` |
| **missing** | **无该组合的 Run**；或 Run COMPLETED 但报告读不到 | **新增取值**；单元格不带 `resolved` 布尔、不带报告链接 |

不变量（照抄 `plan.md` 第 5 节并已由原型测试覆盖）：缺失**不当作未通过或零**；缺失单元格的 `resolved` 必须为 `None`（不是 `false`）。

### 2. 对比读取方案（两个候选，推荐 A）

- **方案 A（推荐）：服务端新增 `GET /api/v1/reports/comparisons?job_ids=a,b`**
  - 一次请求返回整张矩阵（列 = Job×配置，行 = 题目并集，每格五档 + 报告链接），并附每列 `decided/missing/coverage` 汇总；
  - 好处：单次往返、服务端做授权与冻结身份校验、避免浏览器为 60 个格子发 60 个请求（`plan.md` 第 5 节的限制）；
  - 代价：新增公共端点 → 需要 B 更新 HTTP 文档、路由挂载，属契约变化。
- **方案 B：前端用现有两个批次报告端点自行聚合**
  - 好处：不动公共契约；
  - 代价：违反"产品代码不在调用侧复制业务规则"（分类口径应由服务端提供）；多请求、前端计算覆盖度易出错。不推荐。

**推荐**：A；矩阵聚合逻辑直接复用已实现并有测试的 `application/reporting/matrix.py`。

### 3. 候选响应形状（方案 A，供 B 对齐，待确认）

```json
{
  "columns": [
    {"job_id": "...", "agent_configuration_id": "...", "agent_display_name": "..."}
  ],
  "rows": [
    {
      "task_instance_id": "python__mypy-15413",
      "repo": "python/mypy",
      "cells": [
        {"outcome": "resolved", "resolved": true, "report_path": "/api/v1/reports/runs/..."},
        {"outcome": "missing", "resolved": null, "report_path": null}
      ]
    }
  ],
  "totals": [
    {"resolved": 6, "unresolved": 0, "infrastructure_error": 0,
     "incomplete": 0, "missing": 0, "decided": 6, "coverage": "6/6"}
  ]
}
```

- 字段名按项目中文注释习惯补充到 HTTP 文档；`coverage` 用"有结论/总数"字符串或两个整数字段（由 B 在文档中定夺）。
- 指标汇总（用量/费用/耗时）沿用 `MetricValueResponse` 的 value+coverage 模式；任一组成值缺失 → value 为 null，coverage 反映实际可用数，**不写 0**。

### 4. 权限与可见性

默认沿用现有报告规则：owner 可见全部；协作者仅见自己创建的 Job（`application/reporting/service.py:142-144`）。跨批次对比若混入他人 Job，协作者视角只显示自己有权的列——**是否需要"对比仅 owner 可用"的约束，待确认**。

### 5. 冻结身份与可比性

对比矩阵的列身份沿用排行榜的冻结校验（`reporting/validation.py`）：配置指纹、网络/工具策略、三 revision 与契约版本一致才算同一列；漂移的列拒绝进入对比并报错（fail-closed）。

## 需要确认的事项（按"契约先于联调"）

1. 是否新增公共端点（方案 A）→ **需 B 更新 HTTP 文档与路由**，并需 owner 确认范围；
2. `BatchOutcome` 是否增加 `missing` 取值（只增不改，属于契约变化）→ B 的前端映射要同步；
3. 对比矩阵的可见性范围（协作者可见自己列 vs 仅 owner）；
4. 单元格与汇总的 UI 文案（"缺失"的界面呈现）——B 的设计域。

## 明确不做（本稿）

不改任何路由、DTO、契约文档或 schema；不实现服务端端点。上述结论均标"候选"，正式实现以任务 03 任务单为准。

## 自验证方式

- 本稿"现状盘点"的每条引用均可打开对应文件核对（见上表位置）；
- 矩阵五档语义已由本分支 `tests/jobs/reporting/test_matrix.py` 与真实数据库演练 `test_matrix_rehearsal.py` 覆盖（历史结果见对应行动文档）。

## 实施增量：JobReporting.compare（内部实现，2026-09-20 追加）

按"内部实现不碰公共接口"的边界，先把设计草案中**纯属于 D 模块**的部分落成正式代码：

```text
apps/backend/src/eval_platform/application/reporting/
  service.py                        # 修改：新增 compare(actor, job_ids) -> ReportMatrix
                                    #   - 复用 job() 的可见性、授权与证据校验（任一批次不可读即整体失败，不泄漏是哪一批）
                                    #   - 去重；空选择 -> EMPTY_COMPARISON_SELECTION；超过 MAX_COMPARISON_JOBS=20 -> COMPARISON_LIMIT_EXCEEDED
                                    #   - 聚合直接复用 matrix.py 的五档语义（含"缺失"）
apps/backend/tests/jobs/reporting/
  test_compare_service.py           # 新增 4 个用例：跨批次聚合与缺失语义、去重、空/超限拒绝、协作者看不到他人 Job（JobNotFound）
```

验证（2026-09-20，`apps/backend`）：

- `pytest tests/jobs/reporting/test_compare_service.py -q` → **4 passed**；`pytest tests/jobs/reporting -q`（无数据库门禁）→ 11 passed / 2 skipped（跳过为需显式门禁的真实 PG 用例）；
- `ruff check` → All checks passed；`mypy src/eval_platform/application/reporting/service.py` → Success；
- 全量回归（含数据库门禁）三次结果如实记录：第 1、2 次 → 3 failed（2 个缺 `framework/harbor` + 1 个 `tests/jobs/cancellation/test_cancel_races.py::test_postgres_cancel_claim_race_never_leaves_an_executable_trial`）；第 3 次 → **2 failed / 449 passed / 36 skipped**（竞态测试通过）。竞态测试单独重跑 **3/3 通过**，定性为全量负载下的时序敏感偶发，与本次只读改动无关；**已标记为 08 回归时需盯的点**，不据此声称"全部通过"。

明确未做：未新增 HTTP 端点、未改 DTO 与 `BatchOutcome` 枚举、未改 `docs/interfaces/HTTP_API.md`——这些仍按"契约先于联调"等待任务 03 发布后与 B 对接。

## 自验证结果

完成时间：2026-09-20。逐项实测：

1. `report_routes.py:23` `run_report`、`:28` `job_report` —— 与"现状盘点"一致，确认无跨批次端点。
2. `batch_schemas.py:15` `BatchOutcome = Literal["resolved", "unresolved", "infrastructure_error", "incomplete"]` —— 确认四档、无"缺失"。
3. `leaderboard/schemas.py:40-42` `MetricValueResponse`（`value: int | float | None` + `coverage: int`）—— 与"指标聚合复用模式"一致。
4. 矩阵五档语义由本分支既有测试覆盖（`tests/jobs/reporting/test_matrix.py` 3 个用例、`test_matrix_rehearsal.py` 1 个真实数据库演练；历史结果见 `2026-09-19-d-report-matrix-spike.md` 与 `2026-09-20-d-continuous-scale-and-rehearsal.md`）。

结论：本稿仅设计、未实现；全部现状引用可核对，候选方案待任务 03 发布后按"契约先于联调"确认。
