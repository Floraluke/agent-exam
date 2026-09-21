# 2026-09-21 D：剩余 2 文件 ruff format 修复与重复 ID 行为确认

## 状态与情况说明

状态：Completed（2026-09-21）。

来源请求：C（目录与配置）在任务 04 收尾时发来协作请求：① 请 D 就"重复 ID"的验收措辞与实现不一致表态（是否刻意）；② 委托 D 对该批格式不合格文件运行 ruff format（验证规范 §3 检查之一）；③ 两条知会（实现地图 §4.1 的 preset ID 候选名与实际落地不符；`test_catalog_job_flow.py` 与 `test_security.py` 的公开面扫描会覆盖 D 负责的端点）。2026-09-21 C 补充：上游 main 已到 `fd369cc`，B 的 `7553ce0` 修好了原 5 个文件中的 3 个并把对比路由搬家，main 上只剩 2 个文件不合格。

当前事实（本机核对）：

- 在 `fd369cc` 上 `ruff format --check src tests prototype_codex_harbor_e2e.py` → 待格式化恰为 2 个文件（`tests/jobs/cancellation/test_cancel_races.py`、`tests/jobs/reporting/test_matrix_rehearsal.py`）、293 个已格式化，与 C 描述一致。
- 重复 ID 行为核对：实现 `application/job_submission.py` 对 task_ids/agent_configuration_ids 做 `sorted(set(...))` 归一化；`tests/jobs/test_security.py` 明确断言数组翻倍后 `trial_count == 1`。权威文档一致：任务 04 行动记录（`2026-09-12-m1-job-submission.md`）已锁定"题目与配置去重后计数"（经用户确认）；`HTTP_API.md` 任务提交小节写明"任务和 Agent 列表必须非空、去重""任务/配置列表在规范正文中去重并排序"（幂等规范化正文，`canonical_request_sha` 直接消费归一化列表）。`verification.md` §2 Q7 与 `plan.md` 第 6 节第 5 步的"重复…拒绝"措辞与上述实现、测试、权威文档不一致。
- 对比端点的"拒绝"与"去重"并非 URL/正文不对称：统一规则是"未知/重复参数键拒绝，值列表去重归一化"（路由拒绝重复键；`job_ids` 列表内重复值去重）。上游 `7553ce0` 的 `_check_query` 已等价实现该规则并带对应用例。
- 分支收尾（D 拍板，`3930f24`）：`xinyue-modules` 上被 `7553ce0` 取代的提交（`cdcb4cf` 拒绝逻辑、`c5e036d` 文档更正）不再合入 main，分支转历史存档；`ComparisonOutcome` 以收敛到 `matrix.py` 的上游版本为准。因此本行动的格式修复直接在 main 上进行，只处理剩余 2 个文件。
- 知会核实：实现地图写候选 `flexible-v2`，实际落地为 `continuous`（`delivery/job_presets.py`）；`HTTP_API.md` 受控选项小节补记时应写 `continuous`（1–20）。

已确认决定：重复 ID 行为是刻意设计（去重后计数），不改为拒绝；Q7 与 `plan.md` 第 6 节第 5 步的措辞由 C 提请组长改为"重复项去重后计数"，只动措辞、不动实现。

明确排除项：不改任何代码行为、接口形状、数据库 schema；不修改 C/B 负责的规划与契约文档；不重复处理已由 `7553ce0` 修好的 3 个文件；不合入存档分支上被取代的提交。

## 实施措施

1. 在 main 上对剩余 2 个文件运行 `ruff format`（仅格式，无行为变化）。
2. 复验：`ruff format --check` 全绿；`ruff check` 目标文件；带 PostgreSQL 门禁运行 `tests/catalog tests/jobs`，确认两个文件的 PG 用例实际执行并通过。
3. 将本行动文档带入 main；向 C 同步最终状态（拒绝逻辑与文档更正被上游覆盖、格式修复落点与验证数字）。

完成标准：`ruff format --check` 0 待格式化；定向测试通过且跳过项如实记录；除 2 个目标文件与本行动文档外无其他改动。

## 受影响文件树

```text
apps/backend/tests/jobs/
  cancellation/test_cancel_races.py       # 修改：仅格式（取消竞争测试）
  reporting/test_matrix_rehearsal.py      # 修改：仅格式（真实 PG 矩阵演练测试）
docs/actions/2026-09-21-d-ruff-format-and-q7-clarification.md  # 本行动文档（新增，随本次落 main）
```

不分属本行动：`adapters/persistence/jobs/__init__.py`、`delivery/http/routes/jobs/reporting/comparisons.py`（由 `report_comparisons.py` 搬家）、`tests/jobs/reporting/test_comparison_http.py` 已由 B 的 `7553ce0` 修好。

不改动：任何业务代码、测试断言、HTTP 契约、数据库 schema，以及其他成员的文档。

## 自验证方式

