# 阶段 0 本地开发环境实施计划

> **给执行者：** 实施时必须使用 `executing-plans` 工作流程，按任务逐项执行；除非用户明确要求委派，否则不使用子代理。每个步骤使用复选框记录真实状态。

**目标（Goal）：** 在 `D:\agent-exam` 建立一套不依赖 Tailscale、共享管理员、Docker 或真实模型的本机后端开发环境，并用隔离的测试库与开发库取得可复查的验证证据。

**结构（Architecture）：** 使用 `D:\pgsql` 中现有 PostgreSQL 15 便携版，只绑定 `127.0.0.1:55432`。`agentexam_identity_test` 作为自动化测试控制库并允许创建随机临时库；`agentexam_dev` 作为日常开发库并安装项目完整 11 表数据库结构（schema）。后端依赖继续使用 `apps/backend/.venv`，数据库地址只注入当前 PowerShell 进程。

**技术工具（Tech Stack）：** Windows PowerShell、PostgreSQL 15.14、Python 3.13、uv、pytest、Ruff、mypy、psycopg 3.3.5。

文中 `Task` 表示可独立验收的任务，`Step` 表示一次具体操作；`Files` 列出涉及的路径，`Interfaces` 说明前后任务怎样交接，`Consumes`/`Produces` 分别表示输入/输出，`Expected` 表示必须检查的预期结果。命令行入口（CLI）指在 PowerShell 中执行的项目命令，不是新的业务接口。

## 全局约束（Global Constraints）

- 本阶段是开发前提工作，不修改产品代码、业务规则、Interface、schema SQL 或架构边界。
- 不连接团队共享 PostgreSQL，不使用共享 `agentexam_admin`，不修复或依赖 Tailscale。
- PostgreSQL 只监听 `127.0.0.1:55432`；回环 `trust` 认证只允许用于这台单人开发机。
- 已存在 `D:\pgsql\data\PG_VERSION` 时严禁再次运行 `initdb`。
- 测试库固定为用户/库 `agentexam_identity_test`，角色必须有 `CREATEDB`；开发库固定为用户/库 `agentexam_dev`，角色不得有超级用户、建库或建角色权限。
- 完整 schema 只通过仓库已有 `agentexam-owner init-db` 建立，不手写、不复制 SQL、不对非空库强制重建。
- 日常开发不创建或读取 owner 的 `infra/.env`；连接串只进入当前 PowerShell 进程，不写入 Git。
- 不启动 Docker、MinIO、Harbor、SWE-Bench-Fork、Worker、Web、完整 FastAPI 运行时或真实模型。
- 不自动提交或推送 Git；实施结果写回本计划、[本地环境记录](../02-environment/LOCAL_SETUP.md)和[进度日志](../03-progress/PROGRESS_LOG.md)。

---

### Task 1: 固定现场并保护已有数据目录

**Files:**

- Modify after execution: `docs/LLY/01-plan/STAGE0_LOCAL_DEVELOPMENT_PLAN.md`
- Modify after execution: `docs/LLY/02-environment/LOCAL_SETUP.md`
- Modify after execution: `docs/LLY/03-progress/PROGRESS_LOG.md`
- Modify after execution: `docs/actions/2026-09-19-stage0-local-development-plan.md`

**Interfaces:**

- Consumes: 本机 `D:\pgsql`、当前 Git 工作区和已有 `.venv`。
- Produces: 不含秘密的执行前快照；后续任务据此判断“恢复”还是“首次创建”。

- [x] **Step 1: 记录 Git 与本机路径状态**

  ```powershell
  Set-Location D:\agent-exam
  git status --short --branch
  git rev-parse HEAD
  Test-Path D:\pgsql\bin\pg_ctl.exe
  Test-Path D:\pgsql\bin\psql.exe
  Test-Path D:\pgsql\data\PG_VERSION
  Test-Path D:\agent-exam\apps\backend\.venv\Scripts\python.exe
  ```

  Expected: 当前分支仍为 `lly/dev`；三个 PostgreSQL 路径和虚拟环境 Python 均为 `True`。任何路径为 `False` 时停止，不用新下载或 `initdb` 掩盖缺失。

- [x] **Step 2: 确认数据目录版本，不修改目录**

  ```powershell
  Get-Content D:\pgsql\data\PG_VERSION
  ```

  Expected: 输出 `15`。其他版本或无法读取时停止，先记录实际结果和兼容性风险。

