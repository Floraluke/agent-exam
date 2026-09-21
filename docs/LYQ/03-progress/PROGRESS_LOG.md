# 开发进度日志

> 只记录事实与实际结果：做了什么、实际输出是什么、遇到什么。计划见 [`01-plan/PLAN.md`](../01-plan/PLAN.md)。
> 格式：按日期倒序追加，最新在最上面。

## 2026-09-21

### 真后端"六题可选"核对：装配已就绪，但启动被 `CatalogUnavailable` 挡住（未完成）

- 目标：按 B 的请求给"真后端六题可选"的证据（目录列表 / options / 一次 6 题提交的冻结结果），用**真装配**（真 PG + 真 MinIO + 真固定数据集 + 代码里的 6 条预设），身份与 Job 层沿用项目测试替身。
- 已就绪：MinIO 端点已起（`agentexam-minio-test:local`，`127.0.0.1:9000`）；`agentexam_dev` 已装完整 11 表 schema（`initialize_empty_database`）；核对脚本写在 `runtime/verify-six-tasks.py`（Git 忽略）。
- **卡点**：脚本第一步 `initialize_schema(DSN)` 抛 `CatalogUnavailable`——底层是 `adapters/persistence/connection.py` 的 `transaction()` 助手把 psycopg 异常统一收敛成 unavailable，而该助手带 `connect_timeout=3`、`statement_timeout=5000`、`lock_timeout=2000`。两个库（`agentexam_dev`、`agentexam_identity_test`）都复现；手工用 psycopg 直连同一 DSN 正常，且 PG 门禁用例（走同一助手但用沙箱 DSN）一直是通过的。
- 下一步该查（留给下轮）：把该助手的异常透出真实类型（临时打印 `type(e)/e`）确认是超时、锁等待还是 DSN 形态问题；或先绕开 `initialize_schema`（表已在）直接进注册流程。
- 结论（对当前问题的建议）：B 的浏览器套件按验证规范本来跑合成后端，**不需要真后端访问**；真后端"六题可选"的证据最省事的来源是**任务 08 在组长机器上的正式部署窗口**（那台机器有完整真 PG/MinIO/数据），C 提供 6 个 preset id 与门禁证据即可，不必在本机重复搭真后端。

### 补上最后一块：MinIO 一致性用例真跑通过

- 用户开启 Clash"允许局域网连接"后，构建容器得以通过 `host.docker.internal:7892` 走代理；按 `tests/catalog/runtime/Dockerfile.minio` 用**固定源码归档**（sha256 `71794c2d…` 校验通过）成功构建 `agentexam-minio-test:local`（112 MB，与组长那份 111,899,710 字节一致，说明固定输入可复现）。
- 本机起端点的偏离：镜像本身是 `FROM scratch` + `USER 65534`，但 WSL2 不认 tmpfs 的 `uid/gid`、Windows 绑定挂载回来是 root 属主 → 前三次尝试都报 `Unable to initialize backend: file access denied`；改用 `--user 0:0` 后正常。**这只影响本机一次性测试端点的启动方式，不改镜像内容**（已记录在环境文档）。
- 结果：7 个原本跳过的用例（5 个目录一致性 + 2 个 MinIO 集成）**真跑通过**——`tests/catalog` 由 42 passed / 22 skipped 变为 **49 passed / 15 skipped**（剩 15 个是门禁用例，按设计等 Fork 开关）；带 PG + MinIO 的全量为 **481 passed / 39 skipped / 0 failed**。模块职责"目录记录与对象摘要一致"本机验证完成。
- 清理：已删容器与 golang 基础镜像、清空构建缓存，保留 112 MB 的 MinIO 镜像供复用。**磁盘提示**：Docker 的 `docker_data.vhdx` 不会随删镜像自动缩盘（C 盘显示 7.3 GB 空闲，其中约 3–4 GB 是 vhdx 内已释放的空间，后续拉镜像会复用；要真正回收需 Docker Desktop 的 Purge 或 `wsl --shutdown` 后压缩）。

### 同步上游新 main 并完成权威文档同步（任务 04 清单最后一条）

- 拉到 D 的落地：`0b66a29`（含 `ad09aaf` 格式修复）等；与我改的文件零交集，`git rebase upstream/main` 干净重放 27 个提交。**复验：`ruff check` 全绿、`ruff format --check` 300 个文件全通过（核对 D 说的 295 全绿，我这份因新增文件计数为 300）、`mypy` 通过、全量 474 passed / 46 skipped / 0 failed。** 已 `push --force-with-lease` 刷新 PR。
- 权威文档同步（按清单，`HTTP_API.md` 经用户确认不改、归 B 维护）：
  - 模块架构 `catalog-and-configuration/ARCHITECTURE.md`：把"当前限制：只有一道题"改为六题现状，写明白名单位置 `adapters/tasks/catalog.py`、五题门禁结论与证据指针。
  - 依赖总表 `DEPENDENCIES.md`：新增五道题的镜像 digest 清单与门禁结果（含 15131 的 `/testbed` 与 base commit 一致性）、说明镜像用完即删可按 digest 重拉；§9 两条锁定项更新（受控目录已扩到 6 题；扩题兼容性已验证）。
  - 模块契约与数据模型：**核对后无需改动**（Interface 与 schema 均未变）。
