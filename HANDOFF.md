# AgentExam 当前接续交接

> 更新：2026-09-21；工作区：`E:\9.1agent_exam`。
>
> 本文是新窗口的恢复入口，不替代架构、接口、运维、任务和行动文档。若本文与当前代码或专题权威文档冲突，先核对 Git 与现实实现并同步当前状态型文档；`docs/actions/` 中已结束的记录是历史档案，不反向改写。

## 1. 目标与当前阶段

项目目标仍是完成 Codex-only MVP（最小可用平台）：协作者提交评测 Job，owner 批准，所有者机器上的 Worker 使用固定执行链运行，保存确定性判卷与证据，并通过 Web 查看结果。M0 技术原型已经跑通；M1 任务 01–13 已完成，任务 14 有正向证据但远程负向/VPN/离线项尚未全部关单，因此整个 MVP 仍不能宣布完成。

当前扩展阶段以现实代码和任务验收为准：

- P1–P4 最小本地持久化已完成；备份恢复已明确移出课设范围。
- 任务 01–02 已完成；任务 03 的跨批次对比 Web 已实现并验证，任务单保持 `ready-for-human` 等待最终人工确认。
- 任务 04 的六题受控目录、五道新题三补丁门禁、`continuous(1–20)`、六题向导与暴露面检查已经落地；任务单全部验收项已勾选，当前转为 `ready-for-human`，不能再写成“尚未实现”。
- 任务 05 的 9 项负责人决定已确认并进入主线，但代理、短令牌、预算账本与双网络仍未实现；拓扑探针 7 条断言均未运行。本轮明确只填文档、不运行探针，这一边界继续有效，除非用户另行授权新的执行窗口。
- 任务 06–08 未实施；不得因 04 完成、Worker 曾在线或 05 决策已确认而自动开始真实供应商调用、充值或冻结矩阵。

### 1.1 上一窗口的开发历程索引

只按当前任务读取对应记录，不从头重跑历史实验：

- `fengyy-fixweb` 合并、两轮远端并发整合、测试与推送：[合并行动](docs/actions/2026-09-21-merge-fengyy-into-main.md)。
- 任务 03 Web 对比页：[任务 03 行动](docs/actions/2026-09-21-ui-comparison-report.md)与[任务单](.scratch/ui-catalog-providers/issues/03-comparison-report-and-evidence.md)。
- 任务 04 六题、规模与资格门禁：[任务 04 行动](docs/actions/2026-09-19-task-04-catalog-candidates-and-scale.md)与[任务单](.scratch/ui-catalog-providers/issues/04-five-new-tasks-and-continuous-scale.md)。已结束行动记录中的早期“未授权/未运行”段落是当时事实，当前结论看任务单、现实代码和当前架构文档。
- 任务 05 当前决定与授权边界：[负责人回执](docs/LLY/01-plan/TASK05_OWNER_ACTION_REQUIRED.md)与[代码事实填充版](docs/LLY/01-plan/TASK05_OWNER_DELIVERY_FILLED.md)。
- 2026-09-21 17:43 的 Web/Worker/Job 运行事实：[运行交接行动](docs/actions/2026-09-21-live-runtime-handoff.md)。它是时点证据，不代表当前进程仍在线。
- 当前进行中的全量核心代码诊断：[诊断行动](docs/actions/2026-09-21-core-code-diagnostic-review.md)。该文件与 `AGENTS.md` 的归档规则增量在本次交接检查时尚未提交，不得被其他任务覆盖或顺手暂存。

## 2. 当前阻塞与授权边界

| 范围 | 当前事实 | 接续边界 |
|---|---|---|
| M1 任务 14 | 已有 HTTPS 双角色正向流程；远程负向、VPN/离线等未全部完成 | 只有用户重新安排任务 14 时才继续，不自动改网络、代理、防火墙或 Tailscale |
| 任务 03 | Web 对比页、五结果矩阵、按需指标和证据钻取已落地 | 只剩人工确认与独立的 20 列滚动手感缺口；不重做后端接口 |
| 任务 04 | 六道题、连续规模与相关回归已落地 | 等人工确认，不再按旧计划重复拉镜像、跑门禁或改白名单 |
| 任务 05 | 9 项决定已确认；实现不存在；前置最新记录为 3/6，7 条拓扑断言未执行 | 没有实施开工和探针执行授权；不得创建/删除任务资源、读取真实 Key 或调用供应商 |
| 任务 06–08 | 未实施 | 真实调用、账户设置、费用与矩阵必须重新取得当轮授权 |
| 正式运行态 | 2026-09-21 曾恢复 Web 和 Worker并完成一条 Job | PID、容器、队列、Cookie、余额均是动态状态；需要时只读重查，不沿用旧快照 |
| 团队数据库接入 | B 侧已定位为不在同一 tailnet；当前不需要数据库，暂不重试 | 不写入私有 tailnet 名/IP；由 owner 分享设备或邀请账号后才重验 |