- [x] **Step 3: 记录当前进程和就绪状态**

  ```powershell
  Get-Process postgres -ErrorAction SilentlyContinue |
    Select-Object Id, ProcessName, Path
  & D:\pgsql\bin\pg_ctl.exe -D D:\pgsql\data status
  & D:\pgsql\bin\pg_isready.exe -h 127.0.0.1 -p 55432
  ```

  Expected at the 2026-09-19 starting point: PostgreSQL 未运行，`pg_isready` 报 `no response`。如果已经运行，不重复启动，直接进入 Task 2 的监听检查。

- [x] **Step 4: 把实际输出写入行动记录**

  只记录版本、路径存在性、运行/停止状态和提交号；不复制数据库文件、连接秘密或无关进程列表。

### Task 2: 按需启动 PostgreSQL 并验证只监听回环

**Files:**

- Read: `D:\pgsql\data\postgresql.conf`
- Read: `D:\pgsql\data\pg_hba.conf`
- Modify after execution: `docs/LLY/02-environment/LOCAL_SETUP.md`

**Interfaces:**

- Consumes: Task 1 确认过的 PostgreSQL 15 数据目录。
- Produces: 可连接且只暴露在本机回环地址的 `127.0.0.1:55432` 服务。

- [x] **Step 1: 仅在未运行时启动**

  ```powershell
  & D:\pgsql\bin\pg_ctl.exe `
    -D D:\pgsql\data `
    -l D:\pgsql\data\pg_ctl-start.log `
    -o "-p 55432 -c listen_addresses=127.0.0.1" `
    start
  ```

  Expected: 输出 `server started`。如果 `pg_ctl status` 已显示 running，则跳过本步并记录“已运行，未重复启动”。