- 04 草案里"同步权威文档"一条已打勾并写明依据；失效链接检查 0。

### 五道新题入库（任务 04 题库半边交付）

- 门禁通过后按计划把五道题写进受控白名单：新增 `adapters/tasks/catalog.py`（`FIXED_TASK_IMAGES` 六条：旧题 + 五道新题，各带 digest）；`swe_gym.py` 改为从该模块显式 re-export（**198 行，未超 200 行指标**，`preflight.py` 一行未改）；`delivery/catalog_presets.py` 的 `TASK_PRESETS` 由 1 条扩为 **6 条**。
- 顺带把门禁测试改成**读白名单**（digest 单一来源），它因此变成白名单的回归门禁：以后任何新题入库都要能在这里逐题通过三补丁验证。
- 复验：`ruff check src tests` 全绿、`mypy src` 通过、`tests/catalog` **42 passed / 22 skipped**、全量 **474 passed / 46 skipped / 0 failed**（跳过 +15 = 新门禁用例，需 Docker + 镜像 + `AGENTEXAM_RUN_FORK_INTEGRATION=1`）。
- 至此任务 04 的**题库半边**（五题合格入库）与**规模半边**（D 已完成、本行动只做核对）都有证据与实现：原题 + 五道新题合格可选、隐藏答案不外泄、目录→提交→冻结链打通。

### 五道候选全部通过三补丁门禁（任务 04 的题库半边完成）

- 按用户要求串行执行，**每轮跑完立刻删镜像**，C 盘稳定在 9.4–13 GB：15139（2:33）、15184（2:20）、15208（2:33）、15876（2:47）各 3 场景通过，加上先跑的 15131，**五题 15/15 全通过**。
- 每题的判据一致：参考补丁 `resolved`、空补丁不解决且不算应用成功、错误补丁能应用但未解决；容器清理 `verified`、Fork 进程 `returncode=0`、`warnings=[]`。
- 证据：`runtime/fork-evidence/` 下 **15 个 scope**（5 题 × 3 场景），Git 忽略、不覆盖旧 scope。
- 磁盘实况：拉取前 16 GB → 每轮删除后回稳；全部跑完删除镜像后 C 盘余 **9.4 GB**（Docker 数据盘 vhdx 约 7 GB，其中大部分是已释放空间，需要时可用 Docker Desktop 的 Purge 回收）。
- **门禁通过 = 这五道题有资格进入受控目录白名单**；下一步是把它们的实例与镜像身份写进 `FIXED_TASK_IMAGES` 与 `TASK_PRESETS`（产品代码 + 测试同步），届时任务 04 的题库半边即可交付。

### 门禁在本机跑通：候选 python__mypy-15131 通过三补丁门禁 🎉

- 准备：用户指示"能做就做，不等授权"。启动 Docker Desktop（引擎 27.5.1）时发现 **Docker 的代理指向 `127.0.0.1:7897`（没有监听）→ 拉取直接失败**；把 Docker Desktop 的 `OverrideProxyHTTP/HTTPS` 改到实际可用的 `127.0.0.1:7892`（先备份 `settings-store.json` 为 `.bak-20260921`）并重启，拉取恢复。
- 拉取第一个候选镜像 `python_s_mypy-15131`（按 digest）：**2.49 GB 解压后**，Docker 数据盘 1.43→4.21 GB，**C 盘余量 16→11 GB**——所以五个镜像必须**串行**处理（拉一个→跑门禁→删掉→下一个），峰值只占一个镜像。
- 镜像身份交叉验证：容器内 `/testbed` 的 HEAD = `00f3913b314994b4b391a2813a839c094482b632`，**与数据集里该题的 `base_commit` 完全一致**（说明镜像和题目对得上）；镜像内 Python 3.11.9。
- 新增参数化门禁测试 `apps/backend/tests/catalog/qualification/test_candidate_gate.py`（5 候选 × 3 补丁，镜像身份由测试注入，**候选通过前不进产品白名单**）。写的过程中修了两个自伤问题：本文件比 `tests/integration/` 深一层，仓库根要上溯 5 级而不是 4 级；证据根必须在仓库内（适配器要生成相对对象引用），改用 `runtime/fork-evidence/`。
- **实跑结果（15131）**：`gold` → `resolved=True, patch_applied=True`（2 分 26 秒）；`empty` → 两者皆否；`wrong` → 能应用但未解决。三个场景的容器清理均 `verified`、Fork 进程 `returncode=0`、无 warnings。**该候选门禁通过**。
- 证据留在 `runtime/fork-evidence/`（Git 忽略），按项目要求不覆盖旧 scope。
- 剩余四个候选（15139、15184、15208、15876）按同一流程串行处理；每个约 2.5–2.8 GB，跑完即删镜像。

### 建立 Fork 的 Linux 依赖环境（门禁的另一半前置）

