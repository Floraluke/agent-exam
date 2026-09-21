# 本地开发环境搭建记录

> 目标：在本机建立一套**不依赖 Tailscale、不依赖 Docker** 的后端开发环境，能写代码、跑静态检查和默认回归。（后端开发与测试仍不依赖 Docker；2026-09-21 起本机已安装 Docker Desktop，但仅拟用于任务 05 的容器与网络工作，见第 1 节变更记录与[任务 05 实施方案](../01-plan/STAGE1_IMPLEMENTATION_PLAN.md)。）
>
> 状态：**阶段 0 已完成**（2026-09-19）。基础安装、两库隔离、开发 schema、工具链、PostgreSQL 集成测试和启停读回均有本轮证据；默认回归仍保留 2 个因缺少 `framework/harbor` 的已知环境失败。
>
> **当前运行状态的唯一来源：** 2026-09-21 实测：PostgreSQL 当时**已停止**（`pg_isready` 返回 `no response`，便携版不注册服务，重启电脑后不会自启），已按第 2 节的既有命令手动启动，现为 `accepting connections`（`127.0.0.1:55432`）。数据库以后停止或重启时只更新本段，其他文档保留带日期的历史证据或指向这里。

## 1. 为什么是这样一套环境

| 决策 | 理由 |
|---|---|
| 用**便携版 PostgreSQL**（zip 解包），不用安装包 | 不需要管理员权限、不注册 Windows 服务、不改系统配置，删目录即卸载；测试本来就不需要"正式部署"的数据库 |
| 端口用 **55432**，不用 5432 | 项目的 PostgreSQL 测试夹具明确拒绝默认端口 5432（`apps/backend/tests/identity/conftest.py`），只接受非默认端口的专属隔离库 |
| 回环信任认证（`trust`，仅 127.0.0.1） | 只监听回环，只有本机进程能连；**因此不需要创建、保存或传递任何数据库密码**。这是开发库的取舍，不得用于任何共享或长期环境 |
| 阶段 0 期间不装 Docker | 当时本机 Docker Desktop 未运行；且 Docker 依赖虚拟网络，与本机现有的网络驱动问题叠加会放大风险。**2026-09-21 变更**：Docker Desktop 已安装（CLI 29.6.2，守护进程当前未运行），用于任务 05 的容器与网络工作；原风险点"能否创建自定义网络"**尚未验证**，见[任务 05 实施方案](../01-plan/STAGE1_IMPLEMENTATION_PLAN.md)第 1 节 |
| 用 `uv sync` 而不是 `pip install` | 仓库自带 `uv.lock`；且 `uv` 会自动准备项目要求的 Python 版本 |
| 日常后端开发不用 `.env` 文件 | 后端代码**不自动读取 `.env`**（无 dotenv 依赖、无加载逻辑），本机便携 PostgreSQL 开发继续使用进程环境变量。自 `6dfa2be` 起，只有 owner 的 `infra` 部署生命周期要求从 `infra/.env.example` 复制出 Git 忽略的 `infra/.env`；本机当前不运行该部署链，所以不创建该文件 |

## 2. 安装步骤（实际执行）

### 2.1 PostgreSQL 15 便携版

```text
下载：postgresql-15.14-1-windows-x64-binaries.zip（320,461,864 字节，来源 get.enterprisedb.com）
解包：D:\pgsql\        （bin / lib / share / doc 等；zip 顶层即 pgsql 目录）
数据：D:\pgsql\data\   （initdb 生成）
端口：55432，仅监听 127.0.0.1
```

```powershell
# 1) 初始化数据目录
D:\pgsql\bin\initdb.exe -D "D:/pgsql/data" -U postgres -E UTF8 --locale=C --auth-local=trust --auth-host=trust

# 2) 启动（仅回环、非默认端口）
D:\pgsql\bin\pg_ctl.exe -D "D:/pgsql/data" -l "D:/pgsql/data/pg_ctl-start.log" -o "-p 55432 -c listen_addresses=127.0.0.1" start

# 3) 就绪检查
D:\pgsql\bin\pg_isready.exe -h 127.0.0.1 -p 55432
# 输出：127.0.0.1:55432 - accepting connections
```

### 2.2 专属测试角色与库

测试夹具要求**库名与用户名都必须是 `agentexam_identity_test`**，且端口不是 5432。`CREATEDB` 是必需的——夹具会在该库中新建随机名字的临时库并在跑完后删除：

```sql
CREATE ROLE agentexam_identity_test LOGIN CREATEDB;
CREATE DATABASE agentexam_identity_test OWNER agentexam_identity_test;
```

