# 任务 04：五道新题合格入库与 1–20 连续规模（目录与配置）

## 状态与情况说明

- 状态：In progress（准备阶段，未获实施授权；本机开发环境已于 2026-09-20 建立）。本行动由 C（目录与配置 DRI、任务 04 任务 DRI）建立，先记录范围、前置门禁、计划文件树与验证方式。**截至当前未修改任何产品代码、未下载镜像或数据、未调用模型、未读取真实凭据、未连接共享数据库。**
- 对应任务：[执行计划](../../.scratch/ui-catalog-providers/plan.md)第 6 节任务 04；分工见[团队分工](../architecture/modules/TEAM_WORK_ALLOCATION.md)第 4.2 与第 5 节。任务 04 当前为“已规划、未发布 issue”，按计划第 1 节第 5 条与第 5.2 节，任务单发布且用户安排前不进入实施。
- 本行动是独立实施任务的行动文档；`ui-catalog-providers` 的规划正文仍由[规划行动](2026-09-17-ui-catalog-provider-planning.md)维护，本文件不复制规则正文，只记录 04 的实施、偏差与验证证据。
- 实施基线（2026-09-20 更新）：团队上游仓库 `anphuchoang5-sys/agent-exam`，只作只读同步、不直接推送；交付分支为个人 fork `Floraluke/agent-exam` 的 `lyq`，基于上游 `main` 的 `a49b000`；PR 从 fork 提到上游 `main`。本机克隆 `C:\Users\陆泳倩\Desktop\agent-exam`。

### 当前事实（2026-09-19 实际核对）

- 受控题目目录只有一道题：`delivery/catalog_presets.py` 的 `TASK_PRESETS` 仅含 `swe-gym-lite-mypy-15413`；`adapters/tasks/swe_gym.py` 用单一常量 `CANDIDATE_INSTANCE_ID` / `CANDIDATE_IMAGE` 冻结该题身份。固定数据源为 `SWE-Gym/SWE-Gym-Lite` `train`，revision `61231f2c…`，快照 931193 字节、sha256 `f3a7cd93…`，并按实例 id 过滤读取。
- 受控配置目录只有一个配置：`codex-0153-terra-medium`（Codex 0.153.0 / gpt-5.6-terra / medium）。
- 规模策略：`delivery/job_presets.py` 当前给 `demo(1,3)`、`quick(5,5)`、`standard(10,20)` 三个 `BatchPreset`；`domain/jobs/policy.py` 的 `SubmissionPolicy` 已有 `maximum_agent_configurations=3` 与 `maximum_runs=60`。缺的是“连续 1–20 题”这一档，不是 60 次上限本身。
- 本机运行条件（2026-09-20 晚间更新）：**已建立本机开发环境**——`apps/backend/.venv`（Python 3.13.15 + `uv.lock` 锁定依赖）、便携 PostgreSQL 15.14 于 `127.0.0.1:55432`、测试库 `agentexam_identity_test` 与开发库 `agentexam_dev`；`tests/catalog` 33 passed / 7 skipped，全量 452 passed / 36 skipped / 2 failed（2 项为缺 `framework/harbor` 的既有环境失败）。见[本机开发环境](../LYQ/06-environment/LOCAL_SETUP.md)与[环境行动文档](2026-09-20-local-environment-setup.md)。**仍不具备**：`framework/`、`runtime/`、`infra/data/`、固定 Parquet 快照与 Docker Desktop——容器类、固定数据类与判卷类步骤仍只能由组长机器或 E 执行。
- 上游 `.scratch/ui-catalog-providers/` **已同步**（2026-09-20 晚间复核）：`issues/01`、`issues/02` 与更新版 `plan.md` 已随 `ff46cec` 进入上游 `main`；我方与上游在该目录下的唯一差异是本人起草的 `issues/04-*` 草案。[ISSUE-02](../LYQ/04-issues/KNOWN_ISSUES.md) 因此关闭。
- 上游 `main` 当前为 `beed93f`（2026-09-20 20:49）：除 D 的任务 03 报告语义设计、对比服务与对比端点、任务 08 runbook 外，还包含 D 的 `continuous(1–20)` 预设与其边界测试、B 的工作台合并。任务 03 仍无任务单，`01 → 02 → 03 → 04` 的顺序门禁未解除。

