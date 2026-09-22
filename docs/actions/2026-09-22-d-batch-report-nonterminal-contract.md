# 2026-09-22 D：未完成批次的批次报告契约与取消态 500 缺陷

## 状态与情况说明

状态：Completed（2026-09-22）。

来源请求：B 在为本仓库做"脱离版前端"录制时，`GET /api/v1/reports/jobs/{job_id}` 对两个批次返回 **500 INTERNAL_ERROR**（`{"code":"INTERNAL_ERROR","message":"平台暂时无法完成请求"}`，两条 request_id：`req_b6c75e28f3a34a2abe8acbd3ed7eb600`、`req_bcc4eca71f7a48c09ccba04c30d6ca37`）。B 判断为"批次尚未产生可汇总结果"的契约空缺，请 D 在 409 / 200+全零 / 404 之间定夺。两个批次都是 `result_scope=internal_test`，且录制过程中被反复变更状态（后期分别是 `CANCELED` 与 `FAILED`）。

已确认的**两个独立问题**：

### 问题一：契约并不空缺——未完成批次本来就该 200

实测（official 作用域，产品路由 + 合成后端）三个中间状态全部 **200**：`AWAITING_OWNER_APPROVAL`（`pending_runs=1`）、`QUEUED`、`PREPARING`（均带 `stage_message`），Run 记 `outcome=incomplete`、`resolved=null`。真实 PostgreSQL 适配器直接读非终态批次报告同样不抛异常。

**D 拍板：维持 200**，理由三条：

1. 前端进度区就消费这些字段（`apps/web/src/features/jobs/batch-report.tsx` 用 `stage_message`/`completed_runs`/`failed_runs`/`pending_runs`）；改成 404/409 会让运行中的批次失去进度显示。
2. "还没有结果"与"结果为零"已经分开：计数按 Run 状态派生，未出结果的 Run 记 `incomplete`、`resolved=null`，`resolved_runs`/`unresolved_runs` 只统计确定结果（`resolved_summary is True/False`）。
3. 与 §10.4 保持一致：对比接口把未完成批次记 `incomplete` 档；批次报告若返回 404/409，两处语义互相矛盾。404 已承载"不存在或无权"（含 `internal_test`），不能再用它表示"还没好"。

### 问题二：取消态批次确实会 500（本次真实缺陷，已修）

按 B 给的线索（两个批次都在反复变更状态、后期为 `CANCELED`/`FAILED`）定位并**复现**：

```text
POST /api/v1/jobs/{job_id}/cancel  → 202，status=CANCELED
GET  /api/v1/reports/jobs/{job_id} → 500
     {"error":{"code":"INTERNAL_ERROR","message":"平台暂时无法完成请求",...}}
```

与 B 录到的两条响应形状、状态码完全一致（request_id 由每次请求生成，不复用）。

**根因**：`delivery/http/routes/jobs/batch_schemas.py` 的 `_JOB_MESSAGES` 缺 `CANCELED` 与 `CANCEL_REQUESTED` 两个状态（`JobStatus` 共 11 个值，映射只有 9 个），`stage_message=_JOB_MESSAGES[job.status]` 因此抛 `KeyError` → 未捕获 → 500 INTERNAL_ERROR。此前诸状态（AWAITING/QUEUED/PREPARING/EXECUTING/FINALIZING/COMPLETED/…）都有条目，所以只在取消相关状态暴露，与 `internal_test` 作用域、"批次未完成"都无关。

**修复**（本行动，落在 D 报告语义范围；文件在 B 的 HTTP 层，已告知 B）：

