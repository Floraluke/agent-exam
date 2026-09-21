# 阶段 0 本地开发环境设计

> 状态：已确认并实施完成；实际证据见[阶段 0 行动记录](../../actions/2026-09-19-stage0-local-development-plan.md)。
>
> 确认日期：2026-09-19。
>
> 适用机器：`D:\agent-exam` 所在的 LLY Windows 开发机。

## 1. 目标与边界

阶段 0 只建立“能安全写代码和验证后端”的本机前提环境，不改变 AgentExam 的产品范围、架构、模块调用约定（Interface）或业务数据模型。由于本机 Tailscale 无法启动，本阶段完全放弃连接团队共享 PostgreSQL，改用本机 PostgreSQL 15。

本阶段包含：本地数据库、Python 3.13 虚拟环境、静态检查、默认回归和显式开启的 PostgreSQL 集成测试。

本阶段不包含：Tailscale、共享管理员账号、Docker、MinIO、Harbor、SWE-Bench-Fork、Worker、完整 Web/API 运行时、真实模型或任何付费调用。完整运行时依赖 MinIO 等 owner 环境，不能用“本地 PostgreSQL 可用”替代其验收。

## 2. 方案选择

采用“两库隔离”，不让自动化测试与日常开发共用数据：

| 本机对象 | 职责 | 权限与数据规则 |
|---|---|---|
| PostgreSQL 15 / `127.0.0.1:55432` | 本机唯一数据库进程 | 仅监听回环；不注册 Windows 服务；不开机自启；不向局域网或公网暴露 |
| `agentexam_identity_test` 角色与同名库 | 自动化 PostgreSQL 测试的控制库 | `LOGIN + CREATEDB`；测试夹具创建随机临时库并在结束后删除；不得保存日常开发数据 |
| `agentexam_dev` 角色与同名库 | 日常开发和手工调试 | `LOGIN`、非超级用户、无 `CREATEDB`；角色拥有该库；完整 11 表数据库结构（schema）只由项目初始化入口建立 |
| `postgres` 本机管理员 | 首次创建/修正角色和数据库 | 仅用于本机维护，不配置给应用，不替代共享管理员，也不用于日常测试 |

本机 PostgreSQL 只绑定 `127.0.0.1`，并使用回环 `trust` 认证，因此连接串不含密码。这个取舍只适用于单人本机开发；任何共享、远程或长期部署都不得照搬。

### 2.1 选择理由与替代方案

| 方案 | 结论 | 理由 |
|---|---|---|
| 本机 PostgreSQL + 测试库/开发库隔离 | 采用 | 不依赖故障中的 Tailscale；自动化测试可创建临时库，同时不会污染手工开发数据 |
| 本机 PostgreSQL + 测试/开发共用一库 | 拒绝 | 测试夹具拥有建库与清理职责，日常数据和测试现场容易混淆 |
| 继续连接团队共享管理员库 | 拒绝 | Tailscale 当前不可用；共享超级管理员扩大误操作范围，也不适合作为个人开发前置 |
| 在本机恢复 owner Docker/MinIO 全套部署 | 本阶段拒绝 | 超出阶段 0 的后端开发目标，并会引入 Docker、秘密和持久化运维职责 |

### 2.2 当前文件树与职责

```text
D:\pgsql\
  bin\                                      # PostgreSQL 15 可执行程序；提供 pg_ctl、psql、createdb、pg_isready
  data\                                     # 本机数据库数据目录；禁止重复 initdb
    PG_VERSION                              # 数据目录主版本标识，当前为 15
    pg_hba.conf                             # 认证边界，只允许 local、127.0.0.1/32、::1/128
    pg_ctl-start.log                        # pg_ctl 独立启动日志，避免与服务日志竞争句柄
D:\agent-exam\
  apps\backend\.venv\                       # Git 忽略的 Python 3.13 后端开发环境
  docs\LLY\01-plan\                        # 阶段设计、实施步骤与 E 模块计划入口
  docs\LLY\02-environment\                 # 本机环境事实、复现命令和验证摘要
  docs\LLY\03-progress\                    # 按日期记录实际进展与当前停点
  docs\LLY\04-issues\                      # 本机 Tailscale 与缺失 framework 等已知限制
  docs\actions\                            # 实施过程、偏差和验证证据的权威行动记录
```

