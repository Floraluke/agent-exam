# 开发进度日志

> 只记录事实与实际结果：做了什么、实际输出是什么、遇到什么。计划见 [`01-plan/PLAN.md`](../01-plan/PLAN.md)。
> 格式：按日期倒序追加，最新在最上面。

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
