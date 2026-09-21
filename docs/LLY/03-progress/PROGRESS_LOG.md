# 开发进度日志

> 只记录事实与实际结果：做了什么、实际输出是什么、遇到什么。计划见 [`01-plan/PLAN.md`](../01-plan/PLAN.md)。
> 格式：按日期倒序追加，最新在最上面。

## 2026-09-21

### 已完成

- 归档扩展计划 6 份文件（来源 `D:\ui-catalog-providers\ui-catalog-providers\`）：4 份更新到权威位置 `.scratch/ui-catalog-providers/`，2 份任务单落位新建的 `issues/` 子目录。归档前仓库版本是旧版（仍写“01 未开工、未发布任务单”）；相对旧版的实际变化为 `spec.md` 2 行、`plan.md` 25 行、`implementation-map.md` 95 行，`verification.md` 内容本就相同。
- 归档方式：`docs/LLY/` 只增加指向权威位置的链接、不复制计划正文 —— 依据本目录 README 的单一事实源规则。
- 更新后的计划确认：**P、任务 01、任务 02 均已完成**（任务 02 是“A 版假数据原型连接现有后端的第一片正式 Web”，含 32 条浏览器回归、类型检查、生产构建、31 项 API 对账与双轴评审）；03–08 仍未发布为独立 issue。
- 拉取远端：`origin/main` 由 `6dfa2be` 前进到 `beed93f`，并新增分支 `origin/xinyue-modules`。远端提交中包含与本次归档**内容完全相同**的 6 份文件，逐份比对差异均为 0 行。
- 因此丢弃本地冗余改动（3 份修改文档 + 2 份新增任务单副本），改由合并 `origin/main` 取得；`lly/dev` 由 `469ba1d` 前进到合并提交 `2a55a9e`，无冲突。
- **2026-09-19 记录的两处缺口已由本次推送补齐**：① `docs/actions/2026-09-18-ui-workbench-prototype.md` 与 `2026-09-18-ui-workbench-implementation.md` 已进入仓库；② 任务 02 的产品代码（`apps/web/src/features/workbench/`、`jobs/wizard/`、`jobs/listing/`、`apps/web/tests/workbench/`）已进入仓库。合并后 6 份计划文件的全部仓库内相对链接可解析。
- 本次推送另带入 D、B 的 03/04/08 准备工作：对比查询接口与矩阵渲染、连续规模 preset、任务 03 报告语义设计、任务 08 runbook。这些任务仍**未发布为独立 issue**；`TEAM_WORK_ALLOCATION.md` 第 7 条已相应改为“01–02 已发布并完成；03–08 仍是未发布的规划编号”。
- 合并后后端验证：`ruff check` 通过；`mypy` 167 源文件无问题（合并前 164）；默认回归 **404 passed / 84 skipped / 2 failed（55.89 秒）**，相对合并前基线 386/82/2 通过数 +18、跳过数 +2，**失败项完全相同**（仍是缺少 `framework/harbor` 的 ISSUE-04），无新增失败。
- 过程与完整证据见[归档与同步行动](../../actions/2026-09-21-file-plan-docs-and-sync.md)。
- 完成 05 的准备性测试设计：[阶段 1（05）假提供方安全执行链测试设计](../01-plan/STAGE1_PROXY_TEST_DESIGN.md)。把[验证规范第 4 节](../../../.scratch/ui-catalog-providers/verification.md)的负例矩阵逐条映射为测试归属（测试文件、用例名、断言、运行位置），并按“本机无 Docker、`framework/runtime` 只在组长机器”的现状分层：策略层、契约层、生命周期层在本机，集成层只在组长机器。
- 覆盖核对发现并补上三处遗漏：直连供应商/宿主/metadata/其他 Trial、容器文件与进程及 Docker inspect/patch 的假 Key 探查、新 Job 重试需重新批准。现五组负例全部有明确归属。
- 同时标出四项**开工前必须冻结、现在不得预设**的未知：Token 上界/请求字段白名单/账本格式（实现地图第 5 节明示未验证）、固定 CLI 是否需要容器承载、Compose 拓扑不能沿用共享网络命名空间的现有侧车、私有文件精确权限条件。
- 本次只产出设计文档：未创建 `tests/providers/`、未写任何测试或产品代码、未安装 Docker、未调用模型。过程见[测试设计行动](../../actions/2026-09-21-stage1-proxy-test-design.md)。
- 拉取远端：`origin/main` 由 `beed93f` 前进到 `361998b`（68 文件、+4435/−153）；`lly/dev` 直接**快进**到该提交（无需合并提交），领先 `origin/lly/dev` 46 个提交。`docs/LLY/` 的既有改动已随 PR #5 合入 main，本地与 main 中的版本逐字节一致。
- **任务 04 已发布且 8 项验收全部完成**。其中第 3 项（五题 × 参考/空/错误 = 15/15 场景）原属 E 的 12 h 配合范围，实际由 C 在组长机器上执行（证据 `runtime/fork-evidence/` 15 个 scope、容器清理 `verified`、Fork `returncode=0`），五道候选已写入白名单。**该事实需与负责人确认**：它影响分工表中 E 的工时构成与任务 08 的输入。
- 记录一个直接落在 E 的 06/07 路径上的潜在缺陷（已在代码中核实）：`routes/catalog.py` 接受并校验 `agent_type` 查询参数，但 `application/agent_registry.py` 的 `list()` 签名不含该参数，因此**该筛选从不生效**；当前因登记路径仅允许 `codex` 而行为等价，06/07 接入 DeepSeek/Kimi 后会静默失灵。C 已转给 D 记录在案，该行动明确"不改动"。
- 合并后的本机验证：`ruff check` 通过；`ruff format --check` 300 文件；`mypy` 169 源文件无问题；默认回归 **417 passed / 101 skipped / 2 failed（59.93 秒）**，相对上次 404/84/2 通过 +13、跳过 +17，失败项完全相同（仍为缺 `framework/harbor` 的 ISSUE-04）。
- 起草 05 任务单：[`issues/05-fake-provider-secure-execution-chain.md`](../../../.scratch/ui-catalog-providers/issues/05-fake-provider-secure-execution-chain.md)，`Status: needs-info`，9 项验收 + 停止条件，等待负责人发布与开工授权。起草方式对照 C 为任务 04 走过的路径（成员起草 → 负责人发布并授权）。过程见[起草行动](../../actions/2026-09-21-draft-task-05-issue.md)。
- 验收项覆盖核对发现并补上一处遗漏：权威负例第一条的"未批准、错误 profile、缺密钥、宽权限/链接文件"未落入第 4 项验收，已补；随后又按权威措辞把第 5 项对齐为"正式链路的合成 Run 可完成"。现关键短语全部命中。
- 05 任务单草案经负责人过目后提交并推送：提交 `6ccf001`，4 个文件（任务单 + 起草行动 + 2 份 LLY 文档），已到 `origin/lly/dev`。**注意区分：这不等于"05 已发布"**——按现有先例（01/02/04）发布以进入 `main` 为准，而开工授权还需负责人明确安排。
- 产出 05 组长机器交接预案：[任务 05 组长机器执行预案](../../actions/2026-09-21-task05-owner-machine-runbook.md) 第 05 节。沿用 D 的"操作手册"形态（标注草稿、以 `plan.md` 第 7 节为准、不复制任务步骤），把"最小拓扑实证"拆成可顺序执行的断言清单、前置核对、停止条件、清理与回报要求、不得做清单；并写明**代码归属**——代理实现由 E 在本机编写并跑通策略/契约/生命周期层替身测试后推送，负责人机器只做需要真实隔离环境的运行与核验，现场改动须回仓库走同一评审。该预案已提交推送（提交 `3db8955`）。
- 产出 05 设计冻结底稿：[阶段 1 代理设计冻结底稿](../01-plan/STAGE1_PROXY_DESIGN_FREEZE.md)。这是 05 第 1 步"冻结代理拓扑、私有文件格式与权限、请求字段白名单、计量策略"的工作底稿，按**机制（E 定稿）与数值（交负责人）分开**的原则编写，六项待冻结内容各有候选设计并标注状态。
- 设计底稿补入一条此前未纳入的硬约束：Codex 官方配置的 `request_max_retries`、`stream_max_retries` **默认值不是零**，必须显式关闭，并由代理独立验证没有发生重发——因为研究第 6.1 节已证明命令行可覆盖模型，只信任配置文件不成立（依据研究第 1 节、第 6.1 节）。
- 读现有侧车代码后确认：`adapters/execution/network.py` 的 `compose_profile()` **刻意不声明 `networks`**，由 Harbor 环境附加自己的侧车，因此主容器与侧车共享网络命名空间——05 的拓扑不能照搬，需替换网络附加方式；能否替换是拓扑实证要回答的第一个问题（与认证接口第 4.1 节第 5 条一致）。
- 列出 **9 项待负责人拍板**的事项：每 Run 输入/输出额度、模型期限、请求频率、首轮支出目标、Kimi 项目日/月预算、输入 Token 计数方式、私有文件宿主路径与 owner 主体、组长机器窗口授权。机制设计不代替这些决定，研究第 4 节的初值只作起点。
- 产出可转发的负责人侧交付要求：[`01-plan/TASK05_OWNER_DELIVERY.md`](../01-plan/TASK05_OWNER_DELIVERY.md)。形态为**自足可整份转发**（负责人或其 AI 助手无需先读其他文档），但不复制权威正文，文末列出对应位置。内容三件：① 9 项拍板表格（含第 7 项两条路线的后果说明，9 个单元格留空待填）；② 6 项前置核对清单（任一不满足即停）；③ 最小替身拓扑实证——7 条断言含三组对照、证据与清理要求、代码归属说明。
- 文档明确了两点边界：**一次性探针**允许在负责人机器上编写与运行（沿用 M0 各次探针的既有做法，位于被 Git 忽略的证据目录、不进产品树）；**产品代码**仍由 E 在本机写好并跑绿后推送，现场不临时改。
- 负责人返回填充版核对结论，原文归档为 [`01-plan/TASK05_OWNER_DELIVERY_FILLED.md`](../01-plan/TASK05_OWNER_DELIVERY_FILLED.md)（正文未改，仅加一行归档说明）。结论是**前置总判定 STOP、拓扑实证未执行**：6 项前置只完整满足 1 项（`framework/harbor` revision `6af8d6e3…` 与依赖表一致、工作树干净）；**9 项拍板全部仍为"待负责人确认"**（第 7 项推荐 A 保守上界起步，但未作最终选择）；7 条断言全部未执行；Docker Engine 27.5.1 可响应但未获创建授权。
- 负责人已核实的代码事实：Catalog/目录 HTTP schema/Agent Registry/Worker 组合/Harbor 引导**仍全部固定 `openai_chatgpt`/Codex**；Harbor 层 `max_retries=0` 已存在但不能替代 Codex CLI 两个重试参数与代理转发次数的独立验证；现有认证文件校验不足以证明 Windows ACL/属主。
- **修掉一处我方措辞缺陷**：原交付要求第 2 节第 3 项写"没有运行中的业务 Job 或容器"，负责人核对时指出持久化服务容器正在运行、该条件按字面不成立。已拆为"无业务 Job"+"不得停止或删除既有持久化服务"，并在文中标注该修正由负责人核对发现。
- **发现并修复一处真实断链**：负责人指出 `docs/LLY/01-plan/STAGE1_PROXY_DESIGN_FREEZE.md` 在仓库中不存在——**该判断正确**。核实 `git log --all -- <path>` 为空，远端 `docs/LLY/01-plan/` 下只有四个文件。根因是上一轮产出设计冻结底稿与交付要求后**未提交即交付**，对方只能从微信副本读取。已在本切片补交并按提交前查路径可用性。
- 负责人核对结论已回填到任务 05 任务单的 `## Comments`，作为该任务的正式讨论记录。
- 产出待负责人回执的文档：[`01-plan/TASK05_OWNER_ACTION_REQUIRED.md`](../01-plan/TASK05_OWNER_ACTION_REQUIRED.md)（可整份转发）。把当前唯一的两处阻塞写成可直接回执的形态：① 9 项决定表（提供"建议全部采用"这一最小回执方式，第 7 项明确 A/B 两条路线的后果）；② 授权范围具体到可批准——给出建议的 Compose 项目名 `agentexam-t05-topology`、逻辑网络 `internal`/`egress`、服务 `workload`/`proxy`/`fake-upstream`、标签与"只按名称与标签删除、禁止全局 prune"的清理规则，并给出可直接改字的授权回执模板。
- 该文档同时减轻对方负担：明确 **假 Key 文件由探针自行生成、不需要负责人准备**（拒绝用例本就需刻意造出符号链接/宽权限等错误形态）；并写明第 2–4 步（白名单机制、私有文件校验、配置渲染、假服务、本机替身测试）**不必等拓扑结论**即可并行开工，即使拓扑最终不可行也不浪费。
- `TASK05_OWNER_DELIVERY.md` → `TASK05_OWNER_DELIVERY_FILLED.md` → `TASK05_OWNER_ACTION_REQUIRED.md` 三份构成"请求 → 回复 → 回执"配对，均置于 `01-plan/`。
- 负责人后续一次性确认 9 项决定：输入 300,000、输出 32,000、期限 900 秒、最多 3 次/分钟、首轮目标不超过 ¥100、Kimi 日/月各 ¥80、输入计数采用 A 保守上界；仓库外私有路径与 owner 规则、专属拓扑资源范围也已确认。负责人同时明确本轮只填文档、不运行探针，因此没有当前 Docker 创建/删除授权或时间窗口。三份负责人文档、设计冻结底稿和 05 任务单 Comments 已同步该边界。

