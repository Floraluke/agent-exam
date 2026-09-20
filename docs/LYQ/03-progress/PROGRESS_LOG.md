# 开发进度日志

> 只记录事实与实际结果：做了什么、实际输出是什么、遇到什么。计划见 [`01-plan/PLAN.md`](../01-plan/PLAN.md)。
> 格式：按日期倒序追加，最新在最上面。

## 2026-09-20（晚间补记：本机开发环境与事实更正）

### 已完成

- 拉取上游：`upstream/main` 前进到 `beed93f`（含 B 的 `ff46cec` 工作台合并、D 的连续规模预设与对比端点等）。我的 `lyq` 已包含上游全部提交（落后 0），fork 的 `main` 也已同步；上游 PR #2 仍开着、**0 条评论 0 个评审**。
- **恢复 `http.proxy`**：仓库本地 git 配置里的代理设置已丢失，导致 `git fetch` 直连失败（21s 超时）。按 [ISSUE-01](../04-issues/KNOWN_ISSUES.md) 的记录重新写入 `http.proxy=http://127.0.0.1:7892`，两个远端 fetch 恢复正常。
- **建立本机开发环境**（本轮最大变化）：
  - 装 uv 0.12.17；在 `apps/backend` 执行 `uv sync --frozen` → Python 3.13.15 + 锁定依赖（此前系统只有 3.11.9，`import eval_platform` 直接失败）。
  - 下载并解压便携 PostgreSQL 15.14 到 `D:\pgsql`（320,461,864 字节，sha256 `234ccc7a5cf07fce70f93faea701fd75fad6bec968359b06cdfc208ed7dfbc30`，来源 get.enterprisedb.com），`initdb` 后只监听 `127.0.0.1:55432`，不注册 Windows 服务、不开机自启。
  - 建库：`agentexam_identity_test`（LOGIN+CREATEDB，测试夹具用）、`agentexam_dev`（仅 LOGIN，日常开发用）。
  - 解压用 7-Zip（`D:\7-Zip\7z.exe`）；Windows 自带 `bsdtar` 在这台机器上创建文件失败，已弃用。
- **实测基线**：`tests/catalog` → **33 passed / 7 skipped**（跳过的是需 MinIO 的用例）；全量 `pytest -q` → **452 passed / 36 skipped / 2 failed**（119.75s）。2 个失败是 `tests/contract/test_execution_network.py` 缺 `framework/harbor` 的既有环境失败，与 D 记录的基线同类，非代码缺陷。
- 记录：新建[环境行动文档](../../actions/2026-09-20-local-environment-setup.md)与[本机开发环境](../06-environment/LOCAL_SETUP.md)，并更新 README 与问题记录。**未修改任何产品代码、测试或依赖清单。**

### 开工增量（用户明确要求“直接安排我开工”后实施）

#### 增量 1：目录 → options → 提交 → 冻结 Job 打通链

- 新增 `apps/backend/tests/catalog/test_catalog_job_flow.py`（**只加测试，未改任何产品代码**），补上任务 04 第 6 条里确实没人走过的一段——目录 → HTTP options → 提交 → 冻结 Job/Runs/初始事件：
  1. `test_catalog_and_options_drive_one_frozen_submission`：登记 6 题 + 2 配置 → 读目录列表 → 读 `/api/v1/job-options` → 按选项用 `continuous` 提交 → 断言 `202`、`AWAITING_OWNER_APPROVAL`、`trial_count == 12`；读回详情后断言冻结的题目身份（instance_id / dataset_id / dataset_revision / split / base_commit / problem_statement）与配置指纹与目录记录**逐字段一致**；断言 12 个 Runs 恰好覆盖 题目 × 配置 的笛卡尔积，Job 与每个 Run 都带 `JOB_SUBMITTED`。
  2. `test_frozen_job_keeps_its_snapshot_when_the_catalog_changes`：提交后停用配置 → 旧 Job 冻结快照与状态不变；新提交返回 `409 AGENT_CONFIGURATION_DISABLED`。
- 实测：目录模块 **35 passed / 7 skipped**（改动前 33 passed，新增 2 个）；全量 `pytest -q` **454 passed / 36 skipped / 2 failed**（103.73s，失败的仍是缺 `framework/harbor` 那 2 项，与改动前完全相同，**无回归**）；`ruff check`、`ruff format --check`、`mypy src/eval_platform` 对新增文件均通过。
- 做了**变异检查**确认断言有效（不是空跑）：把 `base_commit` 比对改成必然不等的值、把笛卡尔积期望缩小一格，跑出来 `1 failed, 1 passed`；探针文件已删除。
- 如实记录未覆盖：三步向导的浏览器动线（B 的）、恢复新 Job、双存储一致性（MinIO 集成在本机按设计跳过）、五道候选题的三补丁门禁（需组长机器）。

