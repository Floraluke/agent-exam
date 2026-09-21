# 已知问题记录

> 记录我遇到的、影响我这项工作的实际问题：现象、证据、处理过程、遗留风险。
> 项目级缺陷应提升到权威文档或对应行动记录，本文件只保留与我工作相关的记录。
> 状态说明：**已解决**表示现象已消失且有验证证据；**待处理 / 待确认**表示仍未消除。
> 编号一经使用不再改号，避免其他文档的引用失效。

## ISSUE-01 本机直连 GitHub 不通，git 操作必须走本机代理 —— 待处理（配置已恢复，根因未消除）

- **现象**：`git push` / `git fetch` 报 `Failed to connect to github.com port 443` 或 `Recv failure: Connection was reset`。
- **证据**：2026-09-20 白天连续 6 次推送失败；同一时刻 `curl https://api.github.com` 直连超时（返回码 000），改走本机 `127.0.0.1:7892` 代理后返回 200。**2026-09-20 晚间复现并复核**：仓库本地配置里的 `http.proxy` 已不存在；直连 `git ls-remote upstream HEAD` 失败，走代理同一命令返回 `beed93f…`；写入代理配置后 `git fetch upstream` 与 `git fetch origin` 均成功。
- **处理**：在该仓库的**本地** git 配置写入 `http.proxy=http://127.0.0.1:7892`（只影响本机，不会提交到仓库）。2026-09-20 晚间发现该配置丢失（原因未查明，可能是重新克隆或手工清理），已按原方案重新写入并验证两个远端 fetch 正常。
- **遗留风险**：代理端口来自本机 Clash 配置，若代理软件关闭或端口变更，git 会再次失败，届时需要更新或删除该配置：
  `git config --unset http.proxy`（在仓库目录执行）。**恢复克隆或换机器后必须重新确认这条配置。**
- **影响范围**：只影响本机联网操作，不影响代码与文档内容。

## ISSUE-02 上游计划文档落后于组长提供的最新版本 —— 已解决（2026-09-20 晚间）

- **现象**：上游 `main` 的 `.scratch/ui-catalog-providers/plan.md` 表头仍写「2026-09-17 计划草案，未开工」，任务 01、02 未标完成；且**没有** `issues/` 目录。
- **证据（当时）**：逐分支核对 `upstream/main`、`upstream/lly/dev`、`upstream/fengyy-fixweb`、`upstream/xinyue-modules`、`origin/main`，`ui-catalog-providers/issues` 文件数均为 0。
- **解决证据（2026-09-20 晚间实测）**：上游 `main` 已包含 `issues/01-clickable-html-prototype.md` 与 `issues/02-role-workbench-submission-approval.md`，且 `plan.md` 与我手上那份更新版**逐字节相同**（`git diff upstream/main lyq -- .scratch/ui-catalog-providers/plan.md` 无输出）；该批文档随提交 `ff46cec`（2026-09-20 20:42，作者冯颖怡）进入上游。我方 `lyq` 与上游在 `.scratch/` 下的唯一差异是我起草的 04 任务单草案。
- **处理**：无需再请组长推送；本条关闭。
- **遗留风险**：无。此后计划文档更新以 `upstream/main` 为准。

## ISSUE-03 开发机不具备任务 04 的容器与固定数据条件 —— 部分解决（环境已建，容器/数据仍缺）

- **现象**：任务 04 的资格验证需要在容器里跑参考/空/错误三种补丁，开发机无法执行。
- **证据（当时，2026-09-19）**：无 `framework/`、`runtime/`、`infra/data/`、`infra/volumes/`；无固定 Parquet 数据快照；`docker ps` 报 `dockerDesktopLinuxEngine` 管道不存在；系统 Python 为 3.11.9（后端要求 3.13），连 `import eval_platform` 都失败。
- **解决部分（2026-09-20）**：已建立本机开发环境——`apps/backend/.venv`（Python 3.13.15 + 锁定依赖）、便携 PostgreSQL 15.14 于 `127.0.0.1:55432`、测试库 `agentexam_identity_test` 与开发库 `agentexam_dev`。`tests/catalog` **33 passed / 7 skipped**；全量 `pytest -q` **452 passed / 36 skipped / 2 failed**（2 项为缺 `framework/harbor` 的既有环境失败）。事实与命令见[本机开发环境](../06-environment/LOCAL_SETUP.md)与[环境行动文档](../../actions/2026-09-20-local-environment-setup.md)。
- **仍未解决**：容器、固定镜像与固定 Parquet 快照仍不存在，Docker Desktop 未运行。五道候选题的三补丁资格验证**只能**在组长机器上或由 E 执行（参见成员 E 的阶段 0 计划，该文档在其分支 `upstream/lly/dev` 的 `docs/LLY/01-plan/PLAN.md`，不在上游 `main` 上）。
- **遗留风险**：不要因为本机可跑测试就把容器类或固定数据类门禁当作已完成；那两类在任务 04 中仍未开始。

## ISSUE-04 fork 与上游仓库的关系曾被误判 —— 已解决

- **现象**：2026-09-19 我在 `Floraluke/agent-exam` 上建分支并开 PR，当时以为它就是团队仓库。
- **证据**：该仓库的 API 返回 `parent = anphuchoang5-sys/agent-exam`，即它是 fork；fork 的 `main` 曾是纯快照，落后上游 21 个提交。
- **处理**：2026-09-20 接入 `upstream` remote，把工作 rebase 到 `upstream/main`。协作方式经确认为 **fork 工作流**：代码推个人 fork、从 fork 向上游提 PR、不直接操作上游仓库。据此收回了最初直接推到上游的 `lyq` 分支（关闭上游侧 PR、删除上游侧分支），改由 `origin`（fork）承载分支与 PR。2026-09-20 晚间复核：fork 的 `main` 已同步到 `beed93f`，与上游一致。
- **遗留风险**：无。教训是动手前先确认 `git remote -v` 与仓库的 parent 关系。

