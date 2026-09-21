# 2026-09-21 D：对比矩阵五档中文文案统一（后端报告 ↔ Web 界面）

## 状态与情况说明

状态：Completed（2026-09-21）。

来源请求：B 经用户转达两点。① 对比矩阵五档中文文案由 B 定为「已解决 / 未解决 / 基础设施错误 / 未完成 / **缺失**」，请 D 确认术语口径——特别是「缺失」（该组合没有 Run，或 Run 完成但报告不可读，不等于「未解决」）；UI 刻意把两种缺失分开成「无运行」和「报告缺失」。② 边界知会：任务 03 的契约 PR #3 已关闭，main 已有 §10.4 且以 `7553ce0` 那版为准；B 此后未再动 D 的提案文档，也未碰 D 归档的分支。

当前事实（本机在 main `0b66a29` 上核对）：

- 后端报告渲染器 `application/reporting/matrix_markdown.py` 的 `_CELL_LABELS` 用「通过 / 未通过 / 基础设施失败 / 未完成 / 缺失」，与 B 的界面文案在 3 档上不一致（通过↔已解决、未通过↔未解决、基础设施失败↔基础设施错误）。同一格子在页面和报告里说不同的话。
- 仓库既有词汇与 B 那一套一致，不是新造：已交付的排行榜页面 `apps/web/src/features/leaderboard/view.tsx:31-32` 用「未解决 / 基础设施错误」；架构层 `docs/architecture/ARCHITECTURE.md:93`、`docs/architecture/MODULE_CONTRACTS.md:80`、`docs/architecture/modules/owner-host-runtime/ARCHITECTURE.md:82` 一律写「基础设施错误」；任务 01 已验收的原型（`.scratch/ui-catalog-providers/issues/01-clickable-html-prototype.md:15`）写「已解决、未解决、……、缺失」。
- 五档的英文 token 已由契约固定：`docs/interfaces/HTTP_API.md` §10.4 的 `resolved/unresolved/infrastructure_error/incomplete/missing`；判据与两种缺失由 `application/reporting/matrix.py:127-146` 实现（`run_id=null` → 没有 Run；`run_id` 非空且 `report_path=null` → 有 Run 但报告缺失）。

已确认决定（B 提出、D 确认口径）：

1. 五档中文文案采用 B 的一套，界面与后端报告共用同一套词，不再各写一份。
2. 「缺失」= 该组合没有 Run，**或** Run 完成但报告不可读；既不等于「未解决」，也不写成 0，且不计入 `decided`；`total = decided + missing`，分母保持完整矩阵。
3. 两种缺失在界面分列时，唯一判据是后端 `run_id` 是否为空，不新增字段、不改响应形状。

明确排除：不改英文 token、响应形状、数据库 schema；不改 B 的 Web 文件与 `HTTP_API.md`（§10.4 归 B）；不改 fengyy 的 `.scratch/ui-catalog-providers/{plan,verification,implementation-map}.md`——其中「未通过 / 执行故障 / 基础设施故障」属验收规范的散文描述，若要统一用词应由文本所有者提出，D 不越界改写。

## 实施措施

1. `matrix_markdown.py`：`_CELL_LABELS` 三档文案与汇总表头改为统一用词；docstring 同步。
2. 同步受影响的断言与 docstring：`test_matrix_markdown.py`（断言与注释）、`test_matrix_rehearsal.py`（文件 docstring 描述）。
3. 在 D 的模块架构文档固化五档术语表（英文 token ↔ 中文文案 ↔ 判据 ↔ 缺失两个子类），写明"语义归 D、文案由 B 定并已确认"。
4. 两条 D 的历史行动记录加一行修订指针（保留当时事实，不重写历史）。
5. 定向测试 + Ruff + mypy + 真实 PostgreSQL 门禁回归。

完成标准：后端报告输出与界面文案逐档一致；术语表成为唯一权威映射；定向与门禁用例全绿；除历史记录修订指针外无残留旧文案。

## 受影响文件树