#### 增量 2：暴露面收敛的 HTTP 层断言

- 修改 `apps/backend/tests/catalog/test_security.py`（只加测试）：新增 `test_hidden_evaluation_fields_never_reach_public_surfaces`——用带哨兵值的合成目录（`HIDDEN_ANSWER` / `hidden_test` / `hidden_pass` / `private-test-reference`，分别来自 `gold_patch`+`test_patch`+原始记录、`fail_to_pass`、`pass_to_pass`、`credential_profile_id`）登记并提交后，逐条请求 **12 个公开读取面**（目录列表与详情、配置列表与详情、`job-options`、Job 列表与详情、批次报告、单 Run 报告、对比报告、制品索引、轨迹），断言哨兵一处都不出现，并用公开题面仍在响应中作为对照（防止"响应为空所以通过"）。
- 实测：目录模块 **36 passed / 7 skipped**；全量 **455 passed / 36 skipped / 2 failed**（104.16s，失败集合不变）；`ruff check`、`ruff format --check` 通过。
- 如实记录：`/runs/{id}/trajectory` 对**未执行**的 Run 返回 **409**（内容尚未产生），用例把拒绝集合显式断言为 `⊆ {trajectory}`，**不把 409 当作通过**；Run 产出制品后的读取路径归 D 的 `test_http_limits.py` / `test_evidence_publication.py`。网页读取面归 B；`leaderboard` 未在本夹具装配，未扫描。
- **变异检查**：把公开题面混进哨兵列表后，用例确实失败（`1 failed`），证明断言真的在扫响应体。
- 同步更新了 04 草案：`Blocked by` 区分题库侧与目录/规模侧、规模侧范围收窄为“核对已有覆盖 + 补 `0 配置` 空白”、标明「重复 ID 现有行为是去重」需与 D 确认、并记录打通链进展。草案状态如实保留 `needs-info`（数据/镜像/Fork 仍未取得）。

### 核对组长通过微信发来的材料

