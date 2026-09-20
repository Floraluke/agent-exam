# 任务 04：五道新题合格入库与 1–20 连续规模（目录与配置）

## 状态与情况说明

- 状态：In progress（准备阶段，未获实施授权）。本行动由 C（目录与配置 DRI、任务 04 任务 DRI）建立，先记录范围、前置门禁、计划文件树与验证方式。**本轮未修改任何产品代码、未下载镜像或数据、未调用模型、未读取真实凭据。**
- 对应任务：[执行计划](../../.scratch/ui-catalog-providers/plan.md)第 6 节任务 04；分工见[团队分工](../architecture/modules/TEAM_WORK_ALLOCATION.md)第 4.2 与第 5 节。任务 04 当前为“已规划、未发布 issue”，按计划第 1 节第 5 条与第 5.2 节，任务单发布且用户安排前不进入实施。
- 本行动是独立实施任务的行动文档；`ui-catalog-providers` 的规划正文仍由[规划行动](2026-09-17-ui-catalog-provider-planning.md)维护，本文件不复制规则正文，只记录 04 的实施、偏差与验证证据。
- 实施基线（2026-09-20 更新）：团队上游仓库 `anphuchoang5-sys/agent-exam`，只作只读同步、不直接推送；交付分支为个人 fork `Floraluke/agent-exam` 的 `lyq`，基于上游 `main` 的 `a49b000`；PR 从 fork 提到上游 `main`。本机克隆 `C:\Users\陆泳倩\Desktop\agent-exam`。

### 当前事实（2026-09-19 实际核对）

- 受控题目目录只有一道题：`delivery/catalog_presets.py` 的 `TASK_PRESETS` 仅含 `swe-gym-lite-mypy-15413`；`adapters/tasks/swe_gym.py` 用单一常量 `CANDIDATE_INSTANCE_ID` / `CANDIDATE_IMAGE` 冻结该题身份。固定数据源为 `SWE-Gym/SWE-Gym-Lite` `train`，revision `61231f2c…`，快照 931193 字节、sha256 `f3a7cd93…`，并按实例 id 过滤读取。
- 受控配置目录只有一个配置：`codex-0153-terra-medium`（Codex 0.153.0 / gpt-5.6-terra / medium）。
- 规模策略：`delivery/job_presets.py` 当前给 `demo(1,3)`、`quick(5,5)`、`standard(10,20)` 三个 `BatchPreset`；`domain/jobs/policy.py` 的 `SubmissionPolicy` 已有 `maximum_agent_configurations=3` 与 `maximum_runs=60`。缺的是“连续 1–20 题”这一档，不是 60 次上限本身。
- 本机不具备 04 的运行条件：无 `framework/`、`runtime/`、`infra/data/`、`infra/volumes/`；未发现固定 Parquet 数据快照；Docker Desktop 未运行（`dockerDesktopLinuxEngine` 管道不存在）。因此资格验证类步骤在本机无法执行，也未尝试执行。
- 上游 `main` 的 `.scratch/ui-catalog-providers/` 仍是 2026-09-17 草案版本（表头写作「计划草案，未开工」，任务 01、02 未标完成），且**没有** `issues/` 目录；组长 2026-09-19 提供的同目录更新版（plan/spec/implementation-map 更新，verification 仅换行符差异，新增 `issues/01`、`issues/02`）经逐分支核对**不在上游任何分支上**。仓库看到的“前项状态”落后于最新事实，本行动的引用以实施时的权威版本为准；差异记录见 [ISSUE-02](../LYQ/04-issues/KNOWN_ISSUES.md)。
- 上游 `main` 在 2026-09-20 有 12 个新提交（作者 `noachlola`），内容涉及任务 03 报告语义设计、对比报告服务与端点、以及给任务 08 用的 D 侧 runbook。即有人正按单项授权推进 03 方向的工作，计划文档尚未同步。任务 04 本身的机制现状未变。

### 上游门禁（未满足前不进入实施）

- 计划第 6 节前置：固定数据、Fork、镜像与专属存储条件可核验；**没有下载范围授权时不拉镜像**。
- 顺序门禁：执行顺序为 `01 → 02 → 03 → 04`，任务 03 完成后才进入 04；多任务并行需先单独修改执行计划，本分工文档不授权越阶段。
- 交接门禁：E 主责参考/空/错误补丁的固定 Fork 资格验证；D 负责 Job 快照与最多 60 Runs 兼容；B 负责 HTTP options 与三步向导；A 负责磁盘与长期 schema 变更窗口。
- 数量门禁：至少五道题未完成不得标记任务完成，不足五题时停止汇报，不从同一固定 mypy 集合之外改项目或数据集。

### 待确认

- 任务 04 的独立任务单（`.scratch/ui-catalog-providers/issues/04-*.md`）由谁发布；发布前不进入实施。
- 镜像/数据的下载授权范围与磁盘配额，以及 `2026-09-19` 更新版文档何时进入仓库。
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
5. 引入新的连续规模预设，保留旧 preset ID 对历史冻结值的解释：`4/6/9` 题请求必须通过，`0/21` 题、`0/4` 配置、重复题目、未知或停用条目的请求必须拒绝，总上限 20×3=60。用合成受控目录验证，不要求现在准备 20 道真实题。
6. 打通目录 → HTTP options → 三步向导 → 冻结 Job/全部 Runs/初始事件的事务；创建只返回“等待批准”。验证读取旧 Job、恢复新 Job、双存储一致性与指纹/摘要防漂移；同步权威文档后收尾。

## 需要修改的文件树（计划；实施时按实际回填）

```text
apps/backend/src/eval_platform/
├─ adapters/tasks/swe_gym.py        # 单题常量 → 受控候选集（instance、镜像 digest、数据身份）
├─ adapters/tasks/collect_patch.sh  # 题目侧 patch 收集；多题时核对参数与路径假设
├─ delivery/catalog_presets.py      # TASK_PRESETS 扩展为旧题+合格新题；AGENT_PRESETS 预留 05–07
├─ application/task_catalog.py      # 白名单登记与校验；多题语义按需扩展，不放松 allowlist
├─ domain/jobs/policy.py            # BatchPreset 连续 1–20；保留旧 preset 解释
├─ delivery/job_presets.py          # 新增连续规模预设组合；保留 demo/quick/standard
├─ application/job_submission.py    # 题数×配置计数、边界与拒绝语义
└─ delivery/http/routes/jobs/routes.py  # job-options 暴露新预设（与 B 交接前端展示）
apps/backend/tests/
├─ catalog/test_http.py             # 目录 HTTP：六题可选、未知/停用拒绝
├─ catalog/test_consistency.py      # 目录记录与对象摘要一致
├─ catalog/test_security.py         # 隐藏答案与 Key 不进入公开输出（05–07 也会触及）
├─ integration/test_swe_bench_integration.py  # 新题固定 Fork 离线判卷（E 执行，C 收证据）
├─ jobs/test_http.py                # 1/4/6/9/20 通过；0/21、0/4、重复、未知/停用拒绝
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

Pending（本轮为准备阶段，未修改代码、未运行任何检查；上述命令均未执行）。
