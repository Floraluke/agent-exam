Status: needs-info

# 04：五道新题合格入库与 1–20 连续规模

**What to build:** 所有者在受控入口登记至少五道经资格验证的固定题目，与旧题并存且身份不可改写；提交规模支持连续 1–20 道题、最多 3 个配置，总数上限 60 次 Run。做题侧、HTTP 与网页均不出现参考补丁、隐藏测试与判分答案。

**Blocked by:** 题库半边需要在固定数据、Fork、镜像与专属存储条件可核验后取得下载范围授权（没有授权不拉镜像），且必须在组长机器上或由 E 执行；目录侧与规模侧（合成受控目录）不依赖这些外部条件。任务 03 按当前节奏完成——计划第 6 节已写明本任务技术上不依赖新 UI，故不构成硬前置。

**Spec stories:** 7、16、17、18。

- [ ] 逐个读取固定快照记录，冻结 instance、base commit、公开题干摘要、隐藏判卷字段摘要及镜像 digest；先列出本地缓存/缺失镜像、磁盘需求与下载来源，未获下载范围授权前不拉取镜像。
- [ ] 按候选顺序资格验证 `python__mypy-15184`、`python__mypy-15208`、`python__mypy-15131`、`python__mypy-15139`、`python__mypy-15876`；它们只是同一固定数据集的候选，不能共用旧题镜像；`15876` 额外确认存在真实 FAIL_TO_PASS，不用仅文档修改凑数量。
- [ ] 每题在独立容器、固定 Fork、外网关闭条件下依次跑参考补丁、空补丁、可应用但错误的补丁；确认测试确实执行且参考通过、负例未解决。基础设施错误不算负例成功；空补丁本来就通过的题不合格。记录镜像/数据/报告身份与精确清理结果。
- [ ] 只有通过门禁的题进入受控目录白名单；保留旧题身份与 M0 单题入口。候选不合格时从同一固定 mypy 集合选替补并重走全部门禁；不足五题时停止汇报，不无声更换项目或数据集。
- [ ] 规模侧已由 D 于 2026-09-20 实现并合入 `main`，本任务**不重复实现、不改写 D 的测试**；剩余范围收窄为「核对既有覆盖」（复核后确认无需补测试）。已覆盖（逐条核对现有测试）：4/6/9 题通过、0 题与 21 题拒绝、20×3=60 允许、第 4 个配置拒绝（`tests/jobs/scale/test_continuous_preset.py`）；未知条目（`tests/jobs/test_security.py:60`）与停用条目（`tests/jobs/test_concurrency.py:58`）拒绝。（原记的「0 个配置」空白项经 2026-09-20 复核**不成立**：`tests/jobs/test_security.py:41-42` 已断言 0 题与 0 个配置都返回 `400 EMPTY_JOB_SELECTION`。）**冲突（2026-09-20 新发现）：「重复项拒绝」的验收标准与现有实现不一致**——[验证规范](../verification.md)第 2 节 Q7 原文要求"0/21题、0/4配置、**重复/停用/未知项拒绝**"，而现有实现是**去重**（`tests/jobs/test_security.py:66` 断言 `task_ids` 翻倍后 `trial_count == 1`）。按 Q7 验收则现有行为不通过；改实现会破坏既有断言。须与组长和 D 确认以哪一侧为准，再决定是否补测试或改行为。
- [ ] 打通目录 → HTTP options → 三步向导 → 冻结 Job/全部 Runs/初始事件的事务；创建只返回“等待 owner 批准”。验证读取旧 Job、恢复新 Job、双存储一致性与指纹/摘要防漂移。**（进程更新 2026-09-20：C 侧打通链已实现并测试——`apps/backend/tests/catalog/test_catalog_job_flow.py` 覆盖“目录列表与 HTTP 选项驱动 6 题 × 2 配置提交 → 创建只返回 `AWAITING_OWNER_APPROVAL` → 全部 Runs 恰好覆盖笛卡尔积 → Job 与每个 Run 都带 `JOB_SUBMITTED` → 冻结身份与目录记录逐字段一致”，并覆盖“配置停用后旧 Job 不被改写、新提交被拒”。剩余：三步向导的浏览器动线（与 B 交接）、恢复新 Job 与双存储一致性。）**
- [ ] 暴露面收敛：`gold_patch`、`test_patch`、测试名单、环境对象键、凭据逻辑引用均不进入做题侧、HTTP、网页与制品。**（进程更新 2026-09-20：C 侧 HTTP 读取面已加全量扫描用例——`tests/catalog/test_security.py::test_hidden_evaluation_fields_never_reach_public_surfaces` 逐条请求 12 个公开端点，断言 `HIDDEN_ANSWER` / `hidden_test` / `hidden_pass` / `private-test-reference` 一处都不出现，并用公开题面作为对照。剩余：网页读取面（B）、Run 产出制品后的制品/轨迹读取路径（D 已覆盖，需在验收时合并结论）、提供方凭据相关字段（05–07）。）**
- [ ] 同步权威文档（模块架构、模块契约、数据模型、HTTP API、依赖总表）并建立独立行动记录；不读真实 `auth.json`、不调用模型。

## Comments

2026-09-20 由成员 C 起草，等待项目负责人发布与开工授权。起草依据：[执行计划第 6 节](../plan.md)、[分层验收规范](../verification.md)需求覆盖表 Q5/Q7、[团队分工](../../../docs/architecture/modules/TEAM_WORK_ALLOCATION.md)第 5 节。

起草时已核对的事实：受控题目目录当前只有 `swe-gym-lite-mypy-15413` 一道题；规模侧 `continuous(1–20)` 已由 D 合入 `main`，本任务规模部分因此收窄为核对与剩余拒绝项归属。开工所需的固定数据集获取方式、候选镜像下载授权与磁盘配额、Fork 判卷的执行安排（E 主责）尚未取得，故状态为 `needs-info`。

2026-09-20 晚间由 C 更新（四点事实更正与进展）：

1. **上游已同步**：`issues/01`、`issues/02` 与更新版 `plan.md` 已随 `ff46cec` 进入上游 `main`；`plan.md` 与本分支版本逐字节相同。本文件是本仓库与上游在 `.scratch/ui-catalog-providers/` 下的唯一差异，此前“请组长推送更新版”的请求作废。
2. **规模侧范围收窄**（见左列对应条）：既有覆盖已包含全部拒绝项（含 0 题、0 个配置）；「重复 ID」的现有行为是**去重**，与早期草案措辞冲突，需先与 D 确认。
3. **C 侧打通链已实现并测试**：新增 `apps/backend/tests/catalog/test_catalog_job_flow.py`（2 个用例）。实测：目录模块 **35 passed / 7 skipped**；全量 **454 passed / 36 skipped / 2 failed**（2 项为缺 `framework/harbor` 的既有环境失败）；`ruff check`、`ruff format --check`、`mypy src/eval_platform` 对本文件均通过。已做变异检查（注入错误断言后测试确实失败），断言有效。
4. **本机环境已就绪**：Python 3.13.15 + 便携 PostgreSQL 15.14（`127.0.0.1:55432`），见 `docs/LYQ/06-environment/LOCAL_SETUP.md` 与 `docs/actions/2026-09-20-local-environment-setup.md`。原先“本机不能验证”不再成立；仍需组长机器的部分只有五道候选题的三补丁门禁与固定数据类验证。

本文件本轮**未**改动 `Status`：题库半边的外部条件（数据、镜像、Fork 安排）仍未取得，按事实保持 `needs-info`。
