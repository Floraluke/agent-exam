# 阶段 0 本地开发环境实施计划

## 状态与情况

- 状态：已完成（执行记录）
- 来源请求：用户确认当前处于阶段 0，要求按建议整理该阶段全部实施步骤并落盘；阶段 0 是项目开发的前提工作，不改变产品业务目标。
- 后续请求：阶段 0 按计划执行并形成下方证据；用户在本次收尾中明确要求审查该执行记录，无问题后提交并推送。
- 执行前事实：本机已存在 PostgreSQL 15 便携版、数据目录 `D:\pgsql\data`、后端 `.venv` 和既有测试库记录；2026-09-19 首次检查时 `127.0.0.1:55432` 无响应。Tailscale 启动失败，因此本机不使用共享管理员数据库。
- 执行结束事实：阶段 0 已实施完成；2026-09-19 收尾时 PostgreSQL 15.14 运行于 `127.0.0.1:55432`，`agentexam_dev` 由同名最小权限角色拥有并含 11 张表，自动化测试继续使用独立的 `agentexam_identity_test`。实时运行状态由[本地环境记录](../LLY/02-environment/LOCAL_SETUP.md)唯一维护。
- 已确认决定：采用两库隔离——`agentexam_identity_test` 只供自动化 PostgreSQL 测试，`agentexam_dev` 只供日常开发和手工调试；PostgreSQL 仅监听回环地址，日常后端开发使用进程环境变量，不使用共享账号或复制 owner 的 `.env`。
- 明确排除：不修改产品代码、Interface、schema 定义或业务规则；不安装/运行 Docker、MinIO、Harbor、固定 Fork、Worker、Web 或真实模型；不修复 Tailscale；不连接、读取或修改团队共享数据库。计划与执行阶段不自动提交或推送 Git；2026-09-19 用户随后明确授权审查通过后提交并推送本批文档。
- 已知限制：完整运行时 `create_runtime_app()` 还要求 MinIO 配置，因此阶段 0 只验证后端工具链、PostgreSQL Adapter/用例和数据库 schema，不声称完整平台可启动。

## 实施措施

1. 写明阶段 0 的设计边界、两库职责、数据流和停止条件。
2. 把实施拆成可逐项执行的任务：现场保护、数据库启动与网络检查、角色/数据库隔离、开发库 schema、Python 工具链、会话变量、数据库测试、基线回归、启停恢复和收尾。
3. 在 E 模块总计划中记录阶段 0 从进行中到完成的实际状态，并链接详细计划；同步本地环境事实，避免把历史快照误写成当前状态。
4. 先对计划做占位符、路径、命令、链接、范围和成功标准自检，再按 9 个任务执行有状态步骤并持续记录实际结果。

完成标准：计划覆盖从执行前“已安装但未运行”的现场到阶段 0 验收完成的全部步骤；每项有精确目标、命令、预期结果、失败停止条件和记录位置；文档之间状态一致。

## 受影响文件树

```text
docs/
  actions/
    2026-09-18-lly-local-dev-environment.md        # 新增：初始本机环境搭建与历史验证记录
    2026-09-19-sync-workspace-and-next-step.md     # 新增：同步远端 main 与恢复任务边界的记录
    2026-09-19-stage0-local-development-plan.md   # 新增：两库设计、实际执行、偏差和最终证据
  LLY/
    README.md                                     # 新增：LLY 文档分类、权威边界和当前状态入口
    01-plan/
      PLAN.md                                     # 新增：E 模块总计划、阶段状态与详细计划入口
      STAGE0_LOCAL_DEVELOPMENT_DESIGN.md          # 新增：已确认的两库隔离设计与范围
      STAGE0_LOCAL_DEVELOPMENT_PLAN.md            # 新增：阶段 0 的 9 项任务、34 步及勾选结果
    02-environment/
      LOCAL_SETUP.md                              # 新增：本机环境事实、复现命令和两轮验证摘要
    03-progress/
      PROGRESS_LOG.md                             # 新增：阶段进展、测试结果和当前停点
    04-issues/
      KNOWN_ISSUES.md                             # 新增：Tailscale、缺失 framework 等本机限制
```

