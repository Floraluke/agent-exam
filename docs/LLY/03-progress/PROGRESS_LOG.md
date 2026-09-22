# 开发进度日志

> 只记录事实与实际结果：做了什么、实际输出是什么、遇到什么。计划见 [`01-plan/PLAN.md`](../01-plan/PLAN.md)。
> 格式：按日期倒序追加，最新在最上面。

## 2026-09-22

### 已完成

- **拉取远端并合并**：`origin/main` 由 `1888aa2` 前进到 `4f2c606`（B 的 5 个提交、9 个文件，全部属 Web 与 HTTP 侧），`lly/dev` 合并该增量后 HEAD 为 `606a3da`，无冲突。合并后实测：`ruff check` 通过、`ruff format --check` 341 文件、`mypy` 184 源文件无问题、默认回归 **587 passed / 105 skipped / 2 failed**（92.09 秒，失败项仍是缺 `framework/harbor` 的 ISSUE-04）、`pytest tests/providers` **165 passed / 1 skipped**——与合并前基线逐项一致，无回归。本机领先 `origin/lly/dev` 14 个提交，其中只有 `57a18f5`、`64d5f0b` 与本次合并提交是本机新产生的；**未推送**。
- **B 已完成两处契约对齐，05 的"待 B 确认"一项关闭**（[B 的对齐行动](../../architecture/modules/web-and-http/actions/05b-t05-controlled-vocabulary-alignment.md)）：`HTTP_API.md` §10.2 列入五个受控 `PROVIDER_*` 码、归入的内部错误族与"内部码绝不回显"规则（与 `provider_access/failures.py` 逐字一致）；§4.2 把 `agent_type`/`model_provider` 记为受控集合、按记录如实呈现、超出集合失败关闭，并说明公开 `internal_test_fake` 是有意的；§6.2 补受控预设 `internal-test-provider-proxy`（与 `catalog_presets.py` 逐字一致）。**B 另修正我方一处转述**：`authentication_type=provider_run_token` **不在** HTTP 响应中，响应只含 `agent_type` 与 `model_provider`——契约本就规定不返回认证方式与凭据 profile，我方此前把它算作要公开的身份，属转述不准确。
- **修掉 B 指出的真实缺陷：超受控集合的存量记录会返回 500**。根因是 `catalog_schemas.py` 的 `_controlled()` 抛裸 `ValueError`，而 `app.py` 只注册了 6 个异常处理器、没有 `ValueError` 的；仓库读取路径（`AgentRegistry.get/list`）不重校验身份，只有 `register()` 校验，因此越过注册表与库级 CHECK 的存量记录会走到响应构造。**修法**：改为抛既有域错误 `CatalogUnavailable`，由 `errors.py` 既有处理器映射为 **503 `DEPENDENCY_UNAVAILABLE`**——`HTTP_API.md` §5 已把"目录对象缺失/损坏"归为 503，故**零契约变更、无新错误码**；内部码 `UNCONTROLLED_AGENT_TYPE`/`UNCONTROLLED_PROVIDER` 只留在进程内、不回显。
- 新增 `tests/catalog/agent_identity/test_uncontrolled_records.py`（4 条用例：域层按字段命名拒绝、HTTP 层 503 受控响应、不泄漏内部码与记录自身取值）。**区分力实测**：把实现退回 `raise ValueError(code)`，4 条全部失败；还原后通过。实测：`pytest tests/catalog` **46 passed / 29 skipped**（增量正好是新用例）、默认回归 **591 passed / 105 skipped / 2 failed**（+4，失败项仍是 ISSUE-04）、`ruff check` 通过、`ruff format --check` 342 文件、`mypy` 184 源文件无问题。
- 顺带记一条工具链事实：文档内说 `apps/backend/.venv` 存在，本机无 PostgreSQL（`55432` 未监听），开启 PG 的集成用例按设计跳过。
- **阶段 1 文档状态同步（纯文档，无代码改动）**：修正 `docs/LLY/` 中与实际进度不符的状态表述。① `STAGE1_IMPLEMENTATION_PLAN.md` 内部自相矛盾——分片表已把 S3–S7 标"已完成"，同表 S2、`service.py`、S8 与首行状态仍写"未做"，现按实际改为 S1–S8 已实施、S9–S11 等 T2，并把第 2 节文件树换成**实际已建**的树、更新目录上限说明、第 5 节 T1 前置句、第 6 节待授权清单（T2 窗口已可用）。② **跨文档矛盾统一口径**：该文此前写"S2–S9 不依赖拓扑结论"，与 `STAGE1_PROXY_SERVICE_PLAN.md` 第 3 节"S9 同样依赖 T2"冲突；经用户确认按较新文档统一为 **S9 依赖 T2**（理由：S9 的绑定接法由拓扑结论决定）。③ 另修三处过期状态：`STAGE1_PROXY_TEST_DESIGN.md` 首行"未开工"、其第 5 节"开工前必须冻结"四项（其中三项已冻结）与第 6 节风险表三行（05 已发布、04 已完成、T2 窗口已可用）、`README.md` 第 39 行、`PLAN.md` 首行与两个阶段标题。过程见[文档状态同步行动](../../actions/2026-09-22-lly-stage1-doc-state-reconciliation.md)；未改动 `TASK05_OWNER_DELIVERY_FILLED.md` 与 `TASK05_OWNER_ACTION_REQUIRED.md`（后两者是"请求→回复→回执"的归档原件，保留当时真实状态）。

- **负责人机器复测 T1 通过（2026-09-22）**：在 `lly/dev` 上正常 **28 PASS / `status=verified`**、反向对照 **4 条预期 FAIL / `status=negative-control-ok`**，4 容器 3 网络均带双标签、清理复核为空。对方同时把探针收紧（预检拒绝同名资源与未缓存镜像、清理按名称+任务标签+本轮 scope 三重匹配、UID 查询容器纳入标签），**断言与 verdict 未改**（E 已逐行核对）——记录见[负责人 T2 复测记录](../../actions/2026-09-22-task05-owner-t2.md)。
- **Harbor 侧车附加：源码结论为"允许按服务绕过"**（显式 `networks`/`network_mode` 的服务不加入生成的侧车覆盖文件，`docker.py:433-449`；入口 `JobConfig.environment` → `extra_docker_compose`）。**但 T2 仍未运行**：Harbor 构造期会起无名称无标签的内核探针容器，常规拆除可能 `down --rmi local --volumes`，都超出原授权。
- **用户 2026-09-22 授权增补**：允许那个 `--rm` 短命探针容器（不得挂载 Docker 套接字/发布端口/写宿主路径）；允许常规拆除但只可删除该次 Trial 自己的 compose 项目资源、不得删拉取的固定镜像或其他项目的卷。范围与硬边界见[组长机器预案附三](../../actions/2026-09-21-task05-owner-machine-runbook.md)，含建议的最小 T2 形态（把七条断言作为 Trial 命令跑，不接 CLI 与真实模型）。

