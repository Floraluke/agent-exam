# 任务 03：对比报告、单次详情与目录管理动线（总行动）

> 状态：**进行中**（2026-09-21 对齐 `main` 的 `fd369cc` 重做）。
>
> 任务 DRI：**B（Web 与 HTTP）**。子行动细节分别落在本目录下的独立文件；本文只做汇总与指针，不复制。
>
> 范围与验收以[执行计划第 5 节](../../../../../.scratch/ui-catalog-providers/plan.md)和[分层验收规范](../../../../../.scratch/ui-catalog-providers/verification.md)为准。

## 1. 情况说明

任务 03 要交付"先看对比、再看单次证据"的完整动线：跨批次"题目 × 配置"矩阵、单元格钻取到单次运行报告与安全证据，以及题库/配置/成员等独立导航。按[团队分工](../../TEAM_WORK_ALLOCATION.md)，B 负责矩阵与详情 UI，D 负责报告、证据与缺失语义，C 负责目录，A 负责成员与保留权限。

**子行动 a 与 b 都已完成，且后端的最终版在 `main` 上**——由 fengyy 的 `7553ce0 fix: harden comparison reports and preset upgrade`（对 D 合并内容的合并后审查修复）交付。因此任务 03 真正剩下的只有**对比页 UI**。

## 2. 子行动

| 子行动 | 做什么 | 状态 | 证据/文件 |
|---|---|---|---|
| a. `03-comparison-api-spec` | 把对比接口写进 `HTTP_API.md` §10.4 | ✅ 已落笔；**PR #3 已决定关闭**——`main` 上已有 §10.4（`7553ce0` 重写），合并会整段替换 | 契约行动在原分支上：`docs/actions/2026-09-20-task03-comparison-api-doc.md`（**不随本 PR 进 main**，分支 `task03/comparison-api-spec`） |
| b. `03-comparison-api-impl` | 对比接口的 HTTP 实现 | ✅ **已在 `main` 上完成**（路由、DTO、严格参数校验、五档收敛、契约用例 4 个，`7553ce0`） | 见上表契约行动的"后续"节与[进展与未决项](../progress.md) |
| c. `03-comparison-ui` | 对比页 UI（列头、单元格、覆盖率、钻取） | ✅ **已实现并验证**（分支 `feat/03-comparison-ui`，待评审合入） | [逐控件契约表](03-comparison-ui.md)（含第 6 节自验证结果：typecheck/build 0、3 条浏览器用例、全量 18 spec 无回归） |

## 3. 当前后端结构（`main` 实际；任务 03 只需消费，不需改动）

```text
apps/backend/src/eval_platform/
  application/reporting/
    matrix.py                    # ComparisonOutcome 五档、矩阵聚合、跨仓库同名隔离
    matrix_markdown.py           # 复用矩阵派生值
  delivery/http/routes/jobs/
    report_routes.py             # §10.1 批次报告、§10.2 单次运行报告
    batch_schemas.py / report_schemas.py / *_schemas.py
    reporting/                   # 7553ce0 新增的子目录（对比接口）
      __init__.py
      comparisons.py             # §10.4 的 DTO 与路由；严格 query 校验在此
    lifecycle/                   # 恢复与重试
apps/backend/tests/jobs/reporting/
  test_comparison_http.py        # 4 个契约用例
  test_matrix.py / test_compare_service.py / test_matrix_*.py
apps/web/src/
  features/jobs/reporting/       # 候选：任务 03 的对比页 UI（尚未创建）
  lib/job-client.ts              # 候选修改：对比接口的前端调用
  lib/reporting-shapes.ts        # 候选新增：矩阵响应运行时校验（未知形状失败关闭）
apps/web/tests/                  # 候选：对比页浏览器用例
docs/interfaces/HTTP_API.md      # §10.4 现行正文在 main 上（B 的分支版本将关闭）
```

`routes/jobs/` 顶层现为 **8 个 `.py`** 加 `lifecycle/`、`reporting/` 两个子目录，**满足**"每层不超过 8 个文件"指标；原先议定的 `schemas/` 拆分**已取消**（指标已由 `reporting/` 子目录达到）。

## 4. 验证方式

1. **契约一致性**：`HTTP_API.md` §10.4（`main` 现行版）与 `reporting/comparisons.py` 逐项对照；运行 `apps/backend/tests/jobs/reporting/test_comparison_http.py`（**4 个用例**，内存替身装配、**不需要真实 PostgreSQL**）。
2. **矩阵语义**：空选择、非 UUID、超 20、未知/重复参数、无会话、无权、`internal_test`、`missing` 语义、五档映射、去重与 UUID 规范化逐项覆盖；`missing` 的 `resolved` 必须为 `null`、不并入未通过、不写成 0。
3. **回归**：`apps/backend` 的 `ruff`/`mypy`/定向 pytest；Web 侧 `npm run typecheck`、`npm run build`、浏览器回归。命令与工作目录以[分层验收规范第 3 节](../../../../../.scratch/ui-catalog-providers/verification.md)为准；**默认跳过的真实存储/容器用例逐项列 skipped，不算通过**。
4. **UI 完成后**：矩阵在桌面/手机均可读可钻取；零用量与未知明确不同；页面权限不变；既有 UI 动线无功能丢失。

## 5. 自验证情况

- B 侧**未新增任何实现代码**；子行动 c 未开始。
- **已执行（2026-09-20，基于当时的 `beed93f`）**：后端环境恢复（`uv 0.12.17` + uv 管理的 Python 3.13.15）；`test_comparison_http.py` → **3 passed**、`tests/jobs/reporting` → 14 passed / 2 skipped、全量 → 2 failed / 404 passed / 84 skipped。当时该分支无第 4 个用例，故为 3。
- **未在新 `main` 上重跑**：环境已就绪；建议按 **4 passed** 预期重跑并核对那 2 个 Harbor 失败。基线可移植性说明见[进展与未决项](../progress.md)。
- **未执行**：B 侧未运行 `ruff` / `mypy`。

## 6. 未验证项与待确认项

| 项 | 说明 |
|---|---|
| 对比页 UI 的契约行 | 按[实现地图 2.1 节门槛](../../../../../.scratch/ui-catalog-providers/implementation-map.md)，写代码前须先补逐控件契约行 |
| 在**新 main** 上重跑测试 | 环境已就绪，未执行；预期 4 passed + 2 个 Harbor 失败 |
| 与 D 的重复工作 | ✅ 已关闭 | D 于 2026-09-21 拍板接受 `main` 为最终形态：`cdcb4cf`/`c5e036d` 不再合入，以 `7553ce0` 为准；"不收敛"决定作废；`xinyue-modules` 转历史存档。细节见[进展与未决项](../progress.md) |
| 任务 03 的正式 issue | `.scratch` 当前无 `03-*` 任务单；是否发布待 B 确认 |
| 实时 OpenAPI 计数 | ✅ 已复核：32 个端点与 §2.1 的 32 条逐条集合比对差异 0（2026-09-21，见[进展与未决项](../progress.md)） |