- 按[依赖总表 §5.2](../../dependencies/DEPENDENCIES.md)的三步恢复流程执行，**未修改系统 Python、未对上游做 editable 安装**：
  1. Windows 侧引导固定 uv：建 `runtime/tools/uv-bootstrap`（Python 3.13 venv）并装 `uv 0.12.10`（与文档 pin 一致）；
  2. 用该 uv 装 Linux 目标版：`uv pip install --target runtime/tools/uv-linux --python-platform x86_64-unknown-linux-gnu --only-binary :all: uv==0.12.10`（在 Windows 上跑不了是正常的，它是 ELF 二进制，只在 WSL 里执行）；
  3. WSL Ubuntu 侧建 venv：`runtime/tools/uv-linux/bin/uv venv framework/swe-bench-fork/.venv --python /usr/bin/python3` → **Python 3.12.3**，`.venv/bin/python` 就位（判卷适配器读的就是这个路径）；
  4. Windows 侧装哈希锁定依赖：`uv pip install --target framework/swe-bench-fork/.venv/lib/python3.12/site-packages --python-platform x86_64-unknown-linux-gnu --require-hashes -r apps/backend/swebench-requirements.txt` → 134 条目 / 316 MB。
- 验证（在 WSL 里）：`swebench 2.0.13`、`docker 7.2.0`、`datasets 5.0.1`、`unidiff` 均可导入；`sys.prefix` 指向该 venv；`swebench` 经 `PYTHONPATH` 解析到固定源码。
- 操作备注：这台机器的仓库路径含中文，WSL 命令行传参会乱码；改用 `/mnt/c/Users/*/Desktop/agent-exam` 通配写法即可稳定执行。
- 本机现在只剩门禁的最后两样外部条件：**Docker Desktop 运行** 与 **五个题目镜像**（待授权）。

### 安装 Harbor 依赖环境 —— 本机全量测试首次全绿

- 用户决定在本机装 Harbor 的依赖环境（组长也提过"把 harbor 下了"）。按[依赖总表](../../dependencies/DEPENDENCIES.md)的固定命令执行：`uv sync --locked --extra huggingface --no-dev`。
- **实测 3 分 20 秒装完**（`.venv` 创建 15:22:38、最后一批包写入 15:25:57）：Python 3.13.15、218 个包 / 325 MB、113 个预编译 `.pyd`、`harbor.exe` 可用；`import harbor` 解析到 `framework/harbor/src/harbor/__init__.py`（正是契约测试断言的位置），版本 `0.22.0`；`--locked` 未改动上游锁文件、`git status` 干净。
- **文档里"Windows 首次编译约 275 分钟"的警告没有复现**：这次全部命中预编译 wheel（`tiktoken`/`tokenizers` 等都没走源码构建）。推测差异来自 Python 版本/平台组合与 wheel 可用性，历史记录仍然有效，只是不是普遍规律。
- 复验：`tests/contract/test_execution_network.py` **28 passed**（此前 27 passed / 1 failed）；全量 `pytest -q` → **474 passed / 31 skipped / 0 failed** —— **本机首次零失败**（4 个原本因缺 Harbor 解释器而跳过的用例也转为通过）。
- 仍未覆盖的 31 个跳过项：需 MinIO 的集成用例、需 Docker/镜像的 Harbor 探针与 Fork 集成、真实 Codex 试用探针、网络探针。

### 恢复三个固定框架源码（组长让"把 harbor 也下了"）

- 按[依赖总表 §7](../../dependencies/DEPENDENCIES.md)的文档命令，把三个框架恢复到指定提交（`--detach`，不跟随可移动分支）：`framework/swe-gym` @ `b681068c…`、`framework/swe-bench-fork` @ `242429c1…`、`framework/harbor` @ `6af8d6e3…`。
- 按 §8 核验：三个 `origin` 与总表一致、`rev-parse HEAD` 等于固定哈希、`status --porcelain` 无输出；另核 `framework/swe-bench-fork/swebench/__init__.py` 仍声明 `2.0.13`。`/framework/` 已在 `.gitignore`，不进仓库。
- **只恢复源码，未安装依赖**：Harbor 的 `uv sync --locked --extra huggingface --no-dev` 在 Windows 上曾耗时 **275 分 06 秒**（`litellm` 源码构建，需 VS 2022 C++ 环境），文档明确要求"不要无理由重建"；Fork 的隔离依赖环境载体是 **Ubuntu WSL2 的 Python 3.12.3**（`framework/swe-bench-fork/.venv`），与后端 Windows venv 不同。
- 全量复验：**469 passed / 35 skipped / 1 failed**——源码恢复后原先两个契约失败**过了一个**（`test_sidecar_exports_traceable_dns_adaptation_and_never_overwrites`）；剩下的 `test_bootstrap_imports_fixed_harbor_not_the_adjacent_adapter_package` 需要 `framework/harbor/.venv/Scripts/python.exe`（Harbor 依赖环境）。
- 结论：**04 的三补丁门禁不需要 Harbor**——门禁只走固定 Fork 判卷、不跑 agent；Harbor 是 05–07 跑真实 agent 才需要的前置。

### 同步上游并重放到新基线（fd369cc），全量复验