- **待办：把 `origin/main` 合并进 `lly/dev`（下一件事，未做）**。`origin/main`（`e6a7138`）比本分支多 24 个提交，其中一批来自 CI 分支的**对我们模块的加固改造**：新增 `provider_access/private_file.py`（抗竞态读私有文件）、`failures.py` 引入 `ProviderAccessError` 并在词表加入 `PRIVATE_FILE_CHANGED`、重写 `request_policy.py`/`secrets.py`/`transport.py`，另加 `mypy.ini`/`pytest.ini` 与较大的 `uv.lock` 更新。
  - 试合并（`git merge-tree`，未落盘）显示 **6 个冲突文件**：任务单、`failures.py`、`test_controlled_failures.py`、`PLAN.md`、`STAGE1_PROXY_TEST_DESIGN.md`、`PROGRESS_LOG.md`。其中 `failures.py` 与对应测试是**同一版本的两种演进**（main 侧是本分支那版的超集），采用 main 侧即可；docs 几处需手工合并保留双方条目。
  - **真正的工作量不在冲突**：main 重写了 `secrets`/`request_policy`/`transport` 的接口，而 `server/`（只在 `lly/dev` 上）依赖它们——合并后必须让 `server/` 适配新接缝并跑全套（含 PG 开关；合并后还要 `uv sync`，因为依赖锁与 `mypy.ini`/`pytest.ini` 都变了）。合并前的实测数字（`tests/providers` 165 passed / 1 skipped、默认回归 591/105/2）在合并后必须重测，不能沿用。
  - **转发 T2 消息不依赖这一步**：负责人的 T2 只跑 `tests/providers/runtime/` 探针，而 main 未改动该目录。

- **负责人机器 T2 首次执行：未测得（工具链失败）**。固定 Harbor 最小环境的 `up --wait` 中，自带侧车 `...-egress-control-sidecar-1` **退出码 127**，七组 Trial 命令一条未执行、运行期 inspect 未取得；负责人按停止条件停手、未改侧车、未重试。拆除前后镜像 90/卷 16 无增删，按标签复核残留为 0。**分类为"工具链失败"而非"拓扑不成立"**：七条断言尚未在 Harbor 上被测量，第 2 项验收既不能记通过也不能记失败，任务停在 T2。
- **诊断线索（仓库内既有）**：本仓库已知固定 Harbor 自带侧车在这台机器上需 DNS 适配（M0 查明上游 `network-policy` 不放行 Docker Desktop 转发解析器 `192.168.65.7:53`），适配由 `network.py::export_sidecar` 提供、**只经 `harbor_entry.py` 的 `_EGRESS_CONTROL_SIDECAR_CONTEXT_PATH` 生效**；负责人用的是自写最小探针，**可能未走这条链**。127 通常为"容器内命令找不到"，与我们的 DNS 守卫（退出 1 且打印 `HARBOR_DOCKER_DNS_CONFIG_UNSUPPORTED`）不符，**原因仍待侧车日志证实**。

- **回复 B 的三问**（落地时间 / 超集合记录的 HTTP 表现 / 夹具控制端点），已写入任务单 Comments。要点：① 落地时间由 T2 结论触发而非日期，且**两项呈现验证不必等链路**——它们验的是 Web 层对"给定码/给定文案"的行为，可在合成夹具上先做（`tests/identity/browser_server.py:194` 已有控制端点先例）；本轮核实链路的实情是 `provider_access` 包外只有一个导入方、`render_provider_config` 零调用方、worker 仍无条件要求 ChatGPT 认证（`runtime.py:66`），故**今天没有任何真实 provider 失败能写到 Run**。② 超集合记录的表现**已实现**（`3a5a9b8`：503 `DEPENDENCY_UNAVAILABLE`，零契约变更），B 可自行决定是否在 §4.2 补一句状态码。③ 夹具控制端点属 B 的测试基建，不依赖 E。另记一处 E 侧同类隐患：`codex/provider_config.py:62-72` 也抛裸 `ValueError("PROVIDER_CONFIG_*")`，当前零调用方，S10 接线时一并收口。过程见[回复行动](../../actions/2026-09-22-t05-b-scheduling-reply.md)。

- **T2 诊断结果：侧车入口 ENOENT（环境/工具链，仍非拓扑结论）**。实测 `exec /opt/egress-sidecar/entrypoint.sh failed: No such file or directory`、`Exited (127)`、镜像为本机构建的 `harbor-prebuilt:...--f57c86fb4906508e`、`RepoDigests=[]`、`error=` 空。**根因强假设且有仓库既有依据**：`DEPENDENCIES.md:314` 早写明"Windows 检出中的 CRLF 会使脚本解释器无效"，而 `network.py` 用 `git show` 取原始 blob 正是为绕开它；负责人的手写 `probe.py` 未设 `_EGRESS_CONTROL_SIDECAR_CONTEXT_PATH`、未调 `export_sidecar()`，于是用了 Harbor 默认上下文。**产品路径不受影响**——`Worker → harbor_command() → harbor_entry.py` 必先导出适配上下文（`:177`/`:186`）。
- **对我此前建议的更正**：我在附三建议的"手写最小探针"会绕过必需的侧车适配，已改为"**经 `harbor_entry.py` 跑最小 job config**，或显式设置 context path"。待负责人做一次只读确认（工作树与镜像内 `entrypoint.sh` 行尾）后即可定论。

### 当前停点

- **任务 05 本机侧已实施完毕**（S2–S8、T1 与 `service.py` 的 S6a–S6e），剩余全部等 T2：**S9（worker 按 Run 选绑定）、S10（`net/` 与网络接线）、S11（集成层）**。
- **T2 的状态（2026-09-22 更新）**：T1 已在负责人机器复测通过；Harbor 源码结论为"允许按服务绕过侧车附加"；授权增补已给出并**已实际执行一次，但未测得**——自带侧车退出 127 且未执行任何 Trial 命令。下一步是**只读确认侧车入口的行尾**（工作树与镜像内各一次），再决定下一轮 T2 走产品入口。
- 推送状态：本机与 `origin/lly/dev` 一致（上一条"领先 14 个提交"的说法已被本轮推送取代）。
- 与 B 的往来状态（2026-09-22 更新）：B 已完成两处契约对齐（§10.2 五个受控码、§4.2 受控集合与 `internal_test_fake`，见当日条目），**"仍等 B"的旧说法作废**。当前挂在 B 侧的是：① 可选——在 §4.2 补一句超集合记录的状态码（503 `DEPENDENCY_UNAVAILABLE`）；② 夹具"强制下一次响应出错"的控制端点与两项呈现验证（**不依赖 E 的链路**，见当日回复条目）。

## 2026-09-21

### 已完成

