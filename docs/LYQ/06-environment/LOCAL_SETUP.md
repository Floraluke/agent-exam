# 本机开发环境（Python 3.13 + 便携 PostgreSQL）

> 目标：在本机建立一套**不依赖 Tailscale、不依赖 Docker、不依赖共享库**的后端开发环境，能写代码、跑静态检查、跑 PostgreSQL 集成测试和默认回归。
>
> 状态：**已建立并验证**（2026-09-20）。过程与逐项证据见[行动文档](../../actions/2026-09-20-local-environment-setup.md)。
>
> **当前运行状态的唯一来源：** 2026-09-20 最后一次核对时，PostgreSQL 15.14 正在 `127.0.0.1:55432` 运行（`pg_isready` 返回 accepting connections）。数据库以后停止或重启时只更新本段。
>
> 方案参照成员 E 的 `docs/LLY/02-environment/LOCAL_SETUP.md`（该目录只存在于 E 的 `lly/dev` 分支，不在上游 `main`）。本目录编号为 `06-environment`，与 `docs/LYQ/` 既有编号衔接。

## 1. 这套环境是什么

| 组件 | 位置 | 说明 |
|---|---|---|
| Python 3.13.15 + 锁定依赖 | `apps/backend/.venv` | 由 `uv sync --frozen` 按仓库 `uv.lock` 安装，不进 Git |
| uv 0.12.17 | 系统（pip 安装） | 自动准备项目要求的 Python 版本 |
| PostgreSQL 15.14 便携版 | `D:\pgsql`（bin/lib/share + `data`） | 只监听 `127.0.0.1:55432`，不注册 Windows 服务、不开机自启 |
| 测试库 | `agentexam_identity_test` | 角色 `LOGIN + CREATEDB`；测试夹具会在此库中创建随机临时库并在跑完后删除，**日常数据不要写这里** |
| 开发库 | `agentexam_dev` | 角色仅 `LOGIN`，无超级用户/建库/建角色权限 |
| 安装包留档 | `D:\agentexam-env\…binaries.zip` | 320,461,864 字节，可删 |
| 固定数据集 | `runtime/cache/swe-gym-lite/61231f2c…/train-0000.parquet` | SWE-Gym Lite 快照，931,193 字节 / sha256 `f3a7cd93…` 已核验；`/runtime/` 已 gitignore |
| 三个固定框架源码 | `framework/{swe-gym,swe-bench-fork,harbor}` | 2026-09-21 按[依赖总表 §7](../../dependencies/DEPENDENCIES.md)恢复到固定提交（`--detach`），HEAD 与 origin 已核对、工作树干净 |
| Harbor 依赖环境 | `framework/harbor/.venv` | 2026-09-21 建立：Python 3.13.15、Harbor `0.22.0`、218 个包 / 325 MB、`harbor.exe` 可用，`import harbor` 指向上游固定源码。**实测 3 分 20 秒**（全命中预编译 wheel，未触发源码构建）——文档里 275 分钟的记录在 Python 3.13 + Windows 上**没有复现**；`--locked` 未改动上游锁文件 |
| Fork 的 Linux 依赖环境 | `framework/swe-bench-fork/.venv` | 2026-09-21 按[依赖总表 §5.2](../../dependencies/DEPENDENCIES.md)三步建立：venv 由 WSL Ubuntu 的 `/usr/bin/python3`（**3.12.3**）创建，依赖用 Windows 侧 uv 以 `--python-platform x86_64-unknown-linux-gnu --require-hashes` 装入（63 项哈希锁定，134 条目 / 316 MB）。验证：`swebench 2.0.13`、`docker 7.2.0`、`datasets 5.0.1` 可导入（`swebench` 经 `PYTHONPATH` 指向固定源码，上游未做 editable 安装） |
| 固定 uv 工具 | `runtime/tools/{uv-bootstrap,uv-linux}` | 2026-09-21 按 §5.2 引导（uv 0.12.10） |
| MinIO 测试端点 | 镜像 `agentexam-minio-test:local`（112 MB）+ 数据目录 `runtime/minio-data` | 2026-09-21 按固定源码归档构建：commit `7aac2a2c…`、归档 sha256 `71794c2d…` 校验通过；构建时把代理指向 `host.docker.internal:7892`（构建容器在 WSL 虚拟机内，`127.0.0.1` 够不到宿主机代理）。**启动时用 `--user 0:0`**——WSL2 不认 tmpfs 的 uid/gid、Windows 绑定挂载回来是 root 属主，而镜像本身是 `FROM scratch` + `USER 65534`；这是为在本机跑通一致性用例的**本地端点偏离**，不改镜像内容 |

## 2. 为什么这么选

| 决策 | 理由 |
|---|---|
| 便携版 PostgreSQL（zip 解包），不用安装包 | 不需管理员权限、不注册服务、删目录即卸载 |
| 端口 **55432** 而非默认 5432 | 测试夹具明确拒绝默认端口 5432，只接受非默认端口的专属隔离库 |
| 回环 trust 认证（仅 `127.0.0.1`） | 只有本机进程能连，因此不需要创建或传递任何数据库密码；这是开发库取舍，**不得**用于共享或长期环境 |
| 不装 Docker | Docker Desktop 未运行；且容器类验证本来就不在开发机做 |
| `uv sync --frozen` 而非 `pip install` | 仓库自带 `uv.lock`，锁文件保证与团队基线一致；uv 会自动准备 Python 3.13 |

## 3. 日常命令

