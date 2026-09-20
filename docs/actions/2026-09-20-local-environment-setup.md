# C 本机开发环境搭建（Python 3.13 + 便携 PostgreSQL）

## 状态与情况说明

- 状态：Completed（2026-09-20 建立并验证）。本行动只建立**本机开发环境**，不涉及任何产品代码、测试或配置改动。
- 来源请求：用户（成员 C）2026-09-20 要求查明任务 04 现在能做什么并开始推进。核对后确认：任务 04 中凡不依赖容器、固定镜像与固定数据快照的部分（目录侧一致性、规模侧拒绝边界、目录→options→提交→冻结 Job 的打通），本机原本因缺少运行环境而无法验证；本行动消除该环境障碍，使这些部分的本机验证具备条件。
- 基线：分支 `lyq`，HEAD `d66ae03`（= 上游 `main` `beed93f` + 个人文档提交）。本行动未提交任何产品代码。
- 参照：成员 E 在 `upstream/lly/dev` 分支上的 `docs/LLY/02-environment/LOCAL_SETUP.md`，以及本目录的[统一本机环境记录](2026-09-18-unified-local-env.md)。说明：`docs/LLY/` 不在上游 `main` 上，只能从 E 的分支读取。本行动采用同一套方案（便携 PostgreSQL + 非默认端口 + 回环 trust + `uv sync`），不新增顶层目录、不改仓库配置。

### 当前事实（2026-09-20 实际核对）

| 检查项 | 搭建前 | 搭建后 |
|---|---|---|
| Python | 系统只有 3.11.9，后端要求 `>=3.13,<3.14`，`import eval_platform` 失败 | `apps/backend/.venv` 为 3.13.15，依赖可导入 |
| 包管理器 | 无 `uv` | `uv 0.12.17` |
| PostgreSQL | 无安装；55432/5432 均未监听 | 便携版 15.14 于 `D:\pgsql`，仅监听 `127.0.0.1:55432` |
| 数据库 | 无 | `agentexam_identity_test`（LOGIN+CREATEDB）、`agentexam_dev`（仅 LOGIN） |
| Node | v22.15.1（已有，未改动） | 同左 |
| 网络 | GitHub 直连不通（`git fetch` 21s 超时）；本机代理 `127.0.0.1:7892` 可用 | 仓库本地 git 配置恢复 `http.proxy`，两个远端 fetch 正常 |

仍然不具备（与本行动无关，属预期）：`framework/`、`runtime/`、`infra/data/` 与固定 Parquet 快照不存在；Docker Desktop 未运行；MinIO 未运行。因此容器类、固定镜像类与固定数据类的验证仍**只能**在组长机器上或由 E 执行。

### 明确排除

- 不修改任何产品代码、测试、依赖清单或仓库级配置（`uv.lock`、`pyproject.toml` 未动）。
- 不下载题目镜像、不读取真实凭据、不调用模型、不连接共享数据库。
- 不注册 Windows 服务、不设置开机自启；数据库只监听回环。

## 实施措施

1. `pip install uv` 装入 uv 0.12.17（走本机代理）。
2. 在 `apps/backend` 执行 `uv sync --frozen`：按仓库已有的 `uv.lock` 安装锁定依赖，由 uv 自带准备 Python 3.13.15，生成 `apps/backend/.venv`。
3. 下载 `postgresql-15.14-1-windows-x64-binaries.zip`（320,461,864 字节，sha256 `234ccc7a5cf07fce70f93faea701fd75fad6bec968359b06cdfc208ed7dfbc30`，来源 get.enterprisedb.com），解压到 `D:\pgsql`。
4. `initdb`：`-U postgres -E UTF8 --locale=C --auth-local=trust --auth-host=trust`。
5. 启动：`pg_ctl -D "D:/pgsql/data" -o "-p 55432 -c listen_addresses=127.0.0.1" start`（不注册服务、不开机自启）。
6. 建角色与库：`agentexam_identity_test`（LOGIN + CREATEDB，测试夹具会在其中创建随机临时库并删除）、`agentexam_dev`（仅 LOGIN，日常开发用）。
7. 运行测试基线并检查实际输出。

完成标准：`pg_isready` 通过；目录模块测试全绿；全量回归的失败集合与既有已知环境失败一致（不新增失败）。

## 受影响文件树（实际）

```text
apps/backend/.venv/                  # 新增：Python 3.13.15 虚拟环境（Git 忽略，不进仓库）
D:\pgsql\                            # 新增：便携 PostgreSQL 15.14（bin/lib/share + data）
D:\agentexam-env\postgresql-15.14-1-windows-x64-binaries.zip  # 新增：安装包留档（可删）
docs/actions/2026-09-20-local-environment-setup.md            # 本行动文档（新增）
docs/LYQ/06-environment/LOCAL_SETUP.md                        # 环境事实与命令（新增）
docs/LYQ/03-progress/PROGRESS_LOG.md                          # 进度日志追记
docs/LYQ/04-issues/KNOWN_ISSUES.md                            # ISSUE-01/02/03 状态更正
docs/LYQ/README.md                                            # 目录分类与当前状态同步
docs/actions/2026-09-19-task-04-catalog-candidates-and-scale.md # 更正“本机不具备条件”等过期事实
```

不改：`apps/backend/pyproject.toml`、`apps/backend/uv.lock`、`.gitignore`、任何 `src/` 或 `tests/` 下的文件。

## 自验证方式与成功标准

- `pg_isready -h 127.0.0.1 -p 55432` 返回 accepting connections。
- `psql` 列出两个角色与两个库，权限符合上表。
- `pytest tests/catalog -q`：目录模块全绿（MinIO 集成按设计跳过）。
- `pytest -q` 全量：无新增失败；仅保留缺 `framework/harbor` 的既有 2 个环境失败。

## 自验证情况（实际运行结果）

| 检查 | 命令 | 实际结果 |
|---|---|---|
| 就绪 | `D:\pgsql\bin\pg_isready.exe -h 127.0.0.1 -p 55432` | `127.0.0.1:55432 - accepting connections` |
| 角色/库 | `psql ... -c "\du" -c "\l"` | `agentexam_dev`（仅 LOGIN）、`agentexam_identity_test`（Create DB）；两个同名库 owner 正确、编码 UTF8 |
| 目录模块 | `pytest tests/catalog -q`（`AGENTEXAM_RUN_IDENTITY_POSTGRES=1`） | **33 passed, 7 skipped**（7 个为需 MinIO 的集成用例，按设计跳过） |
| 全量回归 | `pytest -q` | **452 passed, 36 skipped, 2 failed**，119.75s |
| 2 个失败归因 | `pytest tests/contract/test_execution_network.py --tb=line` | `FileNotFoundError` / `CalledProcessError: git -C ...\framework\harbor rev-parse HEAD` — 缺 `framework/harbor` 的既有环境失败，与 D 记录的基线同类，非代码缺陷 |

限制与遗留风险：

- 失败集合中的 2 项在本机**无法**修复（`framework/` 不进 Git），必须按“环境失败”对待，不得描述为通过。
- `agentexam_identity_test` 使用回环 trust 认证（无密码），这是开发库取舍，**不得**用于共享或长期环境；本机数据库也不承载任何真实评测数据。
- 环境隔离依赖 `http.proxy` 指向本机代理；代理关闭时 git 会失败，处理方式见 [ISSUE-01](../LYQ/04-issues/KNOWN_ISSUES.md)。
- 本行动不产生“任务 04 已完成”的任何结论；容器类与固定数据类门禁仍未开始。