## ISSUE-05 任务 04 的「规模」半已由 D 实现，我的剩余边界待确认 —— 待确认（分工问题）

- **现象**：按[团队分工](../../architecture/modules/TEAM_WORK_ALLOCATION.md)第 5 节，任务 04 中「题目目录、preset、**规模版本**」归 C；但上游 `main` 上连续规模预置已由 D 侧实现并合入。
- **证据**：`delivery/job_presets.py` 现有 `BatchPreset("continuous", 1, 20)`；D 的测试 `apps/backend/tests/jobs/scale/test_continuous_preset.py` 已覆盖 4/6/9 题通过、0/21 题拒绝、20×3=60 允许与第 4 个配置拒绝；行动记录为 `docs/actions/2026-09-20-d-continuous-scale-and-rehearsal.md`，其中写明受控选项的契约补记留给 B。
- **2026-09-20 晚间补充核对**（逐条查现有测试，用于收窄范围）：
  - 「4 个配置被拒」「未知条目被拒」「停用条目被拒」**已有测试**：`tests/jobs/scale/test_continuous_preset.py:43`、`tests/jobs/test_security.py:60`（`AGENT_CONFIGURATION_NOT_FOUND`）、`tests/jobs/test_concurrency.py:58`（`JobConfigurationDisabled`）。
  - 「重复 ID」的**现有行为是去重而不是拒绝**：`tests/jobs/test_security.py:66` 断言 `task_ids *= 2` 后 `trial_count == 1`。我 09-19 起草的 04 草案里写「重复题目必须拒绝」，与该既有断言冲突，**不得**按草案直接实现。
  - **权威依据（2026-09-20 补读组长材料后）**：不是我的推测——[分层验收规范](../../../.scratch/ui-catalog-providers/verification.md)第 2 节需求覆盖表的 Q7 原文是「1/4/6/9/20题和1/3配置合法；0/21题、0/4配置、**重复**/停用/未知项拒绝；最多60 Runs」，归属 04。即**验收标准要求拒绝重复，现有实现是去重**，两者直接冲突。风险升级：按 Q7 验收时，规模侧现在就不满足；若改实现则要动 D 的既有断言。
  - **已确认（2026-09-20 深夜，D 回复）**：去重是**刻意设计，实现不改**。统一规则是「未知/重复**参数键**拒绝、值列表**去重归一化**」。依据：[任务 04 行动记录](../../actions/2026-09-12-m1-job-submission.md)第 22 行「题目与配置**去重后计数**；空选择、规模不符、非法覆盖在创建前拒绝」；[HTTP_API.md](../../interfaces/HTTP_API.md) 第 426/430 行「必须非空、去重」「列表在规范正文中去重并排序」。两处均已逐字核对属实。**剩余动作只在措辞侧**：请组长把 Q7 与 `plan.md` 第 6 节第 5 步的「重复 ID…拒绝」对齐为「重复项去重后计数」。另：D 说「plan.md 第 5 节」，实际在**第 6 节第 5 步**。
  - **「0 个配置」原本被我记为空白项，2026-09-20 复核更正：该用例已存在**——`tests/jobs/test_security.py:41-42` 的参数化用例（`test_rejects_untrusted_fields_and_all_controlled_selection_errors`）同时断言「0 题」与「0 个配置」都返回 `400 EMPTY_JOB_SELECTION`。我先前只查了 D 的规模测试文件就下结论，属核查不充分，此处更正。
- **处理**：未处理，属分工边界问题，需人类判断。我没有改动 `job_presets.py` 或 D 的测试。
- **遗留风险**：若我按原计划实现规模预置或按草案实现「重复即拒绝」，会与 D 的工作重复或撞上既有断言。
- **建议**：与组长和 D 确认三件事——（1）规模侧的拒绝边界是否按「既有覆盖已足够、本地无需再补测试」收口；（2）~~重复 ID 应去重还是拒绝~~ 已由 D 确认**去重是刻意行为**，只需组长对齐 Q7 与 plan.md 的措辞；（3）04 的工时基线（54 h 中 04 占 30 h）是否按剩余范围下调。

## ISSUE-06 共享 PostgreSQL 连不上：本机 Tailscale 看不到其他设备 —— 待 host 侧处理

- **现象**：Navicat 连共享库失败，报错从「连接超时」变为「找不到主机名」。
- **证据（2026-09-20 晚间复核）**：
  - 本机 Tailscale `BackendState = Running`，自己的地址 `100.117.118.37`，设备名 `laptop-nf02sf9o.tail03c757.ts.net`，登录身份 `Floraluke@github`——**tailnet 后缀与共享库入口一致**（`tail03c757.ts.net`，netmap `Domain = fengyycon@gmail.com`），说明我在正确的 tailnet 内。
  - `tailscale debug netmap` 显示 `Peers = 0` 且 `Cached = false`：设备列表是**实时从控制面取回的**，不是本地缓存问题。
  - `tailscale ping sss.tail03c757.ts.net` 返回 `no such host`；用 Tailscale 内部解析器查该名字同样查不到。
  - 端口 `55432` 是 owner 本机回环端口，外部不可达；教程要求的入口是 `sss.tail03c757.ts.net:15432`。
- **处理**：未处理，需 host 侧操作：由 tailnet 管理端确认 `sss` 设备是否存在/在线，以及对我的账号 `Floraluke@github` 的共享或 ACL 可见性设置。
- **遗留风险**：暂搁置，不阻塞任务 04 的准备与实现（本机已能独立验证目录侧与规模侧）。若后续要读共享库里的真实目录记录，需先解决本条。