- **任务 05 本机实施（S3–S7）已完成**：`adapters/execution/provider_access/` 现有 6 个源文件（`__init__`/`secrets` 158/`request_policy` 125/`budget` 186/`binding` 134/`transport` 109 行，均 ≤200，目录上限 8）。测试在 `tests/providers/policy/`（5 个测试文件，**67 passed / 1 skipped**，跳过项为"POSIX 属主位仅限类 Unix"，本机 Windows 属设计如此）。
- **测试抓出 4 处真实缺陷**（非测试写错）：① 缺 `profiles` 键时结构校验被短路成 `PRIVATE_PROFILE_NOT_FOUND`，掩盖结构非法；② 上游地址只用正则校验 `https://` 前缀，**任意主机都能通过**，已改为按登记上游成对校验；③ 请求缺 `stream` 键时抛**裸 `KeyError`**，安全边界上不可接受，已收敛为受控错误码；④ `transport` 原把 `Authorization: Bearer …` 并进 headers，导致 **`repr(request)` 泄漏秘密**（且给正文加 `repr=False` 也挡不住 `repr(headers)`），已改为认证值与客户端头分开存放、`safe_summary()` 只报头名与正文长度。
- 关键机制取舍已落进代码：`load_profile(..., verify_access=…)` **无默认值**，调用方无法不声明"私有文件如何被证明仅 owner 可读"就取得 profile；`OutboundRequest` 对 `max_attempts != 1` 与 `follow_redirects=True` 直接抛错（重试与重定向结构上不可配）；账本的 `consumed_*` 为必填构造参数，代理重启不会无意从零开始；8 线程并发抢额度的用例断言**恰好 4 成功 4 拒绝**。
- **T1（纯 Docker 层拓扑）已在本机证成**：探针七条断言全部测到并通过（**28 项判定**全 PASS，`status=verified`，连续两次一致）。**探针已按用户确认纳入仓库** `apps/backend/tests/providers/runtime/`（拆成 driver / 原语 / 判定三文件，均 ≤200 行，含 README 与假值 fixture），证据默认写到被忽略的 `.tmp/t05-topology/`；原始记录已抄进[本机实施行动](../../actions/2026-09-21-task05-local-implementation.md)。
- **run 01"未证成"的根因已定位**：监听端容器启动即退出，报 `setpriv: setresuid failed: Operation not permitted`（退出码 127）——`--cap-drop ALL` 去掉了 `CAP_SETUID`/`CAP_SETGID`，而镜像入口脚本需要它们降权。**修法是让监听端以镜像内 redis 用户运行**，`--cap-drop ALL` 与 `no-new-privileges` 全部保留。因此 run 01 的 CLOSED 确为工具链假象。
- **本轮另修掉 4 处会产出假阴性的探针缺陷**：监听端 Alpine 镜像**无 bash**（从监听端发起的检查一律静默 CLOSED，已改用镜像自带 `redis-cli`）；转发替身脚本**漏端口号**（`${ENTRY_PORT}` 写在容器侧展开位置，容器内无此变量，故 `exec nc <主机> ` 无端口、每次转发被重置）；一次性 `nc -e` 监听在重生窗口重置新连接（改为常驻 `nc -lk -e`）；**redis 会改写自己的进程名**，用其 argv 做 PID 隔离标记恒为 0（改用中继脚本路径，并保留代理侧正对照）。
- **探针新增健康门禁与反向对照**：任一容器非 running/地址为空/监听端不应答即 `harness-failed` 中止且**不输出任何断言**（本轮实际生效一次）；`NEGATIVE_CONTROL=1` 故意把做题侧接进出网网络，断言 2/3 如预期失败（`status=negative-control-ok`），证明负例不是空断言。清理每次复核残留为 0，未执行全局 prune。
- 记录一条 Windows 环境陷阱：Git Bash 会把传给容器的绝对路径做 MSYS 转换（`--tmpfs /data` 曾被改写成非法路径，`/dev/tcp` 参数同样受影响），**后果是假阴性 CLOSED**；任何容器探针都必须在脚本内 `export MSYS_NO_PATHCONV=1`。
- 静态检查与回归（HEAD `4c7c4d6`，本机实测）：`ruff check` 通过、`ruff format --check` 313 文件、`mypy` 174 源文件无问题、默认回归 **484 passed / 102 skipped / 2 failed**（失败项与基线完全相同，仍是缺 `framework/harbor` 的 ISSUE-04）。
- 归档扩展计划 6 份文件（来源 `D:\ui-catalog-providers\ui-catalog-providers\`）：4 份更新到权威位置 `.scratch/ui-catalog-providers/`，2 份任务单落位新建的 `issues/` 子目录。归档前仓库版本是旧版（仍写“01 未开工、未发布任务单”）；相对旧版的实际变化为 `spec.md` 2 行、`plan.md` 25 行、`implementation-map.md` 95 行，`verification.md` 内容本就相同。
- 归档方式：`docs/LLY/` 只增加指向权威位置的链接、不复制计划正文 —— 依据本目录 README 的单一事实源规则。
- 更新后的计划确认：**P、任务 01、任务 02 均已完成**（任务 02 是“A 版假数据原型连接现有后端的第一片正式 Web”，含 32 条浏览器回归、类型检查、生产构建、31 项 API 对账与双轴评审）；03–08 仍未发布为独立 issue。
- 拉取远端：`origin/main` 由 `6dfa2be` 前进到 `beed93f`，并新增分支 `origin/xinyue-modules`。远端提交中包含与本次归档**内容完全相同**的 6 份文件，逐份比对差异均为 0 行。
- 因此丢弃本地冗余改动（3 份修改文档 + 2 份新增任务单副本），改由合并 `origin/main` 取得；`lly/dev` 由 `469ba1d` 前进到合并提交 `2a55a9e`，无冲突。
- **2026-09-19 记录的两处缺口已由本次推送补齐**：① `docs/actions/2026-09-18-ui-workbench-prototype.md` 与 `2026-09-18-ui-workbench-implementation.md` 已进入仓库；② 任务 02 的产品代码（`apps/web/src/features/workbench/`、`jobs/wizard/`、`jobs/listing/`、`apps/web/tests/workbench/`）已进入仓库。合并后 6 份计划文件的全部仓库内相对链接可解析。
- 本次推送另带入 D、B 的 03/04/08 准备工作：对比查询接口与矩阵渲染、连续规模 preset、任务 03 报告语义设计、任务 08 runbook。这些任务仍**未发布为独立 issue**；`TEAM_WORK_ALLOCATION.md` 第 7 条已相应改为“01–02 已发布并完成；03–08 仍是未发布的规划编号”。
- 合并后后端验证：`ruff check` 通过；`mypy` 167 源文件无问题（合并前 164）；默认回归 **404 passed / 84 skipped / 2 failed（55.89 秒）**，相对合并前基线 386/82/2 通过数 +18、跳过数 +2，**失败项完全相同**（仍是缺少 `framework/harbor` 的 ISSUE-04），无新增失败。
- 过程与完整证据见[归档与同步行动](../../actions/2026-09-21-file-plan-docs-and-sync.md)。
- 完成 05 的准备性测试设计：[阶段 1（05）假提供方安全执行链测试设计](../01-plan/STAGE1_PROXY_TEST_DESIGN.md)。把[验证规范第 4 节](../../../.scratch/ui-catalog-providers/verification.md)的负例矩阵逐条映射为测试归属（测试文件、用例名、断言、运行位置），并按“本机无 Docker、`framework/runtime` 只在组长机器”的现状分层：策略层、契约层、生命周期层在本机，集成层只在组长机器。（**当日随后变更**：本机已装 Docker，T1 已在纯 Docker 层证成；见本日上方条目。）
- 覆盖核对发现并补上三处遗漏：直连供应商/宿主/metadata/其他 Trial、容器文件与进程及 Docker inspect/patch 的假 Key 探查、新 Job 重试需重新批准。现五组负例全部有明确归属。
- 同时标出四项**开工前必须冻结、现在不得预设**的未知：Token 上界/请求字段白名单/账本格式（实现地图第 5 节明示未验证）、固定 CLI 是否需要容器承载、Compose 拓扑不能沿用共享网络命名空间的现有侧车、私有文件精确权限条件。
- 本次只产出设计文档：未创建 `tests/providers/`、未写任何测试或产品代码、未安装 Docker、未调用模型。过程见[测试设计行动](../../actions/2026-09-21-stage1-proxy-test-design.md)。
- 拉取远端：`origin/main` 由 `beed93f` 前进到 `361998b`（68 文件、+4435/−153）；`lly/dev` 直接**快进**到该提交（无需合并提交），领先 `origin/lly/dev` 46 个提交。`docs/LLY/` 的既有改动已随 PR #5 合入 main，本地与 main 中的版本逐字节一致。
- **任务 04 已发布且 8 项验收全部完成**。其中第 3 项（五题 × 参考/空/错误 = 15/15 场景）原属 E 的 12 h 配合范围，实际由 C 在组长机器上执行（证据 `runtime/fork-evidence/` 15 个 scope、容器清理 `verified`、Fork `returncode=0`），五道候选已写入白名单。**该事实需与负责人确认**：它影响分工表中 E 的工时构成与任务 08 的输入。
- 记录一个直接落在 E 的 06/07 路径上的潜在缺陷（已在代码中核实）：`routes/catalog.py` 接受并校验 `agent_type` 查询参数，但 `application/agent_registry.py` 的 `list()` 签名不含该参数，因此**该筛选从不生效**；当前因登记路径仅允许 `codex` 而行为等价，06/07 接入 DeepSeek/Kimi 后会静默失灵。C 已转给 D 记录在案，该行动明确"不改动"。**（E 侧更正，2026-09-21）**：本行“06/07 接入 DeepSeek/Kimi 后会静默失灵”的触发条件不准确——`agent_type` 是**执行器类型**（`codex`/`aider`/`claude_code`/`custom`，见 DATA_MODEL 第 271 行、HTTP_API 第 297 行），DeepSeek/Kimi 预设的 `agent_type` 仍是 `codex`；真实缺口是 HTTP 契约要求“合法筛选无匹配返回空列表”而实现从不传入该参数（HTTP_API 第 315 行），要等出现第二个合法 agent_type 才会显形。代码未改动，接线归 S8 范围。
- 合并后的本机验证：`ruff check` 通过；`ruff format --check` 300 文件；`mypy` 169 源文件无问题；默认回归 **417 passed / 101 skipped / 2 failed（59.93 秒）**，相对上次 404/84/2 通过 +13、跳过 +17，失败项完全相同（仍为缺 `framework/harbor` 的 ISSUE-04）。
- 起草 05 任务单：[`issues/05-fake-provider-secure-execution-chain.md`](../../../.scratch/ui-catalog-providers/issues/05-fake-provider-secure-execution-chain.md)，`Status: needs-info`，9 项验收 + 停止条件，等待负责人发布与开工授权。起草方式对照 C 为任务 04 走过的路径（成员起草 → 负责人发布并授权）。过程见[起草行动](../../actions/2026-09-21-draft-task-05-issue.md)。
- 验收项覆盖核对发现并补上一处遗漏：权威负例第一条的"未批准、错误 profile、缺密钥、宽权限/链接文件"未落入第 4 项验收，已补；随后又按权威措辞把第 5 项对齐为"正式链路的合成 Run 可完成"。现关键短语全部命中。
- 05 任务单草案经负责人过目后提交并推送：提交 `6ccf001`，4 个文件（任务单 + 起草行动 + 2 份 LLY 文档），已到 `origin/lly/dev`。**注意区分：这不等于"05 已发布"**——按现有先例（01/02/04）发布以进入 `main` 为准，而开工授权还需负责人明确安排。
- 产出 05 组长机器交接预案：[任务 05 组长机器执行预案](../../actions/2026-09-21-task05-owner-machine-runbook.md) 第 05 节。沿用 D 的"操作手册"形态（标注草稿、以 `plan.md` 第 7 节为准、不复制任务步骤），把"最小拓扑实证"拆成可顺序执行的断言清单、前置核对、停止条件、清理与回报要求、不得做清单；并写明**代码归属**——代理实现由 E 在本机编写并跑通策略/契约/生命周期层替身测试后推送，负责人机器只做需要真实隔离环境的运行与核验，现场改动须回仓库走同一评审。该预案已提交推送（提交 `3db8955`）。
- 产出 05 设计冻结底稿：[阶段 1 代理设计冻结底稿](../01-plan/STAGE1_PROXY_DESIGN_FREEZE.md)。这是 05 第 1 步"冻结代理拓扑、私有文件格式与权限、请求字段白名单、计量策略"的工作底稿，按**机制（E 定稿）与数值（交负责人）分开**的原则编写，六项待冻结内容各有候选设计并标注状态。
- 设计底稿补入一条此前未纳入的硬约束：Codex 官方配置的 `request_max_retries`、`stream_max_retries` **默认值不是零**，必须显式关闭，并由代理独立验证没有发生重发——因为研究第 6.1 节已证明命令行可覆盖模型，只信任配置文件不成立（依据研究第 1 节、第 6.1 节）。
- 读现有侧车代码后确认：`adapters/execution/network.py` 的 `compose_profile()` **刻意不声明 `networks`**，由 Harbor 环境附加自己的侧车，因此主容器与侧车共享网络命名空间——05 的拓扑不能照搬，需替换网络附加方式；能否替换是拓扑实证要回答的第一个问题（与认证接口第 4.1 节第 5 条一致）。
- 列出 **9 项待负责人拍板**的事项：每 Run 输入/输出额度、模型期限、请求频率、首轮支出目标、Kimi 项目日/月预算、输入 Token 计数方式、私有文件宿主路径与 owner 主体、组长机器窗口授权。机制设计不代替这些决定，研究第 4 节的初值只作起点。
- 产出可转发的负责人侧交付要求：[`01-plan/TASK05_OWNER_DELIVERY.md`](../01-plan/TASK05_OWNER_DELIVERY.md)。形态为**自足可整份转发**（负责人或其 AI 助手无需先读其他文档），但不复制权威正文，文末列出对应位置。内容三件：① 9 项拍板表格（含第 7 项两条路线的后果说明，9 个单元格留空待填）；② 6 项前置核对清单（任一不满足即停）；③ 最小替身拓扑实证——7 条断言含三组对照、证据与清理要求、代码归属说明。
- 文档明确了两点边界：**一次性探针**允许在负责人机器上编写与运行（沿用 M0 各次探针的既有做法，位于被 Git 忽略的证据目录、不进产品树）；**产品代码**仍由 E 在本机写好并跑绿后推送，现场不临时改。
- 负责人返回填充版核对结论，原文归档为 [`01-plan/TASK05_OWNER_DELIVERY_FILLED.md`](../01-plan/TASK05_OWNER_DELIVERY_FILLED.md)（正文未改，仅加一行归档说明）。结论是**前置总判定 STOP、拓扑实证未执行**：6 项前置只完整满足 1 项（`framework/harbor` revision `6af8d6e3…` 与依赖表一致、工作树干净）；**9 项拍板全部仍为"待负责人确认"**（第 7 项推荐 A 保守上界起步，但未作最终选择）；7 条断言全部未执行；Docker Engine 27.5.1 可响应但未获创建授权。
- 负责人已核实的代码事实：Catalog/目录 HTTP schema/Agent Registry/Worker 组合/Harbor 引导**仍全部固定 `openai_chatgpt`/Codex**；Harbor 层 `max_retries=0` 已存在但不能替代 Codex CLI 两个重试参数与代理转发次数的独立验证；现有认证文件校验不足以证明 Windows ACL/属主。
- **修掉一处我方措辞缺陷**：原交付要求第 2 节第 3 项写"没有运行中的业务 Job 或容器"，负责人核对时指出持久化服务容器正在运行、该条件按字面不成立。已拆为"无业务 Job"+"不得停止或删除既有持久化服务"，并在文中标注该修正由负责人核对发现。
- **发现并修复一处真实断链**：负责人指出 `docs/LLY/01-plan/STAGE1_PROXY_DESIGN_FREEZE.md` 在仓库中不存在——**该判断正确**。核实 `git log --all -- <path>` 为空，远端 `docs/LLY/01-plan/` 下只有四个文件。根因是上一轮产出设计冻结底稿与交付要求后**未提交即交付**，对方只能从微信副本读取。已在本切片补交并按提交前查路径可用性。
- 负责人核对结论已回填到任务 05 任务单的 `## Comments`，作为该任务的正式讨论记录。
- 产出待负责人回执的文档：[`01-plan/TASK05_OWNER_ACTION_REQUIRED.md`](../01-plan/TASK05_OWNER_ACTION_REQUIRED.md)（可整份转发）。把当前唯一的两处阻塞写成可直接回执的形态：① 9 项决定表（提供"建议全部采用"这一最小回执方式，第 7 项明确 A/B 两条路线的后果）；② 授权范围具体到可批准——给出建议的 Compose 项目名 `agentexam-t05-topology`、逻辑网络 `internal`/`egress`、服务 `workload`/`proxy`/`fake-upstream`、标签与"只按名称与标签删除、禁止全局 prune"的清理规则，并给出可直接改字的授权回执模板。
- 该文档同时减轻对方负担：明确 **假 Key 文件由探针自行生成、不需要负责人准备**（拒绝用例本就需刻意造出符号链接/宽权限等错误形态）；并写明第 2–4 步（白名单机制、私有文件校验、配置渲染、假服务、本机替身测试）**不必等拓扑结论**即可并行开工，即使拓扑最终不可行也不浪费。
- `TASK05_OWNER_DELIVERY.md` → `TASK05_OWNER_DELIVERY_FILLED.md` → `TASK05_OWNER_ACTION_REQUIRED.md` 三份构成"请求 → 回复 → 回执"配对，均置于 `01-plan/`。
- **负责人已把 9 项全部拍板**（回执见 [`01-plan/TASK05_OWNER_ACTION_REQUIRED.md`](../01-plan/TASK05_OWNER_ACTION_REQUIRED.md)）：输入 300,000 / 输出 32,000（含推理）/ 期限 900 秒（与构建、判卷分开计时）/ 频率 3 次每分钟（账户更低时从低）/ 支出目标 ¥100（只称计划目标）/ Kimi 日/月各 ¥80（账户设置本轮未执行）；**第 7 项选 A 保守上界**（必须证明不低估、不承诺精确账单）；私有文件用负责人已选定的仓库外路径、当前 Windows 用户为属主、绝对路径不入 Git；第 9 项**只确认资源范围、未给执行窗口**。
- 负责人三份回执原件已按原件归档（文件名去掉微信去重后缀，替换我此前发出的版本，保持一文件一权威内容）。
- 已确认数值写入[设计冻结底稿](../01-plan/STAGE1_PROXY_DESIGN_FREEZE.md)：第 3.4 节新增已确认数值表、第 2 条由"未决"改为"A 保守上界"、第 4 节由"待拍板"改为"已确认"，并在状态行与第 5 节区分**数值已确认 / 机制仍候选 / 拓扑未证**。（**当日随后更新**：T1 已在本机证成，该文件的"拓扑未证"已改为"T1 已证成、T2 未证"；见本日上方条目。）负责人明确"允许把第 1 步数值部分写入冻结记录，但未授予实施开工许可"。
- 前置核对由 1/6 升为 **3/6**（Harbor revision、无活动业务 Job、专属资源范围）；Docker 创建能力、假文件权限、当前执行授权仍缺。**7 条拓扑断言仍全部未执行，总判定仍 STOP。**
- 拉取远端：`origin/main` 由 `0cc6fb8` 前进到 `051ea51`（含 B 的 §10.2 契约、任务 03 对比页、任务 04 向导规模、五结果措辞统一等），`origin/fengyy-fixweb` 由 `6dfa2be` 前进到 `d9a7759`；`lly/dev` 由 `272a4bd` **快进**到 `051ea51`，无冲突。
- **B（Web 与 HTTP）发来两项对齐，均已核实并落位**：
  1. **接口边界纳入冻结项**：`HTTP_API.md` 第 638 行（§10.2）确实新增受控文案约束——`failure_code` 受控枚举、`failure_summary` 与 `stage_message` 为面向用户的受控短文案，不得含上游主机名或 URL、文件系统路径、凭据 profile 名、令牌或 Key 片段、容器与网络拓扑；**内容安全由写入方负责、Web 层不猜测**，并点名任务 05 的假提供方链必须遵守。已作为第 3.7 节纳入设计冻结底稿的第 1 项冻结范围，权威正文以 §10.2 为准（不复制）。
  2. **呈现验证排期**：B 需在链条落地后补两项呈现验证（受控文案忠实呈现、未知错误码失败关闭），后者需给浏览器夹具加"强制下一次响应出错"的控制端点；B 不希望为尚不存在的链路先扩测试基建，**约在本任务链条落地后一起加**。该端点属 B 的测试基建，本任务不代为实现；触发条件已写入任务单 Comments。
  3. B 明确任务 05 内无其他实现项；若错误呈现需要新出口，E 侧提前告知。B 的切片记录见 `docs/architecture/modules/web-and-http/actions/05-necessary-error-presentation.md`（其审计确认 `failure_summary` 在 `application/` 层当前无写入方、恒为 `None`，风险在将来）。