通用边界：不把规划或文档回执当作产品实现；不自动批准 Job、不自动重试真实模型、不自动充值；不读取或输出 `auth.json`、Key、Cookie、密码等正文；不使用全局 Docker prune；不把历史 passed/skipped 数字冒充本轮刚跑结果。

## 3. 权威文档必读顺序

开始任何修改前按以下顺序读取，按任务追加而不是一次加载全部历史：

1. [AGENTS.md](AGENTS.md) 与本文：协作规则、当前 Git/任务边界。
2. [CONTEXT.md](CONTEXT.md)：Job、Run、Agent Configuration、确定性验证等领域词义。
3. [总架构](docs/architecture/ARCHITECTURE.md)、[模块索引](docs/architecture/modules/README.md)与相关模块架构：模块边界、依赖方向和现实代码地图。
4. [模块契约](docs/architecture/MODULE_CONTRACTS.md)、[HTTP API](docs/interfaces/HTTP_API.md)、[数据模型](docs/architecture/DATA_MODEL.md)：接口、错误、字段、状态机与持久化约束。
5. [Harbor 执行接口](docs/interfaces/HARBOR_EXECUTION.md)、[认证接口](docs/interfaces/CODEX_AUTHENTICATION.md)、[依赖表](docs/dependencies/DEPENDENCIES.md)：执行链、秘密边界和固定身份。
6. 做规格或任务前，先读 [`docs/agents`](docs/agents/) 约定，再读当前[扩展计划](.scratch/ui-catalog-providers/plan.md)、对应 issue 和同任务行动。
7. 做运行、Docker、网络或远程接入前，追加读[所有者行动指南](docs/architecture/modules/owner-host-runtime/ACTION_GUIDE.md)、[本机环境](docs/operations/LOCAL_DOCKER_ENVIRONMENT.md)和[远程接入](docs/operations/REMOTE_TEAM_ACCESS.md)。

完成阅读的标准不是“打开过文件”，而是能从代码和契约指出当前入口、拒绝条件、授权边界及未验证项。历史行动中的旧快照不能覆盖当前代码或持续维护文档。

## 4. 核心代码与测试必读

当前主要依赖方向仍为 `Web/CLI → delivery → application → domain/ports ← adapters`。继续工作前按涉及模块实际读实现和测试：

- 目录与六题身份：[受控镜像映射](apps/backend/src/eval_platform/adapters/tasks/catalog.py)、[HTTP 预设](apps/backend/src/eval_platform/delivery/catalog_presets.py)及 `apps/backend/tests/catalog/`。
- Job 提交/批准/执行：[提交](apps/backend/src/eval_platform/application/job_submission.py)、[批准](apps/backend/src/eval_platform/application/owner_approval.py)、[执行](apps/backend/src/eval_platform/application/execute_job.py)、`application/job_lifecycle/` 与 `adapters/persistence/jobs/`。
- 报告与五结果矩阵：[矩阵](apps/backend/src/eval_platform/application/reporting/matrix.py)、[比较路由](apps/backend/src/eval_platform/delivery/http/routes/jobs/reporting/comparisons.py)及 `apps/backend/tests/jobs/reporting/`。
- Worker 与现有提供方边界：[Worker 装配](apps/backend/src/eval_platform/delivery/worker/runtime.py)、`adapters/execution/` 和认证接口。当前仍是固定 Codex/`openai_chatgpt` 链，不能假定任务 05 已有实现。
- Web 工作台与对比页：`apps/web/src/features/workbench/`、`apps/web/src/features/jobs/`、[对比页](apps/web/src/features/jobs/reporting/comparison.tsx)及 `apps/web/tests/`。
- 生命周期与部署：根目录四个 `*-AgentExam.ps1`、`infra/` 和 owner-host-runtime 文档；运行状态必须现场检查。

当前全量代码诊断仍在进行中。接续该审查时先读其行动记录，并保持“只审查、不修业务代码”的既定范围；诊断报告尚未完成前不要替它下最终结论。

## 5. Git、环境与测试快照

### Git 与必须保留的增量

本次检查时：