- [x] **Step 2: 检查就绪与服务端实际设置**

  ```powershell
  & D:\pgsql\bin\pg_isready.exe -h 127.0.0.1 -p 55432
  & D:\pgsql\bin\psql.exe `
    -h 127.0.0.1 -p 55432 -U postgres -d postgres `
    -v ON_ERROR_STOP=1 `
    -Atc "SHOW server_version; SHOW listen_addresses; SHOW port;"
  ```

  Expected: `accepting connections`；版本为 `15.x`；`listen_addresses` 为 `127.0.0.1`；端口为 `55432`。

- [x] **Step 3: 检查 Windows 监听地址**

  ```powershell
  Get-NetTCPConnection -State Listen -LocalPort 55432 |
    Select-Object LocalAddress, LocalPort, OwningProcess
  ```

  Expected: 只出现 `127.0.0.1:55432`。若出现 `0.0.0.0`、局域网地址或非预期 IPv6 地址，立即停止数据库并修正启动参数，不继续建库。

- [x] **Step 4: 检查认证规则没有远程网段**

  ```powershell
  Get-Content D:\pgsql\data\pg_hba.conf |
    Select-String -Pattern '^(host|local)'
  ```

  Expected: `trust` 只覆盖本机 local、`127.0.0.1/32` 和 `::1/128`；不得有 `0.0.0.0/0`、局域网网段或 Tailscale 网段。

### Task 3: 建立测试库与开发库的角色隔离

**Files:**

- Modify: PostgreSQL 本机系统目录（只创建/校正明确命名的角色和数据库）。
- Modify after execution: `docs/LLY/02-environment/LOCAL_SETUP.md`

**Interfaces:**

- Consumes: `postgres` 本机维护连接，仅用于本任务。
- Produces: 测试控制库 `agentexam_identity_test` 和开发库 `agentexam_dev`。

- [x] **Step 1: 查询现有角色和数据库，不先修改**

  ```powershell
  & D:\pgsql\bin\psql.exe `
    -h 127.0.0.1 -p 55432 -U postgres -d postgres `
    -v ON_ERROR_STOP=1 `
    -c "SELECT rolname, rolcreatedb, rolsuper, rolcreaterole FROM pg_roles WHERE rolname IN ('agentexam_identity_test', 'agentexam_dev') ORDER BY rolname;"

  & D:\pgsql\bin\psql.exe `
    -h 127.0.0.1 -p 55432 -U postgres -d postgres `
    -v ON_ERROR_STOP=1 `
    -c "SELECT d.datname, r.rolname AS owner FROM pg_database d JOIN pg_roles r ON r.oid=d.datdba WHERE d.datname IN ('agentexam_identity_test', 'agentexam_dev') ORDER BY d.datname;"
  ```

  Expected: 可能只有既有 `agentexam_identity_test`，也可能两者均存在。记录实际结果；出现同名但非预期用途的数据时停止，不删除。

- [x] **Step 2: 创建或收紧两个角色**

  ```powershell
  $stage0Psql = 'D:\pgsql\bin\psql.exe'

  $stage0TestRole = & $stage0Psql -h 127.0.0.1 -p 55432 -U postgres -d postgres -Atc `
    "SELECT 1 FROM pg_roles WHERE rolname='agentexam_identity_test'"
  if (-not $stage0TestRole) {
    & $stage0Psql -h 127.0.0.1 -p 55432 -U postgres -d postgres `
      -v ON_ERROR_STOP=1 -c "CREATE ROLE agentexam_identity_test LOGIN CREATEDB NOSUPERUSER NOCREATEROLE NOREPLICATION"
  } else {
    & $stage0Psql -h 127.0.0.1 -p 55432 -U postgres -d postgres `
      -v ON_ERROR_STOP=1 -c "ALTER ROLE agentexam_identity_test LOGIN CREATEDB NOSUPERUSER NOCREATEROLE NOREPLICATION"
  }

  $stage0DevRole = & $stage0Psql -h 127.0.0.1 -p 55432 -U postgres -d postgres -Atc `
    "SELECT 1 FROM pg_roles WHERE rolname='agentexam_dev'"
  if (-not $stage0DevRole) {
    & $stage0Psql -h 127.0.0.1 -p 55432 -U postgres -d postgres `
      -v ON_ERROR_STOP=1 -c "CREATE ROLE agentexam_dev LOGIN NOCREATEDB NOSUPERUSER NOCREATEROLE NOREPLICATION"
  } else {
    & $stage0Psql -h 127.0.0.1 -p 55432 -U postgres -d postgres `
      -v ON_ERROR_STOP=1 -c "ALTER ROLE agentexam_dev LOGIN NOCREATEDB NOSUPERUSER NOCREATEROLE NOREPLICATION"
  }
  ```

  Expected: 命令退出码为 0；测试角色 `rolcreatedb=true`，开发角色 `rolcreatedb=false`，两者 `rolsuper=false`、`rolcreaterole=false`。

- [x] **Step 3: 只创建缺失的同名数据库**

  ```powershell
  $stage0Psql = 'D:\pgsql\bin\psql.exe'
  $stage0Createdb = 'D:\pgsql\bin\createdb.exe'

  $stage0TestDb = & $stage0Psql -h 127.0.0.1 -p 55432 -U postgres -d postgres -Atc `
    "SELECT 1 FROM pg_database WHERE datname='agentexam_identity_test'"
  if (-not $stage0TestDb) {
    & $stage0Createdb -h 127.0.0.1 -p 55432 -U postgres `
      -O agentexam_identity_test -E UTF8 agentexam_identity_test
  }

  $stage0DevDb = & $stage0Psql -h 127.0.0.1 -p 55432 -U postgres -d postgres -Atc `
    "SELECT 1 FROM pg_database WHERE datname='agentexam_dev'"
  if (-not $stage0DevDb) {
    & $stage0Createdb -h 127.0.0.1 -p 55432 -U postgres `
      -O agentexam_dev -E UTF8 agentexam_dev
  }
  ```

  Expected: 两个数据库均存在；已有数据库不会被删除或重建。

- [x] **Step 4: 验证所有者和最小权限**

  ```powershell
  & D:\pgsql\bin\psql.exe `
    -h 127.0.0.1 -p 55432 -U postgres -d postgres `
    -v ON_ERROR_STOP=1 `
    -c "SELECT d.datname, r.rolname AS owner, r.rolcreatedb, r.rolsuper, r.rolcreaterole FROM pg_database d JOIN pg_roles r ON r.oid=d.datdba WHERE d.datname IN ('agentexam_identity_test', 'agentexam_dev') ORDER BY d.datname;"
  ```

  Expected: `agentexam_identity_test` 由同名角色拥有且仅它有 `CREATEDB`；`agentexam_dev` 由同名角色拥有且没有管理权限。若 owner 不匹配，停止并记录，不自动 `ALTER DATABASE` 覆盖未知现场。