### 上游门禁（未满足前不进入实施）

- 计划第 6 节前置：固定数据、Fork、镜像与专属存储条件可核验；**没有下载范围授权时不拉镜像**。
- 顺序门禁：执行顺序为 `01 → 02 → 03 → 04`，任务 03 完成后才进入 04；多任务并行需先单独修改执行计划，本分工文档不授权越阶段。
- 交接门禁：E 主责参考/空/错误补丁的固定 Fork 资格验证；D 负责 Job 快照与最多 60 Runs 兼容；B 负责 HTTP options 与三步向导；A 负责磁盘与长期 schema 变更窗口。
- 数量门禁：至少五道题未完成不得标记任务完成，不足五题时停止汇报，不从同一固定 mypy 集合之外改项目或数据集。

### 待确认

- 任务 04 的独立任务单（`.scratch/ui-catalog-providers/issues/04-*.md`）由谁发布、以何范围发布；本人已起草草案（`Status: needs-info`）并随 PR #2 提交给上游，**尚无评论与评审**。计划第 5.2 节的措辞是「任务未发布/用户未安排时」不提前改产品代码，即发布或明确安排任一满足即可开工。
- 镜像/数据的下载授权范围与磁盘配额；以及五道候选题三补丁门禁的执行安排（E 主责，需组长机器的执行窗口）。
- 规模侧收口口径（见实施措施第 5 条）：既有覆盖是否已满足计划要求，以及「重复 ID」应维持去重还是改为拒绝。
- 05–07 提供方配置的最终型号与协议以规格 Q8–Q10 为准，C 的受控配置部分需在其任务发布后另行建立或并入本行动。

### 明确排除

- 不改 Web 产品代码（任务 02/03 属 B）；不改 05–07 的代理与执行链（属 E）。
- 不新增顶层 Module、公共 Interface 或数据库表；若 04 需要 schema 变更，先说明理由并取得用户确认，再由 A 安排变更窗口。
- 不调用真实模型、不读真实 `auth.json`、不把隐藏答案或判卷字段暴露给做题侧或 HTTP/Web。

## 实施措施

1. 按候选顺序逐个读取固定快照记录，冻结 instance、base commit、公开题面摘要、隐藏判卷字段摘要与镜像 digest；先列本地缓存/缺失镜像、磁盘需求与下载来源，未获授权不拉取。
2. 资格验证候选顺序：`python__mypy-15184`、`python__mypy-15208`、`python__mypy-15131`、`python__mypy-15139`、`python__mypy-15876`。同项目不共用旧题镜像；`15876` 额外确认存在真实 FAIL_TO_PASS，不用仅文档修改凑数量。
3. 每题独立容器、固定 Fork、外网关闭，依次跑参考补丁、空补丁、可应用但错误的补丁；确认测试确实执行且参考通过、负例未解决。基础设施错误不算负例成功；空补丁本来就通过的题不合格。记录镜像/数据/报告身份与精确清理结果（执行由 E 主责，C 组织交接并收口证据）。
4. 只有通过门禁的题进入受控目录白名单；保留旧题身份与 M0 单题入口。候选不合格时从同一固定 mypy 集合选替补并重走全部门禁。
5. 规模侧（2026-09-20 核对后收窄）：连续预设 `continuous(1–20)` 及其边界用例**已由 D 合入上游**——4/6/9 题通过、0/21 题拒绝、20×3=60 允许、第 4 个配置拒绝均已有测试；「未知条目」「停用条目」的拒绝也已覆盖（`tests/jobs/test_security.py:60`、`tests/jobs/test_concurrency.py:58`）。剩余工作改为：**核对**上述既有覆盖是否覆盖计划要求的全部拒绝项。**2026-09-20 复核更正**：所谓「0 个配置」空白项并不存在——`tests/jobs/test_security.py:41-42` 已同时断言 0 题与 0 个配置返回 `400 EMPTY_JOB_SELECTION`，我先前的结论核查不充分。**已定案（2026-09-20 深夜，D 回复）**：「重复 ID」的**去重是刻意设计，实现不改**。统一规则为「未知/重复**参数键**拒绝、值列表**去重归一化**」。依据：[任务 04 行动记录](2026-09-12-m1-job-submission.md)第 22 行「题目与配置**去重后计数**；空选择、规模不符、非法覆盖在创建前拒绝」，[HTTP_API.md](../interfaces/HTTP_API.md) 第 426/430 行「必须非空、去重」「列表在规范正文中去重并排序」（两处已逐字核对属实）。剩余动作在措辞侧：请组长把 `verification.md` Q7 与 `plan.md` 第 6 节第 5 步的「重复 ID…拒绝」对齐为「重复项去重后计数」。本行动 09-19 版的「重复题目必须拒绝」表述作废。
6. 打通目录 → HTTP options → 三步向导 → 冻结 Job/全部 Runs/初始事件的事务；创建只返回“等待批准”。验证读取旧 Job、恢复新 Job、双存储一致性与指纹/摘要防漂移；同步权威文档后收尾。**进展（2026-09-20）：C 侧打通链已实现并测试**——新增 `apps/backend/tests/catalog/test_catalog_job_flow.py`，用目录列表与 HTTP 选项驱动 6 题 × 2 配置提交，断言创建只返回 `AWAITING_OWNER_APPROVAL`、全部 Runs 恰好覆盖笛卡尔积、Job 与每个 Run 都带 `JOB_SUBMITTED`、冻结身份与目录记录逐字段一致；并覆盖“配置停用后旧 Job 不被改写、新提交被拒”。剩余：三步向导的浏览器动线（与 B 交接）、恢复新 Job 与双存储一致性。

