# 2026-09-21 D：08 十二 Run 矩阵预演与 04 恢复/制品结论记录

## 状态与情况说明

状态：Completed（2026-09-21）。

来源请求：用户问"我还有什么是没有完成的"，随后确认"这些事情能不能现在就做"。本行动只做**现在不依赖他人**的两件：

1. **08 预演**：六题已由 C 入库（`delivery/catalog_presets.py` 6 个 preset、`adapters/tasks/catalog.py` 的 `FIXED_TASK_IMAGES` 6 条身份），因此可以在本机用受控假执行把任务 08 的矩阵形状先跑通——"6 题 × 2 配置 = 12 Run"。
2. **04 的 D 侧结论记录**：C 的任务单（`.scratch/ui-catalog-providers/issues/04-five-new-tasks-and-continuous-scale.md`）把"恢复新 Job"划给 D，并注明"Run 产出制品后的制品/轨迹读取路径由 D 覆盖，需在验收时合并结论"；本行动把这两条的**已有实现与用例证据**收口成可引用的记录。

当前事实（本机核对）：

- 六题身份已在 main：`swe-gym-lite-mypy-15413/15131/15139/15184/15208/15876`。
- 规模侧（D 于 2026-09-20 交付）已在 main：`continuous(1–20)`、最多 3 配置、60 Run 上限，用例 `tests/jobs/scale/test_continuous_preset.py`。
- 恢复/重试用例已存在且在本机全绿：`tests/jobs/recovery/`（HTTP、真实 PG、边界与重试共 13 个用例）、`tests/jobs/test_postgres.py::test_explicit_upgrade_and_recreated_http_restore_frozen_job`（旧 Job 快照读回）。
- 双存储一致性：C 侧 2026-09-21 用真实 MinIO 跑通 7 个原跳过用例；D 侧 `tests/jobs/artifacts/test_postgres_minio.py` 仍受 MinIO 门控，本机记为 skipped，不记为通过。

已确认决定：预演使用受控假执行（合成 `Backend`/`Evaluator`）与隔离随机测试库，**不调用模型、不拉镜像**；预演证明的是矩阵形状、状态推进、报告与零重试不变量，不冒充真实 provider 结果。

明确排除：不跑真实 provider、不碰 05/06/07、不改产品代码行为、不改 C/B/fengyy 的文档、不把预演写成 08 完成。

## 实施措施

1. 新增 `apps/backend/tests/jobs/reporting/test_matrix_rehearsal_twelve_runs.py`：单 Job 提交 6 题 × 2 配置 → 断言笛卡尔积 12 个 Run、批准后 Worker 一次执行完成、全部 `COMPLETED` 且 `resolved_summary=true`、矩阵 2 列 × 6 行、每列 6/6、`missing=0`、Markdown 每行两格"已解决"且两列覆盖率均为 6/6。
2. 在本文档固化 04 的 D 侧结论：恢复新 Job、旧 Job 快照读回、制品/轨迹读取路径、双存储一致性与防漂移，各自指向实现与用例，并标明未验证边界。
3. 08 验证清单骨架（预演版）：把真实数据到位后要填的格子先列出来，避免 08 开工时从零组织。

完成标准：新用例通过；D 模块与全量门禁结果如实记录；两条 04 结论有可引用出处；不出现把预演当 08 完成的表述。

## 受影响文件树

```text
apps/backend/tests/jobs/reporting/
  test_matrix_rehearsal_twelve_runs.py   # 新增：6 题 × 2 配置 = 12 Run 的 08 形状预演（真实 PG + 受控假执行）
docs/actions/
  2026-09-21-d-task08-rehearsal-and-task04-records.md  # 本行动文档（含 04 结论与 08 清单骨架）
```

参与关系：复用 `test_matrix_rehearsal.py` 的夹具（`_job_seams`/`_preset_names`/`NOW`/`PATCH`）避免第二套构造；被测对象仍是 D 模块的 `JobSubmission`、`OwnerApproval`、`JobExecutor`、`WorkerShell`、`build_matrix`、`render_matrix_markdown`，没有新增接口或绕过执行链。

## 04 的 D 侧结论（可引用）