- **本机 Docker 前提变更（2026-09-21 实测）**：Docker Desktop **已安装**（CLI 29.6.2 + Desktop），但**守护进程未运行**；WSL 存在 Ubuntu-22.04。原方案"本机不装 Docker、容器与网络全部在负责人机器"的前提不再成立。**不变的事实**：`framework/harbor` 仍只在负责人机器（`.gitignore` 排除），"固定 Harbor 是否允许替换侧车网络附加"仍只能由负责人机器回答。阶段 0 当时拒绝装 Docker 的理由（虚拟网络风险）**尚未验证**——本机能否创建自定义网络仍未知，正是前置第 1 项所指。
- 产出[阶段 1 实施方案](../01-plan/STAGE1_IMPLEMENTATION_PLAN.md)：按实现地图第 3 节候选树列出文件树（`provider_access/` 恰 8 文件、`tests/providers/` 分层）、S1–S11 分片与逐片验证方式、以及**拓扑实证拆成 T1（本机纯 Docker/Compose 层）/ T2（负责人机器 Harbor 集成层）**的提案。T1 可覆盖断言 1–7 中不依赖 Harbor 的全部条目，价值是本机先证拓扑概念、负责人侧只剩 Harbor 集成一半；但 T1 通过不等于拓扑验收通过。
- 现行文档已按变更修正：`02-environment/LOCAL_SETUP.md` 的三处"Docker 未安装"表述、`01-plan/STAGE1_PROXY_TEST_DESIGN.md` 的环境前提段与风险表行。**历史行动记录保留原样**（记录当时真实状态）。
- **未修改任务单已批准的验收项**：第 2 项仍写"（组长机器）"。已在任务单 Comments 记录变更事实与 T1/T2 提案，明确"未获负责人批准前不执行拆分、不擅自修改已批准验收项"。　**（同日更新）**：负责人已同意实施开工与该拆分（经用户转述），第 2 项机器归属已同步为“T1 本机已证成 / T2 负责人机器”，原措辞在括号内保留。
- **三项授权仍全部未取得**：① 任务 05 实施开工授权（S1–S9 代码）；② T1 在本机的执行授权（启动 Docker Desktop、创建/删除专属网络与容器）；③ T2 在负责人机器的窗口与执行授权。**因此本次只产出方案文档，未写一行产品代码。**　**（同日更新）**：三项均已到位——① 实施开工与拆分由负责人同意（经用户转述）；② T1 已在本机执行完毕；③ T2 窗口可用；仍缺 T2 的**实际执行**（在负责人机器上）。