- 上游在我这条 PR 打开期间前进了：`beed93f → fd369cc`（B 的 `7553ce0 fix: harden comparison reports and preset upgrade` + 合并提交；同期 E 的 `lly/dev` 也更新到我这里）。其中对比报告模块被**重命名/搬家**：`delivery/http/routes/jobs/report_comparisons.py` → `delivery/http/routes/jobs/reporting/comparisons.py`。
- 先算交集确认**我的改动与上游新改动零重叠**，再在本机 `git rebase upstream/main`：20 个提交全部干净重放，无冲突（旧头存为本地分支 `backup-lyq-before-rebase`）。
- 新基线上复验：`ruff check` 通过；`mypy src prototype_codex_harbor_e2e.py` 通过（168 个源文件）；全量 `pytest -q` → **468 passed / 35 skipped / 2 failed**（2 项仍是缺 `framework/harbor` 的既有环境失败；通过数从 461 升到 468 是上游新增用例）。我的三个测试增量在新 main 上全部仍然通过，包括会打到已搬家对比端点的公开面扫描。
- `ruff format --check` 复核：**从 5 个不合格降到 2 个**（`tests/jobs/cancellation/test_cancel_races.py`、`tests/jobs/reporting/test_matrix_rehearsal.py`）——另外 3 个已随上游修好；这 2 个仍是 D 的文件。
- 已 `git push --force-with-lease` 更新 fork 分支，PR #2 随之刷新（20 个提交）。

### 04 第一步：固定快照到位、五题身份冻结

- 组长授权下载 SWE-Gym 数据集后已下载并校验：HuggingFace `SWE-Gym/SWE-Gym-Lite` revision `61231f2c…` 的 `default/train/0000.parquet` → `runtime/cache/swe-gym-lite/<revision>/train-0000.parquet`（与 `preflight.py`、契约/集成测试的约定路径一致；`/runtime/` 已在 `.gitignore`）。本地校验 **931,193 字节**、sha256 **`f3a7cd93…`**，与代码里 `DatasetIdentity` 的固定身份**逐位一致**，远程 `X-Linked-Size`/`X-Linked-ETag` 亦一致。数据集为上游原样拉取、未修改，不入 Git。
- 快照共 **230 题**（其中 mypy **40 题**）；**五道候选全部在快照中**（逐条确认，非按题号推断）。
- 用产品代码 `SWEGymTaskSource` 读取并冻结五题身份（instance / repo / base_commit / 题面字节 / gold 与 test 的字节与文件类型 / FAIL_TO_PASS 与 PASS_TO_PASS 计数 / `raw_record_sha256` 前缀），完整表见[任务 04 行动文档](../../actions/2026-09-19-task-04-catalog-candidates-and-scale.md)。五条记录都通过 `_map_record` 的字段完整性校验。
- 只读查询 Docker Hub 元数据（**未拉镜像**）：**五个镜像都真实存在**，每库一个 `latest` 标签 + digest，压缩后合计约 **4.96 GiB**，解压预计 10–15 GB；本机可用 `D:` ≈19 GB、`C:` ≈16 GB——够但不宽裕。
- `15876` 的额外预检通过：gold patch 改 1 个 `.py`（1303 字节）、test patch 覆盖 8 个 `.test`、FAIL_TO_PASS **6 项**，**不是纯文档修改**；真实判定仍需容器门禁。
- **明确未做**：没有 `docker pull`、没有运行容器、没有把任何新题写进白名单（门禁未跑，白名单仍只有 `python__mypy-15413`）。

## 2026-09-20（晚间补记：本机开发环境与事实更正）

### 已完成

- 拉取上游：`upstream/main` 前进到 `beed93f`（含 B 的 `ff46cec` 工作台合并、D 的连续规模预设与对比端点等）。我的 `lyq` 已包含上游全部提交（落后 0），fork 的 `main` 也已同步；上游 PR #2 仍开着、**0 条评论 0 个评审**。
- **恢复 `http.proxy`**：仓库本地 git 配置里的代理设置已丢失，导致 `git fetch` 直连失败（21s 超时）。按 [ISSUE-01](../04-issues/KNOWN_ISSUES.md) 的记录重新写入 `http.proxy=http://127.0.0.1:7892`，两个远端 fetch 恢复正常。
- **建立本机开发环境**（本轮最大变化）：
  - 装 uv 0.12.17；在 `apps/backend` 执行 `uv sync --frozen` → Python 3.13.15 + 锁定依赖（此前系统只有 3.11.9，`import eval_platform` 直接失败）。
  - 下载并解压便携 PostgreSQL 15.14 到 `D:\pgsql`（320,461,864 字节，sha256 `234ccc7a5cf07fce70f93faea701fd75fad6bec968359b06cdfc208ed7dfbc30`，来源 get.enterprisedb.com），`initdb` 后只监听 `127.0.0.1:55432`，不注册 Windows 服务、不开机自启。
  - 建库：`agentexam_identity_test`（LOGIN+CREATEDB，测试夹具用）、`agentexam_dev`（仅 LOGIN，日常开发用）。
  - 解压用 7-Zip（`D:\7-Zip\7z.exe`）；Windows 自带 `bsdtar` 在这台机器上创建文件失败，已弃用。