这些文件只描述本机前提环境，不参与产品设计模式，也不新增业务 Module、Interface、数据库表或源码目录。PostgreSQL 是本地测试依赖；项目 schema 仍唯一来自现有 `initialize_empty_database()`。

## 自验证方式

1. 核对详细计划包含阶段 0 的范围、两库职责、逐步命令、预期结果、停止条件和最终验收。
2. 检查计划只调用仓库已有入口和本机已确认路径，不虚构 CLI；数据库初始化必须复用 `agentexam-owner init-db`。
3. 检查计划不要求 Tailscale、共享账号、Docker、MinIO、Harbor、Worker 或真实模型。
4. 检查新增/修改 Markdown 的相对链接全部存在、无行尾空白、无未决占位符。
5. 检查 Git 状态，确认未意外修改产品代码或远端同步带入的文件。

## 自验证结果

- 设计覆盖：已固定阶段 0 的目标、明确排除项、两库职责、进程环境变量数据流、失败保护和七项完成标准；与用户确认的“本地独立数据库、不使用共享管理员”一致。
- 计划覆盖：详细计划共 9 个任务、34 个可勾选步骤，覆盖现场保护、启动与回环检查、两库角色/权限、开发库 11 表 schema、Python 工具链、PostgreSQL 集成测试、默认回归、启停恢复和文档收尾。每项包含具体命令、预期结果与停止条件。
- 现有接口核对：`agentexam-owner.exe`、Python 虚拟环境、uv、`pg_ctl`、`pg_isready`、`psql`、`createdb`、`PG_VERSION` 及对应源码入口均实际存在；计划未虚构 CLI。当前 schema SQL 静态提取恰为 11 张表，与计划清单逐项一致。
- 静态命令检查：从实施计划提取 28 个 PowerShell 代码块，全部通过 PowerShell AST 语法解析，错误数为 0。这里只验证语法，没有执行代码块中的启动、建库、改角色或测试操作。
- 文档检查：6 份新增/修改 Markdown 的相对文件链接全部存在；未发现未决占位符或行尾空白。计划执行前阶段总计划、本地环境事实和进度日志已同步为“阶段 0 进行中”，完成后再更新为已完成。
- 范围检查：`git status` 只显示既有和本次本地文档目录；`git diff --name-only -- apps infra` 无输出，没有修改产品源码、schema、基础设施配置或测试。
- 计划编写阶段未执行：PostgreSQL 当时未启动；未查询或创建 `agentexam_dev`，未修改任何角色/数据库，未运行阶段 0 测试，未连接共享库，未使用 Docker/MinIO/Worker/模型，未提交或推送 Git。实际执行结果从此处继续追加。

### 执行结果：Task 1 固定现场

- `git rev-parse HEAD`：`6dfa2bee285e71e073b0286370b7e24257b367ad`；分支为 `lly/dev`。
- `D:\pgsql\bin\pg_ctl.exe`、`psql.exe`、`pg_isready.exe`、`D:\pgsql\data\PG_VERSION` 和后端 `.venv\Scripts\python.exe` 均存在。
- `D:\pgsql\data\PG_VERSION` 输出 `15`。
- `pg_ctl status` 输出 `no server running`，退出码 3；`pg_isready -h 127.0.0.1 -p 55432` 输出 `no response`，退出码 2。
- 未运行 `initdb`，未修改数据目录；Task 1 四步完成，进入 Task 2。

### 执行结果：Task 2 PostgreSQL 启动与回环验证