- 主工作区分支为 `main`，已提交基线 `c71d342041e45c63dad91883b6d4bb33289b0ec3`，与 `origin/main` 一致。
- `fengyy-fixweb` 已通过 `2874577` 合并；随后两轮并发 `origin/main` 由 `d7e875f`、`c71d342` 安全整合并普通推送。临时 `runtime/worktrees/fengyy-fixweb` 已移除，分支与 `d9a7759` 提交仍保留。
- 另有 Codex 管理的 detached worktree `C:\Users\YINGYI\.codex\worktrees\b025\9.1agent_exam`，本轮未触碰；不要因整理当前仓库而删除它。
- 当前工作树不是干净状态。独立进行中的代码诊断拥有 `AGENTS.md` 修改和 `docs/actions/2026-09-21-core-code-diagnostic-review.md`；本 HANDOFF 更新拥有本文及自己的行动记录。恢复时必须先重新运行 `git status`/`git diff`，按归属处理，禁止 `git add .`、reset 或覆盖。
- `.scratch/ui-catalog-providers.zip` 与 `apps/web/%USERPROFILE%/` 是保留的本地临时产物，不提交、不删除；除非用户另行决定，可后续单独加入忽略规则。

远程布局以本机 `git remote -v` 的实际结果为准，不沿用旧窗口关于 fork/upstream 的概括。本轮已实际向 `origin/main` 普通推送并以远端哈希核对成功；该授权已经完成，不延伸为新窗口自动 push。

### 最近已完成的验证

下列结果来自[合并行动](docs/actions/2026-09-21-merge-fengyy-into-main.md)，本次 HANDOFF 更新没有重跑代码测试：

- Backend：Ruff check 通过；300 个文件格式检查通过；Mypy 169 个源文件通过；默认回归 `424 passed / 96 skipped / 2 warnings / 0 failed`。
- Web：类型检查通过；生产构建与 4 个静态页面生成通过；完整端到端回归 `35 passed / 0 failed`。
- 合并冲突定向验证：后端报告矩阵 `16 passed / 2 skipped / 2 warnings`；相关端到端 10 项通过。
- 文档/Git：合并时相对链接、冲突标记、空白错误和有限敏感形态扫描通过。

`skipped` 仍代表外部存储、Docker、Fork/Harbor 等显式门禁未在该轮启用，不能计为通过。任务 05 拓扑探针没有运行。

## 6. 下一窗口的工作顺序与验收

1. 完整读当前 `AGENTS.md` 与本文，再运行只读的 `git status --short --branch`、`git log -8 --oneline --decorate` 和按路径 `git diff`；先识别文件归属，保留诊断任务、临时产物、`framework/` 与 `runtime/`。
2. 若用户只说“恢复上下文”，完成只读核对后汇报已恢复并等待，不自动拉取、测试、实现、提交或推送。
3. 若接续当前代码诊断，读取[诊断行动](docs/actions/2026-09-21-core-code-diagnostic-review.md)和适用评审技能；继续审查与报告，不修业务代码，除非用户另行授权修复。
4. 若接续任务 04，只处理人工确认或明确缺口，不重复已完成的五题门禁、白名单、continuous 和向导回归。
5. 若接续任务 05，先从[负责人回执](docs/LLY/01-plan/TASK05_OWNER_ACTION_REQUIRED.md)核对 9 项决定，再确认新的实施授权与探针窗口；没有新授权时只可继续文档/设计，不运行拓扑、不创建 Docker 资源、不读取 Key。
6. 任务 06–08、任务 14 或机器网络/运行态均需用户明确安排。任何真实供应商调用、充值、账号设置、Docker/WSL/代理/防火墙变更或共享数据库写入都不得从历史授权推断。
7. 修改后同步当前架构/接口/状态文档与本任务行动记录，实际运行相称的检查并查看输出；历史证据与本轮新验证分开报告。

当前没有自动续做的产品实现目标。最小接续点是完成进行中的全量核心代码诊断，或等待用户指定任务 04 人工确认、任务 05 实施/探针、任务 14 远程验收中的一项。

## 7. 历史入口

早期 M0、M1 分任务、持久化、远程运行和网络实验均保留在 `docs/actions/`、`docs/research/` 及对应接口/运维文档中。它们记录各自时点的过程和证据，不再把旧提示词、旧 PID、旧提交领先数或旧测试数量复制到本恢复入口。

面向项目所有者的阅读路线见[项目阅读指南](docs/architecture/READING_GUIDE.md)。需要追溯 M0 真实运行时，从[M0 行动记录](docs/actions/2026-09-05-m0-codex-harbor-implementation.md)对应事件段落进入；需要追溯持久化时，从[所有者单机运行模块](docs/architecture/modules/owner-host-runtime/ARCHITECTURE.md)与其行动指南进入。

## 8. 建议使用的技能

- 修改项目文件：`action-document`。
- 项目范围、进度与收尾汇报：`project-control-report`。
- 审查当前分支或固定差异：`code-review`；全量语言/安全/架构诊断按已开始的 `code-review-skill` 行动范围继续。
- 复杂故障或性能回归：`diagnosing-bugs`。
- 实际出现 Git 冲突：`resolving-merge-conflicts`。

技能只规定工作方法，不扩展业务、运行、提交或外部调用授权。