7. 暴露面收敛的 HTTP 层断言（2026-09-20 第二增量，实施中）：现有断言只在契约层（`tests/contract/test_m0_pipeline.py:47` 的 `not hasattr(request.runs[0].task, "gold_patch")`）与个别响应上成立，**没有任何测试逐条扫描公开读取面**。做法：用带哨兵值的合成目录（`HIDDEN_ANSWER`、`hidden_test`、`hidden_pass`、`private-test-reference` 分别来自 `gold_patch`/`test_patch`、`fail_to_pass`、`pass_to_pass`、`credential_profile_id`）登记并提交后，逐条请求目录、配置、选项、Job、报告、对比、制品索引与轨迹端点，断言哨兵一处都不出现，并用公开题面仍在作为对照，避免"响应为空所以通过"。加在既有 `tests/catalog/test_security.py`（该文件已负责"隐藏答案与 Key 不进入公开输出"，且 `tests/catalog/` 内容文件数已达 8 的上限，不再新增第 9 个）。浏览器页面与其他读取面仍归 B/后续任务。

## 需要修改的文件树（计划；实施时按实际回填）

```text
apps/backend/src/eval_platform/
├─ adapters/tasks/swe_gym.py        # 单题常量 → 受控候选集（instance、镜像 digest、数据身份）
├─ adapters/tasks/collect_patch.sh  # 题目侧 patch 收集；多题时核对参数与路径假设
├─ delivery/catalog_presets.py      # TASK_PRESETS 扩展为旧题+合格新题；AGENT_PRESETS 预留 05–07
├─ application/task_catalog.py      # 白名单登记与校验；多题语义按需扩展，不放松 allowlist
├─ domain/jobs/policy.py            # （已由 D 完成，本行动不改）BatchPreset 连续 1–20 与既有区间解释
├─ delivery/job_presets.py          # （已由 D 完成，本行动不改）continuous(1,20) 已于 2026-09-20 合入上游
├─ application/job_submission.py    # （2026-09-20 复核：空选择的拒绝已有覆盖，无需改动）
└─ delivery/http/routes/jobs/routes.py  # job-options 暴露新预设（与 B 交接前端展示）
apps/backend/tests/
├─ catalog/test_http.py             # 目录 HTTP：登记与读取；2026-09-20 增补配置列表分页与状态筛选
├─ catalog/conftest.py              # 2026-09-20：catalog_api 增加可选 agent_presets（默认行为不变）
├─ catalog/test_catalog_job_flow.py # 新增（2026-09-20 已实现）：目录→options→提交→冻结 Job/Runs/初始事件的打通链
├─ catalog/test_consistency.py      # 目录记录与对象摘要一致
├─ catalog/test_security.py         # 隐藏答案与 Key 不进入公开输出（2026-09-20 新增公开读取面全量扫描用例）
├─ integration/test_swe_bench_integration.py  # 新题固定 Fork 离线判卷（E 执行，C 收证据）
├─ jobs/scale/test_continuous_preset.py  # （D 已建，不改）规模边界覆盖现状见实施措施第 5 条
├─ jobs/test_concurrency.py         # 并发批准/claim 只有一个合法结果
├─ jobs/test_postgres.py            # 真实 PG 下的快照与事务
└─ jobs/recovery/test_retry.py      # 恢复不自动续跑旧 Job
docs/
├─ architecture/modules/catalog-and-configuration/ARCHITECTURE.md  # 目录能力现状与规划边界
├─ architecture/MODULE_CONTRACTS.md # Task/Agent Catalog 契约与稳定错误
├─ architecture/DATA_MODEL.md       # 仅在确实需要 schema 变更时同步（A 的窗口）
├─ interfaces/HTTP_API.md           # 目录、job-options 与提交契约同步
└─ actions/2026-09-19-task-04-catalog-candidates-and-scale.md      # 本行动
HANDOFF.md                          # 当前停点与下一步（收尾时更新）
```