- **实测基线**：`tests/catalog` → **33 passed / 7 skipped**（跳过的是需 MinIO 的用例）；全量 `pytest -q` → **452 passed / 36 skipped / 2 failed**（119.75s）。2 个失败是 `tests/contract/test_execution_network.py` 缺 `framework/harbor` 的既有环境失败，与 D 记录的基线同类，非代码缺陷。
- 记录：新建[环境行动文档](../../actions/2026-09-20-local-environment-setup.md)与[本机开发环境](../06-environment/LOCAL_SETUP.md)，并更新 README 与问题记录。**未修改任何产品代码、测试或依赖清单。**

### 开工增量（用户明确要求“直接安排我开工”后实施）

#### 增量 1：目录 → options → 提交 → 冻结 Job 打通链

- 新增 `apps/backend/tests/catalog/test_catalog_job_flow.py`（**只加测试，未改任何产品代码**），补上任务 04 第 6 条里确实没人走过的一段——目录 → HTTP options → 提交 → 冻结 Job/Runs/初始事件：
  1. `test_catalog_and_options_drive_one_frozen_submission`：登记 6 题 + 2 配置 → 读目录列表 → 读 `/api/v1/job-options` → 按选项用 `continuous` 提交 → 断言 `202`、`AWAITING_OWNER_APPROVAL`、`trial_count == 12`；读回详情后断言冻结的题目身份（instance_id / dataset_id / dataset_revision / split / base_commit / problem_statement）与配置指纹与目录记录**逐字段一致**；断言 12 个 Runs 恰好覆盖 题目 × 配置 的笛卡尔积，Job 与每个 Run 都带 `JOB_SUBMITTED`。
  2. `test_frozen_job_keeps_its_snapshot_when_the_catalog_changes`：提交后停用配置 → 旧 Job 冻结快照与状态不变；新提交返回 `409 AGENT_CONFIGURATION_DISABLED`。
- 实测：目录模块 **35 passed / 7 skipped**（改动前 33 passed，新增 2 个）；全量 `pytest -q` **454 passed / 36 skipped / 2 failed**（103.73s，失败的仍是缺 `framework/harbor` 那 2 项，与改动前完全相同，**无回归**）；`ruff check`、`ruff format --check`、`mypy src/eval_platform` 对新增文件均通过。
- 做了**变异检查**确认断言有效（不是空跑）：把 `base_commit` 比对改成必然不等的值、把笛卡尔积期望缩小一格，跑出来 `1 failed, 1 passed`；探针文件已删除。
- 如实记录未覆盖：三步向导的浏览器动线（B 的）、恢复新 Job、双存储一致性（MinIO 集成在本机按设计跳过）、五道候选题的三补丁门禁（需组长机器）。

#### 增量 2：暴露面收敛的 HTTP 层断言

- 修改 `apps/backend/tests/catalog/test_security.py`（只加测试）：新增 `test_hidden_evaluation_fields_never_reach_public_surfaces`——用带哨兵值的合成目录（`HIDDEN_ANSWER` / `hidden_test` / `hidden_pass` / `private-test-reference`，分别来自 `gold_patch`+`test_patch`+原始记录、`fail_to_pass`、`pass_to_pass`、`credential_profile_id`）登记并提交后，逐条请求 **12 个公开读取面**（目录列表与详情、配置列表与详情、`job-options`、Job 列表与详情、批次报告、单 Run 报告、对比报告、制品索引、轨迹），断言哨兵一处都不出现，并用公开题面仍在响应中作为对照（防止"响应为空所以通过"）。
- 实测：目录模块 **36 passed / 7 skipped**；全量 **455 passed / 36 skipped / 2 failed**（104.16s，失败集合不变）；`ruff check`、`ruff format --check` 通过。
- 如实记录：`/runs/{id}/trajectory` 对**未执行**的 Run 返回 **409**（内容尚未产生），用例把拒绝集合显式断言为 `⊆ {trajectory}`，**不把 409 当作通过**；Run 产出制品后的读取路径归 D 的 `test_http_limits.py` / `test_evidence_publication.py`。网页读取面归 B；`leaderboard` 未在本夹具装配，未扫描。
- **变异检查**：把公开题面混进哨兵列表后，用例确实失败（`1 failed`），证明断言真的在扫响应体。
- 同步更新了 04 草案：`Blocked by` 区分题库侧与目录/规模侧、规模侧范围收窄为“核对已有覆盖”（复核后确认无需补测试）、标明「重复 ID 现有行为是去重」需与 D 确认、并记录打通链进展。草案状态如实保留 `needs-info`（数据/镜像/Fork 仍未取得）。

### 核对组长通过微信发来的材料