该库现在只作为自动化测试的控制库。测试夹具会临时创建 `identity_<随机值>`、`leaderboard_<随机值>` 等数据库并在结束后删除，因此日常开发数据不得写入 `agentexam_identity_test`。

### 2.3 独立开发角色与库

日常开发改用 `agentexam_dev` 角色与同名数据库。角色只需要登录和拥有本数据库，不授予超级用户、建库或建角色权限。创建前必须先查询现场；存在同名对象时不得删除重建。

2026-09-19 已创建并核验：`agentexam_dev` 角色为 `LOGIN`、非超级用户、无 `CREATEDB`/`CREATEROLE`，同名数据库由该角色拥有。完整命令、幂等检查和权限验收见[阶段 0 详细实施计划 Task 3](../01-plan/STAGE0_LOCAL_DEVELOPMENT_PLAN.md#task-3-建立测试库与开发库的角色隔离)。

### 2.4 业务 schema（11 张表）

2026-09-18 的历史操作是在 `agentexam_identity_test` 中用项目函数安装 11 张表；该结果只证明当时数据库结构（schema）可建立，不再作为日常开发库。2026-09-19 实施两库方案时保留了该现场，没有删除测试控制库中的既有对象，并把日常开发 schema 单独安装到 `agentexam_dev`。

新方案仍由项目自带代码安装，不手写 SQL：

```python
from eval_platform.adapters.persistence.bootstrap import initialize_empty_database
initialize_empty_database("postgresql://agentexam_dev@127.0.0.1:55432/agentexam_dev")
```

它会按顺序应用 `identity.sql`、`membership.sql`、`catalog/schema.sql`、`jobs/schema.sql`，并**拒绝非空数据库**。

`agentexam_dev` 必须通过现有 `agentexam-owner init-db` 间接调用该函数；上面的 Python 片段只解释实际入口复用的函数，不作为建议的手工执行命令。测试控制库中即使保留历史表，也不再承担日常开发数据。

### 2.5 Python 环境

项目要求 `>=3.13,<3.14`，而本机系统 Python 是 **3.12.0**，不满足。`uv` 会自动准备匹配的解释器，因此直接用：

```powershell
cd apps\backend
uv sync          # 自动准备 Python 3.13.15，并按 uv.lock 安装依赖（含 dev 组）
```

### 2.6 前端依赖

尚未安装，且不属于 E 模块阶段 0。以后只有进入明确的 Web 任务时才按锁文件安装，不在本阶段执行：

```powershell
cd apps\web
npm ci --ignore-scripts
```

## 3. 环境变量（日常后端开发不用 `.env`）

后端应用只认进程环境变量。本机便携 PostgreSQL 开发需要的几个（**都不含秘密**）：

| 变量 | 用途 | 本机取值 |
|---|---|---|
| `AGENTEXAM_TEST_DATABASE_URL` | PostgreSQL 集成测试的连接串 | `postgresql://agentexam_identity_test@127.0.0.1:55432/agentexam_identity_test` |
| `AGENTEXAM_DATABASE_URL` | 日常开发/本机维护命令的数据库连接 | `postgresql://agentexam_dev@127.0.0.1:55432/agentexam_dev` |
| `AGENTEXAM_RUN_IDENTITY_POSTGRES=1` | 显式开启真实 PostgreSQL 测试 | 仅跑该层测试时设置 |
| `AGENTEXAM_MINIO_*` | 对象存储测试 | 本机未配置，相关用例保持跳过 |

注意：本机库使用回环信任认证，连接串里不需要密码；所以本机不存在任何需要保管的数据库密码。

两个连接串不得互换：`AGENTEXAM_TEST_DATABASE_URL` 只指向测试控制库，`AGENTEXAM_DATABASE_URL` 只指向开发库。变量只设置在当前 PowerShell 进程，不持久写入系统或仓库。

`infra/.env` 是另一种场景：它是 owner 单机部署的私有配置输入，由 `infra/local/AgentExam.Local.psm1` 和 Docker Compose 使用。若以后本机承担 owner 部署职责，应按 [`infra/.env.example`](../../../infra/.env.example) 创建并私下填写；在当前“不依赖 Docker”的开发范围内不需要创建，也不能向管理员索取或复制他人的真实 `.env`。

## 4. 验证清单与结果

历史基线执行于 2026-09-18，工作目录 `apps/backend`：

| 序号 | 检查项 | 命令 | 结果 |
|---|---|---|---|
| 1 | 数据库就绪 | `pg_isready -h 127.0.0.1 -p 55432` | 通过：`accepting connections` |
| 2 | 版本为 15.x | `SELECT version();`（服务器日志） | 通过：`PostgreSQL 15.14, compiled by Visual C++ build 1944, 64-bit` |
| 3 | 仅监听回环 | 服务器日志 | 通过：`listening on IPv4 address "127.0.0.1", port 55432` |
| 4 | schema 完整 | `SELECT tablename FROM pg_tables WHERE schemaname='public'` | 通过：11 张表，与预期清单一致 |
| 5 | 专属角色可连 | 以 `agentexam_identity_test` 连接 | 通过：`current_user / current_database` 均为 `agentexam_identity_test` |
| 6 | 静态检查 | `ruff check src tests prototype_codex_harbor_e2e.py` | 通过：`All checks passed!` |
| 7 | 格式检查 | `ruff format --check …` | 通过：`283 files already formatted` |
| 8 | 类型检查 | `mypy src prototype_codex_harbor_e2e.py` | 通过：`no issues found in 164 source files` |
| 9 | 默认回归 | `pytest -q -p no:cacheprovider` | **386 passed, 82 skipped, 2 failed, 52.96s** |
| 10 | 未启用开关时正确跳过 | 不设 `AGENTEXAM_RUN_*` | 通过：82 项以"专属 PostgreSQL 测试未显式启用"等理由跳过，非失败 |

### 关于第 9 项的 2 个失败

失败的两项都在 `tests/contract/test_execution_network.py`，**根因相同：都需要访问 `framework/harbor`**——

- `test_bootstrap_imports_fixed_harbor_not_the_adjacent_adapter_package`：要执行 `framework/harbor/.venv/Scripts/python.exe`，该路径不存在。
- `test_sidecar_exports_traceable_dns_adaptation_and_never_overwrites`：要执行 `git -C framework/harbor rev-parse HEAD`，返回 128（目录不存在）。

`framework/` 是被 `.gitignore` 排除的固定 Harbor 上游源码，只存在于组长机器上（文档记载 Windows 首次编译约 275 分钟，且明确要求不要无理由重建）。所以这两项是**环境依赖导致的失败**，不是产品缺陷。已记录到[问题记录](../04-issues/KNOWN_ISSUES.md)的 ISSUE-04。

### 阶段 0 本轮执行结果（2026-09-19）

| 检查项 | 实际结果 |
|---|---|
| PostgreSQL 恢复 | `pg_ctl` 启动成功；`pg_isready` 为 `accepting connections` |
| 服务边界 | PostgreSQL 15.14、`127.0.0.1:55432`；Windows 只发现回环监听；`pg_hba.conf` 无远程网段 |
| 两库与权限 | `agentexam_identity_test` / `agentexam_dev` 均存在且由同名角色拥有；测试角色 `CREATEDB=true`，开发角色 `CREATEDB=false`，两者均非超级用户/建角色 |
| 开发 schema | `agentexam-owner init-db` 成功；`agentexam_dev` 精确 11 表；重启后仍为 11 表 |
| 工具链 | `uv sync --locked` 成功；Python 3.13.15；Ruff、格式检查、mypy 均通过 |
| PostgreSQL 集成测试 | **246 passed、11 skipped、2 warnings，96.86 秒** |
| 默认回归 | **386 passed、82 skipped、2 failed、2 warnings，47.55 秒**；2 个失败均为缺少 `framework/harbor` 的 ISSUE-04 |
| 启停 | 正常停止后 `pg_isready=no response`；独立日志文件重启成功并读回 11 表；当前数据库保持运行 |

## 5. 已知限制

- 本机**不能**运行真实执行链（Harbor / 固定 Fork / 固定镜像只在组长机器上），因此网络、Harbor 相关集成测试在本机只能跳过；上面 2 项契约测试还会直接失败，见 ISSUE-04。
- 本机不使用团队共享库；Tailscale 故障见[问题记录](../04-issues/KNOWN_ISSUES.md)的 ISSUE-01，但已从阶段 0 前置条件中移除。
- 便携版 PostgreSQL 不是 Windows 服务：重启电脑后需要手动启动

  ```powershell
  D:\pgsql\bin\pg_ctl.exe -D "D:/pgsql/data" -l "D:/pgsql/data/pg_ctl-start.log" -o "-p 55432 -c listen_addresses=127.0.0.1" start
  ```

  启动日志必须使用独立的 `pg_ctl-start.log`，避免与 PostgreSQL 自身日志竞争 Windows 文件句柄。当前不注册为开机自启服务，避免引入系统级改动。
- 前端依赖未安装；MinIO 未配置。Docker Desktop 已于 2026-09-21 安装（CLI 29.6.2），但**守护进程未运行**，且能否创建自定义网络尚未验证；后端开发与测试仍不依赖 Docker。