- **S8 首个片段（`agent_type` 筛选接线）已完成并验证**：按 [HTTP_API 第 315 行](../../interfaces/HTTP_API.md)"合法筛选无匹配返回空列表"的要求，把路由收下的 `agent_type` 一路传到持久层（路由 → 注册表 → 仓库端口 → SQL 条件），替身同步。新增 2 个用例（HTTP 层 + 真实 PG 层），并**实测其区分力**：把路由退回旧行为时用例失败、还原后通过。开启 PG 的 `pytest tests/catalog` 为 **44 passed / 22 skipped**；全量开 PG **536 passed / 52 skipped / 2 failed**，默认为 **485 passed / 103 skipped / 2 failed**——失败项与基线完全相同（缺 `framework/harbor` 的 ISSUE-04），增量正好是新用例。静态检查全绿。
- 顺带发现一处同类隐患（**未改**，留给 S8 主体）：`catalog_schemas.py` 的 `AgentDetail.from_record` 把 `agent_type`/`model_provider` 写死而非从记录读取；今天因两者是 `Literal` 而一致，登记第二个提供方时会不符。
- 本机 PostgreSQL 曾未运行（便携版不注册服务），已按本地环境文档命令手动启动；实时状态仍只以[本地环境记录](../02-environment/LOCAL_SETUP.md)为准。

