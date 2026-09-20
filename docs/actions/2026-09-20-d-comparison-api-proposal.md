# 跨批次对比报告接口提案（任务 03 · D 侧发起，待 B 确认）

> 状态：**已按 B 授权由 D 定稿**（2026-09-20）。成员 B 授权由 D 定案本接口；本文即定稿版本，可私下发给 B 过目。**尚未写入共享文档** `docs/interfaces/HTTP_API.md`——该文档归 B 维护，待 B 确认后由 B 落笔新增 §10.4，本文届时只留指针、不复制维护。
>
> 依据：规格 story 24–27（"每题一行、配置一列"、"分清未通过、执行故障和未完成"）；执行计划第 5 节（"复用批次报告建'题×配置'矩阵……缺失 Run 或报告标为缺失，不当作未通过或零"）；现有接口契约 §10.1/10.2/10.3。

## 0. 为什么需要这个接口

现有报告接口只有单批次（§10.1）与单 Run（§10.2）。规格要求"同题跨配置矩阵"比较——页面需要一个服务端聚合入口，避免浏览器为 60 个格子发 60 个请求（计划第 5 节原文限制）。**聚合分类逻辑已实现并测试**（D 模块内部：`application/reporting/matrix.py`、`JobReporting.compare`），本提案只新增 HTTP 翻译层。

## 1. 端点定义

`GET /api/v1/reports/comparisons?job_ids=<uuid>,<uuid>,...`

- 只读 GET，与既有报告端点一致；`Cache-Control: no-store`。
- `job_ids`：必填，逗号分隔的 Job UUID，**去重后按出现顺序**排成矩阵列，最多 **20** 个（服务端常量 `MAX_COMPARISON_JOBS=20`，防无界请求）。
- 携带会话 Cookie；无会话返回 401。
- 未知参数、重复参数、非法 UUID、空列表、超过 20 个：400（见第 4 节错误表）。

## 2. 响应形状

```json
{
  "columns": [
    {
      "job_id": "00000000-0000-0000-0000-000000000103",
      "agent_configuration_id": "00000000-0000-0000-0000-000000000102",
      "agent_display_name": "Codex 0.153.0 / gpt-5.6-terra / medium"
    }
  ],
  "rows": [
    {
      "task_instance_id": "python__mypy-15413",
      "repo": "python/mypy",
      "cells": [
        {
          "outcome": "resolved",
          "resolved": true,
          "run_id": "00000000-0000-0000-0000-000000000104",
          "failure_code": null,
          "report_path": "/api/v1/reports/runs/00000000-0000-0000-0000-000000000104"
        },
        {
          "outcome": "missing",
          "resolved": null,
          "run_id": null,
          "failure_code": null,
          "report_path": null
        }
      ]
    }
  ],
  "totals": [
    {
      "resolved": 6,
      "unresolved": 0,
      "infrastructure_error": 0,
      "incomplete": 0,
      "missing": 0,
      "decided": 6,
      "coverage": "6/6"
    }
  ]
}
```

字段说明（与 D 模块内部 `matrix.py` 的值对象一一对应）：

| 字段 | 含义 | 对应内部类型 |
|---|---|---|
| `columns[]` | 每个（Job × 配置）一列；列序 = `job_ids` 去重后的顺序；同一 Job 多配置时按 Run 顺序展开 | `MatrixColumn` |
| `rows[]` | 全部 Job 的题目并集，按 `(repo, task_instance_id)` 排序 | `MatrixRow` |
| `cells[]` | 该题在该列的结果，五档之一 | `MatrixCellValue` |
| `totals[]` | 每列分类计数；`decided` = 四档有结论数，`coverage` = "有结论/总数" | `MatrixColumnTotals` |

**单元格 `outcome` 五档判定**（新类型 `ComparisonOutcome`，只用于本接口，**不改动** §10.1 既有 `outcome` 四档）：