### 当前停点

- 阶段 0 环境仍可用（PostgreSQL `127.0.0.1:55432`、`agentexam_dev` 11 表）；实时状态只在[本地环境记录](../02-environment/LOCAL_SETUP.md)维护。
- 任务 04 已发布并完成；03 无独立任务单但 B 在推进；05 任务单现已进入 `main`，但仍为 `needs-info`，**未获实施开工授权**。负责人 9 项决定已经确认；机制合同尚未整体冻结，最小拓扑实证仍须取得组长机器窗口和单独执行授权。不得因决定回执完成而提前修改任务 05 产品代码、调用真实模型或下载大体量镜像。
- 前端依赖仍未安装：合并带入的任务 02 Web 代码在本机**未经验证**（未跑类型检查、生产构建与浏览器回归）。
- 历史 `lly/dev` 切片及任务 05 准备文档现已随主线合并进入 `main`；旧提交记录保留为历史证据，不再把“尚未合并进 main”当作当前状态。
- **下一步（E 侧）**：先由负责人另行发布实施开工指令，再按已确认的 A 保守上界与数值完善机制合同；拓扑和集成层仍等待组长机器时间窗口及创建/删除专属资源的单独执行授权。本轮只完成分支同步和文档回执，不启动实现。

## 2026-09-19