- 材料位置：`E:\Wechat\...\msg\file\2026-09\`，共三份（zip 与其解压目录内容一致）：`ui-catalog-providers`（4 个文档 + `issues/01`、`issues/02`）、`TEAM_WORK_ALLOCATION.md`、`TEAM_POSTGRESQL_CONNECTION.md`。
- 逐文件对比结果：`ui-catalog-providers` 的 6 个文件与仓库**逐字节相同**（仅 LF 与仓库工作区 CRLF 的差异，用 `diff --strip-trailing-cr` 复核）；`TEAM_POSTGRESQL_CONNECTION.md` 相同；**`TEAM_WORK_ALLOCATION.md` 是仓库更新**——微信版停在 09-19 20:59，规则 7 与 01/02 两行仍是"已规划、未发布 issue"，仓库版已标 01/02 完成。结论：组长这份材料里没有仓库看不到的内容，后续以仓库 `main` 为准。
- 任务单齐全度：组长材料里 `issues/` 仍只有 `01`、`02`；03–08（含 04）都没有任务单，与我此前的结论一致。
- **新发现 1（验收标准与实现冲突）**：[验证规范](../../../.scratch/ui-catalog-providers/verification.md)第 2 节 Q7 原文要求"0/21题、0/4配置、**重复**/停用/未知项拒绝"，而现有实现是**去重**（`tests/jobs/test_security.py:66`）。此前我只把它当作"草案措辞要改"，现在有了权威依据——按 Q7 验收，规模侧现状不满足；这条已写进 ISSUE-05 与 04 草案。
- **新发现 2（preset ID 与地图候选不一致）**：[实现地图](../../../.scratch/ui-catalog-providers/implementation-map.md)第 4.1 节把连续规模的 preset ID 候选写作 `flexible-v2`，而 D 实际落地为 `continuous` 并已合入 `main`。地图原文标明是"候选"，故不算违规，但**地图、D 的实现与 B 待补的 `HTTP_API.md` 受控选项小节三者需要对齐**（`continuous` 已是公开选项取值）。
- 新发现 3（对后续测试归属有用）：实现地图第 3 节已规划 04 的候选测试目录 `apps/backend/tests/catalog/qualification/`（五题参数化资格/隐藏信息/漂移）与 `apps/backend/tests/jobs/submission/`（新规模与旧快照兼容矩阵）。后续 04 测试应落在这两个候选目录，而不是继续往 `tests/catalog/` 平铺。

#### 增量 3：目录 HTTP 的配置列表分页与状态筛选

- 改 `tests/catalog/conftest.py`（`catalog_api` 加可选 `agent_presets`，默认行为与原先完全一致）与
  `tests/catalog/test_http.py`（新增 `test_agent_list_paginates_and_filters_by_state`）。补的缺口：配置列表的
  **游标往返与状态筛选**此前没有测试，而三步向导真实调用是
  `GET /api/v1/agent-configurations?limit=100&agent_type=codex&enabled=true`。
- 实测：目录模块 **37 passed / 7 skipped**；全量 **456 passed / 36 skipped / 2 failed**（失败集合同前，无回归）；
  `ruff check` 与 `ruff format --check` 对改动文件通过；变异检查（改错首页期望与停用侧期望）确实失败，探针已删。
- 附带发现：`agent_type` 被路由接受并做字面量校验（只允许 `codex`），但**不参与过滤**
  （`registry.list` 只接收 `enabled`/`cursor`/`limit`）。因登记路径本身只接受 codex 配置，行为上等价；
  将来新增提供方时需要真正接上过滤。

#### 增量 4（产品代码）：固定候选的镜像身份机制

- 用户决定「不等任务单、直接做 04」后，先做了 04 里**唯一不依赖外部资源**的实现改造。
- 原状：`adapters/tasks/swe_gym.py` 把镜像写死成单一常量 `CANDIDATE_IMAGE`，并在 `_map_record` 里遇到
  `instance_id != CANDIDATE_INSTANCE_ID` 就拒绝——题目目录在代码层只可能有一道题。
- 改法：改为 `FIXED_TASK_IMAGES`（instance_id → 含 digest 的固定镜像身份）查表，未登记一律拒绝；
  `CANDIDATE_IMAGE` 保留为旧题别名，继续服务既有 M0 诊断入口（`preflight.py` 未改动，
  计划要求保留旧题身份与 M0 单题入口）。**白名单内容未变**（仍只有 `python__mypy-15413`），
  门禁通过的题以后加一行即可。
- 新增 `tests/catalog/qualification/test_fixed_task_identity.py`（5 用例，合成 Parquet，
  不读真实数据、不需要容器）。
- 实测：该目录 **5 passed**；全量 **461 passed / 36 skipped / 2 failed**（失败集合同前，无回归）；
  `ruff check`、`ruff format --check`、`mypy src/eval_platform` 通过；两处变异检查都让用例失败。
- 说明：这是本轮第一次改产品代码（前三个增量只加测试）。改动边界刻意收在 1 个文件内，未碰他人文件。

### D 的回复与核实（2026-09-20 深夜）

- D 回复「刻意」，并纠正我的表述：不是 URL 与正文的不对称，对比端点本身遵循统一规则
  **「未知/重复参数键拒绝、值列表去重归一化」**。
- 我逐条核实他给的两处依据，**均属实**：
  - `docs/actions/2026-09-12-m1-job-submission.md` 第 22 行：「题目与配置**去重后计数**；空选择、规模不符、
    非法覆盖在创建前拒绝。」
  - `docs/interfaces/HTTP_API.md` 第 426/430 行：「任务和 Agent 列表**必须非空、去重**」
    「任务/配置列表在规范正文中**去重并排序**；相同规范正文返回原 Job」。
  - 另核实 `report_comparisons.py` 的 `_parse_job_ids` 确实对列表内重复值去重。
- 两处小出入（已回给 D 指出）：他说「plan.md 第 5 节」，实际在**第 6 节第 5 步**（第 5 节是任务 03）；
  HTTP_API 行号在我的版本是 **426/430**（他的 384/388 属版本差异）。
- 结论：**实现不改、改措辞**——请组长把 `verification.md` Q7 与 `plan.md` 第 6 节第 5 步的
  「重复 ID…拒绝」对齐为「重复项去重后计数」。
- D 同时报 `ruff format` 已修：那 5 个文件跑完 format，`--check` 293/293 全绿，受影响用例 8 passed
  （含 4 个真实 PG 门禁用例），diff 为纯格式差异。**该修复不在我当前基线 `beed93f` 上**，
  本地 `ruff format --check` 仍报那 5 个文件；rebase 到含修复的提交后需重新复核，我不替那次复核下结论。
- 环境事实（如实记录）：**本机代理 `127.0.0.1:7892` 与 GitHub 直连在深夜都出现过连不上**，
  `git fetch` 一度既走不通代理也走不通直连；期间我把 `http.proxy` 临时移除又加回。
  当前配置指向代理，能否连通取决于代理是否在运行与线路状态，两种切换方式见 ISSUE-01。本地测试不受影响。

### 事实更正

- **ISSUE-02 已解决**：上游 `main` 现在包含 `issues/01`、`issues/02`，且 `plan.md` 与我手上那份更新版逐字节相同（随 `ff46cec` 于 09-20 20:42 进入上游）。此前「请组长推送更新版」的请求作废。
- **任务 04 的规模侧剩余范围被高估**：逐条查测试后确认「4 个配置被拒」「未知条目被拒」「停用条目被拒」都已有测试（`tests/jobs/scale/test_continuous_preset.py:43`、`tests/jobs/test_security.py:60`、`tests/jobs/test_concurrency.py:58`）；而「重复 ID」的**现有行为是去重而不是拒绝**（`tests/jobs/test_security.py:66` 断言 `trial_count == 1`），我 09-19 草案里写的「重复题目必须拒绝」与之冲突，不能照草案实现。**更正（2026-09-20 复核）**：我当时说「0 个配置」是空白项，是**错的**——`tests/jobs/test_security.py:41-42` 的参数化用例已同时断言 0 题与 0 个配置返回 `400 EMPTY_JOB_SELECTION`；错误来自只查了 D 的规模测试文件就下结论。
- **本机确实没人做过的 C 侧交付**：目录 → HTTP options → 提交 → 冻结 Job / 全部 Runs / 初始事件的事务打通。现有测试只在 `tests/jobs/test_http.py` 断言过 options 的响应形状，没有走完这条链。
- **静态检查基线**：`ruff check .` 全通过；`mypy src/eval_platform` 166 个源文件无问题（直接跑 `mypy` 会因 editable 安装缺 `py.typed` 报错，须给显式路径）；但 `ruff format --check .` **有 5 个文件不合格**——`adapters/persistence/jobs/__init__.py`、`delivery/http/routes/jobs/report_comparisons.py`、`tests/jobs/cancellation/test_cancel_races.py`、`tests/jobs/reporting/test_comparison_http.py`、`tests/jobs/reporting/test_matrix_rehearsal.py`。这 5 个都是 D 近期合入的文件，不是我引入的，我也没有格式化它们（不擅自改他人文件）。
- **共享库仍不可达**（记为 [ISSUE-06](../04-issues/KNOWN_ISSUES.md)）：本机 tailnet 正确（`tail03c757.ts.net`）但 netmap `Peers = 0` 且 `Cached = false`（实时从控制面取回），`sss.tail03c757.ts.net` 解析不到，需 host 侧处理。

### 当前停点

- 环境已就绪；产品代码未开工，未下载任何题目镜像、未调用模型、未连接共享库。
- 任务 04 仍无任务单；下一步是本机可做的那条打通链，以及向组长确认规模侧收口与「重复 ID」的行为取向。

## 2026-09-20

### 已完成

- 确认仓库关系：`Floraluke/agent-exam` 是**个人 fork**，团队上游仓库是 `anphuchoang5-sys/agent-exam`。接入 `upstream` remote 并 fetch；上游 `main` 比我 fork 的 `main` 领先 **21 个提交**，且 fork 没有上游缺的提交（fork 是纯快照）。
- 上游现有分支：`main`、`fengyy-fixweb`（冯颖怡）、`lly/dev`（成员 E）、`xinyue-modules`。上游当前 **0 个 PR**。
- 把我个人的两个提交 rebase 到 `upstream/main`（`a49b000`）。rebase 干净，无冲突。
- 建立个人分支 `lyq`（基于 `upstream/main`）与个人文档目录 `docs/LYQ/`，结构参照成员 E 的 `docs/LLY/` 约定（README + 01-plan + 03-progress + 04-issues，另按分工文档要求加 02-module 放模块架构/契约/接口的个人视图）。
- **确认协作方式为 fork 工作流**（用户 2026-09-20 明确）：在自己 fork 上开发、从 fork 向上游提 PR，**不直接操作上游仓库**。据此把我最初直接推到上游的 `lyq` 分支收回：关闭上游侧 PR 并删除上游侧分支，代码改为推送到 `origin`（fork），PR 改为 `Floraluke:lyq → anphuchoang5-sys:main`。本地 `lyq` 的跟踪目标同时从 `upstream/lyq` 改回 `origin/lyq`。
- 个人视图三份文档的实际来源：`TaskCatalog`/`AgentRegistry` 的调用形状与 7 个 HTTP 端点逐条从 `apps/backend/src/eval_platform/` 代码核对；契约内容取自[模块契约](../../architecture/MODULE_CONTRACTS.md)第 6.2、6.3 节。

### 观察到的事实

- 上游 `main` 的 [`.scratch/ui-catalog-providers/plan.md`](../../../.scratch/ui-catalog-providers/plan.md) 仍是 **09-17 草案版**（表头写「计划草案，未开工」，01、02 未标完成），且没有 `issues/` 目录。而我 09-19 从组长处收到的同目录更新版（plan/spec/implementation-map 更新，任务 01、02 标注完成，含 `issues/01`、`issues/02`）**不在上游任何分支上**。详见[问题记录 ISSUE-02](../04-issues/KNOWN_ISSUES.md)。
- 上游 `main` 09-20 有 12 个新提交（作者 `noachlola`），内容包括任务 03 报告语义设计、对比报告的服务与端点、以及给 08 用的 D 侧 runbook。即：**有人在按单项授权推进 03 方向的工作**，但计划文档尚未同步这个进展。
- **任务 04 的「规模」半已由 D 完成并合入上游**：`delivery/job_presets.py` 第 25–29 行现有四个预设，新增的是 `BatchPreset("continuous", 1, 20)`（既有 `demo`/`quick`/`standard` 区间未改）；配套新增 `apps/backend/tests/jobs/scale/test_continuous_preset.py` 与 `tests/jobs/reporting/test_matrix_rehearsal.py`；行动记录为 `docs/actions/2026-09-20-d-continuous-scale-and-rehearsal.md`，其中明确把受控选项的契约补记留给 B。对我而言：09-19 记的「缺连续 1–20 档位」已被上游现状取代（当时读的是 fork 的旧快照），我的剩余范围需与组长、D 确认，记为 [ISSUE-05](../04-issues/KNOWN_ISSUES.md)。我没有改动 `job_presets.py` 或 D 的测试，避免与其提交冲突。
- 成员 E 的阶段 0 计划明确（该文档在其分支 `upstream/lly/dev` 的 `docs/LLY/01-plan/PLAN.md`，不在上游 `main` 上）：真实执行链（Harbor、SWE-Bench-Fork、固定镜像、`framework/`、`runtime/`）只在组长机器上，不进 Git；开发机只做代码、单元与契约测试、替身验证。这条同样约束我的任务 04。

### 当前停点

- `lyq` 分支已基于上游最新提交，个人文档目录已建立；**产品代码未开工，未下载镜像或数据，未运行容器或模型**。
- 任务 04 仍无开工授权；按顺序先等 `03`（B 主责）完成。

## 2026-09-19

### 已完成

- 从组长处收到更新版规划文档（`TEAM_WORK_ALLOCATION.md`、`ui-catalog-providers` 目录、Navicat 连接教程）。
- 通读我负责模块的权威文档与源码：模块架构、模块契约 6.2/6.3 节、数据模型、HTTP API 第 5/6 节，以及 `catalog_presets.py`、`swe_gym.py`、`job_presets.py`、`domain/jobs/policy.py`、`routes/catalog.py`。
- 核对出任务 04 的机制现状：`TASK_PRESETS` 只有一道题 `swe-gym-lite-mypy-15413`；`AGENT_PRESETS` 只有一个配置 `codex-0153-terra-medium`；`SubmissionPolicy` 已有 `maximum_agent_configurations=3` 与 `maximum_runs=60`，**缺的是「连续 1–20 题」的 `BatchPreset`**（现在只有 `demo` 1–3、`quick` 恰好 5、`standard` 10–20，所以 4 道或 6 道题的请求会被拒）。
- 建立任务 04 的行动文档并按验证规范补出测试设计（目录层、规模层、判卷层、浏览器层四组用例）。
- 建立 `docs/lyq/` 个人文档目录（后于 09-20 按上游约定重命名为 `docs/LYQ/`）。

### 实际结果

- 我 fork 的 `main` 停在 `6dfa2be`，当时误认为是最新；09-20 接入上游后才知道上游已领先 21 个提交。

## 2026-09-18

- 五人分工确定（[团队分工文档](../../architecture/modules/TEAM_WORK_ALLOCATION.md)）。我被分配为成员 C：长期负责「目录与配置」Module，任务 04 的任务 DRI，工时基线 54 h。
- 分工文档同时明确：01–08 仍未发布独立 issue，分工不等于开工；成员可提前阅读自己 Module 和准备测试设计，但不提前修改后续任务代码、不调用真实模型、不下载大体量镜像。