- 材料位置：`E:\Wechat\...\msg\file\2026-09\`，共三份（zip 与其解压目录内容一致）：`ui-catalog-providers`（4 个文档 + `issues/01`、`issues/02`）、`TEAM_WORK_ALLOCATION.md`、`TEAM_POSTGRESQL_CONNECTION.md`。
- 逐文件对比结果：`ui-catalog-providers` 的 6 个文件与仓库**逐字节相同**（仅 LF 与仓库工作区 CRLF 的差异，用 `diff --strip-trailing-cr` 复核）；`TEAM_POSTGRESQL_CONNECTION.md` 相同；**`TEAM_WORK_ALLOCATION.md` 是仓库更新**——微信版停在 09-19 20:59，规则 7 与 01/02 两行仍是"已规划、未发布 issue"，仓库版已标 01/02 完成。结论：组长这份材料里没有仓库看不到的内容，后续以仓库 `main` 为准。
- 任务单齐全度：组长材料里 `issues/` 仍只有 `01`、`02`；03–08（含 04）都没有任务单，与我此前的结论一致。
- **新发现 1（验收标准与实现冲突）**：[验证规范](../../../.scratch/ui-catalog-providers/verification.md)第 2 节 Q7 原文要求"0/21题、0/4配置、**重复**/停用/未知项拒绝"，而现有实现是**去重**（`tests/jobs/test_security.py:66`）。此前我只把它当作"草案措辞要改"，现在有了权威依据——按 Q7 验收，规模侧现状不满足；这条已写进 ISSUE-05 与 04 草案。
- **新发现 2（preset ID 与地图候选不一致）**：[实现地图](../../../.scratch/ui-catalog-providers/implementation-map.md)第 4.1 节把连续规模的 preset ID 候选写作 `flexible-v2`，而 D 实际落地为 `continuous` 并已合入 `main`。地图原文标明是"候选"，故不算违规，但**地图、D 的实现与 B 待补的 `HTTP_API.md` 受控选项小节三者需要对齐**（`continuous` 已是公开选项取值）。
- 新发现 3（对后续测试归属有用）：实现地图第 3 节已规划 04 的候选测试目录 `apps/backend/tests/catalog/qualification/`（五题参数化资格/隐藏信息/漂移）与 `apps/backend/tests/jobs/submission/`（新规模与旧快照兼容矩阵）。后续 04 测试应落在这两个候选目录，而不是继续往 `tests/catalog/` 平铺。

### 事实更正

- **ISSUE-02 已解决**：上游 `main` 现在包含 `issues/01`、`issues/02`，且 `plan.md` 与我手上那份更新版逐字节相同（随 `ff46cec` 于 09-20 20:42 进入上游）。此前「请组长推送更新版」的请求作废。
- **任务 04 的规模侧剩余范围被高估**：逐条查测试后确认「4 个配置被拒」「未知条目被拒」「停用条目被拒」都已有测试（`tests/jobs/scale/test_continuous_preset.py:43`、`tests/jobs/test_security.py:60`、`tests/jobs/test_concurrency.py:58`）；而「重复 ID」的**现有行为是去重而不是拒绝**（`tests/jobs/test_security.py:66` 断言 `trial_count == 1`），我 09-19 草案里写的「重复题目必须拒绝」与之冲突，不能照草案实现。真正空白的是「0 个配置」的用例（代码有 `EMPTY_JOB_SELECTION`，`application/job_submission.py:60`，无对应测试）。
- **本机确实没人做过的 C 侧交付**：目录 → HTTP options → 提交 → 冻结 Job / 全部 Runs / 初始事件的事务打通。现有测试只在 `tests/jobs/test_http.py` 断言过 options 的响应形状，没有走完这条链。
- **静态检查基线**：`ruff check .` 全通过；`mypy src/eval_platform` 166 个源文件无问题（直接跑 `mypy` 会因 editable 安装缺 `py.typed` 报错，须给显式路径）；但 `ruff format --check .` **有 5 个文件不合格**——`adapters/persistence/jobs/__init__.py`、`delivery/http/routes/jobs/report_comparisons.py`、`tests/jobs/cancellation/test_cancel_races.py`、`tests/jobs/reporting/test_comparison_http.py`、`tests/jobs/reporting/test_matrix_rehearsal.py`。这 5 个都是 D 近期合入的文件，不是我引入的，我也没有格式化它们（不擅自改他人文件）。
- **共享库仍不可达**（记为 [ISSUE-06](../04-issues/KNOWN_ISSUES.md)）：本机 tailnet 正确（`tail03c757.ts.net`）但 netmap `Peers = 0` 且 `Cached = false`（实时从控制面取回），`sss.tail03c757.ts.net` 解析不到，需 host 侧处理。

### 当前停点

- 环境已就绪；产品代码未开工，未下载任何题目镜像、未调用模型、未连接共享库。
- 任务 04 仍无任务单；下一步是本机可做的那条打通链，以及向组长确认规模侧收口与「重复 ID」的行为取向。

## 2026-09-20

### 已完成

- 确认仓库关系：`Floraluke/agent-exam` 是**个人 fork**，团队上游仓库是 `anphuchoang5-sys/agent-exam`。接入 `upstream` remote 并 fetch；上游 `main` 比我 fork 的 `main` 领先 **21 个提交**，且 fork 没有上游缺的提交（fork 是纯快照）。
- 上游现有分支：`main`、`fengyy-fixweb`（冯颖怡）、`lly/dev`（成员 E）、`xinyue-modules`。上游当前 **0 个 PR**。
- 把我个人的两个提交 rebase 到 `upstream/main`（`a49b000`）。rebase 干净，无冲突。
- 建立个人分支 `lyq`（基于 `upstream/main`）与个人文档目录 `docs/LYQ/`，结构参照成员 E 的 `docs/LLY/` 约定（README + 01-plan + 03-progress + 04-issues，另按分工文档要求加 02-module 放模块架构/契约/接口的个人视图）。
- **确认协作方式为 fork 工作流**（用户 2026-09-20 明确）：在自己 fork 上开发、从 fork 向上游提 PR，**不直接操作上游仓库**。据此把我最初直接推到上游的 `lyq` 分支收回：关闭上游侧 PR 并删除上游侧分支，代码改为推送到 `origin`（fork），PR 改为 `Floraluke:lyq → anphuchoang5-sys:main`。本地 `lyq` 的跟踪目标同时从 `upstream/lyq` 改回 `origin/lyq`。
- 个人视图三份文档的实际来源：`TaskCatalog`/`AgentRegistry` 的调用形状与 7 个 HTTP 端点逐条从 `apps/backend/src/eval_platform/` 代码核对；契约内容取自[模块契约](../../architecture/MODULE_CONTRACTS.md)第 6.2、6.3 节。

### 观察到的事实

- 上游 `main` 的 [`.scratch/ui-catalog-providers/plan.md`](../../../.scratch/ui-catalog-providers/plan.md) 仍是 **09-17 草案版**（表头写「计划草案，未开工」，01、02 未标完成），且没有 `issues/` 目录。而我 09-19 从组长处收到的同目录更新版（plan/spec/implementation-map 更新，任务 01、02 标注完成，含 `issues/01`、`issues/02`）**不在上游任何分支上**。详见[问题记录 ISSUE-02](../04-issues/KNOWN_ISSUES.md)。
- 上游 `main` 09-20 有 12 个新提交（作者 `noachlola`），内容包括任务 03 报告语义设计、对比报告的服务与端点、以及给 08 用的 D 侧 runbook。即：**有人在按单项授权推进 03 方向的工作**，但计划文档尚未同步这个进展。
- **任务 04 的「规模」半已由 D 完成并合入上游**：`delivery/job_presets.py` 第 25–29 行现有四个预设，新增的是 `BatchPreset("continuous", 1, 20)`（既有 `demo`/`quick`/`standard` 区间未改）；配套新增 `apps/backend/tests/jobs/scale/test_continuous_preset.py` 与 `tests/jobs/reporting/test_matrix_rehearsal.py`；行动记录为 `docs/actions/2026-09-20-d-continuous-scale-and-rehearsal.md`，其中明确把受控选项的契约补记留给 B。对我而言：09-19 记的「缺连续 1–20 档位」已被上游现状取代（当时读的是 fork 的旧快照），我的剩余范围需与组长、D 确认，记为 [ISSUE-05](../04-issues/KNOWN_ISSUES.md)。我没有改动 `job_presets.py` 或 D 的测试，避免与其提交冲突。
- 成员 E 的阶段 0 计划明确（该文档在其分支 `upstream/lly/dev` 的 `docs/LLY/01-plan/PLAN.md`，不在上游 `main` 上）：真实执行链（Harbor、SWE-Bench-Fork、固定镜像、`framework/`、`runtime/`）只在组长机器上，不进 Git；开发机只做代码、单元与契约测试、替身验证。这条同样约束我的任务 04。

### 当前停点

- `lyq` 分支已基于上游最新提交，个人文档目录已建立；**产品代码未开工，未下载镜像或数据，未运行容器或模型**。
- 任务 04 仍无开工授权；按顺序先等 `03`（B 主责）完成。

## 2026-09-19

### 已完成

- 从组长处收到更新版规划文档（`TEAM_WORK_ALLOCATION.md`、`ui-catalog-providers` 目录、Navicat 连接教程）。
- 通读我负责模块的权威文档与源码：模块架构、模块契约 6.2/6.3 节、数据模型、HTTP API 第 5/6 节，以及 `catalog_presets.py`、`swe_gym.py`、`job_presets.py`、`domain/jobs/policy.py`、`routes/catalog.py`。
- 核对出任务 04 的机制现状：`TASK_PRESETS` 只有一道题 `swe-gym-lite-mypy-15413`；`AGENT_PRESETS` 只有一个配置 `codex-0153-terra-medium`；`SubmissionPolicy` 已有 `maximum_agent_configurations=3` 与 `maximum_runs=60`，**缺的是「连续 1–20 题」的 `BatchPreset`**（现在只有 `demo` 1–3、`quick` 恰好 5、`standard` 10–20，所以 4 道或 6 道题的请求会被拒）。
- 建立任务 04 的行动文档并按验证规范补出测试设计（目录层、规模层、判卷层、浏览器层四组用例）。
- 建立 `docs/lyq/` 个人文档目录（后于 09-20 按上游约定重命名为 `docs/LYQ/`）。

### 实际结果

- 我 fork 的 `main` 停在 `6dfa2be`，当时误认为是最新；09-20 接入上游后才知道上游已领先 21 个提交。

## 2026-09-18

- 五人分工确定（[团队分工文档](../../architecture/modules/TEAM_WORK_ALLOCATION.md)）。我被分配为成员 C：长期负责「目录与配置」Module，任务 04 的任务 DRI，工时基线 54 h。
- 分工文档同时明确：01–08 仍未发布独立 issue，分工不等于开工；成员可提前阅读自己 Module 和准备测试设计，但不提前修改后续任务代码、不调用真实模型、不下载大体量镜像。