不修改：`.scratch/ui-catalog-providers/plan.md` 等规划正文（归规划行动维护）、`apps/web/` 产品代码（归 B）、代理与执行链实现（归 E）。

## 任务 04 测试设计（准备阶段成果，未执行）

按[分层验收规范](../../.scratch/ui-catalog-providers/verification.md)第 2 节需求覆盖表（Q5、Q7 归 04）与第 4 节负例整理。用例先落在此处，实施时再落到具体测试文件；本轮未编写也未运行任何测试。

### A. 目录层：新题入库

1. 六题可选：登记旧题与五道新题后，目录读取返回六道，每道带固定的 dataset revision、base commit 与镜像 digest。
2. 公开与隐藏分离：登记响应、目录列表与网页里都不出现 `gold_patch`、`test_patch`、测试名单、环境对象键与认证文件内容。
3. 摘要一致：目录记录与对象存储摘要吻合；对象被替换或损坏后读取必须失败，不返回看似正常的任务。
4. 未知与停用拒绝：不在受控白名单的 instance、已停用条目、重复登记返回稳定错误，不静默接受。
5. 旧题不退化：`swe-gym-lite-mypy-15413` 仍可读，M0 单题入口仍可用。
6. 镜像未冻结的候选不得登记：镜像 digest 未确认时拒绝登记，不用占位值放行。

### B. 规模层：1–20 连续

1. 合法通过：1、4、6、9、20 道题，配 1、2、3 个配置均可提交。
2. 必须拒绝：0 道题、21 道题、0 个配置、4 个配置、重复题目、重复配置、未知或停用条目。
3. 总上限：题数×配置数超过 60 必须拒绝（例如 20×4、21×3）。
4. 旧快照兼容：`demo`、`quick`、`standard` 三个旧预设对历史 Job 的解释不变；新策略不改写任何历史 Job 快照。
5. 事务完整性：创建失败不留下半个 Run 矩阵；同一幂等键配不同请求体必须冲突。
6. 并发：并发批准与并发 claim 各自只有一个合法结果。

### C. 新题判卷：固定 Fork 离线（E 执行，C 组织交接并收证据）

逐题跑三种补丁并分类：参考补丁必须 resolved；空补丁必须不通过，且不能是“本来就通过”的题；可应用但错误的补丁必须不通过。基础设施错误单独归类，不得算作负例成功。

### D. 浏览器：少量动线（与 B 交接）

向导能选到六道题、能看清题数×配置数与最多 60 次 Run 的提示、提交后只显示“等待 owner 批准”。

## 自验证方式与成功标准

获授权实施后，按[分层验收规范](../../.scratch/ui-catalog-providers/verification.md)执行；命令在对应任务获安排、依赖与工具核对后才运行，本轮不运行：