- 首次启动命令使用既有 `server.log` 时，`pg_ctl` 等待超过 30 秒；随后只读检查确认服务器已运行并完成自动恢复。日志显示旧日志文件发生 Windows sharing violation，数据库仍在约 35 秒后完成 WAL recovery 并进入 ready 状态。
- 当前 `pg_isready -h 127.0.0.1 -p 55432` 返回 `accepting connections`。
- 服务端查询返回：PostgreSQL `15.14`、`listen_addresses=127.0.0.1`、`port=55432`。
- `Get-NetTCPConnection` 只发现 `127.0.0.1:55432`，没有 `0.0.0.0`、局域网或 Tailscale 地址。
- `pg_hba.conf` 只包含 local、`127.0.0.1/32` 和 `::1/128` 的 `trust` 规则；未发现远程网段。
- 已调整计划：后续 `pg_ctl` 启动日志使用独立的 `D:\pgsql\data\pg_ctl-start.log`，避免与 PostgreSQL 自身日志文件竞争句柄。Task 2 四步完成，进入 Task 3。

### 执行结果：Task 3 两库角色隔离

- 只读核对确认既有 `agentexam_identity_test` 角色/数据库存在，角色为 `CREATEDB=true`、`SUPERUSER=false`、`CREATEROLE=false`，数据库 owner 为同名角色。
- 按计划校正测试角色属性；未删除或重建测试库。
- 创建缺失的 `agentexam_dev` 角色和同名数据库；最终开发角色为 `CREATEDB=false`、`SUPERUSER=false`、`CREATEROLE=false`，数据库 owner 为 `agentexam_dev`。
- 两个数据库均在 `127.0.0.1:55432` 的本机 PostgreSQL 中，Task 3 四步完成，进入 Task 4。

### 执行结果：Task 4 开发库 schema

- 首次按计划检查 `agentexam_dev` 的 public 表数为 `0`。第一次尝试暴露了计划命令顺序错误：`psql` 连接串放在选项前会把后续选项当作 extra arguments；该命令只输出 warning，没有执行查询，也没有改库。
- 已修正计划，把选项放在连接串前，并用修正命令重新检查确认表数为 `0`。
- 设置当前子进程 `AGENTEXAM_DATABASE_URL=postgresql://agentexam_dev@127.0.0.1:55432/agentexam_dev`，执行现有 `agentexam-owner.exe init-db` 成功，输出“平台全部表已建立；未创建账号、任务、Job 或文件。”
- 读回 `agentexam_dev` 得到精确 11 张表：`accounts`、`agent_configurations`、`artifact_records`、`deterministic_results`、`evaluation_jobs`、`evaluation_runs`、`evaluation_tasks`、`invitations`、`job_state_events`、`run_state_events`、`sessions`。
- `current_user/current_database` 为 `agentexam_dev/agentexam_dev`，角色 `rolcreatedb=false`。Task 4 四步完成，进入 Task 5。

### 执行结果：Task 5 Python 工具链

- `C:\Users\liliy\.local\bin\uv.exe sync --locked` 成功：`Resolved 42 packages`、`Checked 42 packages`；未修改 `pyproject.toml` 或 `uv.lock`。
- `.venv\Scripts\python.exe --version`：`Python 3.13.15`。
- Ruff：`All checks passed!`。
- Ruff format：`283 files already formatted`。
- mypy：`Success: no issues found in 164 source files`。
- Task 5 三步完成，进入 Task 6。

### 执行结果：Task 6 PostgreSQL 集成测试

- 在单次测试子进程中设置 `AGENTEXAM_TEST_DATABASE_URL=postgresql://agentexam_identity_test@127.0.0.1:55432/agentexam_identity_test`、`AGENTEXAM_RUN_IDENTITY_POSTGRES=1` 和 `AGENTEXAM_RUN_LEADERBOARD_POSTGRES=1`；未创建 `.env` 或持久化环境变量。
- 执行身份、成员、目录、Job 和排行榜测试目录：**246 passed、11 skipped、2 warnings，96.86 秒**，退出码 0。
- 11 项跳过均为未开启的 MinIO 集成；2 项是 Starlette/httpx 弃用提示，没有失败或 error。
- 查询 `identity_<32 hex>` 与 `leaderboard_<32 hex>` 数据库无输出，临时库均已清理。
- Task 6 四步完成，进入 Task 7。

### 执行结果：Task 7 默认回归