### Task 4: 在开发库安装完整项目 schema

**Files:**

- Reuse: `apps/backend/src/eval_platform/delivery/owner.py`
- Reuse: `apps/backend/src/eval_platform/adapters/persistence/bootstrap.py`
- Reuse: `apps/backend/src/eval_platform/adapters/persistence/**/*.sql`
- Modify: 本机数据库 `agentexam_dev`（首次建立当前 11 张表）。

**Interfaces:**

- Consumes: 空白 `agentexam_dev` 与现有 `agentexam-owner init-db`。
- Produces: 可供日常开发使用的完整 schema；不创建账号、任务、Job 或文件。

- [x] **Step 1: 先确认开发库是否为空**

  ```powershell
  $stage0DevDsn = 'postgresql://agentexam_dev@127.0.0.1:55432/agentexam_dev'
  & D:\pgsql\bin\psql.exe -v ON_ERROR_STOP=1 -Atc "SELECT count(*) FROM pg_tables WHERE schemaname='public';" $stage0DevDsn
  ```

  Expected on first creation: `0`。如果非 0，不运行初始化；先列出对象并判断是否已经是完整 schema。

- [x] **Step 2: 仅对空白开发库运行项目初始化入口**

  ```powershell
  Set-Location D:\agent-exam\apps\backend
  $env:AGENTEXAM_DATABASE_URL = $stage0DevDsn
  & .\.venv\Scripts\agentexam-owner.exe init-db
  ```

  Expected: 输出“平台全部表已建立；未创建账号、任务、Job 或文件。”且退出码为 0。若报告非空或失败，不删除对象、不重试覆盖。

- [x] **Step 3: 核对精确 11 表**

  ```powershell
  & D:\pgsql\bin\psql.exe -v ON_ERROR_STOP=1 -Atc "SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename;" $stage0DevDsn
  ```

  Expected set:

  ```text
  accounts
  agent_configurations
  artifact_records
  deterministic_results
  evaluation_jobs
  evaluation_runs
  evaluation_tasks
  invitations
  job_state_events
  run_state_events
  sessions
  ```

- [x] **Step 4: 验证应用角色能连接且不能建库**

  ```powershell
  & D:\pgsql\bin\psql.exe -v ON_ERROR_STOP=1 -Atc "SELECT current_user, current_database();" $stage0DevDsn
  & D:\pgsql\bin\psql.exe `
    -h 127.0.0.1 -p 55432 -U postgres -d postgres `
    -Atc "SELECT rolcreatedb FROM pg_roles WHERE rolname='agentexam_dev';"
  ```

  Expected: `agentexam_dev|agentexam_dev` 与 `f`。

### Task 5: 固定 Python 3.13 工具链和锁定依赖

**Files:**

- Reuse: `apps/backend/pyproject.toml`
- Reuse: `apps/backend/uv.lock`
- Modify: ignored local directory `apps/backend/.venv/` only if dependency synchronization is required.

**Interfaces:**

- Consumes: 本机 uv `C:\Users\liliy\.local\bin\uv.exe` 与仓库锁文件。
- Produces: Python 3.13 后端开发/测试命令环境。

- [x] **Step 1: 同步锁定依赖**

  ```powershell
  Set-Location D:\agent-exam\apps\backend
  & C:\Users\liliy\.local\bin\uv.exe sync --locked
  ```

  Expected: 命令退出码 0；不修改 `pyproject.toml` 或 `uv.lock`。若 uv 路径变化，先用 `Get-Command uv -All` 或只读文件搜索定位，不重新安装不同版本掩盖问题。

- [x] **Step 2: 验证 Python 主版本**

  ```powershell
  & .\.venv\Scripts\python.exe --version
  ```

  Expected: `Python 3.13.x`。

- [x] **Step 3: 运行静态检查**

  ```powershell
  & .\.venv\Scripts\python.exe -m ruff check src tests prototype_codex_harbor_e2e.py
  & .\.venv\Scripts\python.exe -m ruff format --check src tests prototype_codex_harbor_e2e.py
  & .\.venv\Scripts\python.exe -m mypy src prototype_codex_harbor_e2e.py
  ```

  Expected: 三条命令均退出码 0。记录 Ruff、格式检查和 mypy 的完整摘要；任何失败都如实保留，不通过自动格式化或改产品代码扩大阶段 0。

