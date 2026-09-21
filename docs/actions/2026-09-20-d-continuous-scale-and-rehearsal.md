# 2026-09-20 D：连续规模预设与 6+5 矩阵演练（真实数据库）

## 状态与情况说明

状态：Completed（2026-09-20 创建并完成；同日完成共享库核验与升级入口收口）。

来源请求：成员 D 于 2026-09-20 要求开始 08 与其它任务里属于 D 的部分。本项对应计划 04 中 D 的交付"Job 快照 / 60 Runs / 兼容"，以及计划 08 的"12 Run 矩阵 + 可复查对比报告"。

当前事实（本机核对）：

- 现有 `batch_presets` 只有 `demo`(1–3)、`quick`(5–5)、`standard`(10–20)（`delivery/job_presets.py:25-27`），**4/6/9 题无法提交**；而 `plan.md` 第 6 节要求"引入新的连续规模预设；新增 4/6/9 题请求必须通过，0/21 题、0/4 配置、重复 ID、未知/停用项拒绝；上限 20×3=60"。
- 本机已具备开发与验证能力：后端环境、锁定依赖、便携 PostgreSQL 15.14（测试库 + 开发库）、真实 PG 集成测试基线 **438 passed / 36 skipped / 2 failed**（2 个失败为缺 `framework/harbor` 的既有环境问题）。

已确认决定：**新增**连续规模预设 `continuous`(1–20)，**不修改**既有预设区间（向后兼容）；总上限仍由既有 `maximum_runs=60` 与 `maximum_agent_configurations=3` 约束。

当时需要协调：`batch_preset` 是 HTTP 受控选项（`GET /api/v1/job-options` 会返回），新增取值属于**公共选项的增量变化**。该待办已于同日由 B 在 `docs/interfaces/HTTP_API.md` 同步完成；本段保留最初责任边界。

明确排除项：不改既有预设区间；不改数据库 schema、路由与 DTO 结构；不调用真实模型；不下载镜像。

## 实施措施

1. `apps/backend/src/eval_platform/delivery/job_presets.py`：新增 `BatchPreset("continuous", 1, 20)`。
2. `apps/backend/tests/jobs/test_http.py`：选项"精确形状"断言同步加入新预设（该断言按设计为精确匹配）。
3. 新增 `apps/backend/tests/jobs/scale/test_continuous_preset.py`：4/6/9 题在 `continuous` 下可提交；0 题与 21 题被拒；既有预设（`demo`/`quick` 各 4 题）仍被拒。
4. 新增 `apps/backend/tests/jobs/reporting/test_matrix_rehearsal.py`：真实 PostgreSQL 上两批 Job（配置 A 跑 6 题；配置 B 跑 5 题且其中 1 题判卷失败）→ 走真实状态机 → 读批次报告 → 用 `matrix.py` + `matrix_markdown.py` 聚合渲染 → 断言覆盖率 6/6 与 5/6、1 格"缺失"、1 格"基础设施失败"（该格文案 2026-09-21 已改名为"基础设施错误"，见[术语统一行动](2026-09-21-d-five-outcome-wording-alignment.md)）。
5. 运行新增用例、含数据库门禁的全量回归、`ruff`、`mypy`，记录真实结果。

完成标准：新用例全部通过；全量回归失败集合不变；除下列文件外无其他改动。

## 受影响文件树

```text
apps/backend/src/eval_platform/delivery/
  job_presets.py                          # 修改：新增 continuous(1–20) 预设；既有预设区间不变
apps/backend/tests/jobs/
  test_http.py                            # 修改：受控选项的精确形状断言加入新预设
  scale/test_continuous_preset.py         # 新增：连续规模的接受与拒绝用例（新子目录，满足层内文件上限）
  reporting/test_matrix_rehearsal.py      # 新增：真实 PostgreSQL 的 6+5 批次矩阵演练
docs/actions/2026-09-20-d-continuous-scale-and-rehearsal.md   # 本行动文档（新增）
```

不改动：`docs/interfaces/HTTP_API.md`、`docs/architecture/MODULE_CONTRACTS.md`（共享契约，待通知/确认后由相应负责人补记）、数据库 schema、HTTP 路由、其他成员模块。

## 自验证方式