- `Get-ChildItem Env:AGENTEXAM_RUN_*` 无输出，默认回归未开启外部依赖门禁。
- 执行 `python -m pytest -q -p no:cacheprovider`，实际结果：**386 passed、82 skipped、2 failed、2 warnings，47.55 秒**，退出码 1。
- 两个失败均为既有 `tests/contract/test_execution_network.py` 环境依赖：`framework/harbor/.venv/Scripts/python.exe` 不存在，以及 `framework/harbor` Git 目录不存在；与历史 ISSUE-04 的两个失败完全一致。
- 未修改测试、未恢复 `framework/harbor`，不把该环境缺口误判为产品失败。Task 7 三步完成，进入 Task 8。

### 执行结果：Task 8 启停恢复

- 停止前查询返回 `agentexam_dev|agentexam_dev|11`。
- `pg_ctl stop -m fast` 正常停止；停止后 `pg_isready` 返回 `no response`、退出码 2。
- 使用独立 `D:\pgsql\data\pg_ctl-start.log` 启动成功；`pg_isready` 返回 `accepting connections`。
- 重启后开发库表数仍为 `11`。本次后续还要继续使用本机环境，因此数据库保持运行；未安装 Windows 服务或开机自启。Task 8 四步完成，进入 Task 9。

### 执行结果：Task 9 收尾与阶段门禁

- 阶段 0 计划 9 个任务、34 个步骤均已完成并在计划中勾选；执行过程中发现并修正了 `psql` 连接串参数顺序和启动日志文件句柄两个技术细节。
- 最终数据库核对：PostgreSQL `15.14`、`listen_addresses=127.0.0.1`、`port=55432`；`agentexam_dev` 为 `agentexam_dev|agentexam_dev|11`；开发角色 `CREATEDB=false`、`SUPERUSER=false`、`CREATEROLE=false`；测试角色 `CREATEDB=true` 且非超级用户/建角色。
- 最终 Windows 监听只有 `127.0.0.1:55432`；未连接共享数据库，未启用 Tailscale、Docker、MinIO、Worker、Web 或模型。
- 6 份本地 Markdown 的相对链接、行尾空白和计划结构检查通过；计划共有 34 步，剩余未勾选数为 0。`git diff --name-only -- apps infra` 无输出，没有产品代码或基础设施 tracked changes。
- 阶段 0 门禁满足：本机开发环境已完成；默认回归的 2 个 `framework/harbor` 缺失失败保留为 ISSUE-04 环境限制，不阻塞本机数据库开发，也不被伪称为全绿。
- 后续停点：数据库保持运行；不自动进入扩展任务 05，等待用户/项目负责人明确发布下一项任务。

### 提交前复验与双轴审查

- 提交前重新核对实时数据库：`pg_isready` 为 `accepting connections`；PostgreSQL `15.14` 只监听 `127.0.0.1:55432`；`agentexam_dev|agentexam_dev|11`；开发角色无 `CREATEDB`/超级用户/建角色权限，测试角色只有 `CREATEDB`。
- 重新运行 PostgreSQL 相关目录：**246 passed、11 skipped、2 warnings，98.47 秒**，退出码 0；跳过项仍全部是未开启的 MinIO 集成。
- 重新运行默认回归：**386 passed、82 skipped、2 failed、2 warnings，46.35 秒**。失败仍精确为 ISSUE-04 记录的两个 `framework/harbor` 缺失项，没有新增失败。
- Standards/Spec 双轴审查发现并修正：README 与设计状态过期、日常启动命令仍引用会发生句柄冲突的 `server.log`、行动记录未区分执行前/当前事实、设计缺少文件树/替代方案/风险、初学者术语说明不足，以及暂存文件树未覆盖全部 10 份关联文档。
- 修正后静态复验：10 份 Markdown 相对文件链接全部可解析、无行尾空白、无疑似秘密赋值或带密码连接串；28 个 PowerShell 代码块均可解析；34 个计划步骤全部勾选；无产品代码或 `infra` tracked changes。

## 最终状态

- 状态：已完成。
- 本次提交批次包含上方列出的 10 份互相引用文档，没有产品代码或基础设施 tracked changes。用户已授权审查通过后提交并推送；具体提交号与远端分支由 Git 历史和最终回复记录。
