# 2026-09-21 D：5 文件 ruff format 修复与重复 ID 行为确认

## 状态与情况说明

状态：Completed（2026-09-21）。

来源请求：C（目录与配置）在任务 04 收尾时发来协作请求：① 请 D 就"重复 ID"的验收措辞与实现不一致表态（是否刻意）；② 委托 D 对 5 个 D 近期合入的文件运行 ruff format（验证规范 §3 检查之一）；③ 两条知会（实现地图 §4.1 的 preset ID 候选名与实际落地不符；`test_catalog_job_flow.py` 与 `test_security.py` 的公开面扫描会覆盖 D 负责的端点）。

当前事实（本机核对）：

- `ruff format --check src tests prototype_codex_harbor_e2e.py`（`apps/backend` 下）→ 5 个文件待格式化、288 个已格式化，与 C 所列完全一致。
- 重复 ID 行为核对：实现 `application/job_submission.py:55-56` 对 task_ids/agent_configuration_ids 做 `sorted(set(...))` 归一化；`tests/jobs/test_security.py:66` 明确断言数组翻倍后 `trial_count == 1`。权威文档一致：任务 04 行动记录 `docs/actions/2026-09-12-m1-job-submission.md:22` 已锁定"题目与配置去重后计数"（经用户确认）；`docs/interfaces/HTTP_API.md:384`"任务和 Agent 列表必须非空、去重"、`:388`"任务/配置列表在规范正文中去重并排序"（幂等规范化正文，`canonical_request_sha` 直接消费归一化列表）。`verification.md` §2 Q7 与 `plan.md` 第 6 节第 5 步的"重复…拒绝"措辞与上述实现、测试、权威文档不一致。
- 对比端点的"拒绝"与"去重"并非 URL/正文不对称：`report_comparisons.py:133-138` 拒绝未知与重复参数键，`:128-129` 对 job_ids 列表内的重复值同样去重——统一规则是"未知/重复参数键拒绝，值列表去重归一化"。
- 知会核实：实现地图 `implementation-map.md:117` 写候选 `flexible-v2`，实际落地为 `continuous`（`delivery/job_presets.py:29`，行动记录 `2026-09-20-d-continuous-scale-and-rehearsal.md:14` 已确认）；`HTTP_API.md` 目前只记 demo/quick/standard（第 322 行），B 补写时应写 `continuous`（1–20）。

已确认决定：重复 ID 行为是刻意设计（去重后计数），不改为拒绝；Q7 措辞由 C 提请组长改为"重复项去重后计数"。本行动仅执行格式修复。

明确排除项：不改任何代码行为、接口形状、数据库 schema；不修改 C/B 负责的规划与契约文档；不提交、不推送（等用户确认后本地提交）。

## 实施措施

1. 对 5 个文件运行 `ruff format`（仅格式，无行为变化）。
2. 复验：`ruff format --check` 全绿；运行受影响测试文件（取消竞争、对比 HTTP、矩阵演练）确认无回归。
3. 向 C 回复结论：重复 ID 为刻意设计，附权威依据；ruff format 已修复。

完成标准：`ruff format --check` 0 待格式化；受影响测试通过；除 5 个目标文件外无其他改动。

## 受影响文件树

```text
apps/backend/src/eval_platform/
  adapters/persistence/jobs/__init__.py                # 修改：仅格式（持久化适配器包入口）
  delivery/http/routes/jobs/report_comparisons.py      # 修改：仅格式（对比报告 HTTP 翻译路由）
apps/backend/tests/jobs/
  cancellation/test_cancel_races.py                    # 修改：仅格式（取消竞争测试）
  reporting/test_comparison_http.py                    # 修改：仅格式（对比 HTTP 测试）
  reporting/test_matrix_rehearsal.py                   # 修改：仅格式（真实 PG 矩阵演练测试）
docs/actions/2026-09-21-d-ruff-format-and-q7-clarification.md   # 本行动文档（新增）
```

不改动：任何业务代码、测试断言、HTTP 契约、数据库 schema，以及其他成员的文档。

## 自验证方式

```text
cd apps/backend
./.venv/Scripts/ruff.exe format src tests prototype_codex_harbor_e2e.py
./.venv/Scripts/ruff.exe format --check src tests prototype_codex_harbor_e2e.py
./.venv/Scripts/ruff.exe check <5 个目标文件>
./.venv/Scripts/python.exe -m pytest tests/jobs/cancellation/test_cancel_races.py \
  tests/jobs/reporting/test_comparison_http.py tests/jobs/reporting/test_matrix_rehearsal.py \
  -q -p no:cacheprovider --tb=short
git status --short
git diff --stat
```

预期：check 输出 0 个待格式化；测试通过（需要真实 PG 的演练用例若未配环境变量则如实记录 skipped）；diff 仅限 5 个目标文件且为格式差异。

## 自验证结果

完成时间：2026-09-21。逐项实测（命令在 `apps/backend` 下执行）：

1. `ruff format src tests prototype_codex_harbor_e2e.py` → **5 files reformatted, 288 files left unchanged**，与 C 所列 5 个文件完全一致。
2. `ruff format --check`（全范围）→ **293 files already formatted**，0 个待格式化。
3. `ruff check`（5 个目标文件）→ **All checks passed**。
4. 改动范围核对：仅 5 个目标文件（合计 5 insertions / 15 deletions），逐文件确认均为格式差异（多行签名合并为单行等），无语义变化；另新增本行动文档。
5. 受影响测试（无 PG 门禁）→ **4 passed, 4 skipped**；4 个 skipped 均为"专属 PostgreSQL 测试未显式启用"。
6. 按 `2026-09-19-d-module-preparation.md:255` 的既有方式启动本机便携 PostgreSQL（`D:\pgsql`，仅监听回环 55432；启动前因上次重启后未手动启动而处于停止状态），带门禁重跑三个受影响文件 → **8 passed（10.02 秒）**：3 个取消竞争 + 1 个真实 PG 矩阵演练 + 4 个内存用例全部通过。
7. 验证后已 `pg_ctl stop`，恢复本机测试库到原先的停止状态。

剩余风险：无。本行动不改任何代码行为；PG 门禁用例依赖本机便携 PG 手动启动，属既有已知限制（见 `2026-09-19-d-module-preparation.md:252`），非本次引入。

另记录 C 转来的已知问题（本行动不改动）：`agent_type` 查询参数经路由字面量校验但不参与过滤（`routes/catalog.py:88` 校验后未传入，`agent_registry.list` 只收 enabled/cursor/limit）；当前因登记路径仅接受 codex 而行为等价，06/07 接入 DeepSeek/Kimi 时须真正接入过滤，否则筛选会静默失灵。