- 后端（`apps/backend`）：`ruff check`、`ruff format --check`、`mypy`、`pytest tests/catalog tests/jobs -q`、最终全量 `pytest`；默认跳过的真实存储/容器用例逐项列 skipped，不算通过。
- 重型入口（需授权与镜像）：`tests/catalog/runtime/verify.ps1`、`tests/jobs/runtime/verify.ps1`、`tests/integration/test_swe_bench_integration.py`。
- Web（与 B 交接后）：`npm run typecheck`、`npm run build`、`npm run test:e2e`。
- 成功标准：原题+至少五道新题合格可选；五组参考/空/错误判卷证据齐备；六题×三配置的合成提交、20×3 边界与旧快照兼容通过；不读真实 auth、不调用模型、隐藏答案不出现在做题侧与 HTTP。

## 自验证情况

- 2026-09-19 至 09-20 白天：准备阶段，未修改代码，未运行任何检查。
- **2026-09-20 晚间：本机环境已建立并实测**（只建立环境、只跑既有测试，未改任何产品代码）：
  - `pytest tests/catalog -q`（带 `AGENTEXAM_RUN_IDENTITY_POSTGRES=1` 与专属回环测试库 DSN）→ **33 passed, 7 skipped**；7 项为需 MinIO 的集成用例，按设计跳过，不计为通过。
  - 全量 `pytest -q` → **452 passed, 36 skipped, 2 failed**（119.75s）。2 个失败为 `tests/contract/test_execution_network.py` 缺 `framework/harbor` 的既有环境失败；已用 `--tb=line` 核对报错为 `git -C .../framework/harbor rev-parse HEAD` 失败，非代码缺陷，也无法在本机修复。
  - 静态检查（同期补跑）：`ruff check .` → **All checks passed**；`mypy src/eval_platform` → **Success: no issues found in 166 source files**（直接跑 `mypy` 会因 editable 安装缺 `py.typed` 标记报错，须给显式路径）；`ruff format --check` → 本分支基线（`beed93f`）仍报 5 个文件不合格，均为 D 近期合入、非本行动引入；**D 已于 2026-09-20 深夜对这批文件跑 `ruff format` 并验证 `format --check` 293/293 全绿、受影响用例 8 个通过（含 4 个真实 PG 门禁用例）、diff 为纯格式差异**。该修复尚未进入本分支基线，rebase 到含修复的提交后需重新复核，本行动不代替那次复核。
- 任务 04 的题库侧与判卷侧验收项**未开始**（需组长机器/E）；目录侧的打通链已按实施措施第 6 条落地，其余目录侧项未开始。

### 本次代码增量（2026-09-20，用户明确要求开工后实施）

- 新增 `apps/backend/tests/catalog/test_catalog_job_flow.py`（2 个用例，只加测试、未改任何产品代码）：
  1. `test_catalog_and_options_drive_one_frozen_submission`：登记 6 题 + 2 配置 → 读目录列表 → 读 `/api/v1/job-options` → 按选项提交 `continuous` → 断言 `202` 且 `AWAITING_OWNER_APPROVAL`、`trial_count == 12`；读回 Job 详情后断言冻结的题目身份（instance_id / dataset_id / dataset_revision / split / base_commit / problem_statement）与配置指纹与目录记录逐字段一致；断言 12 个 Runs 恰好覆盖 题目 × 配置 的笛卡尔积，且 Job 与每个 Run 都带 `JOB_SUBMITTED` 初始事件。
  2. `test_frozen_job_keeps_its_snapshot_when_the_catalog_changes`：提交后停用该配置 → 旧 Job 的冻结快照与状态不变（不被目录变更改写）；新提交返回 `409 AGENT_CONFIGURATION_DISABLED`。