```text
cd apps/backend
# 新增与相关用例（内存层，不需要数据库）
./.venv/Scripts/python.exe -m pytest tests/jobs/scale tests/jobs/test_http.py -q
# 含数据库门禁的全量回归（预期：失败集合与基线一致）
AGENTEXAM_TEST_DATABASE_URL=postgresql://agentexam_identity_test@127.0.0.1:55432/agentexam_identity_test \
AGENTEXAM_RUN_IDENTITY_POSTGRES=1 ./.venv/Scripts/python.exe -m pytest -q
# 静态检查
./.venv/Scripts/python.exe -m ruff check src/eval_platform/delivery/job_presets.py tests/jobs/scale tests/jobs/reporting
./.venv/Scripts/python.exe -m mypy src/eval_platform/delivery/job_presets.py
# 改动范围
git status --short
```

预期：新用例全部通过；全量回归仅剩缺 `framework/harbor` 的 2 个既有失败；`ruff`/`mypy` 无新增错误；除上表文件外无改动。

## 自验证结果

完成时间：2026-09-20。逐项实测（命令在 `apps/backend` 下执行，数据库门禁开启）：

1. 新用例与相关用例：`pytest tests/jobs/scale tests/jobs/reporting -q` → **11 passed**（4 个连续规模用例含边界矩阵 + 1 个真实数据库演练 + 既有矩阵与渲染用例）。边界矩阵覆盖：20 题 × 3 配置 = 60 Run 通过；追加第 4 个配置被拒（`BATCH_PRESET_EXCEEDED`）。
2. 含数据库门禁的全量回归：**2 failed / 443 passed / 36 skipped（149.69 秒）**。相比本机数据库基线（2 / 438 / 36）：通过数 +5（本项新增用例），失败集合不变（仍是缺 `framework/harbor` 的既有环境问题）。
3. `ruff check`（改动文件）→ 首轮 1 处 `I001`（导入排序），用 `ruff check --fix` 修复后 **All checks passed**。
4. `mypy`（`job_presets.py`）→ Success: no issues found。
5. `git status --short` → 修改 3 个文件、新增 3 项，无其他改动。

过程中的偏差与关键发现（如实记录）：

- 首轮失败有两个根因：① 测试夹具的题目预设名是 `verified-task` 与 `verified-task-2..21`（**没有** `verified-task-1`），已修正；② **数据库层 CHECK 约束把允许的预设写死**（`adapters/persistence/jobs/schema.sql:12` 的 `evaluation_jobs_batch_preset_check`），新增策略预设必须同步改 schema——这正是计划所说的"改变 SQL 约束"，因此：
  - 已更新 `schema.sql`（新建库与测试沙箱自动获得新约束）；
  - 本机开发库 `agentexam_dev` 已执行 ALTER 升级；
  - 当时确认共享库需要相同约束变化；2026-09-20 后续只读核验已确认它已由他人完成升级；
  - 计划要求"04–07 改变 SQL 约束时必须交付针对基线的升级路径"；后续审查已补 `agentexam-jobs upgrade-continuous-preset`，不再依赖手抄裸 ALTER。
- 公共选项的增量变化已经写入 `docs/interfaces/HTTP_API.md` 第 7.0 节。

### 历史共享库升级输入（已执行，不要重复操作）

```sql
ALTER TABLE evaluation_jobs DROP CONSTRAINT evaluation_jobs_batch_preset_check;
ALTER TABLE evaluation_jobs ADD CONSTRAINT evaluation_jobs_batch_preset_check
    CHECK (batch_preset IN ('demo', 'quick', 'standard', 'continuous'));
```

2026-09-20 后续核验：共享长期库约束定义已包含 `demo/quick/standard/continuous`，`convalidated=true`，活动 Job 为 0。本轮没有重复执行 ALTER。代码现提供显式、幂等、失败关闭的 `agentexam-jobs upgrade-continuous-preset`：只接受已知旧三值约束并原子升级；已是四值时无操作；未知定义拒绝覆盖。隔离真实 PostgreSQL 验证了三种路径，并在验证后删除专属临时数据库与角色。

### 演练用例实际覆盖（真实 PostgreSQL）

`tests/jobs/reporting/test_matrix_rehearsal.py`：配置 A 提交 6 题、配置 B 提交 5 题（缺第 6 题），两批各自批准并由真实状态机执行；配置 B 中一题判卷失败。结果断言：A 列 `resolved=6 / missing=0`，B 列 `resolved=4 / infrastructure_error=1 / missing=1`，Markdown 汇总覆盖率分别为 `6/6` 与 `5/6`。