```text
cd apps/backend
./.venv/Scripts/ruff.exe format tests/jobs/cancellation/test_cancel_races.py \
  tests/jobs/reporting/test_matrix_rehearsal.py
./.venv/Scripts/ruff.exe format --check src tests prototype_codex_harbor_e2e.py
./.venv/Scripts/ruff.exe check tests/jobs/cancellation/test_cancel_races.py \
  tests/jobs/reporting/test_matrix_rehearsal.py
AGENTEXAM_TEST_DATABASE_URL=postgresql://agentexam_identity_test@127.0.0.1:55432/agentexam_identity_test \
AGENTEXAM_RUN_IDENTITY_POSTGRES=1 \
  ./.venv/Scripts/python.exe -m pytest tests/catalog tests/jobs -q -p no:cacheprovider --tb=short
git status --short
git diff --stat
```

预期：check 输出 0 个待格式化；定向测试通过，MinIO 集成类跳过项如实记录；diff 仅限 2 个目标文件且为格式差异。

## 自验证结果

完成时间：2026-09-21，命令在 `apps/backend` 下执行，基线为 main `fd369cc`：

1. `ruff format`（2 个目标文件）→ **2 files reformatted**。
2. `ruff format --check`（全范围）→ **295 files already formatted**，0 个待格式化。
3. `ruff check`（2 个目标文件）→ **All checks passed**。
4. 改动范围核对：仅 2 个目标文件（合计 2 insertions / 6 deletions），逐行确认为格式差异（多行表达式合并为单行），无语义变化。
5. 带 PostgreSQL 门禁：`pytest tests/catalog tests/jobs -q` → **194 passed / 11 skipped（69.19 秒）**；跳过项全部为"专属 MinIO 集成未显式启用"（非本次引入）；两个目标文件的 PG 门禁用例（取消竞争、真实 PG 矩阵演练）实际执行并通过。
6. 环境说明：本机便携 PostgreSQL 由用户另一并行会话启动并保持运行（PID 23396），本次验证直接复用，未由本行动启动或停止；未清理非本行动创建的资源。
7. 推送时 `origin/main` 已前进到 `f487f61`（web-http 模块文档，共 6 个文档文件、不触碰后端代码；含一条按 D 拍板记录的分支收尾说明）；本行动 2 个提交 rebase 到该基线后重新核对：`ruff format --check` 仍 295 全绿，代码内容与上述验证时一致。

过程中的偏差（如实记录）：原计划在 `xinyue-modules` 上 rebase 后提交 5 文件格式修复；执行中发现该分支已被 D 拍板转历史存档（`3930f24`），且 rebase 逐提交核对确认 `cdcb4cf`、`c5e036d` 被 B 的 `7553ce0` 完全覆盖（`_check_query` 等价拒绝、测试用例齐备、文档已含 `coverage→total` 更正与 `ComparisonOutcome` 收敛）。据此改为在 main 上直接修复剩余 2 个文件；存档分支不删除、不再合入。

剩余风险：无新增。本行动不改任何代码行为；PG 门禁用例依赖本机便携 PG 手动启动，属既有已知限制（见 `2026-09-19-d-module-preparation.md` 的本机数据库小节），非本次引入。

另记录 C 转来的已知问题（本行动不改动）：`agent_type` 查询参数经路由字面量校验但不参与过滤（`routes/catalog.py` 校验后未传入，`agent_registry.list` 只收 enabled/cursor/limit）；当前因登记路径仅接受 codex 而行为等价，06/07 接入 DeepSeek/Kimi 时须真正接入过滤，否则筛选会静默失灵。

> **2026-09-21 E 侧更正（原文不动）**：上文"06/07 接入 DeepSeek/Kimi 时须真正接入过滤，否则筛选会静默失灵"的**触发条件不准确**。按权威定义，`agent_type` 是**执行器类型**而非模型提供方：[DATA_MODEL.md 第 271 行](../../docs/architecture/DATA_MODEL.md) 列其为 `custom`/`codex`/`aider`/`claude_code`，[HTTP_API.md 第 297 行](../../docs/interfaces/HTTP_API.md) 写明"MVP 为 `codex`；后续加入 `aider`、`claude_code`；P2 才启用 `custom`"。因此 DeepSeek/Kimi 预设的 `agent_type` **仍是 `codex`**（变化的是 `model_provider` 与 `authentication_type`），06/07 不会因此失灵。
>
> 真实的缺口是另一条：[HTTP_API.md 第 315 行](../../docs/interfaces/HTTP_API.md) 要求"**合法筛选无匹配返回空列表**"，而实现从不把该参数传下去，所以一旦出现第二个**合法 agent_type**，请求它只会拿到全部条目、不会返回空列表。今天只有 `codex` 一种合法值，行为等价，故不可观测。
>
> 代码未改动。该接线属任务 05 实施方案 S8（目录与身份扩展）范围，建议与"解除 `model_provider` / `authentication_type` 的库级 CHECK 以登记受控 API 预设"同批处理。