### 已完成

- `lly/dev` 从 `625d02b` 安全快进到 `origin/main` 的 `6dfa2be`；同步前已有的 `docs/LLY/` 与本地行动文档均保留，无冲突。
- 阅读新提交的统一环境配置：owner 的 `infra` 部署链现在要求 Git 忽略的 `infra/.env`；普通后端应用仍只读取进程环境变量。本机便携 PostgreSQL 开发不使用 Docker，因此当前不创建 `infra/.env`。
- 重新核对项目停点：扩展规格、计划、实现地图和验证规范仍为 `needs-info`，01–08 仍未发布 issue；E 模块下一项是任务 05，但尚未获开工授权。
- 用户确认当前继续处于阶段 0，并授权按建议自行确定本机前提环境方案；已确定 `agentexam_identity_test`（自动化测试）与 `agentexam_dev`（日常开发）两库隔离，不再把 Tailscale 或共享管理员数据库作为前置。
- 已落盘[阶段 0 设计](../01-plan/STAGE0_LOCAL_DEVELOPMENT_DESIGN.md)与[详细实施计划](../01-plan/STAGE0_LOCAL_DEVELOPMENT_PLAN.md)，并按计划完成了本机环境实施。
- 已按计划完成阶段 0：恢复 PostgreSQL、创建 `agentexam_dev`、安装 11 表 schema、同步 Python 依赖、运行静态检查与本地 PostgreSQL 集成测试，并完成停止/重启读回。
- PostgreSQL 集成测试实际结果为 **246 passed / 11 skipped / 2 warnings**；默认回归为 **386 passed / 82 skipped / 2 failed / 2 warnings**，两个失败均为缺少 `framework/harbor` 的已知 ISSUE-04。