- 补齐 `CANCELED`（"批次已取消；未开始的组合不再执行。"）与 `CANCEL_REQUESTED`（"已请求取消；当前 Trial 运行到冻结上限后不再开始新组合。"）；文案取自 `docs/architecture/DATA_MODEL.md` 对这两个状态的既有定义。
- 两个映射改为 `dict[JobStatus, str]` / `dict[str, str]` 并用 `.get(..., _UNKNOWN_MESSAGE)` 兜底：展示文案不该让只读端点 500。
- 新增完整性测试 `tests/jobs/reporting/test_batch_status_messages.py`：逐个断言 `JobStatus` 的每个值、以及执行侧实际写入的每个 stage（`preparing`/`running_agent`/`collecting`/`verifying`/`completed`/`failed`/`canceled`/`pending`）都有文案，且没有多余条目。

## 实施措施

1. 补 `_JOB_MESSAGES` 两个状态 + 兜底文案（`batch_schemas.py`）。
2. 新增完整性测试与取消态回归：`test_batch_status_messages.py`、`test_job_report_states.py`（含 `CANCELED` 与 `CANCEL_REQUESTED` 两条路径）。
3. 修掉本行动早前用例里的一个不稳定断言（十二 Run 演练按列顺序断言，而列顺序由 `run_order_key` 与随机配置 UUID 决定）→ 改为集合断言。
4. 把结论写成本文，供 B 更新 §10.1/§15 与其待办行。

完成标准：取消态与取消请求态的报告返回 200 且文案正确；完整性测试能阻止再漏状态；D 模块与静态检查全绿。

## 受影响文件树

```text
apps/backend/src/eval_platform/delivery/http/routes/jobs/
  batch_schemas.py                                     # 修改：补齐 CANCELED / CANCEL_REQUESTED 文案，映射改为带兜底的查询
apps/backend/tests/jobs/reporting/
  test_batch_status_messages.py                        # 新增：状态文案完整性（JobStatus 全值 + 执行侧 stage）
  test_job_report_states.py                            # 新增：未完成/队列/准备/已取消/取消请求态的报告契约
  test_matrix_rehearsal_twelve_runs.py                 # 修改：列顺序断言改为集合断言（消除不稳定）
docs/actions/
  2026-09-22-d-batch-report-nonterminal-contract.md    # 本行动文档
```

参与关系：`batch_schemas.py` 是 HTTP DTO 翻译层（B 的模块），状态→文案属 D 的报告语义；`report_routes.py` 与 `JobReporting` 不变；测试都在 D 的报告测试目录。

## 自验证方式与结果

```text
cd apps/backend
uv run pytest tests/jobs -q                                  # 两次连续运行
uv run ruff check . && uv run ruff format --check src tests
uv run mypy src
```

结果：

- `pytest tests/jobs`（含真实 PostgreSQL 门禁）→ **171 passed / 4 skipped**，连跑两次一致（跳过项均为"专属 MinIO 集成未显式启用"）。
- 定向：`tests/jobs/reporting` → 25 passed / 3 skipped（PG 门控未开时）；预演与状态契约用例均通过。
- `ruff check` → All checks passed；`ruff format --check src tests` → 319 files already formatted；`mypy src` → Success: no issues found in 175 source files。
- 复现与修复对照：修复前 `CANCELED` 批次报告 500（与 B 的响应同形状）；修复后 200 且 `stage_message` 为取消文案。复现用的一次性临时用例已删除。

## 给 B 的契约文字（供 §10.1 采用）

> 批次尚未进入终态时，本端点仍返回 `200`：`stage_message` 说明当前阶段，`completed_runs` / `failed_runs` / `pending_runs` 按 Run 状态计数；尚无确定性结果的 Run 记 `outcome=incomplete`、`resolved=null`，不写入 `resolved_runs` / `unresolved_runs`。未完成不是 `404`（那表示不存在或无权，含 `internal_test`），也不是 `409`。`report_path` 是通往单 Run 报告的链接，不代表结果已经可用。

## 遗留与边界

- B 录到的两条 500 已定位为同一根因（取消态缺文案），其 request_id 无法回查（每次请求新生成，未存异常栈），但复现形状与状态一致；不再按"无法复现"关闭。
- 本行动不改状态机、不改响应形状、不改前端；`HTTP_API.md` 由 B 维护。
