# E 模块本地开发环境与过程文档目录

> 2026-09-19 后续同步：提交 `6dfa2be` 为 owner 的 `infra` 部署链新增了 Git 忽略的 `infra/.env`。本文“无需 `.env`”仅指本机便携 PostgreSQL 与普通后端开发；若运行 owner 部署脚本，须按 `infra/.env.example` 私下创建本机配置。历史验证结果不因此改写。

## 状态与情况

- 状态：已完成（分支、目录、计划书、本地 PostgreSQL 与 Python 环境、静态检查与默认回归基线均已落地）
- 来源请求：E 模块负责人（组员 LLY）要求：(1) 安装本地 PostgreSQL（此前对比的路线 A，已获组长许可）；(2) 建立开发分支；(3) 在 `docs/` 下新建 `LLY/` 目录分类存放开发过程文档，并先写一份计划书；(4) 确认是否需要配置 `.env` 文件。
- 当前事实：
  - 仓库当前分支为 `main`，与 `origin/main` 一致；此前 HANDOFF 记录的 `E:\9.1agent_exam` 工作区不是本机。
  - 本机（`D:\agent-exam`）没有 Python 虚拟环境、没有前端 `node_modules`、Docker 未运行、`D:\AgentExamData` 不存在，属于新克隆。
  - 后端应用**不自动读取 `.env` 文件**：`pyproject.toml` 无 dotenv 依赖，源码中无 `load_dotenv`，配置来自进程环境变量（如 `AGENTEXAM_DATABASE_URL`、`AGENTEXAM_MINIO_*`）。后续提交 `6dfa2be` 让 owner 的 `infra` 部署脚本与 Docker Compose 读取 Git 忽略的 `infra/.env`；该路径不属于本轮便携 PostgreSQL 开发环境。
  - 需要真实 PostgreSQL 的测试要求专属隔离库：回环地址、**非 5432 端口**、库名与用户名均为 `agentexam_identity_test`，不满足即 `pytest.fail`（`apps/backend/tests/identity/conftest.py`）。
  - 本地环境暂时无法连接团队共享库：Tailscale 的 Wintun 虚拟网卡在本机装不上（设备 `CM_PROB_*` 失败），已排除 360、Clash、设备安装服务、类过滤驱动、HVCI 等原因，尚未解决；该问题不影响本轮开发环境搭建与代码工作。
- 已确认决定：采用路线 A（本机原生 PostgreSQL，不用 Docker）；本地库仅作开发与测试用途；新建 `docs/LLY/` 目录；本轮改动全部在 `lly/dev` 分支上。
- 明确排除：不修改产品代码、模块 Interface、数据库表或项目 schema；不使用真实模型或凭据；不连接团队共享库（既不读也不写）；不推送 Git；不在本地库中放入任何真实业务数据。
- 未知：本地 PostgreSQL 的具体安装形态与版本下载可用性；默认回归在当前依赖版本下的实际结果。

## 实施措施

1. 从 `main` 新建开发分支 `lly/dev`，本轮所有文件改动只在该分支产生。
2. 新建 `docs/LLY/` 目录，按「计划、环境、进度、问题」四类归档开发过程文档；在 `README.md` 中写明本目录与项目权威文档的边界，避免同一事实两处维护。
3. 编写 `docs/LLY/01-plan/PLAN.md`：E 模块（执行与判卷）的本地开发计划书，覆盖模块边界、任务归属、阶段计划、验证方式与停止条件；正文引用现有权威文档，不复制字段、路由或表结构。
4. 安装 PostgreSQL 15（与项目固定大版本一致）到 `127.0.0.1:55432`，建立专属测试角色与库 `agentexam_identity_test`，并使用项目自带 `initialize_empty_database()` 安装 schema（11 张表）。
5. 建立后端 Python 虚拟环境并安装依赖，运行默认回归与静态检查，确认基线状态。
6. 回答 `.env` 问题：本轮本地后端开发不需要 `.env`；若确实要连共享库，需向管理员索取**可直接使用的库连接信息**，而不是复制管理员的私有 `.env`。owner 部署场景另按公开模板创建各自的 `infra/.env`。

完成标准：分支、目录与计划书可用且内容与现有权威文档不冲突；本地 PostgreSQL 可连、schema 完整、专属测试库可用；默认回归与静态检查有实际输出记录；`.env` 结论有代码依据。

## 受影响文件树

```text
docs/
  actions/
    2026-09-18-lly-local-dev-environment.md   # 新增：本次行动的记录、验证结果与偏差（权威行动记录）
  LLY/
    README.md                                 # 新增：LLY 过程文档目录的用途、边界与分类说明
    01-plan/
      PLAN.md                                 # 新增：E 模块本地开发计划书（本轮主要交付）
    02-environment/
      LOCAL_SETUP.md                          # 新增：本地开发环境搭建记录（PostgreSQL、venv、依赖）
    03-progress/
      PROGRESS_LOG.md                         # 新增：开发进度日志（按日期追加）
    04-issues/
      KNOWN_ISSUES.md                         # 新增：本机开发环境问题记录（含 Tailscale/Wintun 未决问题）
```

设计关系：本目录是**个人/小组开发过程记录**，属交付物之外的协作材料；产品级事实仍由现有权威文档单处维护（架构 → `docs/architecture/`、接口 → `docs/interfaces/`、运维 → `docs/operations/`、行动 → `docs/actions/`）。`docs/LLY/` 只做索引用途；某项事实一旦成为项目级结论，必须提升到对应权威文档，并在原处只留指针。

新增 `docs/LLY/` 的理由：现有 `docs/actions/` 只承载**已实施的行动记录**，`docs/operations/` 承载**机器与环境事实**，缺少一个「本组开发过程的计划、进度与个人环境记录」的归集位置；由用户提出并确认建立独立目录，避免把过程性材料混入权威文档。

