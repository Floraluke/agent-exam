# 2026-09-17 最小本地持久化实施

## 状态与情况说明

状态：In progress（2026-09-17；用户已明确“继续目标”，恢复 P1–P4 实施，不恢复已取消的备份与恢复）。AIStor Free 修复版方向及官方版本/许可核对已完成；许可真实性及服务端有效性仍须验证。P1 配置及 Worker 命令控制切片已有阶段证据，但不是完整持久化交付。本行动从用户发布持续目标开始，独立于先前已完成的模块/单机规划行动。交付范围与成功标准以[行动指南](../architecture/modules/owner-host-runtime/ACTION_GUIDE.md)为准；不把基线测试当部署验收。

用户已确认新增 `infra/` 作为本地运行工具箱，并确认从初始化、启停、状态命令及现有 Worker/存储接口验收。只放部署配置/脚本，不新增业务 Module、Interface 或表。用户后来明确取消备份、导出、恢复命令和恢复演练：这是课设范围裁剪，不是已经具备备份能力。实际工作区为 `E:\9.1agent_exam`；目标文本中的 `E:\9.1agent\_exam` 不存在，按会话既定工作区处理。D 盘根目录及 private 子目录现已为保存许可而创建；尚无 PostgreSQL/MinIO 业务数据目录或服务，不是已完成业务落盘。

授权：本目标代码、配置、文档与无模型测试；D 盘写入、专属容器部署、整机重启按精确作用域审批。不连接/覆盖旧库、不删除旧数据、不迁移或重启共享 Docker/WSL、不改全局网络、不读真实模型凭据、不消费真实队列、不运行模型或付费。用户末尾“重要节点本地提交”覆盖前文不提交，允许精确本地检查点，仍禁止 push。

开工 HEAD：`19a0b63b66f77c3c860e0bffa8f2905757de321d`。产品源码 tracked diff 为空；旧混合文档、未跟踪规划、缓存与 framework/runtime 全部保留，不整批暂存。后续评审须包括现场权威文档和本行动新增文件，不能只看旧提交中的文档。