- **用户确认 S8 采用方案 A**（只放开到受控假提供方；DeepSeek/Kimi 真实身份留给 06/07），已写入[设计冻结第 3.8 节](../01-plan/STAGE1_PROXY_DESIGN_FREEZE.md)。同节记录三处硬钉 `openai_chatgpt` 的位置与一处需 B 配合的契约变更。
- **已按任务单"E 侧提前告知"向 B 提出契约请求**（写入任务单 Comments）：`AgentSummary`/`AgentDetail` 的 `model_provider` 与 `agent_type` 现为只含既有值的 `Literal`，登记受控预设会在**响应序列化**阶段被拒，故需扩为受控集合；`catalog_schemas.py` 的 `from_record` 写死这两个值的问题一并交由 S8 修复。　**（更正，2026-09-21 实测）**：不是“被拒”而是**假报告**——给一条 `model_provider="deepseek"` 的记录，列表接口照旧回 `"model_provider":"openai_chatgpt"`（`from_record` 写死不读记录，指纹却按真实记录算）。因此“改读取”与“扩受控枚举”必须同批：先改读取会在窄枚举下直接 500。
- 用户告知**负责人机器窗口随时可用**；T2（固定 Harbor 是否允许替换其侧车网络附加）因此具备开工前提，仍缺一句书面授权（实施开工 + T1/T2 拆分）与本次创建/删除带标签资源的操作授权。　**（同日更新）**：负责人已同意授权；T2 就绪说明（命令、前置核对、回报要求）已写入组长机器预案附二。

- **S8 主体完成：受控 API 预设可登记**。身份机制由 E 定稿（provider `internal_test_fake` + authentication `provider_run_token`，成对校验，权威清单在 `domain/agent.py`）；其固定上游登记在保留域 `.invalid`，隔离网络之外永不解析→生产误配也失败关闭。改动含注册表校验、响应如实呈现（**顺带修掉把身份写死导致的假报告**）、库级约束放宽 + 显式升级 `upgrade_api_constraints()`、受控预设单独一份（生产 `AGENT_PRESETS` 不含假服务）。
- 验证：默认回归 **489/104/2**、开启 PG **541/52/2**（增量正好是 5 个新用例），`ruff`/`format`/`mypy` 全绿，2 项失败仍是 ISSUE-04。**用例区分力实测两处**，并在**本机真实旧库 `agentexam_dev` 上实测升级**（首次 True、再次 False）。
- 权威文档同步：`DATA_MODEL.md` 4.2 节与 `model_provider` 行改为"受控集合 + 指向 `CONTROLLED_IDENTITIES`"；设计冻结第 3.8 节记录身份机制。两处计划偏差已如实记入行动文档（改用既有升级模式而非新增 .sql；代码侧先落地、只把契约措辞留 B）。

- **受控文案映射（S6 片段）完成**：新增 `provider_access/failures.py`，把代理内部错误码按四类映射为 `PROVIDER_*` 受控码与固定中文短句，**未映射的内部码一律落通用值、绝不回显**。两条结构性门禁：**词汇表防漂移**（扫描包内全部大写码，出现未决定的新码即失败）与**文案哨兵扫描**（不得含主机名/URL/路径/profile 名/令牌片段/拓扑词）。`pytest tests/providers` **73 passed / 1 skipped**，默认回归 **495/104/2**（增量正是 6 个新用例），静态检查全绿；门禁区分力已实测（注入未审查的新码即失败）。边界：映射表尚无调用方（接线在 `service.py`，等 T2），受控码标注为候选待 B 列入 §10.2。