| 值 | 判定 |
|---|---|
| `resolved` | Run `COMPLETED` 且 `resolved_summary=True` |
| `unresolved` | Run `COMPLETED` 且 `resolved_summary=False` |
| `infrastructure_error` | Run `FAILED` |
| `incomplete` | 其余非终态（取消/未完成） |
| `missing` | ① 该组合没有 Run；或 ② Run `COMPLETED` 但报告不可读 |

**硬规则（计划第 5 节原文，已由测试覆盖）**：`missing` 的 `resolved` 必须为 `null`（不是 `false`）、`report_path` 为 `null`，**不当作未通过或零**；`missing` 的 `run_id` 为 `null` 表示"没有 Run"、非 `null` 表示"有 Run 但报告缺失"（供界面区分文案）。`coverage` 保持完整矩阵分母，不因缺失扣减。

## 3. 权限与可见性（沿用 §10.2 既有规则，不新设计）

- owner 可对比全部；协作者只能对比**自己创建**的 Job；任何无权 Job 使**整个请求 404**（与既有报告一致，不泄漏哪个资源存在）。
- `result_scope=internal_test` 的 Job 按不存在处理（404）；正式配置不接受内部范围谓词注入。

## 4. 错误契约（沿用既有错误形状 `{error:{code,message,details,request_id}}`）

| 情况 | HTTP | `error.code` | 建议文案 |
|---|---|---|---|
| 无会话 | 401 | `AUTHENTICATION_REQUIRED` | 登录无效或已失效，请重新登录 |
| 无权/不存在/internal_test | 404 | `JOB_NOT_FOUND` | 评测批次不存在 |
| `job_ids` 为空 | 400 | `EMPTY_COMPARISON_SELECTION` | 请至少选择一个评测批次 |
| 超过 20 个 Job | 400 | `COMPARISON_LIMIT_EXCEEDED` | 一次对比最多选择 20 个评测批次 |
| 未知/重复参数、非法 UUID | 400 | `INVALID_REQUEST` | 请求参数无效 |
| 存储正文/数据库读取失败 | 503 | `DEPENDENCY_UNAVAILABLE` | 依赖服务暂不可用 |

## 5. 已有实现与剩余工作

| 内容 | 状态 | 归属 |
|---|---|---|
| 五档分类、缺失语义、去重/上限、授权（`JobReporting.compare` + `matrix.py`） | ✅ 已实现并测试（4 用例；全量回归 449 passed / 36 skipped / 2 failed，2 个失败为缺 `framework/harbor` 的环境问题） | D 已完成 |
| 本接口的路由、DTO、错误映射、OpenAPI | ⬜ 待实现 | **B**（Web/HTTP Module） |
| 本文落入 `HTTP_API.md` §10.4 | ⬜ 待 B 确认后落笔 | **B** |
| 对比页 UI（列头、单元格、覆盖率、钻取） | ⬜ 待实现 | B（任务 03 主责） |
| 每列指标汇总（用量/费用/耗时 `{value, coverage}`） | ⬜ 可后续增量；v1 不含，页面可经既有单 Run 报告惰性取得 | 待定 |

## 6. 已定案的决定（2026-09-20，B 授权 D 定案）

1. 方法：**GET + 逗号分隔 query**，与既有只读端点（排行榜等）一致。
2. §10.1 的 `BatchOutcome` **保持不变**（四档）；对比接口使用独立的五档 `ComparisonOutcome`，不改旧契约。
3. 协作者可见性：**沿用报告授权**——owner 可对比全部，协作者只能对比自己创建的 Job；任一无权 Job 使整个请求 404。
4. `totals` 提供 `decided` 与 `total` 两个整数（`decided + missing = total`），不另设字符串覆盖率。

## 7. 明确不做（本提案范围外）

- 不改既有端点、不改 `BatchOutcome`、不改数据库 schema、不加新表；
- 不在对比响应中返回对象键、秘密路径或原始正文（下载仍走 §9.3 公开三类制品）；
- 不引入 Judge 分或"公平排名"（不同限制的对比差异由界面提示，见规格 story 27 与已确认范围）。