```bash
# 启动数据库
D:/pgsql/bin/pg_ctl.exe -D "D:/pgsql/data" -l "D:/pgsql/data/pg_ctl-start.log" \
  -o "-p 55432 -c listen_addresses=127.0.0.1" start

# 停止数据库
D:/pgsql/bin/pg_ctl.exe -D "D:/pgsql/data" stop

# 就绪检查
D:/pgsql/bin/pg_isready.exe -h 127.0.0.1 -p 55432
```

```bash
# 跑测试（在 apps/backend 下）
cd apps/backend
AGENTEXAM_RUN_IDENTITY_POSTGRES=1 \
AGENTEXAM_TEST_DATABASE_URL="postgresql://agentexam_identity_test@127.0.0.1:55432/agentexam_identity_test" \
./.venv/Scripts/python.exe -m pytest -q

# 只跑目录模块（我负责）
./.venv/Scripts/python.exe -m pytest tests/catalog -q        # 同样带上上面两个环境变量

# 静态检查
./.venv/Scripts/python.exe -m ruff check .            # 通过
./.venv/Scripts/python.exe -m ruff format --check .    # 本机当前 5 个文件不合格，见第 4 节
./.venv/Scripts/python.exe -m mypy src/eval_platform   # 注意：必须给显式路径，见下
```

**mypy 的坑**：直接跑 `mypy`（按 `pyproject.toml` 的 `packages = ["eval_platform"]`）会报
`Package 'eval_platform' cannot be type checked due to missing py.typed marker`。原因是 editable 安装让 mypy 把它当成第三方包。改成 `mypy src/eval_platform`（显式路径）即可：实测 `Success: no issues found in 166 source files`。

## 4. 当前基线（2026-09-21 实测）

| 范围 | 结果 |
|---|---|
| `tests/catalog` | **37 passed, 7 skipped**（7 个为需 MinIO 的集成用例，按设计跳过） |
| `tests/catalog/qualification` | **5 passed**（固定候选身份机制） |
| 全量 `pytest -q`（PG + MinIO 全开） | **481 passed, 39 skipped, 0 failed**；`tests/catalog` **49 passed / 15 skipped**（此前 7 个 MinIO 用例由跳过转为真跑通过） |
| 失败项 | **无**（此前两项 `framework/harbor` 环境失败已随源码恢复 + 依赖环境安装全部消除） |
| `ruff check .` | **All checks passed!** |
| `ruff format --check .` | 2026-09-21 重放到上游 `fd369cc` 后复核：**仍有 2 个文件不合格**（`tests/jobs/cancellation/test_cancel_races.py`、`tests/jobs/reporting/test_matrix_rehearsal.py`），均为他人文件；原先 5 个中的 3 个已随上游 `7553ce0` 修好 |
| `mypy src prototype_codex_harbor_e2e.py` | **Success: no issues found in 168 source files** |

## 5. 仍然做不到的事（不要在本机浪费时间）

- 容器类验证：Docker Desktop **已在运行**、五个候选镜像已按 digest 拉取验证过（用完即删）；其余需 Docker 的用例（Harbor 探针、真实 Codex Trial、网络探针、Fork 的旧题集成）仍需各自开关与镜像，未在本机跑。
- ~~Harbor 的依赖环境~~ **已完成**（2026-09-21，3 分 20 秒，见第 1 节）。
- ~~SWE-Bench-Fork 的隔离依赖环境~~ **已完成**；~~需要固定 MinIO 镜像~~ **已完成**（两者均见第 1 节）。
- 启动本地 MinIO 跑一致性用例：`docker run -d --name ae-minio-test --user 0:0 -p 127.0.0.1:9000:9000 -v "<仓库>/runtime/minio-data:/data" -e MINIO_ROOT_USER=ae_test_local -e MINIO_ROOT_PASSWORD=ae_test_local_secret -e MINIO_BROWSER=off agentexam-minio-test:local server /data --address :9000 --console-address :9001`，并设 `AGENTEXAM_RUN_CATALOG_MINIO=1`、`AGENTEXAM_MINIO_ENDPOINT=http://127.0.0.1:9000`、`AGENTEXAM_MINIO_BUCKET=agentexam-synthetic-test`、`AGENTEXAM_MINIO_ACCESS_KEY=ae_test_local`、`AGENTEXAM_MINIO_SECRET_KEY=...`（桶 `agentexam-synthetic-test` 需预先建好且私有）。
- 真实模型调用与真实凭据：需单独授权，且与本机环境无关。
- 共享 PostgreSQL（`sss.tail03c757.ts.net:15432`）：本机 Tailscale 在正确的 tailnet 内但看不到任何其他设备（netmap `Peers = 0`），问题在 host 侧，见 [ISSUE-06](../04-issues/KNOWN_ISSUES.md)。
- 门禁所需的三样（Docker、五个题目镜像、Fork 的 Linux 依赖环境）本机尚不具备，因此五道候选题的三补丁资格验证仍需要组长机器或由 E 执行；**Harbor 不在门禁的前置里**（门禁只走固定 Fork 判卷，不跑 agent）。

## 6. 清理方式

```text
删除 D:\pgsql                        # 连数据库带数据一起删；删前先 pg_ctl stop
删除 D:\agentexam-env                # 安装包留档
删除 apps/backend/.venv              # 虚拟环境
```

删除后按第 3 节命令即可重建（安装包可从 get.enterprisedb.com 重新下载，sha256 见行动文档）。