## 自验证方式

1. `git branch --show-current` 确认为 `lly/dev`；`git status --short` 核对改动范围只含本次新增与行动文档。
2. 检查 `docs/LLY/` 下四类目录与 `README.md` 均存在且非空；`README.md` 中写明与权威文档的边界。
3. 检查 `PLAN.md` 内容与 `.scratch/ui-catalog-providers/plan.md`、`docs/architecture/modules/TEAM_WORK_ALLOCATION.md` 不冲突，且未把规划写成已开工。
4. 检查所有 Markdown 相对链接指向存在的文件；检查代码围栏成对；检查无行尾空格。
5. 本地 PostgreSQL：`pg_isready -h 127.0.0.1 -p 55432`；连接后 `\dt` 应为 11 张表；`SELECT version()` 应为 15.x。
6. 专属测试库校验：设置 `AGENTEXAM_TEST_DATABASE_URL` 与显式开关后运行身份 PostgreSQL 测试；未设置开关时应为 skip 而非 fail。
7. 静态检查与默认回归：在 `apps/backend` 运行 `ruff check`、`ruff format --check`、`mypy`、`pytest -q`，记录实际输出。
8. 检查仓库内无 `.env` 文件被创建，也无任何密码、连接串或凭据进入被跟踪文件。

## 自验证结果

实际执行于 2026-09-18，全部在工作区 `D:\agent-exam`。**本任务未修改任何产品代码、schema、表或 Interface。**

### 分支与改动范围

- `git checkout -b lly/dev` 成功，`git status --short --branch` 显示当前分支 `lly/dev`。
- 本次新增文件仅：行动文档 1 份 + `docs/LLY/` 下 5 份 Markdown。工作区无产品代码改动。

### 文档检查

- 相对链接：对 6 份新文件做脚本校验，修正了两处"多退一层目录"的错误后复检，**失效链接 0 个**（首次检查报 21 个失效，属本任务自身错误，已修正）。
- 目录结构：`docs/LLY/` 下 `README.md` 与四个分类目录的文档均存在且非空。
- 未把规划写成已开工：`PLAN.md` 首段明确标注"计划，未开工"，并声明不构成实施与真实调用授权。

### 环境验证（工作目录 `apps/backend`）

| 检查 | 实际结果 |
|---|---|
| PostgreSQL 就绪 | `pg_isready -h 127.0.0.1 -p 55432` → `accepting connections` |
| 版本 | 服务器日志 → `PostgreSQL 15.14, compiled by Visual C++ build 1944, 64-bit` |
| 监听范围 | 服务器日志 → `listening on IPv4 address "127.0.0.1", port 55432`（仅回环） |
| schema | `pg_tables` 查出 11 张表，与预期清单逐项一致 |
| 专属角色 | 以 `agentexam_identity_test` 连接成功，`current_user` / `current_database` 均为该名 |
| Python 版本 | `uv sync` 自动准备 **3.13.15**（系统 Python 3.12.0 不满足 `>=3.13,<3.14`） |
| `ruff check` | `All checks passed!` |
| `ruff format --check` | `283 files already formatted` |
| `mypy` | `Success: no issues found in 164 source files` |
| 默认回归 | `386 passed, 82 skipped, 2 failed in 52.96s` |

### 失败项说明（如实记录，未粉饰）

默认回归的 2 个失败均在 `tests/contract/test_execution_network.py`，根因相同——都需要访问被 `.gitignore` 排除的 `framework/harbor`（固定 Harbor 上游源码，只存在于组长机器）：

- `test_bootstrap_imports_fixed_harbor_not_the_adjacent_adapter_package`：目标 `framework/harbor/.venv/Scripts/python.exe` 不存在。
- `test_sidecar_exports_traceable_dns_adaptation_and_never_overwrites`：`git -C framework/harbor rev-parse HEAD` 返回 128。

这两项属**环境依赖失败，不是产品缺陷**，未做任何"为了让测试变绿"的修改。已记录为[问题记录 ISSUE-04](../../docs/LLY/04-issues/KNOWN_ISSUES.md)。

### 未验证 / 未做

- 前端依赖未安装（`apps/web` 无 `node_modules`），未做任何前端验证。
- MinIO 与 Docker 未配置，相关测试保持跳过。
- 未启用任何 `AGENTEXAM_RUN_*` 开关，因此真实 PostgreSQL 集成层（identity / membership / jobs / leaderboard 等）本轮**未执行**；本轮只验证了专属库可连与 schema 正确。
- 团队共享库未连接（ISSUE-01 未决）。
- 未提交、未推送 Git。

### `.env` 结论

**本轮便携 PostgreSQL 与普通后端开发不需要 `.env`，也不应向管理员索取其私有文件。** 依据：`apps/backend/pyproject.toml` 无 dotenv 依赖，源码中无 `load_dotenv`，应用配置来自进程环境变量。2026-09-19 同步后，owner 的部署生命周期改为读取 Git 忽略的 `infra/.env`；若本机以后运行这条部署链，应从公开 `infra/.env.example` 创建自己的文件并私下填值。使用共享库时应获取最小必要的连接信息，而不是复制他人的 `.env`。

### 偏差

- 原计划用 `initdb -W` 设置密码、测试库用密码认证；实际改为**仅回环 + 信任认证**，理由是只监听 `127.0.0.1`、且可完全避免创建与保管数据库密码。风险是任何本机进程都能以超级用户连入该开发库——仅限本机开发库，不适用于共享或长期环境。
- 原计划 `python -m venv` + `pip install -e .`；实际改用 `uv sync`，因为仓库自带 `uv.lock` 且需要 Python 3.13（uv 能自动准备）。