- **契约层假 Responses 上游完成**（验收第 4、5 项要的"以假上游请求记录为证"）：新增 `tests/providers/contract/`（事件构造 + 可脚本化假上游 + 薄启动脚本 + 13 个用例）。假上游记录每次请求的方法/路径/头名与正文（凭据单独保存供断言），可产出四种"丢失终止事件"的形态（连接重置、流干净提前收尾、按住不答、usage 为 null）加 401/429/500/503。**启动脚本已端到端实测**，且其输出不含凭据哨兵。`pytest tests/providers` **86 passed / 1 skipped**，默认回归 **508/105/2**（增量正是 13 个新用例），静态检查全绿。两处缺口如实记录：假上游是明文 HTTP（代理→上游那段需 TLS 包装，归集成层）；事件词表是候选、待固定 CLI 对账。

- **S2 配置渲染完成（字段名待复核）**：`codex/provider_config.py` 渲染指向代理入口的固定 TOML + sha256 摘要；**只接受环境变量名、凭据结构上无从进入**；拒绝 loopback 入口、带路径/凭据的 URL、以及任何登记过的真实上游地址（只能在可信代理侧）。两个重试参数**在顶层与 provider 表都写 0**——仓库内没有"固定 0.153.0 读哪一层"的依据，两个都写不会静默丢失上限且严格解析器拒绝时会响亮失败；真正的保底是 `transport.py` 的结构性不重试。`pytest tests/providers` **109 passed / 1 skipped**，默认回归 **531/105/2**（增量正是 23 个新用例），静态检查全绿。渲染结果尚无调用方，配置内容未与固定 CLI 对账。

- **产出第三块实施计划（准备件）**：[`01-plan/STAGE1_PROXY_SERVICE_PLAN.md`](../01-plan/STAGE1_PROXY_SERVICE_PLAN.md)——`service.py` 与接线的失败关闭流水线顺序、文件树与指标约束、分片 S6a–S6e（加 T2 后的 S10/S11）、取证规则与风险。过程见[计划行动](../../actions/2026-09-21-task05-service-plan.md)。计划里两处硬约束来自本轮核对：`provider_access/` 已 7 个源文件、`tests/providers/policy/` 已 8 个，**因此新增文件必须落在子目录**（`provider_access/server/`、`tests/providers/lifecycle/`），不需要新顶层模块或例外。

- **第三块（`service.py` 与接线）按该计划实施完毕：S6a–S6e 五片全绿；S10/S11 未碰（等 T2）。**
  - 开工前复跑第 2 节基线**无漂移**：`pytest tests/providers` 109/1、默认回归 531/105/2、`ruff format --check` 326 文件、`mypy` 176 源文件，逐项与计划一致。**另发现并如实上报一处与本任务无关的既有 flaky（未擅改）**：`tests/jobs/reporting/test_matrix_rehearsal_twelve_runs.py` 在开启真实 PG 时失败，根因是矩阵列序取自 `str(uuid4())` 生成的配置 ID，约 50% 概率与断言的顺序不符——当时单独跑通过是一次运气；该用例在默认回归里被开关跳过，故不影响 531/105/2。
  - 新增 `provider_access/server/`（8 文件，**已达每层上限**）：`contracts`（跨边界值）、`service`（六步失败关闭流水线）、`stream`（终止事件与 usage 的有界扫描）、`runner`（执行即结算；未知一律按整笔预留全额计费并关闭 Run）、`egress`（唯一开 socket 的地方：一次尝试、不跟随重定向、上游状态映射为固定码）、`http`（入站表面：受控文案应答、字节原样透传、客户端消失也结算）、`closure`（撤销令牌 + 关闭账本）。另新增 `tests/providers/lifecycle/`（5 个用例文件 + 共享替身，共 56 条新用例）。
  - **最终实测：默认回归 587 passed / 105 skipped / 2 failed**（失败项仍是 ISSUE-04 那两项）、`pytest tests/providers` **165 passed / 1 skipped**、`ruff check` 通过、`ruff format --check` 341 文件、`mypy` 184 源文件无问题。
  - **以记录为证**：假上游自己的请求记录证明了“经代理发出”（1 次请求、模型名与凭据来自绑定）与“被拒时只有一次尝试、绝不重发”；客户端收到的字节与上游逐字节一致；五条错误路径的对外文案与响应头、进程 stdout/stderr、环境与 argv、运行目录落盘文件**全部零哨兵命中**。**区分力实测共七处**（改实现让它失败、还原后通过），细节见行动记录。
  - 过程中修掉三处真实缺陷：出站漏发 `Content-Length`（假上游收到空正文当场抓到）、`decide()` 把“已关闭的 Run”误报为额度错误、以及两条测试自身的缺陷（如实记录，不改口）。

### 当前停点

- 阶段 0 环境仍可用（PostgreSQL `127.0.0.1:55432`、`agentexam_dev` 11 表）；实时状态只在[本地环境记录](../02-environment/LOCAL_SETUP.md)维护。
- 任务 04 已发布并完成；03 无独立任务单但 B 在推进；**05 已在本机实施完毕**：前置核对、S2–S8、T1 与本轮 S6a–S6e 全部完成；**S9（worker 绑定选择）、S10（`net/`）、S11（集成层）未做，均等 T2**。
- **授权与状态已同步**：任务单 05 确认**已在 `main`**（`6ccf001` 是 `origin/main` 的祖先），标签 `needs-info` → `ready-for-agent`，第 2 项验收机器归属改为“T1 本机已证成 / T2 负责人机器”。依据为**经用户转述**的负责人同意，已建议负责人补一句书面确认。
- **仍未完成的两件事**：① **T2 在负责人机器执行**——T1 已在其机器复测通过、源码结论也已拿到（允许按服务绕过），**授权增补已给出**，只差按"最小 T2 形态"跑一次并回报；② **B 的契约确认**——受控提供方在响应中的呈现方式（枚举扩宽与如实读取记录）。
- ~~一处待用户拍板的架构选择~~：已定稿（受控 provider 值 + 保留域上游），见上方 S8 主体条目。
- 推送状态（2026-09-21 合并 `origin/main` 时核对）：**早期切片**（`af00f83`、`272a4bd`、`c544eef`、`15828f4`、`6ccf001`、`3db8955`）已随 PR #9/#10 进入 `main`；**本轮切片**（`40a5f16` 起，含 S3–S8 与 T1 探针、受控文案映射）在 `origin/lly/dev`，待合并。本轮另合并了 `origin/main` 的 `051ea51`→`1888aa2`（B 的任务 03 对比页、D 的任务 08 预演与文档），4 处文档冲突按"以当前状态为准"解决：`docs/LLY/` 三份与任务单取我方较新记录，`README.md` 手工合并并保留 feng 侧行动记录链接；main 侧的并行负责人决定记录无新事实、状态更旧，未保留重复条目。**合并后实测**：`ruff check` 通过、`ruff format --check` 318 文件、`mypy` 175 源文件无问题；默认回归 **495 passed / 105 skipped / 2 failed**（跳过 +1 是 D 新加的十二 Run 演练用例，默认不启用；失败项仍是 ISSUE-04），开启 PG 全量 **548 passed / 52 skipped / 2 failed**。**前端未验证**：本机仍未安装 `node_modules`，合并带入的 B 侧任务 03 UI 改动在本机无法跑类型检查与构建。
- **下一步（E 侧）**：① **本机可做的基本做完**——S6a–S6e 已实施，S9/S10/S11 都卡在 T2 的结论上；② **待用户/负责人拍板一件安全取舍**：客户端转发头是否收紧为白名单（当前 `Host`/`Accept-Encoding`/`Content-Length`/`Transfer-Encoding`/`Connection` 由传输层接管，其余客户端头仍转发）；③ S2 字段名等固定 CLI 在负责人机器复核；④ **T2 在负责人机器执行**（窗口已可用）；⑤ 本任务链条已落地，**可以通知 B** 排期加“强制下一次响应出错”的夹具端点与两项呈现验证。
- 前端依赖仍未安装：合并带入的任务 02 Web 代码在本机**未经验证**（未跑类型检查、生产构建与浏览器回归）。