```text
apps/backend/src/eval_platform/application/reporting/
  matrix_markdown.py                     # 修改：五档文案与汇总表头对齐 B 的界面用词（唯一输出中文文案处）
apps/backend/tests/jobs/reporting/
  test_matrix_markdown.py                # 修改：断言与注释改为新文案
  test_matrix_rehearsal.py               # 修改：文件 docstring 描述文案
docs/architecture/modules/evidence-and-reporting/
  ARCHITECTURE.md                        # 修改：新增五档术语表（token ↔ 文案 ↔ 判据）并统一既有措辞
docs/actions/
  2026-09-19-d-report-matrix-spike.md    # 修改：加一行修订指针（当时用词为 通过/未通过/基础设施失败）
  2026-09-20-d-continuous-scale-and-rehearsal.md # 修改：同上
  2026-09-21-d-five-outcome-wording-alignment.md # 本行动文档
```

参与关系：`matrix.py` 是领域值与聚合实现（判据唯一来源，不改）；`matrix_markdown.py` 只是显示层映射（本行动唯一改动点）；界面文案由 B 的 Web 层消费同一套词；`HTTP_API.md` §10.4 继续只固定英文 token，不复制中文文案。

## 自验证方式

```text
cd apps/backend
uv run pytest tests/jobs/reporting -q -p no:cacheprovider
AGENTEXAM_RUN_IDENTITY_POSTGRES=1 \
AGENTEXAM_TEST_DATABASE_URL=postgresql://agentexam_identity_test@127.0.0.1:55432/agentexam_identity_test \
  uv run pytest tests/jobs -q -p no:cacheprovider
uv run ruff check . && uv run ruff format --check src tests
uv run mypy src
```

预期：报告/矩阵/CLI 用例全绿（含真实 PG 演练）；五档文案与 `apps/web/src/features/leaderboard/view.tsx` 用词一致；无新增 mypy/Ruff 告警；旧文案只出现在历史记录并被修订指针说明。

## 自验证结果

### 定向与门禁（实际输出）

首次验证在 `0b66a29` 上完成；推送时远端 main 已前进到 `ae0cc9f`（B 的任务 03 对比页、C 的五题入库等），本提交变基到该基线后**重新跑过**下列检查：

- `pytest tests/jobs/reporting -q`（含真实 PostgreSQL 门禁）→ **18 passed，0 failed**；覆盖矩阵五档、Markdown 标签与缺失计数、`render-matrix` 命令端到端（真实 PG）和对比 HTTP。
- `pytest tests/jobs/reporting tests/jobs/scale -q`（变基后复跑）→ **26 passed**。
- `pytest tests/jobs -q`（含真实 PostgreSQL 门禁）→ **161 passed / 4 skipped**；跳过项全是"专属 MinIO 集成未显式启用"，非本次引入。
- 全量后端回归（变基后）：**2 failed / 467 passed / 51 skipped（195.21 秒）**；两个失败仍是 `tests/contract/test_execution_network.py` 缺 `framework/harbor` 的既有环境缺口（`passed/skipped` 随上游新增用例与门禁环境变化，不作为跨机器基线）。
- `ruff check .` → 首次报 **1 个 E501**（汇总表头行 90 > 88 字符，中文扩容导致），把该行改成两段隐式字符串拼接后 **All checks passed**。
- `ruff format --check src tests` → **294 files already formatted**；`mypy src` → **Success: no issues found in 167 source files**。
- 文案核对：`_CELL_LABELS` 五档为 已解决 / 未解决 / 基础设施错误 / 未完成 / 缺失，与已合并的 Web 对比页 `apps/web/src/lib/reporting/comparison-shapes.ts:12-14`、批次报告 `apps/web/src/features/jobs/batch-report.tsx:4-6` 和排行榜 `view.tsx:31-32` 一致。

### 偏差与边界

- 历史行动记录（`2026-09-19-d-report-matrix-spike.md`、`2026-09-20-d-continuous-scale-and-rehearsal.md`）里的旧用词保留原文，只加修订指针——它们是当时的真实记录，不改写历史。
- fengyy 的验收规范散文里仍有"未通过 / 执行故障 / 基础设施故障"，本行动不改（不属 D 的文档，且属描述性表述）。
- 前端仍有两处残留用词不在本次范围（属 B 的文件，D 未改动）：`apps/web/src/features/jobs/report.tsx:20` 的"基础设施失败"与 `apps/web/src/features/jobs/reporting/comparison.tsx:70` 的"不当作未通过"，已同步给 B 由其决定。
- 未做：没有生成新的真实矩阵报告样例（需要真实 Run，属任务 08 范围）。