### 当前停点

- 阶段 0 已完成；2026-09-19 收尾时 PostgreSQL 按 `127.0.0.1:55432` 运行、`agentexam_dev` 可用。实时运行状态只在[本地环境记录](../02-environment/LOCAL_SETUP.md)维护。
- 不自动开始任务 05，不调用真实模型、不下载 Harbor/Fork 大体积环境。
- 下一步应由项目负责人先审阅并发布扩展任务；按既定顺序，团队整体先处理 01，轮到 E 模块时再为 05 冻结代理拓扑与安全合同。

## 2026-09-18

### 已完成

- 克隆并同步仓库到 `D:\agent-exam`；工作区 HEAD 与 `origin/main` 一致（`625d02b`）。
- 通读项目入口文档：`AGENTS.md`、`HANDOFF.md`、`CONTEXT.md`、模块索引与七个模块架构、团队分工文档、M1 规格与任务单、扩展执行计划。
- 确认项目现状：M0 核心闭环通过；M1 任务 01–13 验收完成，14（私有双机协作验收）进行中；P（本地持久化）已完成；扩展 01–08 已规划未发布 issue。
- 排查本机 Tailscale 无法登录的问题，结论记录在[问题记录](../04-issues/KNOWN_ISSUES.md)（尚未解决，已排除多项）。
- 当日确认本机便携 PostgreSQL 开发不需要 `.env`：后端无 dotenv 依赖、无 `.env` 自动读取逻辑，配置来自进程环境变量。owner `infra` 部署链在次日同步的新提交中另行引入 Git 忽略的 `infra/.env`，不改变本机开发结论。
- 创建开发分支 `lly/dev`。
- 建立 `docs/LLY/` 四类过程文档目录与目录说明。
- 编写 E 模块本地开发计划书。
- 启动 PostgreSQL 15.14 便携版下载（约 320 MB）。