## 2026-09-19

### 已完成

- `lly/dev` 从 `625d02b` 安全快进到 `origin/main` 的 `6dfa2be`；同步前已有的 `docs/LLY/` 与本地行动文档均保留，无冲突。
- 阅读新提交的统一环境配置：owner 的 `infra` 部署链现在要求 Git 忽略的 `infra/.env`；普通后端应用仍只读取进程环境变量。本机便携 PostgreSQL 开发不使用 Docker，因此当前不创建 `infra/.env`。
- 重新核对项目停点：扩展规格、计划、实现地图和验证规范仍为 `needs-info`，01–08 仍未发布 issue；E 模块下一项是任务 05，但尚未获开工授权。
- 用户确认当前继续处于阶段 0，并授权按建议自行确定本机前提环境方案；已确定 `agentexam_identity_test`（自动化测试）与 `agentexam_dev`（日常开发）两库隔离，不再把 Tailscale 或共享管理员数据库作为前置。
- 已落盘[阶段 0 设计](../01-plan/STAGE0_LOCAL_DEVELOPMENT_DESIGN.md)与[详细实施计划](../01-plan/STAGE0_LOCAL_DEVELOPMENT_PLAN.md)，并按计划完成了本机环境实施。
- 已按计划完成阶段 0：恢复 PostgreSQL、创建 `agentexam_dev`、安装 11 表 schema、同步 Python 依赖、运行静态检查与本地 PostgreSQL 集成测试，并完成停止/重启读回。
- PostgreSQL 集成测试实际结果为 **246 passed / 11 skipped / 2 warnings**；默认回归为 **386 passed / 82 skipped / 2 failed / 2 warnings**，两个失败均为缺少 `framework/harbor` 的已知 ISSUE-04。

### 当前停点

- 阶段 0 已完成；2026-09-19 收尾时 PostgreSQL 按 `127.0.0.1:55432` 运行、`agentexam_dev` 可用。实时运行状态只在[本地环境记录](../02-environment/LOCAL_SETUP.md)维护。
- 不自动开始任务 05，不调用真实模型、不下载 Harbor/Fork 大体积环境。
- 下一步应由项目负责人先审阅并发布扩展任务；按既定顺序，团队整体先处理 01，轮到 E 模块时再为 05 冻结代理拓扑与安全合同。

## 2026-09-18

### 已完成

- 克隆并同步仓库到 `D:\agent-exam`；工作区 HEAD 与 `origin/main` 一致（`625d02b`）。
- 通读项目入口文档：`AGENTS.md`、`HANDOFF.md`、`CONTEXT.md`、模块索引与七个模块架构、团队分工文档、M1 规格与任务单、扩展执行计划。
- 确认项目现状：M0 核心闭环通过；M1 任务 01–13 验收完成，14（私有双机协作验收）进行中；P（本地持久化）已完成；扩展 01–08 已规划未发布 issue。
- 排查本机 Tailscale 无法登录的问题，结论记录在[问题记录](../04-issues/KNOWN_ISSUES.md)（尚未解决，已排除多项）。
- 当日确认本机便携 PostgreSQL 开发不需要 `.env`：后端无 dotenv 依赖、无 `.env` 自动读取逻辑，配置来自进程环境变量。owner `infra` 部署链在次日同步的新提交中另行引入 Git 忽略的 `infra/.env`，不改变本机开发结论。
- 创建开发分支 `lly/dev`。
- 建立 `docs/LLY/` 四类过程文档目录与目录说明。
- 编写 E 模块本地开发计划书。
- 启动 PostgreSQL 15.14 便携版下载（约 320 MB）。

### 本地环境（已完成）

- 安装 PostgreSQL 15.14 便携版到 `D:\pgsql`，数据目录 `D:\pgsql\data`，监听 `127.0.0.1:55432`（仅回环），回环信任认证（因此无需创建或保管任何数据库密码）。
- 建立专属测试角色与库 `agentexam_identity_test`（含 `CREATEDB`，测试夹具需要自建临时库）。
- 用项目自带 `initialize_empty_database()` 安装业务 schema，实际得到 **11 张表**，与预期清单逐项一致。
- 用 `uv sync` 建好 Python 环境：uv 自动准备 **Python 3.13.15**（系统 Python 是 3.12.0，不满足项目要求 `>=3.13,<3.14`），依赖按 `uv.lock` 装齐。
- 静态检查基线：`ruff check` 通过、`ruff format --check` 283 文件已格式化、`mypy` 164 源文件无问题。
- 默认回归基线：**386 passed / 82 skipped / 2 failed（52.96 秒）**。
  - 82 项跳过是设计如此：需要真实外部依赖的用例藏在 `AGENTEXAM_RUN_*` 显式开关后面。
  - 2 项失败均因缺少被 gitignore 的 `framework/harbor`（只在组长机器上），属环境依赖，非产品缺陷；已记为 ISSUE-04。
  - 注意：文档中曾记载的"194 passed / 19 skipped"是 M0 时期的数据，当前默认套件规模已明显增大，不能沿用旧数字。

### 进行中

- 前端依赖未安装；MinIO、Docker 未配置。

### 观察与结论

- 本机（`D:\agent-exam`）是一份新克隆：没有 `apps/backend/.venv`、没有 `apps/web/node_modules`、Docker 未运行、`D:\AgentExamData` 不存在。文档中记录的历史验证证据来自另一台机器，本机不能声称"刚跑过"。
- `HANDOFF.md` 中记录的 workspace 是 `E:\9.1agent_exam`，与本机路径不同；文档中的提交数、环境现场描述带有上一台机器的假设，接续时需重新核对。
- M1 任务单的 `**Status:**` 标签不一致：01–11 仍为 `ready-for-agent`，12–13 为 `completed`，14 为 `in-progress`。任务 01–13 的验收勾选框实际已全满（按任务 01 注释的规则，完成以验收项与行动证据判定，标签不增设完成值），但仅凭标签统计进度会读错。