- 实测结果：`pytest tests/catalog -q`（带 `AGENTEXAM_RUN_IDENTITY_POSTGRES=1`）→ **35 passed / 7 skipped**（此前 33 passed，新增 2 个）；全量 `pytest -q` → **454 passed / 36 skipped / 2 failed**（103.73s，失败项与本次改动前完全相同，无回归）；`ruff check`、`ruff format --check`、`mypy src/eval_platform` 对新增文件均通过。
- **变异检查**（确认断言有效，非空跑）：把 `base_commit` 比对改成必然不等的值和把笛卡尔积期望缩小一格后跑测试，结果 `1 failed, 1 passed`，探针文件已删除。
- 未覆盖（如实记录）：三步向导的浏览器动线（B）、恢复新 Job、双存储一致性（MinIO 集成在本机跳过）、五道题的三补丁门禁。

### 本次代码增量 2（2026-09-20，暴露面收敛的 HTTP 层断言）

- 修改 `apps/backend/tests/catalog/test_security.py`（只加测试）：新增 `test_hidden_evaluation_fields_never_reach_public_surfaces`。
- 做法：用带哨兵值的合成目录登记并提交一道题（`HIDDEN_ANSWER` 来自 `gold_patch`/`test_patch` 与原始记录的 `patch` 字段、`hidden_test` 来自 `fail_to_pass`、`hidden_pass` 来自 `pass_to_pass`、`private-test-reference` 来自 `credential_profile_id`），随后逐条请求 12 个公开读取面——`/tasks`、`/tasks/{id}`、`/agent-configurations`、`/agent-configurations/{id}`、`/job-options`、`/jobs`、`/jobs/{id}`、`/reports/jobs/{id}`、`/reports/runs/{id}`、`/reports/comparisons?job_ids=`、`/runs/{id}/artifacts`、`/runs/{id}/trajectory`——断言四个哨兵一处都不出现。
- 实测结果：`pytest tests/catalog -q` → **36 passed / 7 skipped**（此前 35）；全量 `pytest -q` → **455 passed / 36 skipped / 2 failed**（104.16s，失败项与改动前完全相同）；`ruff check`、`ruff format --check` 通过。
- 如实记录：`/runs/{id}/trajectory` 对**未执行**的 Run 按契约返回 **409**（内容尚未产出），本用例把拒绝集合显式断言为 `⊆ {trajectory}` 并**不把 409 当作通过**，只验证"拒绝响应里同样不含隐藏字段"；一旦 Run 真正产出制品，读取成功路径由 D 的 `tests/jobs/artifacts/test_http_limits.py`、`tests/jobs/execution/test_evidence_publication.py` 覆盖。
- **变异检查**：把公开题面 `"Fix the visible bug."` 混入哨兵列表后跑该用例，结果 `1 failed`（说明断言确实在扫描响应体，不是空跑）；探针文件已删除。


### 本次代码增量 3（2026-09-20，目录 HTTP 的配置列表分页与筛选）

- 修改 `apps/backend/tests/catalog/conftest.py`（加可选参数 `agent_presets`，默认与原先完全一致）与 `apps/backend/tests/catalog/test_http.py`（新增 `test_agent_list_paginates_and_filters_by_state`）。
- 补的缺口：目录 HTTP 支持 `cursor`/`limit`/`agent_type`/`enabled`，但此前只有「停用后 `?enabled=true` 返回空」一个断点；**配置列表的游标往返与状态筛选没有测试**，而三步向导真实调用是 `GET /api/v1/agent-configurations?limit=100&agent_type=codex&enabled=true`。
- 用例断言：3 个配置两页取完、不重不漏、末页无 `next_cursor`；`?limit=100&agent_type=codex` 返回全部 3 个；`?agent_type=other` 被 422 拒绝；停用一个后 `enabled=true` 返回其余两个、`enabled=false` 只返回被停用的那个。
- 实测：`pytest tests/catalog -q` → **37 passed / 7 skipped**；全量 `pytest -q` → **456 passed / 36 skipped / 2 failed**（失败集合同前，无回归）；`ruff check`、`ruff format --check` 对改动文件通过。
- **变异检查**：把首页期望改为 3 项、把停用侧期望改为空列表后，用例确实失败（探针已删）。
- 如实记录一条实现事实：`agent_type` 参数被路由接受并做字面量校验（只允许 `codex`），但**不参与过滤**（`registry.list` 只接收 `enabled`/`cursor`/`limit`）。因为登记路径本身只接受 codex 配置，行为上等价；但若将来新增提供方，这个参数需要真正接上过滤。