### 本地环境（已完成）

- 安装 PostgreSQL 15.14 便携版到 `D:\pgsql`，数据目录 `D:\pgsql\data`，监听 `127.0.0.1:55432`（仅回环），回环信任认证（因此无需创建或保管任何数据库密码）。
- 建立专属测试角色与库 `agentexam_identity_test`（含 `CREATEDB`，测试夹具需要自建临时库）。
- 用项目自带 `initialize_empty_database()` 安装业务 schema，实际得到 **11 张表**，与预期清单逐项一致。
- 用 `uv sync` 建好 Python 环境：uv 自动准备 **Python 3.13.15**（系统 Python 是 3.12.0，不满足项目要求 `>=3.13,<3.14`），依赖按 `uv.lock` 装齐。
- 静态检查基线：`ruff check` 通过、`ruff format --check` 283 文件已格式化、`mypy` 164 源文件无问题。
- 默认回归基线：**386 passed / 82 skipped / 2 failed（52.96 秒）**。
  - 82 项跳过是设计如此：需要真实外部依赖的用例藏在 `AGENTEXAM_RUN_*` 显式开关后面。
  - 2 项失败均因缺少被 gitignore 的 `framework/harbor`（只在组长机器上），属环境依赖，非产品缺陷；已记为 ISSUE-04。
  - 注意：文档中曾记载的"194 passed / 19 skipped"是 M0 时期的数据，当前默认套件规模已明显增大，不能沿用旧数字。

### 进行中

- 前端依赖未安装；MinIO、Docker 未配置。

### 观察与结论

- 本机（`D:\agent-exam`）是一份新克隆：没有 `apps/backend/.venv`、没有 `apps/web/node_modules`、Docker 未运行、`D:\AgentExamData` 不存在。文档中记录的历史验证证据来自另一台机器，本机不能声称"刚跑过"。
- `HANDOFF.md` 中记录的 workspace 是 `E:\9.1agent_exam`，与本机路径不同；文档中的提交数、环境现场描述带有上一台机器的假设，接续时需重新核对。
- M1 任务单的 `**Status:**` 标签不一致：01–11 仍为 `ready-for-agent`，12–13 为 `completed`，14 为 `in-progress`。任务 01–13 的验收勾选框实际已全满（按任务 01 注释的规则，完成以验收项与行动证据判定，标签不增设完成值），但仅凭标签统计进度会读错。