新增执行要求：每半小时检查 Codex 账户额度；若剩余 1–4%，先本地提交本目标安全检查点并报告停止。当前工具目录没有自动化或直接额度读取工具；通过[官方 App Server](https://learn.chatgpt.com/docs/app-server) 的 `account/rateLimits/read` 查询。沙箱内返回认证不可用，经审批的原生接口查询成功。最新检查为 **2026-09-17 22:20（新加坡时间）**：`codex` 主窗口剩余 **19%**，未触发停工阈值；持续执行的下次检查最迟 **22:50**。恢复后的首个原生查询脚本因异步流重复读取失败，第二次虽取得响应但错误按旧字段解析为空，第三次只输出非敏感 `rateLimits` 字段并确认 `primary.usedPercent=81`；这些是检查方法失败，不是账户额度异常。历史 20:26 为 28%、20:53 为 26%、21:01 为 25%、21:34 为 21%；不以 goal token 数或另一限额池替代。只查询限额，不创建模型 turn、不打开/输出认证文件、不重置登录；辅助进程已退出。

## 实施措施

1. P1：固定专属 PG/MinIO 部署配置，明确宿主绑定目录、回环端口、凭据文件、手动启停策略和资源标识；先经 Compose 配置解析验证，再获准测试实际 D 盘落盘与容器重建。不能采用 tmpfs 保存业务数据或静默退回 E 盘默认卷。
2. P2：统一空库前置检查，复用现有四份 schema，避免三个独立 init-db 命令形成不可识别的半初始化；私有 bucket 与最小应用权限显式准备。启动不建表，初始化不覆盖旧数据。
3. P3：深化现有 Worker 单次入口并增加显式受控循环；启停工具只管理本项目身份可验证的进程/容器，不自动批准/重试、不强杀当前 Job。验收关闭真实队列消费。
4. P4：用合成数据完成正常停止/启动、容器重建后保留、权限和端口验证，交付初学者运行手册。整机重启与跨设备验证依授权/人工窗口执行；未验项保留，不宣布整个目标完成。

每个行为先写失败测试，再最小实现、回归和类型/静态检查。待代码切片形成后按项目要求进行固定基准 Standards/Spec 双轴评审；本次尚未开始评审，不自行新增开发子代理。

## 受影响文件树

P1 配置和 P3 Worker 命令壳切片已落盘，AIStor Free 私有许可文件已保存；后续继续固定镜像与实际接入验收。用户取消备份恢复后，整体完成标准改为 P1–P4。下面冻结当前精确树，不以占位代码冒充实现。

```text
infra/                                     # 已获确认：项目专属运行工具箱，不是新业务模块
  compose.yaml                             # P1：双存储持久挂载、回环端口、凭据文件与手动重启策略
  .env.example                             # P1：镜像身份、数据路径与端口模板，无秘密
  tests/
    test_compose_config.py                 # P1：通过真实 Compose config 命令验收可观察配置
  local/                                   # 后续：初始化/启停/状态入口；实现前细化，不先创建空目录
apps/backend/src/eval_platform/delivery/worker/
  runtime.py                               # 既有 Composition Root；主入口委托内部命令壳，延迟生产装配
  command.py                               # 新增内部实现：默认单次、显式循环、停领与安全错误输出
apps/backend/tests/jobs/runtime/
  test_worker_command.py                   # 新增：在已确认 Worker 命令入口使用假 Worker 验收控制流程
docs/actions/2026-09-17-minimal-local-persistence.md # 本行动及实际验证、偏差、检查点
docs/research/2026-09-12-minio-m1-baseline.md  # 保留 CE 历史，新增 AIStor Free 官方版本/许可取得核对
docs/dependencies/DEPENDENCIES.md            # 区分历史测试输入、正式发行方向和未部署的固定版本候选
docs/operations/LOCAL_DOCKER_ENVIRONMENT.md   # 记录限定 D/E 余量检查，不重新扫描私人目录
docs/architecture/modules/owner-host-runtime/
  ACTION_GUIDE.md                           # 用户目标已生效、P1–P4 完成度与操作边界
  ARCHITECTURE.md                           # 现实部署树和已确认目录/命令职责
.scratch/persistence-deferred/spec.md        # 已开工及剩余门禁指针
HANDOFF.md                                  # 最新目标、执行证据、尚未完成项与下一停点
D:/AgentExamData/private/minio.license       # 用户明确要求代保存的私有许可；仓库外，不提交、不输出正文
```

配置消费关系：owner 本地命令 → 本项目 Compose 配置 → PG/MinIO；现有应用 Repository 与 ArtifactStore Adapter 继续负责业务读写。Worker runtime 仍是生产依赖的 Composition Root，不把部署逻辑塞入业务用例。首片不引入新依赖，不修改第三方源码。

Worker 控制关系：原 `agentexam-worker` → runtime 主入口 → 内部 command → 既有 WorkerShell.run_once；工厂调用延迟到参数与停止检查后，假 Worker 是命令控制测试的替身，不装配凭据/Harbor。新文件位于已存在 worker/runtime 测试目录，不新增业务 Module、Interface、表或目录。现有 PostgreSQL claim 仍唯一决定 QUEUED 可领、单活动 Job 与排序，循环不自行批准/重试。默认单次的 JSON 与退出码保持兼容。

P3 本片验收：预存停止标记不得装配真实依赖；显式 `--loop --stop-file <绝对路径>` 顺序执行；任务中产生停止标记则当前 run_once 正常返回、下一轮不领取；无任务等待一秒，不忙轮询；异常立即退出且不打印敏感异常、不自动重试；相对路径/缺少停止路径拒绝。标记检测与数据库 claim 不是原子操作，最后检查后已经进入的领取仍可能完成，该竞争边界必须实测并在指南明确。标记只读不删除；启动命令今后显式管理旧标记，不在 Worker 内擅自清除。

## 自验证方式与成功标准

- 使用真实 `docker compose config --format json` 解析受控合成变量，断言业务目录为 bind mount、宿主路径在指定根内、缺失根/镜像配置失败、端口只绑定回环、无自动启动、无 Docker socket/宿主广域挂载。此命令不创建容器、不连接旧库。
- 后续实际 `docker inspect` 挂载与合成数据在停止/启动、容器重建后的读回证据必须独立记录；配置测试通过不等于运行安全/持久化通过。
- 初始化后从现有应用接口读回；非空库拒绝且原账号仍可用；故障不产生可误认为成功的半初始化。
- Worker 假存储/执行测试覆盖默认单次、空闲、停止、故障退出和零自动重试；不装配真实凭据。
- 正常停止/启动及容器重建后，使用同一合成账号、Job/Run、报告和对象摘要核对持久化；该验证不证明误删或磁盘损坏后可恢复。
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

Ruff 初检发现两处长行、format 检查失败；已运行项目配置的格式化，复检 `ruff check --config apps/backend/pyproject.toml --no-cache infra/tests/test_compose_config.py` 为 All checks passed，`ruff format --check` 为 1 file already formatted。配置文件并非完整部署入口：初始化/启停、目录 ACL、固定版本、资源约束与实际容器验收均未完成。`127.0.0.1` 不等于真实隔离，Docker <28 风险仍依据[官方说明](https://docs.docker.com/engine/network/port-publishing/) 保留门禁。

最终配置回归 **8 passed / 1.10 秒**，Ruff lint/format 复检通过，`git diff --check` 通过（仅既有 LF/CRLF 提示）。新测试文件 147 行，infra 根 2 个文件、tests 1 个文件，未超源文件/目录指标。本片无新增产品 Python 代码，未另跑产品 Mypy、全量回归或双轴评审；这些不冒记为通过，仍在后续实现验收范围。

本行动、指南、模块架构、P 规格与 HANDOFF 的本地链接目标全部存在（未自动验证段落锚点）。首次精确 `git add` 因 `.git/index.lock` 沙箱权限失败；获准后只暂存上述三份新配置/测试和本行动，共四文件，暂存 `diff --check` 通过。其他文档同步保留工作区，未混入旧改动；检查点提交身份在 git log 和 HANDOFF 记录。

D 盘写入、真实重建保留与端口验收：Pending。尚未创建正式数据目录、启动服务或调用模型。重要节点仅提交本行动和新增配置/测试；原有混合文档仍保留工作区，暂不整批纳入提交。正式 MinIO 风险处置需要用户决定；未把保留产品选型等同于接受已知漏洞用于正式数据。

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

### 历史停止审计与恢复条件（已由后续选择解除）

同一正式存储决定已连续三轮未关闭：第一轮完成配置和风险核对，第二轮继续完成可独立的 Worker 控制，第三轮重新检查 git、行动与配置，仍无新的用户选择，镜像模板仍有意留空。上轮归类为“实质进展”；本轮是受阻核对，不是轮询已启动的部署，也不把重复状态说明计为实现进展。

目标要求遇到必须由用户决定的事项等待。不能把“漏洞不严重才用”扩大成接受 High/8.8，不能自行改用不同许可的 AIStor，也不能通过付费服务、旁路代理或共享 Docker 变更绕过。正式存储初始化、统一启停、备份恢复与真实 D 盘验收须先确定可部署发行版；当前停止在该门禁，不继续生成未经选择验证的部署方案。目标已置为 blocked，未置为 complete。

最小恢复输入：用户确认是否采用官方修复版 AIStor Free 方向。确认方向后仍须核对具体版本、免费许可取得方式和本机兼容性；需要用户接受条款或账户操作时另明确说明，不能把方向确认当作代为签署协议。Docker 端口隔离、D 盘写入、实际重建/恢复和重启窗口等门禁继续保留。暂停期间没有后台额度自动化；恢复时先核对额度再继续，不沿用旧百分比。

### 采用 AIStor Free 后恢复（20:58）

用户明确“采用 MinIO AIStor Free 修复版方向”，解除原发行版选择阻点；仍保留本机/D 盘/S3 Adapter，不切云、不付费、不迁共享 Docker。方向确认不等于已取得有效许可证或代为接受条款。先核对官方精确版本、镜像固定身份、免费许可取得方式和必要的 Windows 挂载条件，再开展专属部署审批与验证。

按 research 技能委派一个限定调研子代理，只查官方版本、安全修复、Free 许可获取/到期规则；将结果追加到已有 MinIO 研究记录并保留 CE 历史。主代理继续本地配置/初始化条件核对，避免重复研究；不委派执行部署、下载、签署、账户注册或模型调用。若出现新的用户操作门禁，按恢复后的新阻塞审计计数，不沿用旧三轮计数直接停止。

本片只更新上述文档，验证方式为检查官方出处、当前与历史状态区分、本地 Markdown 链接目标、精确 diff 和 `git diff --check`；不因文档更新重跑产品测试或生成部署成功证据。恢复后的额度已更新到开头。21:05 左右仅用 `Get-PSDrive -Name D,E` 与 `Test-Path -LiteralPath D:\AgentExamData` 核对余量/目标存在性，没有遍历私人目录；数值由本机环境第 2.1 节唯一维护，目标仍不存在。

PostgreSQL 继续 15 系列；官方 [15.19 发布说明](https://www.postgresql.org/docs/release/15.19/) 包含相对 15.18 的安全修复，作为新部署候选而非擅自升级旧库。只读查询 Docker Hub 官方标签 API 成功，固定身份/大小记入依赖总表；普通沙箱 HTTP 的 socket 权限错误经限定只读审批后解除。未拉镜像、连接旧库或启动容器；新镜像的实际运行、UID、Windows 挂载和兼容性尚未验证。

### AIStor 官方核对完成，等待用户取得免费许可

研究结果已写入[MinIO 调研第 6 节](../research/2026-09-12-minio-m1-baseline.md#6-2026-09-17aistor-free-修复版方向核对)：官方当前标准发行候选为 `RELEASE.2026-09-07T08-39-31Z`，七项已记录的 2026 年通告有对应修复发行；这是官方版本范围证据，不是制品漏洞扫描或实际运行验收。镜像 digest、制品运行身份和应用兼容性仍未验证。Free 为单节点、官方说明不到期，不能误用下载页的两个月 Trial；许可证文件挂载与 server 的 `--license` 参数已有官方出处，配置接线尚未实施。

新的具体停点是**用户亲自阅读/接受 Free 条款并领取许可证文件**，不是再次选型。官方协议规定下载、安装或使用即接受，故目前不拉镜像、不注册、不填写/提交用户资料。已提供官方定价页 Free → Get Started Free 的最小入口；表单实际必填字段、个人邮箱接受情况和邮件时延未实测。用户领到后仅提供私有文件路径，不贴正文；后续许可核验只记录脱敏结果，不能整段输出可能含 API Key 的 `mc license info`。

本次仅文档与官方只读核对，没有产品代码改动、产品测试、D 盘写入或服务部署。已修正 HANDOFF 中仍称选型未确认的当前描述，保留此前停止审计为历史；指南/架构/P 规格/依赖和容量文档同步。P1–P5 仍未完成，持久目标保持 active；恢复后的首次许可等待不沿用旧阻塞计数直接标 blocked。未安排后台工作或额度自动检查，用户完成该步骤后再继续实际部署。

文档验证实际结果：8 份本片文档共 243 个本地链接目标全部存在（未验证段落锚点）；`git diff --check -- <上述文档>` 通过，仅有 LF/CRLF 提示。核对研究与行动 diff 后，只提交这两份文件的选型/许可检查点 **`35a62a6`**；暂存集合与允许集合一致、暂存 diff 检查通过、提交后暂存区为空，无推送。其余同步文档混有开工前增量，留工作区，不整批纳入；本段提交结果回填也保留工作区。未运行产品全量回归或双轴代码评审，本片无代码变更。

### 恢复后的许可阻点审计与停止（21:19）

从用户确认 AIStor Free 后重新计数：第一轮完成官方研究、文档同步和 `35a62a6`，属于实质进展，但已报告需要用户亲自取得许可；第二轮只读复核交接、配置与 git，仍未收到许可路径，属于无新增进展，不是轮询运行中的作业；第三轮再次核对行动/交接/检查点，用户没有提供新的许可结果，同一条件仍在。自动接续不构成许可接受或账户申请授权；没有已启动的镜像拉取/部署任务可等待。

本轮按目标的三轮规则将状态置为 blocked，停止自动接续，不标 complete、不缩减 P1–P5。现有可独立的配置、Worker 控制和官方准备证据已保留；不能代用户提交个人信息或接受条款，也不回退旧 CE/临时 Trial 绕过。最小恢复输入仍是用户自行完成 Free 许可取得后提供**私有文件路径**，不发送正文。恢复后先核对额度与许可状态，再按原范围进行镜像/挂载/初始化/重建及恢复验收。

本轮只同步本行动与 HANDOFF 的停点，不新增代码/测试或部署；两文件 `git diff --check` 通过（仅 LF/CRLF 提示），目标工具已返回 blocked，未返回 complete。范围与文件职责沿用上方行动树；停止检查点只纳入本行动，HANDOFF 含旧混合增量，继续保留工作区，提交身份以 git log 为准。21:19 尚未到上次额度检查后 30 分钟；暂停后不安排后台额度查询，恢复时重新检查。

### 用户提供许可文本后的文件检查（21:25）

目标已再次为 active，随后用户在聊天中提供许可证文本。本记录不复制正文、个人字段、许可标识或签名，也不把收到文本当作签名/有效性验证通过。已请用户将官方原始文件保存到 `D:\AgentExamData\private\minio.license` 并只回复路径，避免聊天转义改变内容；不再声称用户尚未取得任何许可材料。

本轮仅对上述文件及 `D:\AgentExamData` 运行 `Test-Path`，两项均为 False；没有遍历私人目录、读取许可正文或写 D 盘。当前缺口是私有文件落地及后续验证，不是重新选型。最新已提交检查点为 `d84cb26`；保持全部五项目标，不以收到文本冒充部署完成。仅同步本行动与 HANDOFF，两文件 `git diff --check` 已通过（仅 LF/CRLF 提示）；无代码/测试/容器或模型操作。本次恢复按新的实际状态审计，不直接套用此前 blocked 计数。

### 用户明确要求代保存许可证（21:28）

用户明确“你直接保存不就行了”，授权将其提供的许可保存到约定私有文件，不再要求用户自行创建。执行范围仅 `D:\AgentExamData`、其 `private` 子目录与 `minio.license`，先核对精确路径/不存在冲突/无重解析点，再按环境审批创建并限制 private ACL（当前 Windows 用户及 SYSTEM）；不覆盖已有许可，不修改旧 D/E Docker 数据或全局设置。许可证通过 apply_patch 写入仓库外目标，不落到仓库或临时源码文件，不在输出中复述正文/个人字段。

保存时只去除聊天格式中的下划线转义及首尾空白，不改变签名令牌的其他字符；若三段结构或字符集不符则拒绝。保存后核对存在性、长度/结构、受限 ACL 和脱敏许可声明（仅产品/计划/试用标志/节点数），这些不是密码学验签或服务端有效性证明。未另外执行原文逐字节比较，不能把长度检查写成完整身份认证；服务端验签仍为后续门禁。

**实际结果（21:39）：** `minio.license` 已通过 apply_patch 写入上述仓库外路径，没有覆盖旧文件。新建 private 目录初次 ACL 检查为 owner/SYSTEM，随后沙箱写入流程附加了访问规则，文件所有者也与当前 Windows 用户不同，因此第一次文件 ACL 检查失败。两次 PowerShell `Set-Acl` 修正均因 `SeSecurityPrivilege` 被拒绝，未提升系统特权；使用 `icacls` 成功修正文件所有者和显式访问规则，目录移除第二条附加规则返回非零。只读复核证实文件已有正确两条规则，目录尚有三条；最终使用 `.NET FileSystemAclExtensions.SetAccessControl` 并仅设置 `AccessControlSections.Access` 修正目录 DACL，不重设所有者/审计权限。

最终同一获准进程的检查退出 0：目录和文件均归当前 Windows 用户、禁止继承、各仅 owner/SYSTEM 两条允许规则；文件结构/预期长度符合，脱敏声明为 `Product=AIStor, Plan=FREE, Trial=false, Nodes=1`，`SignatureVerified=false`。只输出这几项状态，未输出正文或个人字段。后续对该私有路径的操作优先走明确审批的 owner 进程，避免普通沙箱文件写入重新附加权限；正式部署前仍需再核对。没有安装/运行 AIStor、读取模型凭据或启动业务服务。

许可文件已就位，之前“等待用户手动保存”停点解除；继续按已确认方向核对固定镜像、补许可证只读挂载及实际初始化/重建/恢复验收。本轮只同步相应文档，仓库内不保存许可证副本；最终文档检查与精确本地检查点记录在本轮工具结果，旧混合文档继续保留工作区，不整批提交。

本片收尾检查：5 份更新文档的 185 个本地链接目标全部存在（未校验锚点），`git diff --check` 通过；infra、产品源码与测试目录没有本轮未提交改动。没有运行产品测试或实际容器验收，不引用旧 24 项结果作为许可证验证。重要节点仅提交本行动的授权、失败/修正与实际结果，不提交 D 盘文件；检查点身份以 git log 为准。

### AIStor 许可证配置接线与固定镜像准备（21:45）

上一片私有文件保存及权限验证已完成，检查点 `1b98314`。当前继续 P1，不等待用户再次操作许可文件。先在已确认的 Compose 公共命令入口增加一条行为测试：AIStor 显式使用文件形式的 `--license`，文件从数据根/private/minio.license 只读挂入，缺失宿主文件不自动创建目录；配置解析不读取许可证正文。依据为[官方容器部署说明](https://docs.min.io/aistor/installation/container/install/)，不照搬默认密码或全网发布端口。

本片精确变更仍限既有 `infra/compose.yaml`（许可路径参数/只读挂载）、`infra/.env.example`（文件位置说明）、`infra/tests/test_compose_config.py`（真实 Compose 解析行为）及行动/相关事实源，不新增目录、Module、Interface 或表。镜像值先保持外部显式输入；通过公开 registry 清单核对候选摘要/平台/体积后，再申请范围明确的拉取与无端口、无模型、专属隔离运行。镜像元数据查询不等于镜像已拉取或许可已验签。

验证：先记录新增许可用例红灯，再最小配置接线并回归整个配置测试文件；Ruff lint/format、行数与 diff 检查。实际容器的 entrypoint、版本/运行 UID、许可证加载和文件密码支持尚需后续实测，不能从 CE 或通用 S3 文档推断。结果 Pending。

### 用户取消备份恢复（后续范围决定）

用户明确确认：这是课设，不再交付 PostgreSQL 逻辑备份、MinIO 对象副本、备份清单、恢复命令或恢复演练。该决定覆盖本文更早日期段落中的 P4 备份恢复计划；当前交付重新编号为 P1–P4，原 P5 验收成为新的 P4。

仍必须完成的是“持久化”：正常停止和重新启动服务、重建本项目容器后，PostgreSQL 数据与 MinIO 对象仍可从原 D 盘绑定目录读回。明确不保证的是“灾难恢复”：误删、文件损坏、数据库逻辑损坏或 D 盘故障时，可能丢失全部业务数据，用户已接受该课设风险。取消备份不放宽安全初始化、禁止覆盖旧数据、端口隔离、私有凭据和不触碰共享 Docker 数据的要求。

本轮只同步行动指南、模块架构、交接与规格指针，不继续实现、不运行产品测试、不启动容器、不调用模型。中断前 `infra/tests/test_compose_config.py` 的 AIStor 接线失败测试保持原状，不能描述为通过；恢复开发时应先审计该未完成红灯，再决定是否继续同一切片。

文档自验证结果：上述五份当前文档共检查 183 个本地链接目标，缺失 0；限定文件的 `git diff --check` 通过，仅有现有 LF/CRLF 提示。没有运行产品测试、Compose 解析、容器或模型。由于 HANDOFF、行动文档及模块文档含既有混合增量，本轮未创建新的本地提交，避免把范围外改动混入检查点。

### 用户恢复目标：继续 P1（后续恢复）

用户明确“继续目标”，解除主动暂停；范围仍为取消备份后的 P1–P4。恢复点是已确认的 Compose 公共接口测试：`infra/tests/test_compose_config.py` 已包含 AIStor `--license` 与只读许可挂载的失败用例，`infra/compose.yaml` 尚未接线。先复跑该测试确认红灯，再只修改既有 Compose/无秘密模板使其通过；不新增业务 Module、Interface、数据库表或顶层目录。

本片成功标准：真实 `docker compose config --format json` 能观察到 `/run/secrets/minio.license` 的只读 bind mount，AIStor 命令显式引用该路径，且既有数据目录、密码文件、回环端口、手动重启和禁止提权约束全部回归通过。配置解析不启动容器、不读取许可正文、不调用模型。实际镜像拉取、服务端验签和 D 盘业务落盘仍属于下一道运行门禁，不能由本片结果代替。

实际红灯保持 **7 passed、2 failed / 1.40 秒**：分别缺少 `--license` 命令参数和 `/run/secrets/minio.license` 挂载。最小实现只修改既有 Compose 命令/只读 bind mount，并在无秘密模板说明固定路径；回归为 **9 passed / 1.58 秒**。Ruff 初检发现暂停前测试有一处 89 字符长行，运行项目格式化器后 lint 与 format check 均通过；限定 infra diff whitespace 检查通过，仅有现有 LF/CRLF 提示。没有启动容器、读取许可正文或调用模型。

随后按固定摘要拉取两个官方镜像。首次并发拉取在部分层下载后以 `unexpected EOF` 退出 1，没有创建容器；改为逐个续传后 PostgreSQL 与 AIStor 均退出 0。只读 inspect 结果分别为 `linux/amd64`、本机 image ID `sha256:aad6289ca337b3ce76896f2e7e61480490152886c7828120371fb28e6b779e1d` 和 `sha256:2cacca14bad4502feddcbf99cd1a927d8002c6d1ba874a81def1c37b2986b580`，RepoDigest 与预定摘要一致；两镜像 `Config.User` 均为空，后续实际进程 UID 仍须运行时核对。无网络、只读、禁止提权且自动删除的临时版本容器分别报告 PostgreSQL `15.19` 与 AIStor `RELEASE.2026-09-07T08-39-31Z` / commit `021f251729c44aa71377b5a740e8b7e753bd35ba`，未挂载数据或许可。

下一小片继续使用已确认的 Compose/模板公共接口：先增加失败断言，要求 `.env.example` 固定上述两个已验证的官方 digest，再把模板从空值更新为精确镜像身份；不采用 `latest` 或仅 tag。完成后回归配置解析与格式检查。实际服务进程身份、许可证加载和 D 盘挂载仍未由版本命令证明。

模板冻结红灯为 **9 passed、1 failed / 1.32 秒**，失败项准确显示两个镜像值仍为空；填入已核验 digest 后为 **10 passed / 1.33 秒**。Ruff lint、format check 与限定 infra diff whitespace 检查通过，仅有现有 LF/CRLF 提示。测试文件 192 行，未超过动态语言 200 行指标；infra 根目录 2 文件、tests 目录 1 文件。P1 的配置准备已形成可提交检查点，但正式 D 盘目录、运行 UID、许可证服务端验证、实际端口隔离和容器重建保留仍未验收，因此 P1 尚不能标完成。

### P2 AIStor 私有 bucket 与最小应用权限切片（进行中）

数据库协调检查点 `4f31130` 后继续 P2。现有 `MinioArtifactStore` 实际只调用对象级 `PutObject`、`GetObject`、`HeadObject`（权限仍为 GetObject）和 `DeleteObject`；客户端显式固定 region 与 path-style，不需要应用账号创建/列举 bucket。因而正式 bucket 冻结为 `agentexam-private`，应用身份冻结为 `agentexam-app`，应用策略只允许该 bucket 的对象 ARN 上 `s3:GetObject`、`s3:PutObject`、`s3:DeleteObject`。建桶、建用户、挂策略与管理员操作只属于首次初始化，不授予日常应用身份。

本片先新增并验证下列文件；它们深化已获确认的 `infra/local/` 部署目录，不新增业务 Module、Interface 或数据库表：

```text
infra/local/
  AgentExam.Local.psm1             # 部署命令共享的固定身份、Docker、路径/ACL 与秘密文件内部实现
  AgentExam.Initialize.psm1        # 首次初始化内部阶段：服务稳定就绪、schema 核验和 AIStor 准备
  minio-app-policy.json             # 非秘密的最小 S3 对象权限；只指向正式私有 bucket
  Initialize-AgentExam.ps1          # 公开首次初始化入口；先提供只读预检，再逐片接入实际初始化
infra/tests/
  test_storage_policy.py            # 权威策略文件验收：精确动作/资源，无管理员或桶管理权限
  test_local_initialization.py      # 显式启用的真实本机预检/初始化验收，不连接旧环境
```

验证先记录策略文件不存在或权限过宽的红灯，再最小落盘策略并回归。后续初始化命令须使用 AIStor 镜像内置 `mc`，通过标准输入接收 root/app 凭据，不能把秘密放入 argv；首次建桶必须为私有且只在确认目标不存在时执行。跨 PostgreSQL 与 AIStor 无法形成单一事务，初始化工具不得谎称原子：仅在两端均成功后写完成标记；中途失败必须报告实际部分状态并保持可安全重试，不能把普通启动与初始化绑定。

初始化命令先实现 `-ValidateOnly` 公开预检：只检查固定仓库/数据根、许可路径、重解析点、固定镜像身份、Docker Server 和 Compose 解析，不创建目录、密码、容器、bucket、表或标记。真实本机测试须显式设置 `AGENTEXAM_RUN_LOCAL_DEPLOYMENT=1`，并断言输出只含非敏感状态；普通回归默认跳过。预检通过不等于初始化或持久化完成，下一片才允许同一入口执行写入。

预检实际红灯依次暴露：脚本不存在；Windows 默认执行策略拒绝仓库脚本；普通沙箱不能读取 owner-only 许可；Windows PowerShell 子进程无法加载 ACL 模块；直接 .NET ACL 对象不能使用 PowerShell 扩展的 `Owner/Access` 属性。公开测试改为项目现有 PowerShell 7，脚本声明最低 7.4，并使用 .NET `GetOwner/GetAccessRules`；owner 进程复检最终 **1 passed / 1.46 秒**。结果只含固定路径、项目名、Docker 版本、镜像引用、许可存在性和初始化状态，未输出许可正文、身份声明或密码，也未产生写入。

下一片将公共入口的内部函数提取到同目录模块，供后续初始化/启动/停止/状态命令复用，避免每个脚本重复 Docker 身份和路径安全判断；这不是新业务 Module 或对外服务 Interface。首次写入在 private 下先建立带阶段的部署状态标记，再创建数据目录和随机密码；任何失败保留非完成阶段并拒绝普通启动，只有 PostgreSQL schema、AIStor bucket/用户/策略和应用凭据读写验证均成功才标 `complete`。普通启动永不调用初始化。

真实初始化红灯一：写入 `preparing` 标记后，PowerShell 7 的 `New-Item` 不接受 `-LiteralPath`，故 **未创建数据目录、密码或容器**；精确核对六个目标均不存在。加入仅允许 `preparing` 且目标全不存在的恢复开关后重试。红灯二：创建空 `postgres` 目录后，ACL 实现重复设置所有者被 Windows 拒绝；精确检查该目录非重解析点、子项数 0、无容器，随后删除这一刚建空目录。ACL 改为先确认 owner 不变、仅替换访问规则，不请求更改所有者。

第三次推进成功创建三个受限目录、三个随机密码文件并启动两只专属容器，状态停在 `services-ready`，但 schema 调用失败。只读诊断显示 TCP/SCRAM 密码认证成功，`public` 表、类、函数、类型和非系统 schema 计数均为 0；容器日志证明 `pg_isready` 在官方 entrypoint 的临时初始化服务器阶段先返回可用，而 `agentexam` 数据库当时尚不存在，脚本因此过早建表。随后以同一私有密码和正式 owner CLI 对确认空库执行，退出 0 并建立完整 schema；没有创建账号、任务、Job 或对象。等待逻辑改为目标数据库连续三次实际 `SELECT 1`，并新增只在阶段与现实 schema 精确吻合时推进的恢复核验，不能仅凭旧标记跳过。

第一次 `services-ready` 恢复又暴露原生命令跨行参数被 PowerShell 当成命令的问题，未改变 schema 或 AIStor；改成显式参数数组后，恢复入口先核对现实为精确 11 张空表，再建立 `agentexam-private`、非秘密策略 `agentexam-app`、同名应用用户并绑定策略，最终状态标记为 `complete`，命令退出 0。23:27 只读复核两只容器均 Running，实际发布端口为 `127.0.0.1:55432` 与 `127.0.0.1:59000`，Compose 标签中的数据源指向 `D:/AgentExamData/postgres` 与 `D:/AgentExamData/minio`。该 `complete` 只代表初始化各命令走完，尚未替代应用权限、匿名拒绝和跨重建数据保留验收。

下一条行为测试继续沿已确认的现有存储 Interface：读取 owner-only 的 `minio-app-password` 到测试进程，使用 `MinioArtifactStore` 写入一个随机、摘要固定的 `raw_30d` 合成对象，回读校验后通过 Adapter 受控删除；同一对象存在期间，无签名读取必须失败，应用身份的 `ListBuckets` 与目标桶 `ListObjectsV2` 也必须失败。测试只清理本次随机对象，不删除 bucket、用户、策略或正式目录；普通回归无显式本机部署标志时跳过。这是对刚由初始化命令创建的外部权限状态追加验收，不为制造红灯而回退真实 bucket/用户；若首次即通过，应记录为现有行为的验收证据，而不是声称测试驱动了此前实现。

22:53 额度检查到期。第一次原生查询错误选中 npm 的 `codex.ps1`，不能作为 Windows 可执行文件启动；第二次通过子 PowerShell 启动没有返回可用结果；第三次使用 Codex 桌面的精确 `codex.exe` 路径成功，只输出 `PrimaryRemaining=18`。未创建模型 turn、未读取或输出认证内容，未触发 1–4% 停工阈值；下次持续执行检查最迟 23:23。

本片精确本地检查点为 **`7875444`**，只包含 `infra/compose.yaml`、`infra/.env.example`、`infra/tests/test_compose_config.py` 与本行动；暂存允许集合和实际集合一致，暂存 diff 检查通过，无推送。依赖、架构、规格及 HANDOFF 的同步事实保留在既有混合工作区，没有混入提交。

### P2 空库统一初始化：数据库协调切片

现实接口核对发现：`agentexam-owner init-db` 只建立身份/邀请表，目录和 Job 各有独立入口且分属不同事务；直接串行执行会在后段失败时留下可误认成完成的半初始化。P2 先深化现有 persistence Adapter 与 owner CLI 的既有 `init-db` Interface：新增一个内部协调实现，在同一个 PostgreSQL 事务中按依赖顺序复用四份现有 SQL；执行前拒绝任何非系统 schema 或 `public` 中的关系、函数、用户类型，不新增表或迁移机制。owner CLI 保持一个 `init-db` 命令，不暴露四个执行细节。

计划文件树与职责：

```text
apps/backend/src/eval_platform/adapters/persistence/
  bootstrap.py                    # 新增内部协调 Implementation：空库检查与四份 schema 单事务安装
apps/backend/src/eval_platform/delivery/
  owner.py                        # 深化既有 owner CLI Interface：init-db 委托统一初始化
infra/tests/
  test_database_initialization.py # 新增部署 seam 的真实 PG 验收：完整表集、重复/非空拒绝且旧数据保留
```

这里没有新增业务 Module、Interface、数据库表或顶层目录；新增文件位于既有 persistence Adapter 和已确认 infra 测试目录。设计模式是 **Facade（外观）**：owner `init-db` 是小 Interface，`bootstrap.py` 隐藏四份 schema 顺序、空库判定与事务。PostgreSQL 是本片的外部依赖，测试使用专属临时真实数据库，不 mock 自有 Repository；MinIO bucket/最小应用权限作为下一垂直切片，不能冒充已由数据库事务原子覆盖。

验证先写真实 PG 测试并记录缺少协调实现的红灯；实现后在固定 PostgreSQL 15.19 的临时、回环、非默认端口容器运行。成功标准：空库一次得到当前全部规划表；重复调用或预存合成表/记录时返回失败且原数据不变；同组原 owner 恢复测试回归。测试容器只用 tmpfs/合成密码，结束时精确删除，不触碰 D 盘或旧数据库。结果 Pending。

实际红灯在专属 `agentexam-p2-init-test`、`127.0.0.1:55439`、tmpfs、合成密码的 PostgreSQL 15.19 上为 **2 failed / 0.52 秒**：旧 owner 命令只建立 `accounts`、`sessions`、`invitations` 三表，且存在 `existing_data` 与合成记录时仍返回 0。新增 Facade 后真实集成为 **2 passed / 0.45 秒**；测试格式修正后复检仍 **2 passed / 0.46 秒**。空库得到当前 11 张规划表，非空库返回 2 且原记录和唯一旧表不变。

原 owner/Compose/初始化非集成组合为 **14 passed、3 deselected、2 个既有弃用警告 / 2.36 秒**；163 个后端源码 Mypy 通过。Ruff 首次发现新测试导入排序和长行，格式化并修复导入后 lint 与 format check 均通过。专属测试容器已按精确名称停止并因 `--rm` 删除，55439 不再监听；没有 D 盘写入、旧库连接、模型调用或残留测试容器。数据库协调切片通过，但 P2 仍缺 AIStor 私有 bucket/最小应用权限初始化，不能标成整体完成。

模板冻结红灯为 **9 passed、1 failed / 1.32 秒**，失败项准确显示两个镜像值仍为空；填入已核验 digest 后为 **10 passed / 1.33 秒**。Ruff lint、format check 与限定 infra diff whitespace 检查通过，仅有现有 LF/CRLF 提示。测试文件 192 行，未超过动态语言 200 行指标；infra 根目录 2 文件、tests 目录 1 文件。P1 的配置准备已形成可提交检查点，但正式 D 盘目录、运行 UID、许可证服务端验证、实际端口隔离和容器重建保留仍未验收，因此 P1 尚不能标完成。

### 23:50 硬停止前的 P2 收口证据

应用权限真实验收首次即通过（这是对已创建外部状态的验收，不倒退制造红灯）：`test_local_storage_access.py` 为 **1 passed / 0.69 秒**。`agentexam-app` 通过现有 `MinioArtifactStore` 完成随机 `raw_30d` 合成对象写入、摘要回读和受控删除；同一对象存在期间，匿名读取、应用身份 `ListBuckets`、目标桶 `ListObjectsV2` 均返回 403。finally 再执行精确对象删除，未删 bucket、用户、策略或目录。

AIStor 服务端 `mc license info --json` 只经临时 `/tmp` 客户端配置查询，最终脱敏结果为 `status=success`、`Product=AIStor`、`Plan=FREE`、`Trial=False`、`Nodes=1`、无到期时间；APIKey、ID、Serial、Organization 均未输出。容器日志的 `MinIO Community License` 是展示名称差异，不再作为许可有效性阻点。

组合回归在提升进程中先得到 **5 passed、9 errors**；9 项全部是 pytest 无权枚举 `C:\Windows\Temp\pytest-of-YINGYI`，不是 Compose 断言失败。拆分后普通权限 `test_compose_config.py` 为 **10 passed / 1.34 秒**；owner 进程的初始化重复执行、真实权限与策略为 **4 passed / 4.99 秒**。四份 Python 测试 Ruff lint 通过、format check 通过；三个 PowerShell 文件 Parser 检查通过。该轮未跑后端全量测试、Mypy 或双轴评审；数据库协调片此前的 163 源文件 Mypy 证据不冒充当前脚本验证。

当前可靠停点：P2 的 schema、AIStor 私有 bucket、应用用户/最小策略、重复初始化和真实权限已经具备证据；P1 尚缺合成业务记录/对象在停止启动及容器重建后的保留验收，P3 尚缺 Start/Stop/Status 公共命令，P4 尚缺完整合成联调与操作说明。两只 `agentexam-local` 容器仍 Running，停止工作不等于停止服务。用户新编辑的目标文本重新出现“备份与恢复”，与此前明确取消且已写入 ACTION_GUIDE 的决定冲突；硬停止前不擅自改回，恢复后首先核对当前用户意图并同步唯一事实源。
