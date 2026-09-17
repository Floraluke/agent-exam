# 2026-09-17 最小本地持久化实施

## 状态与情况说明

状态：Blocked（2026-09-17 20:56；等待正式对象存储发行版/许可方向决定，目标工具已同步）。P1 配置及 P3 Worker 命令控制切片已验证，但不是完整持久化交付。本行动从用户发布持续目标开始，独立于先前已完成的模块/单机规划行动。交付范围与成功标准以[行动指南](../architecture/modules/owner-host-runtime/ACTION_GUIDE.md)为准；P1–P5 尚未完成，不把基线测试当部署验收。

用户已确认新增 `infra/` 作为本地运行工具箱，并确认从初始化、启停、备份、恢复命令及现有 Worker/存储接口验收。只放部署配置/脚本，不新增业务 Module、Interface 或表。实际工作区为 `E:\9.1agent_exam`；目标文本中的 `E:\9.1agent\_exam` 不存在，按会话既定工作区处理。正式数据根目录尚不存在，未发现需要覆盖的目标目录。

授权：本目标代码、配置、文档与无模型测试；D 盘写入、专属容器部署、整机重启按精确作用域审批。不连接/覆盖旧库、不删除旧数据、不迁移或重启共享 Docker/WSL、不改全局网络、不读真实模型凭据、不消费真实队列、不运行模型或付费。用户末尾“重要节点本地提交”覆盖前文不提交，允许精确本地检查点，仍禁止 push。

开工 HEAD：`19a0b63b66f77c3c860e0bffa8f2905757de321d`。产品源码 tracked diff 为空；旧混合文档、未跟踪规划、缓存与 framework/runtime 全部保留，不整批暂存。后续评审须包括现场权威文档和本行动新增文件，不能只看旧提交中的文档。