### Task 6: 设置进程级变量并运行 PostgreSQL 集成测试

**Files:**

- Reuse: `apps/backend/tests/identity/conftest.py`
- Reuse: `apps/backend/tests/leaderboard/postgres_support.py`
- Modify: 测试创建的随机临时数据库；测试结束后必须精确删除。

**Interfaces:**

- Consumes: `agentexam_identity_test` 控制库。
- Produces: 身份、成员、目录、Job 和排行榜 PostgreSQL Adapter 的本机测试证据。

- [x] **Step 1: 只在当前 PowerShell 设置测试变量**

  ```powershell
  Set-Location D:\agent-exam\apps\backend
  $env:AGENTEXAM_TEST_DATABASE_URL = 'postgresql://agentexam_identity_test@127.0.0.1:55432/agentexam_identity_test'
  $env:AGENTEXAM_RUN_IDENTITY_POSTGRES = '1'
  $env:AGENTEXAM_RUN_LEADERBOARD_POSTGRES = '1'
  ```

  Expected: 不创建 `.env`，不设置用户级或系统级环境变量。

- [x] **Step 2: 运行数据库相关测试层**

  ```powershell
  & .\.venv\Scripts\python.exe -m pytest `
    tests\identity `
    tests\membership `
    tests\catalog `
    tests\jobs `
    tests\leaderboard `
    -q -p no:cacheprovider
  ```

  Expected: 命令退出码 0，`failed=0`、`errors=0`；未显式开启的 MinIO 或真实外部依赖用例允许显示为 skipped。实际 passed/skipped 数必须现场记录，不能沿用历史数字。