这里没有新增产品设计模式。依赖方向是“当前 PowerShell 进程 → 现有后端配置入口 → PostgreSQL 适配器（Adapter，即把项目存储接口转换为 PostgreSQL 操作的实现）”；数据库 schema 仍只来自现有初始化入口。

## 3. 配置与数据流

日常开发不创建应用可自动读取的 `.env`：后端继续从当前 PowerShell 进程读取环境变量。

```text
自动化测试
  → AGENTEXAM_TEST_DATABASE_URL
  → agentexam_identity_test 控制库
  → 每个测试自己的随机临时数据库
  → 测试结束后精确删除临时数据库

日常开发 / 本机维护命令
  → AGENTEXAM_DATABASE_URL
  → agentexam_dev
  → 现有 PostgreSQL Adapter
  → 项目自带 initialize_empty_database() 建立 11 张表
```

`infra/.env` 属于 owner 的 Docker/Compose 部署链，不属于本阶段。既不向 owner 索取该文件，也不复制其中的密码或连接串。

## 4. 启停与失败处理

- 每次开发前显式运行 `pg_ctl status` 和 `pg_isready`；数据库未运行时才启动。
- 已存在 `D:\pgsql\data\PG_VERSION` 时严禁再次运行 `initdb`，避免覆盖既有数据目录。
- 建库前先查询角色和数据库是否存在；只创建缺失对象，不删除、重建或清空未知对象。
- `agentexam-owner init-db` 只允许指向空白的 `agentexam_dev`；发现非空数据库时停止调查，不通过删表规避保护。
- 测试只允许使用满足固定主机、端口、库名和用户名门禁的 `agentexam_identity_test` 连接串。
- 阶段 0 结束时数据库可保持运行或手动停止；两种状态都要有明确命令，不安装自动启动服务。

## 5. 完成标准

阶段 0 只有同时满足以下条件才完成：

1. PostgreSQL 15 可按需启动，`pg_isready` 返回 accepting connections，服务端地址为 `127.0.0.1`、端口为 `55432`。
2. `agentexam_identity_test` 与 `agentexam_dev` 的角色、数据库、权限和所有者符合本设计。
3. `agentexam_dev` 中存在项目当前 11 张表，且 schema 来自现有 `agentexam-owner init-db`，不是手写 SQL。
4. Python 3.13 虚拟环境与锁定依赖可用，Ruff、格式检查和 mypy 有新鲜结果。
5. PostgreSQL 集成测试有新鲜结果；临时数据库在测试后没有残留。
6. 默认回归已运行，所有失败、跳过和本机缺失的 `framework/` 限制均如实记录。
7. 未连接共享数据库，未创建或泄漏密码，未启动 Docker、MinIO、Worker 或模型。

## 6. 已知风险

- 回环 `trust` 允许本机进程无密码连接，只适用于这台单人开发机；如果监听范围改变，必须先改认证策略。
- PostgreSQL 不注册为 Windows 服务，重启电脑后需要手动启动；这是减少系统改动的明确取舍。
- 本机缺少 Git 忽略的 `framework/harbor`，默认回归保留两个已知环境失败；这不等于完整执行链已通过。
- MinIO、完整 HTTP 运行时、Worker 和真实模型仍未配置，不能由数据库阶段完成状态推导为平台可运行。

详细命令、执行顺序和记录要求见[阶段 0 实施计划](./STAGE0_LOCAL_DEVELOPMENT_PLAN.md)。