新增执行要求：每半小时检查 Codex 账户额度；若剩余 1–4%，先本地提交本目标安全检查点并报告停止。当前工具目录没有自动化或直接额度读取工具；通过[官方 App Server](https://learn.chatgpt.com/docs/app-server) 的 `account/rateLimits/read` 查询。沙箱内两次返回 `-32600`，第二次明确归类为认证不可用；经审批的原生接口查询已成功（2026-09-17 20:26，新加坡时间）：`codex` 主窗口剩余 28%，`codex_bengalfox` 两窗口均 100%。未触发停工阈值；下次持续执行检查最迟 20:56，不以 goal token 数或另一限额池替代。只查询限额，不创建模型 turn、不打开/输出认证文件、不重置登录；辅助进程已退出。未建立后台自动化，暂停后的后台半小时检查不能保证。

## 实施措施

1. P1：固定专属 PG/MinIO 部署配置，明确宿主绑定目录、回环端口、凭据文件、手动启停策略和资源标识；先经 Compose 配置解析验证，再获准测试实际 D 盘落盘与容器重建。不能采用 tmpfs 保存业务数据或静默退回 E 盘默认卷。
2. P2：统一空库前置检查，复用现有四份 schema，避免三个独立 init-db 命令形成不可识别的半初始化；私有 bucket 与最小应用权限显式准备。启动不建表，初始化不覆盖旧数据。
3. P3：深化现有 Worker 单次入口并增加显式受控循环；启停工具只管理本项目身份可验证的进程/容器，不自动批准/重试、不强杀当前 Job。验收关闭真实队列消费。
4. P4：先停写并确认无活动 Job，再生成 PG 逻辑导出、对象副本、版本/摘要清单；恢复只到全新隔离位置，复用应用接口核对身份、Job/Run、报告和对象。失败集不冒记为成功备份。
5. P5：合成数据完成重建保留、恢复、权限和端口验证，交付初学者运行手册。整机重启与跨设备验证依授权/人工窗口执行；未验项保留，不宣布整个目标完成。

每个行为先写失败测试，再最小实现、回归和类型/静态检查。待代码切片形成后按项目要求进行固定基准 Standards/Spec 双轴评审；本次尚未开始评审，不自行新增开发子代理。

## 受影响文件树

P1 配置切片已落盘；正式存储发行版待决定期间，只推进不依赖该选择的 P3 Worker 命令壳，不改变 P1–P5 整体完成标准。下面冻结当前精确树，不以占位代码冒充实现。

```text
infra/                                     # 已获确认：项目专属运行工具箱，不是新业务模块
  compose.yaml                             # P1：双存储持久挂载、回环端口、凭据文件与手动重启策略
  .env.example                             # P1：镜像身份、数据路径与端口模板，无秘密
  tests/
    test_compose_config.py                 # P1：通过真实 Compose config 命令验收可观察配置
  local/                                   # 后续：初始化/启停/备份恢复入口；实现前细化，不先创建空目录
apps/backend/src/eval_platform/delivery/worker/
  runtime.py                               # 既有 Composition Root；主入口委托内部命令壳，延迟生产装配
  command.py                               # 新增内部实现：默认单次、显式循环、停领与安全错误输出
apps/backend/tests/jobs/runtime/
  test_worker_command.py                   # 新增：在已确认 Worker 命令入口使用假 Worker 验收控制流程
docs/actions/2026-09-17-minimal-local-persistence.md # 本行动及实际验证、偏差、检查点
docs/architecture/modules/owner-host-runtime/
  ACTION_GUIDE.md                           # 用户目标已生效、P1–P5 完成度与操作边界
  ARCHITECTURE.md                           # 现实部署树和已确认目录/命令职责
.scratch/persistence-deferred/spec.md        # 已开工及剩余门禁指针
HANDOFF.md                                  # 最新目标、执行证据、尚未完成项与下一停点
```

配置消费关系：owner 本地命令 → 本项目 Compose 配置 → PG/MinIO；现有应用 Repository 与 ArtifactStore Adapter 继续负责业务读写。Worker runtime 仍是生产依赖的 Composition Root，不把部署逻辑塞入业务用例。首片不引入新依赖，不修改第三方源码。

Worker 控制关系：原 `agentexam-worker` → runtime 主入口 → 内部 command → 既有 WorkerShell.run_once；工厂调用延迟到参数与停止检查后，假 Worker 是命令控制测试的替身，不装配凭据/Harbor。新文件位于已存在 worker/runtime 测试目录，不新增业务 Module、Interface、表或目录。现有 PostgreSQL claim 仍唯一决定 QUEUED 可领、单活动 Job 与排序，循环不自行批准/重试。默认单次的 JSON 与退出码保持兼容。

P3 本片验收：预存停止标记不得装配真实依赖；显式 `--loop --stop-file <绝对路径>` 顺序执行；任务中产生停止标记则当前 run_once 正常返回、下一轮不领取；无任务等待一秒，不忙轮询；异常立即退出且不打印敏感异常、不自动重试；相对路径/缺少停止路径拒绝。标记检测与数据库 claim 不是原子操作，最后检查后已经进入的领取仍可能完成，该竞争边界必须实测并在指南明确。标记只读不删除；启动命令今后显式管理旧标记，不在 Worker 内擅自清除。

## 自验证方式与成功标准

- 使用真实 `docker compose config --format json` 解析受控合成变量，断言业务目录为 bind mount、宿主路径在指定根内、缺失根/镜像配置失败、端口只绑定回环、无自动启动、无 Docker socket/宿主广域挂载。此命令不创建容器、不连接旧库。
- 后续实际 `docker inspect` 挂载与合成数据重建/恢复证据必须独立记录；配置测试通过不等于运行安全/持久化通过。
- 初始化后从现有应用接口读回；非空库拒绝且原账号仍可用；故障不产生可误认为成功的半初始化。
- Worker 假存储/执行测试覆盖默认单次、空闲、停止、故障退出和零自动重试；不装配真实凭据。
- 备份恢复核对完整记录及文件 SHA-256，拒绝旧目标、损坏清单与不完整备份。
- 每片检查文件行数/目录文件数、Ruff/Mypy（适用源文件）、文档链接与 `git diff --check`；本地提交前精确核对暂存集合，不包含缓存、秘密、数据或旧混合文档。

## 自验证情况

已核对现实 owner/catalog/jobs 初始化与底层事务：身份两份 schema 在同一事务，目录和 Job 分别在各自事务；直接串行调用可能留下先前已成功部分，需要正式初始化协调，不改旧业务规则。

2026-09-17 基线命令（`apps/backend`，禁用 pytest 插件自动装载与字节码，`-p no:cacheprovider`）：

```text
.venv/Scripts/python.exe -B -m pytest -q -p no:cacheprovider --tb=short -m "not integration" tests/jobs/runtime/test_worker_runtime.py tests/identity/test_owner_recovery.py
```

结果：8 passed、1 deselected、2 warnings，pytest 1.16 秒、命令退出 0。选中的测试使用合成值/内存依赖，不连接真实存储、读取真实认证或启动模型；被排除的是实际 PG 测试。两条现有警告分别为 Starlette/httpx 和 AnyIO 别名弃用，不为此扩大依赖升级范围。

只读 CLI 检查：Compose 为 `v2.32.4-desktop.1`，Docker Client 为 `27.5.1`。首次 Docker 用户配置与 daemon pipe 受沙箱权限拒绝；随后获准的 `desktop-linux` 只读检查得到 Server **27.5.1**。现有 `postgres:15-alpine`、`agentexam-minio-test:7aac2a2c-go1.26.8` 镜像仍存在，任务 14 两个专属容器处于 Exited；未连接、启动、删除或改动它们，也不据此判定整个旧环境健康。

部署风险：既有 MinIO 固定镜像仅批准用于隔离合成测试，CE 归档和已知风险见[现有调研](../research/2026-09-12-minio-m1-baseline.md)及[依赖基线](../dependencies/DEPENDENCIES.md#23-任务-03-对象存储依赖复核)。本轮官方仓库复核仍为归档，不把旧测试批准扩为正式部署许可；版本/支持或明确风险处置是部署前门禁。当前只准备参数化配置，不能默认为该旧镜像可正式上线。

### P1 配置切片实际证据

实际新增 `infra/compose.yaml`、`infra/.env.example` 和 `infra/tests/test_compose_config.py`。密码仅通过精确的只读文件挂载；根目录和镜像未指定时拒绝解析，模板镜像留空；业务目录不自动创建。PostgreSQL 的文件密码入口经官方 entrypoint 查证，MinIO 经固定源码归档 `cmd/common-main.go` 查证，未臆造 `_FILE` 参数。PG 配置采用 15 系列数据布局，具体正式镜像未选定，不能替换为 18 系列直接启动。

命令（仓库根；禁插件自动装载、字节码及 pytest 缓存）：

```text
apps/backend/.venv/Scripts/python.exe -B -m pytest -q -p no:cacheprovider --tb=short infra/tests/test_compose_config.py
```

逐片红绿：缺少 compose 文件 → 1 failed → 1 passed；缺少 MinIO 服务 → 1 failed/1 passed → 2 passed；缺少手动重启策略 → 1 failed/2 passed → 3 passed；缺少文件密码配置 → 1 failed/3 passed → 4 passed；缺少禁止提权配置 → 1 failed/7 passed → **8 passed**（1.15 秒）。另外三项为已有必填变量行为的回归检查，不冒称产生过红灯。所有检查仅运行真实 Compose 配置解析，无 daemon 工作负载、真实凭据或模型。

Ruff 初检发现两处长行、format 检查失败；已运行项目配置的格式化，复检 `ruff check --config apps/backend/pyproject.toml --no-cache infra/tests/test_compose_config.py` 为 All checks passed，`ruff format --check` 为 1 file already formatted。配置文件并非完整部署入口：初始化/启停/备份恢复、目录 ACL、固定版本、资源约束与实际容器验收均未完成。`127.0.0.1` 不等于真实隔离，Docker <28 风险仍依据[官方说明](https://docs.docker.com/engine/network/port-publishing/) 保留门禁。

最终配置回归 **8 passed / 1.10 秒**，Ruff lint/format 复检通过，`git diff --check` 通过（仅既有 LF/CRLF 提示）。新测试文件 147 行，infra 根 2 个文件、tests 1 个文件，未超源文件/目录指标。本片无新增产品 Python 代码，未另跑产品 Mypy、全量回归或双轴评审；这些不冒记为通过，仍在后续实现验收范围。

本行动、指南、模块架构、P 规格与 HANDOFF 的本地链接目标全部存在（未自动验证段落锚点）。首次精确 `git add` 因 `.git/index.lock` 沙箱权限失败；获准后只暂存上述三份新配置/测试和本行动，共四文件，暂存 `diff --check` 通过。其他文档同步保留工作区，未混入旧改动；检查点提交身份在 git log 和 HANDOFF 记录。

D 盘写入、真实重建、备份恢复与端口验收：Pending。尚未创建正式数据目录、启动服务或调用模型。重要节点仅提交本行动和新增配置/测试；原有混合文档仍保留工作区，暂不整批纳入提交。正式 MinIO 风险处置需要用户决定；未把保留产品选型等同于接受已知漏洞用于正式数据。

### 最新用户条件与安全核对

用户补充“漏洞如果不严重就用”，这是条件性允许，不是接受高危风险。2026-09-17 重读 [MinIO 官方 GHSA-hv4r-mvr4-25vw](https://github.com/minio/minio/security/advisories/GHSA-hv4r-mvr4-25vw)：CVSS 4.0 **8.8 / High**，涉及普通对象和分片写入的认证绕过；可达服务且知道有写权限的 access key 与 bucket 名时，无需 secret key 或有效签名即可冒用该身份写对象。不是仅影响未使用的 LDAP/多节点功能。

只读 `tar -xOf` 核对既有固定源码归档的 `cmd/object-handlers.go` 和 `cmd/object-multipart-handlers.go`，两处仍使用通告所述的 Authorization 头存在性作为 unsigned-trailer 签名验证条件。未运行漏洞利用；结合官方通告，不能满足用户“不严重”的放行条件。强密码、单节点和备份都不是该缺陷的修复；网络隔离会影响可利用性，但本机尚未有足够隔离验收证据。

候选最小替代：仍保留 MinIO/S3 Adapter 与单机/D 盘架构，核对官方已修复的 AIStor Free 发行版。[官方许可文档](https://docs.min.io/aistor/operations/licenses/) 说明 Free 可用于单节点，但须有效许可证，与原 CE 不同；尚未下载、注册、接受协议、付费或更换镜像。先请用户确认是否采用这条发行版方向，不把有免费方案写成已经拿到许可证或所有漏洞均已修复。

### P3 独立命令控制切片

接续审计：上轮有实质进展（配置、验证与本地提交 `477c281`），不是运行中的后台作业。重新核对 git 和源码，未收到新的发行版确认；正式部署保持暂停，仅推进不依赖发行版、已获目标授权的命令壳，不把这一配套切片代替持久化交付。

已接回 runtime 的既有主入口。默认单次行为及 JSON 保留；显式循环每轮只调用一次 run_once，空闲等一秒。启动前已有停止标记时不装配生产依赖，装配期间产生标记则首次领取也不开始；当前轮内产生标记不打断该轮，返回后不进入下一轮。停止目录不存在/不可访问时安全退出，标记不删除；异常退出 2、只输出安全状态，不重试、不自动批准。文件检查与数据库 claim 之间仍有已说明的竞争窗口，不承诺标记创建瞬间原子阻断一轮已经开始的领取。

红绿记录：不存在 command 模块时 collection error → 单次 1 passed；无 loop 参数时 1 failed/1 passed → 2 passed；未循环时 1 failed/2 passed → 3 passed；未等待时 1 failed/3 passed → 4 passed；非法停止参数三例 3 failed/4 passed → 7 passed；原 runtime 未接线时 1 failed/9 passed → 14 passed（含原四项 runtime）；停止目录缺失仍尝试装配时 1 failed/10 passed → 最终 **16 passed**（含默认空队列回归、原四项 runtime），pytest 0.07 秒。异常去敏和装配途中停止原逻辑已通过，属于补充回归，不虚构红灯。

命令均在 `apps/backend`，禁插件自动装载、字节码及 pytest 缓存：

```text
.venv/Scripts/python.exe -B -m pytest -q -p no:cacheprovider --tb=short tests/jobs/runtime/test_worker_command.py tests/jobs/runtime/test_worker_runtime.py
.venv/Scripts/python.exe -B -m ruff check --no-cache src/eval_platform/delivery/worker tests/jobs/runtime/test_worker_command.py
.venv/Scripts/python.exe -B -m ruff format --check --no-cache src/eval_platform/delivery/worker/command.py tests/jobs/runtime/test_worker_command.py
.venv/Scripts/python.exe -B -m mypy --no-incremental src/eval_platform
```

Ruff 首次长行失败已修正；Mypy 首次识别 optional stop_path 两处类型错误已修正，局部 2 文件通过；显式源码范围全后端 **162 文件通过**。format 最后一次检查发现新增测试需格式化，已格式化并复检 2 文件 unchanged。原两条 Starlette/AnyIO 弃用警告保留，不升级依赖。

校验入口限制：不带路径直接运行 Mypy 时无法识别已安装包的 py.typed；指定 `src/eval_platform` 后通过。当前 venv 不存在 `agentexam-worker.exe`，没有擅自安装/重建环境；明确 `PYTHONPATH=src` 后使用 `python -m eval_platform.delivery.worker.runtime --help` 成功显示 loop/stop 参数，没有实例化生产 Worker。后续正式启动工具须确定模块启动环境，不能假设 console exe 已安装。源码 68/161 行，新测试 190 行；两个目录各 4 文件，未超过指标。统一进程管理、真实 Worker、全量产品测试和部署仍未验收。

最终组合检查：在上述 Worker 两个测试文件外追加 `../../infra/tests/test_compose_config.py`，显式 `-c pyproject.toml`，结果 **24 passed / 2 warnings / 1.19 秒**；Ruff lint/format 通过，局部 diff whitespace 检查通过。帮助输出首次中文编码不匹配，指定 `PYTHONUTF8=1` 后参数与中文帮助均正常。此轮只提交 command、runtime、本片测试与本行动；正式发行版仍待用户决定，未写 D 盘、部署容器、调用模型或把目标标为完成。

本地 Worker 检查点为 `d069511`，只有计划四文件，无推送；重命名测试说明后再次组合检查仍 **24 passed / 2 warnings / 1.17 秒**。2026-09-17 **20:53** 再次经审批查询账户额度：`codex` 主窗口剩余 **26%**，其他已返回限额池仍 100%，未触发停工阈值；持续执行的下次检查最迟 **21:23**。查询辅助进程已退出，没有后台模型请求或自动化。当前正式部署待用户确认发行版；目标未完成。

### 停止审计与恢复条件

同一正式存储决定已连续三轮未关闭：第一轮完成配置和风险核对，第二轮继续完成可独立的 Worker 控制，第三轮重新检查 git、行动与配置，仍无新的用户选择，镜像模板仍有意留空。上轮归类为“实质进展”；本轮是受阻核对，不是轮询已启动的部署，也不把重复状态说明计为实现进展。

目标要求遇到必须由用户决定的事项等待。不能把“漏洞不严重才用”扩大成接受 High/8.8，不能自行改用不同许可的 AIStor，也不能通过付费服务、旁路代理或共享 Docker 变更绕过。正式存储初始化、统一启停、备份恢复与真实 D 盘验收须先确定可部署发行版；当前停止在该门禁，不继续生成未经选择验证的部署方案。目标已置为 blocked，未置为 complete。

最小恢复输入：用户确认是否采用官方修复版 AIStor Free 方向。确认方向后仍须核对具体版本、免费许可取得方式和本机兼容性；需要用户接受条款或账户操作时另明确说明，不能把方向确认当作代为签署协议。Docker 端口隔离、D 盘写入、实际重建/恢复和重启窗口等门禁继续保留。暂停期间没有后台额度自动化；恢复时先核对额度再继续，不沿用旧百分比。