- [x] **Step 3: 检查没有残留测试数据库**

  ```powershell
  & D:\pgsql\bin\psql.exe `
    -h 127.0.0.1 -p 55432 -U postgres -d postgres `
    -v ON_ERROR_STOP=1 `
    -Atc "SELECT datname FROM pg_database WHERE datname ~ '^(identity|leaderboard)_[0-9a-f]{32}$' ORDER BY datname;"
  ```

  Expected: 无输出。若有残留，先确认没有测试进程占用，再只处理与本轮记录完全匹配的随机库；不得用通配式删除未知数据库。

- [x] **Step 4: 清理当前会话的测试开关**

  ```powershell
  Remove-Item Env:\AGENTEXAM_RUN_IDENTITY_POSTGRES -ErrorAction SilentlyContinue
  Remove-Item Env:\AGENTEXAM_RUN_LEADERBOARD_POSTGRES -ErrorAction SilentlyContinue
  Remove-Item Env:\AGENTEXAM_TEST_DATABASE_URL -ErrorAction SilentlyContinue
  ```

  Expected: 三个测试变量不再存在；开发库变量可留到当前开发会话结束。

### Task 7: 运行默认回归并区分环境缺口

**Files:**

- Read: `apps/backend/tests/contract/test_execution_network.py`
- Modify after execution: `docs/LLY/04-issues/KNOWN_ISSUES.md` only if the observed failure set changes.

**Interfaces:**

- Consumes: Python 工具链；不启用任何 `AGENTEXAM_RUN_*` 外部依赖开关。
- Produces: 当前提交在本机的完整默认回归基线。

- [x] **Step 1: 确认外部依赖开关已关闭**

  ```powershell
  Get-ChildItem Env:AGENTEXAM_RUN_* -ErrorAction SilentlyContinue
  ```

  Expected: 无输出。若有变量，逐项删除后再运行默认回归。

- [x] **Step 2: 运行默认回归，不隐藏已知失败**

  ```powershell
  Set-Location D:\agent-exam\apps\backend
  & .\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider
  ```

  Expected: 记录完整 passed/skipped/failed 数。历史基线是因本机缺少被 Git 忽略的 `framework/harbor` 而出现 2 个契约测试失败；本轮必须按实际输出重新判断，不能预先写成通过。

- [x] **Step 3: 对每个失败做归因核对**

  如果仍只有以下两项失败，记录为既有环境依赖，不修改测试：

  ```text
  tests/contract/test_execution_network.py::test_bootstrap_imports_fixed_harbor_not_the_adjacent_adapter_package
  tests/contract/test_execution_network.py::test_sidecar_exports_traceable_dns_adaptation_and_never_overwrites
  ```

  Expected cause: `framework/harbor/.venv/Scripts/python.exe` 或固定 Harbor Git 目录不存在。任何新增失败、不同异常或数据库失败都视为阶段 0 未完成，先诊断，不归入 ISSUE-04。

### Task 8: 验证开发库可重复连接与手动启停恢复

**Files:**

- Modify after execution: `docs/LLY/02-environment/LOCAL_SETUP.md`
- Modify after execution: `docs/LLY/03-progress/PROGRESS_LOG.md`

**Interfaces:**

- Consumes: 已初始化的 `agentexam_dev`。
- Produces: 不依赖开机自启的可重复恢复流程。

- [x] **Step 1: 记录停止前开发库摘要**

  ```powershell
  $stage0DevDsn = 'postgresql://agentexam_dev@127.0.0.1:55432/agentexam_dev'
  & D:\pgsql\bin\psql.exe -v ON_ERROR_STOP=1 -Atc "SELECT current_database(), current_user, count(*) FROM pg_tables WHERE schemaname='public';" $stage0DevDsn
  ```

  Expected: `agentexam_dev|agentexam_dev|11`。

- [x] **Step 2: 正常停止数据库**

  ```powershell
  & D:\pgsql\bin\pg_ctl.exe -D D:\pgsql\data stop -m fast
  & D:\pgsql\bin\pg_isready.exe -h 127.0.0.1 -p 55432
  ```

  Expected: 正常停止；随后 `pg_isready` 返回 `no response`。不删除 `D:\pgsql\data`。

- [x] **Step 3: 使用固定命令重新启动并读回 schema**

  ```powershell
  & D:\pgsql\bin\pg_ctl.exe `
    -D D:\pgsql\data `
    -l D:\pgsql\data\pg_ctl-start.log `
    -o "-p 55432 -c listen_addresses=127.0.0.1" `
    start
  & D:\pgsql\bin\pg_isready.exe -h 127.0.0.1 -p 55432
  & D:\pgsql\bin\psql.exe -v ON_ERROR_STOP=1 -Atc "SELECT count(*) FROM pg_tables WHERE schemaname='public';" $stage0DevDsn
  ```

  Expected: 服务恢复为 accepting connections，表数仍为 `11`。

- [x] **Step 4: 决定本次会话结束状态并记录**

  若后续立即开发，数据库保持运行；否则执行正常停止命令。无论哪种选择，都在进度日志中记录最终实际状态，不安装 Windows 服务或开机启动。

### Task 9: 收尾文档与阶段门禁

**Files:**

- Modify: `docs/LLY/01-plan/STAGE0_LOCAL_DEVELOPMENT_PLAN.md`
- Modify: `docs/LLY/02-environment/LOCAL_SETUP.md`
- Modify: `docs/LLY/03-progress/PROGRESS_LOG.md`
- Modify: `docs/LLY/04-issues/KNOWN_ISSUES.md` only when facts changed.
- Modify: `docs/actions/2026-09-19-stage0-local-development-plan.md`

**Interfaces:**

- Consumes: Tasks 1–8 的实际命令输出。
- Produces: 可复查的阶段 0 完成/阻塞结论；不自动进入任务 05。

- [x] **Step 1: 更新每个任务复选框和实际结果**

  只勾选真正执行且检查过输出的步骤；失败、跳过和未运行保持未勾选并写原因。

- [x] **Step 2: 核对阶段 0 七项完成标准**

  逐项对照[阶段 0 设计](./STAGE0_LOCAL_DEVELOPMENT_DESIGN.md#5-完成标准)。任一项缺证据时，阶段状态保持“进行中”或“阻塞”，不能写“完成”。

- [x] **Step 3: 检查文档一致性和 Git 范围**

  ```powershell
  Set-Location D:\agent-exam
  git status --short --branch
  git diff --check
  rg -n "阶段 0|agentexam_dev|agentexam_identity_test" docs\LLY docs\actions\2026-09-19-stage0-local-development-plan.md
  ```

  Expected: 只有本任务明确记录的本地文档变化；无产品代码、schema、配置模板或 Interface 改动；`git diff --check` 无错误。

- [x] **Step 4: 停在阶段 0 完成点**

  阶段 0 完成后只汇报结果并等待新任务。扩展任务 01–08 仍未发布时，不自动开始 E 模块任务 05，不下载 `framework/`，不启动模型或付费调用。