| 验收要求 | D 侧实现与证据 | 状态 |
|---|---|---|
| 恢复新 Job 不重跑旧 Job、重试需重新批准 | `tests/jobs/recovery/test_recovery_http.py`（过期恢复不重启、重放不产生新事件、仅 owner 且拒绝伪造控制字段）、`test_recovery_postgres.py`（过期恢复原子并让旧 worker 失效、从已持久化完整 Run 收束且不重执行）、`test_recovery_postgres_edges.py`（结果证据损坏回滚、保留已持久化取消意图、与过期 worker 事务竞争）、`test_retry.py`（新 Job 重试只归原提交者、幂等且不可伪造、重新校验配置启用）、`test_states.py`（只对过期活跃工作分类、混合 Run 收束） | 已实现并测试（本机全绿） |
| 读取旧 Job 快照 | `tests/jobs/test_postgres.py::test_explicit_upgrade_and_recreated_http_restore_frozen_job`：显式升级 + 重建 HTTP 后仍按冻结快照读回旧 Job | 已实现并测试 |
| 制品/轨迹读取路径不泄漏隐藏字段 | `tests/jobs/artifacts/test_http_status.py`（公开/受限制品状态）、`test_http_limits.py`（超限 raw 仍可见核心结论、超长轨迹截断不破坏核心结果）、`test_limits.py`（边界与拒绝） | 已实现并测试；C 已对 12 个公开读取面做哨兵零命中扫描 |
| 双存储一致性（MinIO 正文 ↔ PG 索引摘要） | C 侧 2026-09-21 用真实 MinIO 跑通 7 个原跳过用例（全量 481 passed / 39 skipped / 0 failed）；D 侧 `tests/jobs/artifacts/test_postgres_minio.py::test_real_postgres_and_minio_cleanup_preserves_results_and_audit` 需 MinIO 门控 | C 侧已验证；D 侧本机 **skipped，不记为通过** |
| 指纹/摘要防漂移 | 规模侧 `test_continuous_preset.py` 覆盖新预设边界；目录侧防漂移由 C 的 `test_catalog_job_flow.py` 覆盖（配置停用后旧 Job 不被改写） | 已覆盖（C 侧为主） |

## 08 验证清单骨架（预演版，真实数据到位后逐格填）

| # | 项 | 预演是否已可证 | 真实数据到位后要补的 |
|---|---|---|---|
| 1 | 12 Run 矩阵一次成型、每组合恰好一个 Run、零自动重试 | ✅ 本行动用例 | 换成真实任务身份与真实 provider |
| 2 | 状态机推进到终态（含部分失败收束） | ✅ 演练（2 批形态）与 `test_states.py` | 真实执行时长、超时与取消路径实测 |
| 3 | 逐 Run 证据：终态、确定性结果、用量与费用、基础设施失败码、证据引用、清理确认 | ⬜ 结构已就位（缺失保持 `null`、不写 0） | 真实用量/费用值、清理证据 |
| 4 | 对比矩阵与报告（五档、缺失语义、跨仓库同名不合并） | ✅ `test_matrix.py`、演练与术语表 | 真实结果分布 |
| 5 | 全量回归（后端 + Web + 浏览器） | 后端本地已跑；Web 属 B | 08 窗口统一跑并记录 |
| 6 | 双轴评审与逐项结论 | ⬜ | 由组长/评审在 08 收口 |

## 自验证方式

```text
cd apps/backend
AGENTEXAM_RUN_IDENTITY_POSTGRES=1 \
AGENTEXAM_TEST_DATABASE_URL=postgresql://agentexam_identity_test@127.0.0.1:55432/agentexam_identity_test \
  uv run pytest tests/jobs/reporting/test_matrix_rehearsal_twelve_runs.py -q
AGENTEXAM_RUN_IDENTITY_POSTGRES=1 \
AGENTEXAM_TEST_DATABASE_URL=postgresql://agentexam_identity_test@127.0.0.1:55432/agentexam_identity_test \
  uv run pytest tests/jobs -q
uv run ruff check . && uv run ruff format --check src tests && uv run mypy src
```

预期：预演用例通过且断言真实生效（12 个 Run 全部 `COMPLETED`、两列 6/6、`missing=0`）；D 模块门禁无失败；Ruff/mypy 干净。

## 自验证结果

见下节。

### 实际输出

- `pytest tests/jobs/reporting/test_matrix_rehearsal_twelve_runs.py -q` → **1 passed（3.06 秒）**：12 个 Run 一次成型、全部 `COMPLETED` 且 `resolved_summary=true`、两列各 6/6、`missing=0`、Markdown 两列覆盖率均 6/6。
- `pytest tests/jobs -q`（含真实 PostgreSQL 门禁）→ **162 passed / 4 skipped**（新增本用例后从 161 增至 162；跳过项仍是"专属 MinIO 集成未显式启用"）。
- `ruff check .` → All checks passed；`ruff format --check src tests` → 300 files already formatted；`mypy src` → Success: no issues found in 168 source files。
- 全量后端回归：**2 failed / 468 passed / 51 skipped（98.80 秒）**；两个失败仍是 `tests/contract/test_execution_network.py` 缺 `framework/harbor` 的既有环境缺口（`passed/skipped` 随上游新增用例变化，不作为跨机器基线）。
- 基线说明：上述后端数字在 `051ea51` 上测得；推送时远端已被他人推进到 `c71d342`，本提交变基到该基线后复跑 `pytest tests/jobs/reporting -q` → **19 passed**（含本新增用例）。已核对 `git diff --name-only 051ea51..c71d342 -- apps/backend` 为**空**：该区间只改文档与 `apps/web`，后端代码与用例未变，故上述后端数字对新基线同样成立。

### 偏差与边界

- 预演用的是**合成题目/配置与假执行**，不是真实六题身份与真实 provider：它证明矩阵形状、状态推进与零重试不变量，**不证明**真实运行结果。08 的"冻结矩阵"必须等 06/07 出真实数据后才算完成。
- D 侧 MinIO 门控用例（`tests/jobs/artifacts/test_postgres_minio.py`）本机仍 skipped，如实记录；双存储一致性的本机结论援引 C 侧 2026-09-21 的真实 MinIO 实跑。
- 未做：没有改任何产品代码行为，没有新增接口或表。
