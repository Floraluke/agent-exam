# 2026-09-22 D：未完成批次的批次报告契约（回应 B 的"契约空缺"）

## 状态与情况说明

状态：Completed（2026-09-22）。

来源请求：B 在为本仓库做"脱离版前端"录制时，报告 `GET /api/v1/reports/jobs/{job_id}` 对 `AWAITING_OWNER_APPROVAL` 与 `PREPARING` 返回 **500 INTERNAL_ERROR**，判断这是"批次尚未产生可汇总结果"的契约空缺，请 D 在 409 / 200+全零 / 404 三个方案中定夺，并说明由谁改。

复现结果（本仓库 main，含 B 描述的同一产品路由与合成后端装配）：**上述现象在当前代码中不可复现**，未完成批次返回的不是 500，而是 200 与已定义语义。

| 实验（都在 official 作用域） | 实际结果 |
|---|---|
| `AWAITING_OWNER_APPROVAL` → `GET /api/v1/reports/jobs/{job_id}` | **200**；`pending_runs=1`、`completed_runs=0`、`stage_message="等待所有者批准，不会启动执行。"`；Run 为 `outcome="incomplete"`、`resolved=null`、`report_path="/api/v1/reports/runs/<run_id>"` |
| owner 批准后 `QUEUED` → 同一端点 | **200**；`stage_message="已批准，正在等待单机 Worker。"` |
| Worker claim 后 `PREPARING` → 同一端点 | **200**；`stage_message="正在准备一个 Harbor Job 的冻结输入。"` |
| 真实 PostgreSQL 适配器 + `JobReporting.job`（非终态） | 无异常：`AWAITING_OWNER_APPROVAL`，2 条 run_report 均 `PENDING` |
| 完成后按保留策略清理制品（对应 B 夹具的 `artifacts/expire-and-clean`） | 清理 3 个制品后仍 **200** |

已核实的代码事实：`delivery/http/routes/jobs/report_routes.py:27` → `JobReporting.job`（`application/reporting/service.py:51`）在 Run 没有确定性结果时**提前返回**（`_verify` 首个分支），因此"批次未跑完"本身不会抛异常；`_verify` 只在结果与制品索引不一致时抛 `ArtifactUnavailable`，而它是 `CatalogUnavailable` 子类，已被映射为 **503 DEPENDENCY_UNAVAILABLE**（`delivery/http/errors.py:66-67`），不会变成 500。

已确认决定（D 拍板）：**不采用 A/B/C 中任何改状态码的方案，维持 200**，并把语义写进契约（由 B 落笔 §10.1）。理由：

1. **前端进度区就消费这些字段**：`apps/web/src/features/jobs/batch-report.tsx` 用 `stage_message`、`completed_runs`、`failed_runs`、`pending_runs` 显示批次进度；改成 404/409 会让运行中的批次失去进度显示。
2. **"还没有结果"与"结果为零"已经分开**：计数是状态计数，未产出结果的 Run 记 `incomplete`、`resolved=null`；`resolved_runs/unresolved_runs` 只统计确定结果（`resolved_summary is True/False`）。B 担心的"零结果混淆"在当前形状里不成立。
3. **与 §10.4 保持一致**：对比接口把未完成批次记为 `incomplete` 档；若批次报告返回 404/409，对比矩阵就无法纳入未完成批次，两处语义会互相矛盾。
4. **404 已承载"不存在或无权"**（`internal_test` 与越权都收敛为 `JOB_NOT_FOUND`），不能再用它表示"还没好"。

需要 B 补充的信息：两份 500 的响应原文、当时的 `job_id` 与批次状态、录制所用提交。若录制实例是较旧的提交，本结论按"当前 main 已定义行为"直接关闭；若在最新 main 仍能复现，D 按缺陷处理（届时定位是在 `_verify`、仓储读取还是响应组装）。

明确排除：不改状态码、不改前端、不改 `HTTP_API.md`（§10.1 归 B）、不为不可复现的现象先写补丁。

## 实施措施

1. 新增回归测试 `tests/jobs/reporting/test_job_report_states.py`（4 个用例），把"未完成批次可读"钉住：AWAITING 的 200 形状与 `incomplete`/`resolved=null`；QUEUED 与 PREPARING 仍可读；对比接口接受未出结果的批次且记为 `incomplete`；`internal_test` 仍收敛为 404。
2. 在 D 的模块架构文档补一条语义说明，指向该测试。
3. 把结论与证据写成本文，供 B 落笔 §10.1 时引用。

完成标准：测试通过；语义说明落在 D 的权威文档；给 B 的答复包含可复现命令、实际输出与需要他补的信息。

## 受影响文件树

```text
apps/backend/tests/jobs/reporting/
  test_job_report_states.py                            # 新增：未完成/中间状态批次报告的契约回归（4 用例）
docs/architecture/modules/evidence-and-reporting/
  ARCHITECTURE.md                                      # 修改：补"未完成批次报告返回 200"的语义说明
docs/actions/
  2026-09-22-d-batch-report-nonterminal-contract.md     # 本行动文档
```

参与关系：`report_routes.py`（B 的 HTTP 层）只做 DTO 翻译，不含状态判断；`JobReporting.job`（D 的应用层）负责授权与证据校验；`batch_schemas.py` 的计数由 Run 状态派生。本行动只新增测试与文档，没有改动产品代码路径。

## 自验证方式与结果

```text
cd apps/backend
uv run pytest tests/jobs/reporting/test_job_report_states.py -q
uv run ruff check . && uv run ruff format --check src tests
```

结果：**4 passed（0.89 秒）**；`ruff check` → All checks passed；`ruff format --check` → 301 files already formatted。复现实验另用了一次性临时用例，确认结论后已删除，未留在仓库。

## 给 B 的契约文字（供 §10.1 采用，B 落笔）

> 批次尚未进入终态时，本端点仍返回 `200`：`stage_message` 说明当前阶段，`completed_runs` / `failed_runs` / `pending_runs` 按 Run 状态计数；尚无确定性结果的 Run 记 `outcome=incomplete`、`resolved=null`，不写入 `resolved_runs` / `unresolved_runs`。未完成不是 `404`（那表示不存在或无权，含 `internal_test`），也不是 `409`。`report_path` 是通往单 Run 报告的链接，不代表结果已经可用。
