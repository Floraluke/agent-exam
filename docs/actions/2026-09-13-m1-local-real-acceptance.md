# M1 任务 13：本机真实平台验收

> 状态：Completed；`-04` 完整真实流程、最终双轴评审和公开证据收尾均已完成。M0 第四场仅作历史基线，不计作本任务证据。

## 情况说明

M1 任务 01–12 已验收。当前需要证明同一个正式平台 Job 能从 HTTP 提交、所有者批准、Worker 领取，经固定 Harbor/Codex/Fork 执行与判卷后，把报告和安全证据持久化到专属 PostgreSQL/MinIO，并由页面读回。

现有 `WorkerShell` 和 `JobExecutor` 已承载业务流程，但尚无把正式 PostgreSQL、MinIO、固定任务源、Harbor Adapter 与 Fork Evaluator 组合起来的本机运行入口。此次只深化该 Worker Module 的 Implementation，不新增业务 Module、port/Interface、数据库表或顶层目录，也不改变既有 `ExecutionBackend` / `PatchEvaluator` seam。

## 已批准的最小范围

- 先运行不调用模型的 Harbor 异常终止/清理门禁；失败即停止真实运行。
- 只创建一个正式 `official` Job，固定任务 `python__mypy-15413`、固定 Agent `codex-0153-terra-medium`、一个 Run；创建与批准请求本身不启动模型。
- 仅所有者批准后，由正式 Worker 领取一次；最多一次真实 Codex 模型尝试，失败不自动重试。
- 固定 Codex 0.153.0、`openai/gpt-5.6-terra`、medium、web disabled；固定 Harbor、SWE-Gym 与 SWE-Bench Fork revision，认证只引用项目私有 `auth.json`，不读取、显示或持久化其正文。
- Agent 上限 900 秒、1 CPU、4096 MiB 内存、8192 MiB存储；Evaluator 上限 300 秒、1 CPU、4096 MiB 内存。模型网络只允许既有固定认证/模型端点范围，不开放网页浏览。
- PostgreSQL、MinIO、HTTP、页面及运行证据使用本任务专属隔离身份和临时目录；不连接现有数据库，不更改 Docker/WSL/代理/防火墙或机器设置。
- 原始 Harbor/Codex 材料保持所有者私有；HTTP/MinIO 只发布既有策略允许的派生安全证据。退出时按专属标签和已核验绝对路径精确清理临时容器、数据与进程，保留固定镜像、构建缓存、私有认证源和公开审计摘要。
- 历史仍未覆盖的 IPv6、长连接/sidecar 故障、完整代理路径和真实 token 刷新不冒称通过；若固定路径触发这些风险或需要新增额度/外部操作，立即停止并重新取得授权。

## 后续追加授权（2026-09-13）

- 用户准备离线休息前明确允许使用既有私有认证，最多再执行 3 次受控的完整真实流程，不需逐次等待批准；先修复并完成任务 13，再进入任务 14，任务 14 完成后执行一次全量回归。
- 三次是上限而不是必须消耗的次数：每次仍固定本行动已有任务、Agent、模型、网络、资源与专属隔离边界；单次失败先诊断和无模型修复，再决定是否使用下一次，不并发、不自动重试、不为凑次数浪费额度。
- 认证正文继续不展示、不入 Git、不进入公开证据；每次使用新 scope 并精确清理。现有额度先使用到约剩 1–2%，届时先保存行动/交接和本地提交，再按用户既有要求使用当前唯一可用的重置，不提前兑换。

## 实施措施

1. **门禁对账**：核验固定源码 revision、归档大小/哈希、数据集身份及私有认证文件的存在性/文件类型；不输出敏感路径或正文。运行无模型的异常清理回归。
2. **Worker 组合切片**：以现有 `WorkerShell.run_once(worker_id)` 为外部 Interface，先写失败测试，再增加显式配置驱动的正式组合 Implementation；所有运行依赖缺失时安全失败，且不创建/批准 Job。
3. **真实平台切片**：启动专属临时 PostgreSQL/MinIO 和回环 HTTP/页面，通过 HTTP 使用合成本机成员提交固定 Job、由唯一所有者批准，然后调用正式 Worker 一次。
4. **结果核对**：经 HTTP 和页面读回状态、一个平台 Job/一个 Harbor Job/一个 Run 的身份、patch 哈希、独立判卷结果、排行来源与兼容空值；扫描公开响应和对象元数据，确认无凭据/原始私有正文。
5. **退出与回归**：精确清理专属运行资源，执行取消×恢复交叉、存储失败、完整后端、浏览器、静态检查和构建；失败/跳过均原样记录。
6. **评审与收尾**：以任务 12 关闭提交 `5e39632` 为固定基准，分别完成 Standards/Spec 评审，修复并复验；同步任务单、架构、数据模型、Interface 和 HANDOFF，只提交本任务明确文件，不推送。

## 需要修改的文件树

```text
apps/backend/
├─ src/eval_platform/adapters/
│  ├─ artifacts/local.py              # 已实现：读取受限本地 Harbor/Fork 证据，分离引用根与安全根
│  └─ execution/harbor/config_mapper.py # 已实现：目录身份映射为固定单次、零重试 Harbor Job 配置
├─ src/eval_platform/delivery/worker/
│  ├─ main.py                         # 既有 Worker 外部 Interface；保持 run_once 语义
│  └─ runtime.py                      # 已实现：集中组合正式 PG/MinIO/Harbor/Fork 依赖
├─ tests/
│  ├─ jobs/execution/test_evidence_publication.py # 本地证据来源的发布行为回归
│  ├─ jobs/runtime/test_worker_runtime.py         # 通过组合入口验证显式绑定与安全失败
│  └─ unit/test_harbor_config_mapper.py           # 固定 Job 配置与目录身份映射契约
└─ pyproject.toml                     # 仅在需要稳定本机命令时注册既有 Worker 入口
docs/
├─ actions/2026-09-13-m1-local-real-acceptance.md  # 本行动及实际证据
├─ architecture/ARCHITECTURE.md                    # 当前模块边界、数据流与风险
├─ architecture/DATA_MODEL.md                      # 实际 Job/Run/证据身份核对
├─ architecture/MODULE_CONTRACTS.md                # Worker 组合 Interface 与依赖方向
├─ interfaces/FRAMEWORK_INTERFACES.md              # 固定 Harbor Job/Trial 配置落盘语义
├─ interfaces/HARBOR_EXECUTION.md                  # 本次真实执行/清理门禁结果
├─ interfaces/HTTP_API.md                          # HTTP 与页面验收结果，不新增契约时只更新状态
└─ operations/LOCAL_DOCKER_ENVIRONMENT.md          # 本机临时拓扑与精确清理证据
.scratch/m1-platform/issues/
└─ 13-local-real-acceptance.md         # 九项验收、状态和证据指针
HANDOFF.md                            # 最新真实状态与下一任务入口
runtime/acceptance/m1-task13-20260913-01/  # Git 忽略的一次性本机验收证据与编排器
├─ runtime_support.py                 # 临时身份、环境、HTTP/Web 生命周期
├─ runtime_parts/
│  ├─ config.py                       # 专属作用域和清理标签
│  ├─ storage.py                      # 固定 PG/MinIO 身份、受限启动和就绪核对
│  └─ cleanup.py                      # 尽力清理全部专属资源并核验终态
├─ platform_flow.py                   # HTTP 提交、批准和唯一 Worker 领取
├─ platform_verify.py                 # 固定身份、失败终态、正文哈希和发布保护核对
├─ platform_identity.py               # 冻结 Task/Agent/策略/执行身份核对
├─ platform_acceptance.py             # preflight/run 模式及保守摘要收束
├─ verify-browser.mjs                 # 少量真实页面验收
└─ tests/
   └─ test_acceptance_harness.py       # 忽略态编排器的失败摘要/清理/哈希红绿测试
runtime/acceptance/m1-task13-20260913-02/  # 第二次 Run 的源码等价专属作用域；不复制首次私有证据
├─ 与上方 10 个初始编排源码/测试路径同构    # 仅 scope/容器/网络测试身份改为 -02；零模型 preflight 已通过
├─ platform_harbor.py                         # 第二次后新增：分层核对源 Job、落盘 Job 与唯一 Trial
├─ platform_verify.py                         # 改为调用分层 Harbor 证据 Interface
└─ tests/
   ├─ harbor_evidence_fixture.py               # 两组 Harbor 验收测试共享的显式合成目录构造器
   ├─ test_acceptance_harness.py               # 最终摘要、制品哈希/下载保护与清理回归
   ├─ test_harbor_evidence.py                  # 默认省略、固定身份/安全配置与错误归一回归
   └─ test_harbor_path_safety.py               # 固定任务入口在解析前拒绝链接的路径安全回归
runtime/acceptance/m1-task13-20260914-03/  # 追加授权第 1 次完整运行的全新隔离作用域
├─ 其余源码与测试由上方 -02 等价复制       # 排除 evidence、safe-summary、缓存及所有既有运行产物
├─ platform_acceptance.py                  # preflight/run 在临时存储前执行浏览器依赖门禁
├─ runtime_support.py                      # 固定项目 Playwright 1243 缓存核对与进程级绑定
├─ runtime_parts/storage.py                # 新增主机侧 PostgreSQL DSN 就绪门禁，避免端口转发竞态
├─ verify-browser.mjs                      # 真实页面登录、完成态、批次/Run 报告与秘密缺席核对
├─ results/                                # 安全摘要、Web 日志和页面截图；与源码根分层
└─ tests/
   ├─ test_browser_runtime.py              # 缺失、链接/junction、项目外缓存均在 Job/模型前失败关闭
   └─ test_storage_readiness.py            # 内部已就绪、主机首连延迟的合成红绿回归
runtime/acceptance/m1-task13-20260914-04/  # 最终成功隔离作用域；16 个源码/测试与 -03 等价
├─ evidence/                              # 私有 Harbor/Fork 原始材料；不入 Git、不经公开接口发布
└─ results/                               # safe-summary、Web 日志与真实浏览器截图
```

文件树已随红绿循环收敛，`runtime.py` 与 `agentexam-worker` 脚本注册均已采用。设计模式保持 Ports & Adapters：`ExecutionBackend` / `PatchEvaluator` 是既有 ports，Harbor / SWE-Bench 是 Adapters，Worker runtime 是 composition root；它只隐藏依赖组装，不形成第二条执行链。

## 修改后自验证方式与成功标准

- **红绿证据**：新增测试先因正式 Worker 组合能力缺失而失败，最小实现后通过；测试从公开 Interface 观察领取结果和依赖校验，不断言内部调用细节。
- **无模型门禁**：异常退出、超时、上传/观察失败的适用测试通过，且 Harbor Compose/临时目录按本次专属身份清理；任何失败都阻断真实 Run。
- **真实 HTTP 主流程**：创建响应为等待批准；批准后才可被 Worker 领取；全程只有一个正式 Job、一个 Run 和一次模型尝试。
- **真实判卷与持久化**：固定任务/配置/revision 与实际 patch SHA-256 可追溯；执行与判卷结论原样保存，PostgreSQL/MinIO/HTTP 页面读回一致。
- **隔离与发布保护**：内部测试结果不进入正式排行；协作者只能看到自身正式结果；公开响应/下载不含认证、原始 Codex 输出或隐藏判卷材料。
- **资源与清理**：容器非特权、受控 CPU/内存/存储/网络；任务结束后没有本次专属容器、监听进程或未清理临时数据。
- **完整回归**：后端 pytest、ruff、format check、compileall、strict mypy，以及 web typecheck/build/浏览器验收均成功；外部门禁跳过数单独报告。
- **双轴终审**：相对 `5e39632` 的 Standards 与 Spec 均无未解决发现；九项任务验收全部有实际证据后才关闭任务 13。任务 14 私有双机验收和 M1/MVP 完成声明保持独立。

## 自验证情况

- 2026-09-13 授权前只读核对：HEAD 为任务 12 关闭提交 `5e39632`；产品源码无未提交改动，既有混合文档、未跟踪阅读/行动文档、缓存及 framework/runtime 均保留。
- 已确认 `WorkerShell` / `JobExecutor`、正式 HTTP composition root、PostgreSQL Job Repository、MinIO Artifact Store、Harbor Adapter 和 SWE-Bench Evaluator 均已存在；缺口是正式 Worker 的依赖组合，而不是新的执行 Interface。
- 已把 TDD seam 固定为 `WorkerShell.run_once(worker_id)` 及 HTTP 用户流程；尚未写测试、实现或启动真实模型。
- M0 第四场的单题成功、资源限制与固定路径只记为历史基线。本行动的门禁、真实运行、回归、评审和精确清理结果待执行后逐项追加。
- 目录→Harbor 契约红灯为 `1 failed, 6 passed`：正式 preset 的业务提供方名 `openai_chatgpt` 未映射成固定 Harbor 运行时名 `openai`，被 `REAL_CODEX_CONFIG_INVALID` 拒绝。`config_mapper` 只在 Adapter 内完成该名称映射后，同文件 `7 passed`；没有改变 Agent 指纹或目录事实。
- Worker 组合按两个红绿切片加入现有 `delivery/worker`：首次分别因模块/命令不存在而在收集期失败；实现显式环境配置、敏感字段不进入 `repr`、固定输入预检、正式 PG/MinIO/Harbor/Fork 组装及一次领取命令后，相关 10 项测试通过，ruff 与 format check 通过。
- 首次专属存储回归使用 Windows PowerShell 5.1，因运行时缺少所需加密随机数 Interface 而在创建测试凭据前失败；`finally` 确认专属容器和 tmpfs 数据已清理。改用项目既有 PowerShell 7 后第一次跑出 133 通过、2 失败，暴露 Worker 依赖源码目录层级推断、无法适配容器复制布局；改为显式 `AGENTEXAM_PROJECT_ROOT` 后重跑为 `135 passed`，再次确认专属容器和 tmpfs 数据全部移除。
- 无模型 Docker 门禁：固定 Codex 离线安装/Harbor 复用 `1 passed in 15.53s`；真实 Harbor 外层 45 秒超时及精确 Compose 清理 `1 passed in 49.11s`。均未提供认证绑定或调用模型。
- 真实模型 Run 尚未启动；下一步先建立一次性专属 PG/MinIO/回环 HTTP/页面拓扑，再执行唯一一次已批准的正式 Job。
- 真实编排器在操作系统进程创建前被安全审批器拒绝：现有“批准最小方案”没有被判定为对“读取本机 ChatGPT 认证引用并访问外部模型网络的一次真实 Run”的足够具体授权。未启动脚本、未创建 Job、未读取认证、未连接模型。随后只读核对未发现本任务标签的容器/网络、验收摘要或 3100/8875/9000/5432 监听；不尝试绕过，等待用户对这一次真实 Run 明确授权。
- 在等待授权期间增加 Git 忽略的 `preflight` 模式，只启动专属临时 PG/MinIO 与回环 HTTP，不创建 Job、不读取认证、不访问模型网络。首次因身份存储统一错误失败并完成清理；最小诊断依次排除了容器内健康、启动等待、schema 主流程、MinIO 和 Uvicorn 自身。
- 诊断确认两个编排器问题：Docker Desktop 的 `--internal` 网络使已发布的 Windows 回环端口持续 `ConnectionTimeout`；移除该标志后端口仍只绑定 `127.0.0.1`，固定存储镜像、非特权限制和一次性随机凭据不变。其次，Identity 初始化已经同时建立邀请表，编排器重复调用 Membership schema 导致重复建表；已删除第二次调用。完整拓扑中回环就绪探针最后取得代理生成的 502，故所有本机 HTTP 客户端显式 `trust_env=False`，不更改机器代理，也不改变 Harbor 模型网络策略。
- 原始零模型预检复跑通过：`storage=ready`、`http=ready`、`jobs_created=0`、`model_called=false`、`auth_read=false`、`cleanup=verified`。临时诊断文件和全部 `[DEBUG-task13-*]` 标记已删除；任务专属容器、网络与 tmpfs 数据没有残留。存储容器所在临时 bridge 理论上具备出站能力，但其固定命令只监听服务、端口仅发布到回环且不持有真实凭据；模型网络仍由 Harbor 单独 allowlist 控制。
- 代码回归复跑通过：后端 `379 passed, 77 skipped, 2 warnings in 49.36s`；77 项均为未设置专属 PG/MinIO、Docker/Fork/网络/真实 Codex 开关的显式外部门禁跳过，不冒称已覆盖。`ruff check`、`ruff format --check`、`compileall` 和 strict mypy 全部通过，mypy 覆盖 161 个源文件；web `typecheck` 通过。
- web 生产构建首次因沙箱/用户级 Next.js 配置缓存跨设备重命名失败（`EXDEV`），不是源码编译失败。改用只对该命令进程生效的任务工作区 `APPDATA` / `LOCALAPPDATA` 与禁用遥测、更新提醒后，`next build` 编译、类型核对、4 个静态页面生成和 build trace 全部成功；没有更改机器设置。工作区缓存目录预创建被拒但构建仍成功，故只把最终退出码 0 和完整构建阶段作为通过证据，不把缓存创建描述为成功。
- 相对固定基准 `5e39632` 的首轮双轴评审各有 4 项：Standards 指出清理过程未逐项核验、失败摘要可误报通过、行动文件树仍写候选/遗漏忽略态编排器、HANDOFF 超前数过期；Spec 同样指出摘要与清理问题，并指出基础设施失败时丢失已持久化 Job/Run 终态、未完整核对冻结 Agent/限制/backend 身份、未重算下载 patch 哈希及未明确断言私有原始制品不可下载/兼容空值。修复先以忽略态单元测试取得红灯，再拆出清理与验证 helper，要求任一业务、浏览器或清理失败都强制 `status=failed`，清理尽力遍历全部专属资源后再汇总失败；真实 Run 仍受单独授权门禁。
- 评审修复红灯为测试收集期 `ImportError: cannot import name 'finalize_result'`。实现最终摘要收束、全部专属资源尽力清理后统一判定、已持久化失败终态安全快照、完整 Task/Agent/限制/策略/backend identity、下载正文 SHA-256 重算、受限原始正文非 200、Judge 兼容空值和唯一 Harbor config 后，忽略态测试 `3 passed`。首次结构检查又发现格式化后的 `runtime_support.py` 为 232 行；没有压行规避，而是拆到 `runtime_parts/{storage,cleanup,config}.py`，最终各 Python 文件均不超过 200 行，根目录 7 个文件；ruff、format check、compileall 均通过。
- 修复后零模型 `preflight` 复跑为 `status=passed`、`storage=ready`、`http=ready`、`jobs_created=0`、`model_called=false`、`auth_read=false`、`cleanup=verified`；随后按 `agentexam.task13=m1-task13-20260913-01` 和精确网络名查询均为空。该证据只证明编排与清理，不替代真实 Run。
- 第二轮双轴复审确认首轮摘要误报、失败快照、文件树和主要清理问题已关闭，但继续发现：Worker 外层超时未纳入统一进程树清理，清理终态只查 API/Web 而漏查 PostgreSQL/MinIO 端口，成功报告未核对 `backend_job_ref/backend_trial_ref`，行动中仍残留一句旧“候选”。新增测试先在收集期因缺少 `validate_backend_refs` 红灯；修复把 Worker handle 纳入 Runtime、Worker/Web 均执行 taskkill 后 wait/poll、四个回环端口全部等待关闭，并要求成功报告的 Harbor Job ref 等于平台 Job、Trial ref 非空。忽略态测试最终 `4 passed`，ruff/format/compileall 通过，所有 Python 文件不超过 200 行；再次零模型预检得到同一通过摘要并验证清理。
- 第三轮终审继续以 `5e39632` 为固定基准并读取未提交权威文档及全部忽略态验收源码：Standards 为 0 findings/PASS，Spec 为 0 findings/PASS；首轮与第二轮问题均确认关闭，未发现范围蔓延或新 smell。真实 Run 尚未获得安全审批器所需的逐项明确授权，仍是验收未完成状态而非代码 finding，九项任务验收不能据此提前关闭。
- 用户随后明确回复“授权”，承接上一条逐项授权文本；唯一真实 Run 已启动且没有重试。HTTP 主流程成功创建一个正式 Job `ab23ff7b-1e35-49df-8bbe-07e5c3967ac6`、等待并取得唯一所有者批准，Worker 执行约 120 秒后收束为 Job `FAILED/BATCH_FAILED`、Run `FAILED/EVIDENCE_UNAVAILABLE`；失败状态由 HTTP 安全快照捕获，专属 PG/MinIO、回环进程、容器和网络清理验证通过。没有进入页面验收，不把本次失败或历史 M0 成功计为任务通过。
- 只读诊断不读取认证或私有原始正文：Harbor 证据树存在唯一 Trial 的 `result.json` 和 1302 字节 `model.patch`，但没有 evaluation 目录，说明模型已形成补丁而独立判卷尚未开始。源码对账确认正式 composition root 构造 `JobExecutor` 时遗漏已有 `LocalArtifactReader(config.evidence_root)`，使 `EvidencePublication` 默认把 MinIO 同时当来源；Harbor 返回的本地绝对 patch 引用必然不符合 MinIO 的 `runs/{uuid}/{type}/{sha256}` 长期对象键契约，遂在 `prepare_patch` 阶段得到 `ArtifactUnavailable`，映射成 `EVIDENCE_UNAVAILABLE`。下一切片先以组合测试取得红灯，再只补上已有本地 reader seam；本次真实尝试已用尽，修复后不得自动重跑模型。
- 证据读取接线的 TDD 红灯为 `1 failed, 3 passed`：新增组合测试捕获到 `JobExecutor.source_artifacts=None`，确认失败来自正式 Worker 组装遗漏，而不是 Harbor patch、MinIO 写入或 Fork 判卷逻辑。最小修复只在既有 composition root 构造 `LocalArtifactReader(config.evidence_root)` 并作为 `source_artifacts` 传入，MinIO 继续只承担规范化长期对象的 destination；没有新增 Interface、执行链、表或目录，也没有改动 M0 `ExecutionBackend` / `PatchEvaluator`。
- 修复后定向回归 `16 passed`；完整后端为 `380 passed, 77 skipped, 2 warnings in 42.02s`，77 项仍是未开启专属 PG/MinIO、Docker/Fork/网络/真实 Codex 开关的显式外部门禁跳过。`ruff check`、`ruff format --check`、`compileall` 与 strict mypy 均通过，生产 `runtime.py` 为 173 行；代码与测试修复提交为 `10f0c53`。这些都是无模型验证，不能替代第二次真实 Run。
- `10f0c53` 提交后没有再次读取认证、调用模型或复用首次私有证据目录；第一次真实 Run 的一次性授权已经使用。下一步先相对 `5e39632` 完成包含现场权威文档的 Standards/Spec 双轴复审；若无未解决发现，仍须用户对新专属验收目录中的第二次且最后一次固定 Run 重新作出同等具体授权。
- `10f0c53` 后双轴复审发现同一 P1 根因：Harbor 返回专属证据根内的绝对引用，但 Fork 的 `result_mapper` 以项目根生成项目相对引用；当前 `LocalArtifactReader(config.evidence_root)` 会把后者误拼成 `evidence_root/runtime/...`，因此补丁发布虽已修复，判卷证据发布仍会再次得到 `EVIDENCE_UNAVAILABLE`。Standards 另记一项 P2：组合测试只断言 reader 的内部根属性，没有用两种既有引用形态观察读取行为，与本行动约定的公开 seam 测试不一致。两轴当前分别为 Standards 2 findings、Spec 1 finding，不能请求真实复跑。
- 下一红绿切片保持既有 `ArtifactReader` Interface：只深化 `LocalArtifactReader` Implementation，把“允许读取的安全根”和“解释相对对象键的引用根”明确分开；绝对或相对引用解析后仍必须落在专属证据根内。通过 `create_runtime_worker` 既有组合入口，用一个 Harbor 绝对引用和一个 Fork 项目相对引用验证可读取正文，并验证项目相对逃逸仍被拒绝；不新增 port、业务 Module、表、顶层目录或平行执行链。
- 第二轮 TDD 红灯为 `1 failed, 3 passed`：Harbor 绝对 patch 已能读取，Fork 的 `runtime/acceptance/.../evaluation/.../report.json` 项目相对引用被错误拼到 `evidence_root/runtime/...` 并抛出 `ArtifactUnavailable`。Implementation 只给既有 `LocalArtifactReader` 增加可选 `reference_root`：相对键从项目根解释，绝对键保持原样；两条路径解析后仍统一执行 `resolved.relative_to(evidence_root)`、普通文件、大小和 SHA-256 检查。组合行为绿灯为 `4 passed`，没有放宽安全根。
- 进一步从既有 `ArtifactReader` Interface 验证：Harbor 绝对 patch 走 `read_verified`、Fork 项目相对报告走 `read_bounded_verified` 均返回预期正文；项目相对键若指向专属证据根外，即使文件真实存在也得到 `ArtifactUnavailable`。证据发布/限额/Worker 定向回归为 `17 passed`。这替换了只读取 `reader.root` 内部属性的脆弱断言，测试语义与调用方实际方法一致。
- 完整无模型回归为 `381 passed, 77 skipped, 2 warnings in 41.18s`；ruff、format check、compileall 与 strict mypy 全部通过，mypy 覆盖 161 个源文件。ruff 尝试写既有不可写缓存时报告 warning，但检查退出码为 0；生产 `local.py`、`runtime.py` 和两份相关测试均未超过 200 行，所在目录未超过 8 个文件。修复提交为 `3d66230`，仅含四个明确代码/测试文件；未读取认证、调用模型或重用首次证据目录。
- `3d66230` 后复审结果：Spec 为 0 findings/PASS，确认既有 `ArtifactReader` Interface、专属根限制及任务未完成表述正确；Standards 确认前两项均关闭，但给出 1 项 P3 判断性 `Duplicated Code`：`read_verified` 与 `read_bounded_verified` 重复同一套类型、路径解释、符号链接、根约束和文件/大小校验。下一步只在 `LocalArtifactReader` Implementation 内提取一个私有受限路径 helper，由现有两种公开读取行为共同复用；Interface、错误模式与调用方不变，使用现有 17 项行为回归验证。
- P3 重构把共享规则集中到私有 `_verified_path`，`read_verified` 只保留 50 MiB 整体读取上限与最终哈希，`read_bounded_verified` 只保留流式有界读取；安全路径、类型、retention、普通文件和声明大小验证只维护一份。定向回归仍为 `17 passed`，完整后端仍为 `381 passed, 77 skipped, 2 warnings in 49.86s`，ruff、format check、compileall、strict mypy 均通过；提交 `1b8e9ba` 仅含该 Implementation 文件。下一步重做最终双轴评审，未取得第二次真实 Run 授权前继续停在无模型状态。
- 最终双轴评审继续固定 `5e39632` 并读取 live 权威文档与全部忽略态任务 13 验收源码：Standards 为 0 findings/PASS，确认 P3 重复安全校验已集中且无新增 smell；Spec 为 0 findings/PASS，确认 `ArtifactReader` Interface、M0 seams、任务范围、失败与未重跑表述均未改变。评审只关闭实现发现；任务仍为 `in-progress`，首次私有证据保持原样，剩余七项验收必须由新专属作用域中的第二次且最后一次获批真实 Run 证明。
- 等待第二次真实 Run 授权期间先做无模型准备：从 `m1-task13-20260913-01` 只复制编排源码和测试到新作用域 `m1-task13-20260913-02`，明确排除首次 `evidence/`、`safe-summary.json`、`__pycache__` 和其他运行产物；只把 scope、专属容器/网络身份及合成测试期望改为 `-02`。先运行编排器单元/静态检查和 `preflight`，成功标准仍为零 Job、零认证读取、零模型调用与精确清理；这不构成第二次真实 Run，也不消耗其一次模型尝试。
- 新作用域源码对账为 `files=10`、`unexpected_differences=0`：除 `m1-task13-20260913-01` 精确替换为 `-02` 外没有漂移，复制前后的首次 `evidence/` 与摘要均未带入。编排器测试 `4 passed`，ruff 通过、9 个 Python 文件 format check 通过、compileall 通过；没有修改首次作用域。
- `m1-task13-20260913-02` 零模型 preflight 实际结果为 `status=passed`、`storage=ready`、`http=ready`、`jobs_created=0`、`model_called=false`、`auth_read=false`、`cleanup=verified`。随后按 `agentexam.task13=m1-task13-20260913-02` 分别查询全部容器与网络均为空。preflight 只生成新作用域的安全摘要，没有创建正式 Job、读取认证或访问模型；下一步仍须取得第二次且最后一次真实 Run 授权。
- 用户随后连续回复“批准你”“批准”，明确承接上一条完整授权文本：允许在 `m1-task13-20260913-02` 验证 `10f0c53`、`3d66230`、`1b8e9ba`，使用既有私有 `auth.json` 和固定 `auth.openai.com` / `chatgpt.com` 模型网络，固定 `python__mypy-15413`、`codex-0153-terra-medium`、`openai/gpt-5.6-terra`、medium，最多一次模型尝试且失败不重试，使用当前额度但不使用重置，并精确清理第二次专属 PG/MinIO/HTTP/Web/Docker 资源。运行前额度为 34% 已用、66% 剩余，重置额度 1 个未使用；新作用域仍无 `evidence/`，可开始唯一一次 `run`。
- 第二次且最后一次真实 Run 已实际执行；观察包装器在进程启动后因方法名拼写错误提前结束观察，但没有重启或追加模型尝试，而是只读定位既有 PID 并等其自然终止。安全摘要为 `status=failed`、`phase=verification`、`cleanup=verified`；平台 Job `fe36949b-3a52-4e73-9d45-e09e9514a2a3` 与 Run `0481becd-3181-49e6-8d1e-fddcdf22a74b` 均为 `COMPLETED` 且无失败码，说明真实 Harbor、证据发布与固定 Fork 主流程完成，失败发生在后置验收方法，浏览器步骤因此未执行。该 scope 的唯一模型尝试已经用尽，不得重跑。
- 只读取公开确定性证据和私有目录的文件名/安全字段：submitted/resolved/error 计数为 `1/1/0`，patch 存在且应用成功、`resolved=true`，三处 patch 哈希一致，正文为 1225 字节；没有展示认证或 Harbor/Codex 原始正文。Job 目录和唯一 Trial 目录各有一份 `config.json`，后者由当前验收器误作 Job 配置检查；同一离线最小命令连续两次稳定得到 `HARBOR_FIXED_CONFIG_MISMATCH`，无需网络、数据库或模型，已形成后续红绿反馈环。
- 当前诊断按四个可证伪假设展开：验证器选错 Job/Trial 层级；检查了锁定 Harbor 版本不存在或默认省略的字段；生产映射漏传单次/零重试；实际存在额外 Trial。下一步先用固定 Harbor `JobConfig` / `TrialConfig` 与源配置离线判定，再仅修错误所在层；在事实确认前不改生产执行链。
- 固定 Harbor 源码与其项目虚拟环境已离线给出反证：Adapter 保留的 `harbor-config.json` 经 `JobConfig` 解析为 Job 名匹配、`n_attempts=1`、`retry.max_retries=0`、1 Agent/1 Task；Harbor 自身保存 Job 配置时使用 `model_dump_json(..., exclude_defaults=True)`，所以等于默认值的 attempts/retry 字段按设计不落盘，但重新解析仍恢复为 `1/0`；唯一 Trial 配置经 `TrialConfig` 解析成功且按模型定义没有 Job 级字段。故生产映射遗漏与额外尝试假设被排除，根因是验收器把 Trial 层配置当作 Job 层配置，并误把默认省略理解为缺失。
- 修复 seam 固定为忽略态编排器的公开 `verify_harbor_evidence(run_root, job_id)` Interface：用合成目录先证明“源 Job 配置明确 1/0、Harbor 落盘 Job 省略默认字段、唯一 Trial 不含 Job 字段”应通过，再实现最小分层核验。只改 `m1-task13-20260913-02/platform_verify.py` 与同作用域测试；不回写 `-01`、不改生产 Worker/Harbor Adapter/数据库/M0 seam，也不调用模型。
- 上述行为测试先在收集期以 `ImportError: cannot import name 'verify_harbor_evidence'` 得到红灯。既有 `platform_verify.py` 已为 200 行，为遵守动态源码指标，不压行或把新职责塞入同文件；实际文件树增加同层 `platform_harbor.py` 承载该深 Module，`platform_verify.py` 只调用其 Interface，根目录文件总数由 7 增至 8，仍不超过目录指标。
- 最小 Implementation 已按三层证据分责：Adapter 留下的源 Job 配置必须明确 `n_attempts=1`、`n_concurrent_trials=1`、`retry.max_retries=0`、关闭 Harbor verifier 且各 1 Agent/Task；Harbor 落盘 Job 允许按固定版本省略默认 attempts/retry，但身份与 Agent/Task 必须和源配置一致；Trial 只校验唯一性及自身 agent/task 结构。合成回归由红转为 `5 passed in 0.62s`，同一第二次真实证据的原始离线复现由 `HARBOR_FIXED_CONFIG_MISMATCH` 转为 `PASS`，没有读取或输出私有正文。
- 第二次作用域定向 ruff check、10 文件 format check 和显式源码/测试 compileall 均以退出码 0 通过；`platform_harbor.py` 70 行、`platform_verify.py` 降为 185 行，作用域根目录共 8 个文件。直接递归扫描整作用域时因私有 0700 证据目录得到拒绝访问提示，故静态检查明确限定到源码、`runtime_parts` 和测试，未把该提示误报为检查失败或改动证据权限。
- 运行结束后的独立 Docker 标签查询再次确认 `agentexam.task13=m1-task13-20260913-02` 下容器与网络均为空；与运行摘要中的四端口关闭检查共同支持 `cleanup=verified`。浏览器脚本未执行仍是明确缺口：验证器在其前一步退出且临时 PostgreSQL/MinIO 已按批准范围销毁，不能事后伪造为同一真实 Job 的页面验证。
- 本次安全摘要按设计只保存异常类型 `RuntimeError`，没有保存异常消息；因此不能仅凭摘要证明运行当时恰好停在配置断言。但离线复现证明旧断言对本次真实 Trial 必然失败，修复后同一证据通过，且 Job/Run/固定 Fork/patch 一致性没有出现其他失败信号；行动将其记录为已证实的后置验收阻断点，同时保留“未重跑完整 verify、HTTP 临时存储已清理”的证据限制。
- 修复后的默认后端回归为 `381 passed, 77 skipped, 2 warnings in 42.64s`；77 项仍是未设置专属 PG/MinIO、Docker/Fork/网络/真实 Codex 开关的外部门禁。生产源码/测试 ruff、280 文件 format check、compileall、strict mypy（162 个源文件）均通过。Web `typecheck` 通过；首次普通 `next build` 因用户级 Next.js 配置目录 `EPERM` 失败，改用仅该命令生效的工作区 APPDATA/LOCALAPPDATA 后，缓存目录创建仍被拒绝但构建本身以退出码 0 完成编译、类型检查、4 个静态页面和 trace；未改机器设置，也未把缓存创建描述为成功。浏览器仍未运行。
- 修复后的任务 13 最终双轴评审暂未通过：Spec 发现 1 项 P1（Trial 固定身份及完整安全配置核对不足）与 1 项 P2（最新三次运行授权未同步）；Standards 同样给出安全配置 P1、行动/架构文件树与授权状态两项 P2，以及目录枚举裸 `OSError` 的 P3 判断项。下一红绿切片只深化忽略态 `verify_harbor_evidence`：对照源 Job 核对落盘 Job 的非默认并发/Verifier/环境及 Trial 的固定 Agent/Task 身份，补错误身份和目录读取失败负例；同步文件树/授权后再复审，不因此使用模型额度。
- 身份切片先让错误 Trial Agent 得到“未抛错”红灯，再要求 Trial agent/task 精确等于源 Job 唯一项后转绿；安全配置切片把落盘 Job 并发改为 4 后同样先得到“未抛错”红灯，再补齐固定 Codex 全配置、`n_concurrent_trials=1`、Verifier disabled、受控网络与 CPU/内存/存储，以及危险环境扩展为空的源/Job/Trial 分层核对后转绿。测试增长到 239 行时立即按职责拆出 `test_harbor_evidence.py`，不以压行规避 200 行指标。
- P3 错误归一负例先让 `Path.iterdir()` 的合成 `PermissionError` 原样逸出，再把 Job/Trial 目录枚举的 `OSError` 统一映射为 `HARBOR_CONFIG_UNAVAILABLE` 后转绿。新 Harbor 证据测试 `2 passed`，全部忽略态编排器测试 `6 passed in 0.76s`；增强后的固定身份/安全验证器对同一第二次真实证据再次离线得到 `PASS`。显式源码范围 ruff、11 文件 format check、compileall 均通过；全部动态源码/测试最大 185 行，作用域根目录仍为 8 文件。递归计数首次仍因私有证据 ACL 退出 1，改为显式根源码、`runtime_parts`、`tests` 范围后退出 0；未修改证据权限。
- 原评审者第一次针对性复审关闭目录错误、文件树和大部分身份/安全项，但 Spec 继续发现源 Task 只验数量、GPU/TPU override 未纳入完整配置；两轴还共同指出 HANDOFF 顶部“最后一次”与新增授权冲突。任务路径负例把三层 task 一致改成错误目录后先得到“未抛错”红灯，随后把固定渲染身份收紧为本 scope 的 `tasks/python--mypy-15413` 真实目录；首次误按领域 ID 拼写 `python__mypy-15413` 使真实离线复验红灯，回读既有 `render_harbor_task` 源码确认双下划线按设计转双连字符后修正，同一证据恢复 `PASS`。加速器负例令源/Job/Trial 同时增加 `override_gpus=1`，先得到“未抛错”红灯，再把 GPU/TPU 默认空值纳入三层归一后转绿；HANDOFF 顶部已同步新增授权。
- 上述补强后 Harbor 证据测试 `3 passed`、全部忽略态编排器测试 `7 passed in 0.75s`；ruff、11 文件 format check、compileall 均退出 0，同一第二次真实证据的完整配置离线复验为 `PASS`。全部源码/测试最大 197 行，scope 根目录 8 文件、测试目录 2 文件，仍满足指标。下一步由原 Standards/Spec 评审者再次复核剩余 finding；通过前不消耗新增真实运行授权。
- 原评审者第二次针对性复审确认此前身份、安全配置、授权和文档树问题均已关闭，但两轴共同发现固定任务目录在 `.resolve()` 后才检查符号链接，链接入口会被解析掉；Standards 另指出一个测试名误称同时覆盖加速器。测试名已改为只描述错误任务，新增路径负例用受控 `Path` 行为模拟链接入口与目标目录：旧实现先解析后检查，得到“未抛错”红灯。
- 最小修复保留未解析的固定任务入口，先拒绝 `tasks` 根或任务入口链接，再以 `strict=True` 解析，并要求最终任务目录的直接父目录等于本次解析后的 `tasks` 根；路径访问错误仍归一为 `HARBOR_CONFIG_UNAVAILABLE`。负例转绿，全部忽略态测试为 `8 passed in 0.86s`，ruff、12 文件 format check、compileall 均通过；最大文件 197 行、scope 根目录 8 文件、测试目录 3 文件。对第二次真实私有证据的只读离线复验再次仅输出 `PASS`，未输出认证或原始模型内容。下一步由原评审者确认最后 finding 关闭，再创建全新隔离 scope 使用追加授权的第 1 次完整运行。
- Spec 最后针对性复审为 0 findings/PASS；Standards 确认全部行为 finding 关闭，但留下 1 项 P3 测试可维护性问题：路径测试从另一个测试模块导入私有 `_layout`，并用动态 `__import__` 写配置。重构把它提取为明确命名的 `harbor_evidence_fixture.write_harbor_layout`，两组测试正常导入 `json` 和共享 fixture，不改变产品或验收器行为。首次提取因返回字典把 `saved` 误命名为 `job` 出现 `3 failed, 5 passed`，修正共享返回键后为 `8 passed in 0.79s`；ruff、13 文件 format check、compileall 均通过，最大文件降为 185 行、测试目录 4 文件。待 Standards/Spec 对这一最终测试重构复核清零。
- 测试重构后的最终 Standards 与 Spec 均为 `0 findings / PASS`：共享 fixture 命名/依赖清晰，链接拒绝、固定路径范围、三层身份/安全配置、错误归一以及授权/文档状态均未回归。代码评审门禁已关闭；下一步新建 `m1-task13-20260914-03`，只复制 `-02` 的源码/测试并替换专属 scope，先用零模型 preflight 验证隔离与清理，再使用追加授权第 1 次运行完整 verify+browser。
- 新作用域实际复制 14 个源码/测试文件，归一 `-03` scope 后与 `-02` 为 `unexpected_differences=0`，且无 `evidence`、安全摘要或 `__pycache__`；测试 `8 passed`、ruff、13 文件 format check、compileall 全部通过。首次零模型 preflight 在 `phase=storage` 以 `IdentityUnavailable` 失败并 `cleanup=verified`，独立标签查询确认专属容器/网络为空；未创建 Job、未读取认证、未调用模型，不计入三次真实运行。
- 同一清空作用域的第二次零模型 preflight 完整通过：`storage/http=ready`、`jobs_created=0`、`model_called=false`、`auth_read=false`、`cleanup=verified`。现象指向启动时序：当前只以容器内 `pg_isready` 放行，不能证明 Docker Desktop 的 Windows 主机端口转发已经可由业务 DSN 建连。下一 TDD 切片在 `start_storage` 既有 Implementation 内增加同一 DSN 的主机侧 `SELECT 1` 就绪门禁；用“内部已就绪、主机首连失败、随后成功”的合成行为测试先取得红灯，再最小修复，不改变产品模块、数据库或真实运行范围。
- 主机侧就绪负例先因 `start_storage` 不接受连接探针而以 `TypeError` 红灯；最小实现保留容器内 `pg_isready`，并在其通过后再用本次随机 DSN 从主机执行 `SELECT 1`，`psycopg.Error` 只在既有 30 秒门禁内继续等待。单测转绿，全部忽略态测试 `9 passed in 0.90s`，ruff、14 文件 format check、compileall 均通过。修复后的零模型 preflight 为 `storage/http=ready`、零 Job/认证/模型调用、`cleanup=verified`；独立标签查询确认专属容器和网络为空。真实运行仍未开始，先让原 Standards/Spec 评审者针对 `-03` 唯一差异复核。
- `-03` 针对性复审共同指出上述实现仍以 60 次循环叠加单次 3 秒连接，持续失败时理论上约 210 秒，行动中的“30 秒门禁”属于过度陈述；Standards 同时要求把 `-03` 实际状态同步到任务单与 HANDOFF。受控时钟负例让持续 `OperationalError` 的旧实现以 `clock=210.0 > 30.5` 红灯；实现改为 `time.monotonic()` 绝对截止时间，容器内探针、主机连接及间隔休眠均只使用剩余预算，最终统一收束为 `POSTGRES_NOT_READY`。定向测试 `2 passed`，全套忽略态测试 `10 passed in 0.79s`，ruff、14 文件 format check、compileall 均通过；修复后零模型 preflight 再次通过且 `cleanup=verified`。当前同步 issue/HANDOFF 后由两轴复核，不提前启动真实 Run。
- 第一次截止时间复核继续发现尾段：`ceil(remaining)` 在不足 1 秒时仍会请求 1 秒连接。先改为不足 1 秒直接结束、其余向下取整，并让容器探针推进受控时钟；随后 Standards 对照 libpq 契约发现 `connect_timeout=1` 实际按最少 2 秒处理。测试据此模拟最小 2 秒语义，使中间实现稳定红灯 `clock=30.9 > 30`；最终实现对剩余不足 2 秒直接结束，连接超时只取 2–3 秒且不超过剩余整秒。定向 `2 passed`、全套 `10 passed in 0.81s`、ruff/format check 通过，最终零模型 preflight 再次 `status=passed`、零 Job/认证/模型调用并 `cleanup=verified`。等待两轴确认该精确边界清零。
- `-03` 最终针对性复核为 Standards `0 findings/PASS`、Spec `0 findings/PASS`：30 秒绝对截止、libpq 最少 2 秒语义、持续失败测试、文档同步、秘密/范围边界均确认无遗留 finding。当前可使用追加授权第 1 次启动完整真实流程；仍固定一次模型尝试、零重试，原始 auth/Harbor/Codex 材料不公开，退出先精确清理，失败不自动发起下一次。
- 追加授权第 1 次真实全流程已在 `m1-task13-20260914-03` 执行且没有重试：HTTP 创建并经唯一所有者批准 Job `f5f3f496-a6eb-454e-805b-2abf67cf5271`，Run 为 `08c11b75-7297-4d79-be9d-3ad8f54f3395`。平台 Job/Run 均 `COMPLETED` 且无失败码，固定 Fork `resolved=true`，patch SHA-256 为 `7966138cd342861fff4d61063a8cd3cbb76fb66ac33751715555be8f4320516c`；数据库计数 `1/1/0`、唯一 Harbor Trial、唯一排行来源、Judge/人工/决胜兼容空值和安全制品下载核对均通过。最终摘要为 `status=failed/phase=browser/error_type=CalledProcessError/cleanup=verified`；独立 Docker 标签查询为空，不能把核心链路成功冒充完整页面验收通过。
- 浏览器失败按可证伪假设诊断：平台/判卷失败被上述 `COMPLETED/resolved=true` 反证；Web 未启动被 Next `Ready`、根页面 200 且 stderr 为空反证；截图或后续断言仍可能另有问题，但脚本在此之前存在一个必然阻断点——它要求“评测批次详情”包含旧文字“状态：全部完成”，当前 `JobDetails` 对 `COMPLETED` 的实际可访问标题是“执行完成”，既有真实浏览器规格也以该标题为契约。安全摘要没有保存 Node stderr，故只把它记录为源码确认的必然阻断点，不冒称已从本次 stderr 精确定位行号。下一切片只更新忽略态浏览器验收断言，先用现有合成浏览器流程验证当前 UI 契约，再经双轴复核决定是否使用剩余授权；不改产品页面/API/执行链。
- 浏览器合成复现补齐了直接原因：不设置浏览器缓存时，`job-batch.spec.ts` 在 `browserType.launch` 以“Chromium 1243 可执行文件不存在”失败，和真实流程同样尚未进入页面断言；这使缺失的进程级 `PLAYWRIGHT_BROWSERS_PATH` 成为本次最早、可复现的直接阻断。项目已有并已在依赖文档固定的 `runtime/tools/playwright/chromium_headless_shell-1243` 实际存在；只对合成测试进程绑定该缓存后，同一真实 Next→合成 FastAPI 流程 `1 passed (13.9s)`，未下载或改机器。旧完成态文案仍是浏览器启动后必然阻断，已改为在详情内核对可访问标题“执行完成”，`node --check` 通过。
- 为避免下一次在模型完成后才发现浏览器依赖缺失，下一红绿切片深化现有一次性 `AcceptanceRuntime`：在启动临时存储和创建 Job 之前，核对固定项目浏览器缓存的预期 1243 普通文件，并只给本次 Web/Node 子进程设置 `PLAYWRIGHT_BROWSERS_PATH`；缺失时以稳定错误安全失败。该门禁不安装/下载浏览器，不改长期配置，不读取 auth，也不触碰产品模块。
- 固定浏览器门禁测试先因 `AcceptanceRuntime.require_browser_runtime` 不存在而 `AttributeError` 红灯；最小实现拒绝缺失或链接缓存路径，严格解析后要求预期 `chromium_headless_shell-1243/.../chrome-headless-shell.exe` 是固定缓存内普通文件，并只写入本次 runtime environment。`platform_acceptance` 在 `start_storage` 前调用门禁，故缺失不会创建 Job 或触发模型。定向测试转绿；全部忽略态测试 `11 passed in 0.89s`，ruff、15 文件 format check、compileall、Node 语法和文件/目录指标通过；零模型 preflight 再次为 `status=passed`、零 Job/认证/模型调用并清理。
- 上述 preflight 按既有实现覆盖了根目录 `safe-summary.json`，使其现在表示“修复后 preflight”，不是先前真实失败；真实运行 JSON 已从本轮命令实际捕获的原样安全输出逐字段保存为 `real-run-safe-summary.json`，不含认证或原始模型正文。行动同时保留这一证据演进，后续不得把两份摘要混读。下一步先做浏览器缓存/文案修复的双轴复核，清零后才考虑使用新增授权第 2 次。
- 浏览器修复首轮 Spec 复核指出文档声称链接缓存失败关闭、但测试只覆盖缺失；同时要求把本次 verify 已独立完成的任务验收项与 HANDOFF 当前表同步。Standards 进一步发现实现未检查 Windows junction、未把解析后缓存锚定到解析后项目根，并指出 `-03` 根层的 7 个源码加 4 个运行文件已达 11，未来截图会继续超出每层 8 文件指标。
- 两个安全负例分别用受控 `Path.is_junction` 和解析到项目外的 cache/executable 模拟旧实现，均先得到 `DID NOT RAISE` 红灯。最小修复从解析后的项目根锚定精确 `runtime/tools/playwright`，逐级拒绝 runtime/tools/cache/version/platform/executable 的 symlink 或 junction，并要求解析后的可执行文件仍是固定 1243 路径；三项定向测试转绿。安全摘要、Web 日志和未来截图统一归入 `results/`，既有 4 个运行文件已精确移动，源码引用同步更新；最终根文件 7、results 4、tests 6，最大动态文件 185 行。
- 此轮全部忽略态测试 `13 passed in 0.81s`，ruff、15 文件 format check、compileall、Node 语法通过；路径/输出修复后的零模型 preflight 再次 `status=passed`、零 Job/认证/模型调用且 `cleanup=verified`。下一步同步任务单/HANDOFF 的已完成独立验收项，再由两轴复核；未把真实页面记为通过，也不自动使用第 2 次。
- 状态同步后浏览器修复的最终 Standards 与 Spec 均为 `0 findings/PASS`：项目根锚定、symlink/junction 拒绝、目录 `7/4/6/3`、测试计数、任务单第 4–7 项与页面/最终提交未完成边界均已确认。当前新建 `m1-task13-20260914-04`，只复制 `-03` 的源码/测试并替换专属 scope；通过等价对账、13 项测试和零模型 preflight 后，才使用新增授权第 2 次完整流程。
- `m1-task13-20260914-04` 已实际从 `-03` 精确复制 16 个源码/测试文件；把 scope 归一回 `-03` 后 `unexpected_differences=0`，且运行前无 `evidence/`、`results/`、摘要或缓存。忽略态测试 `13 passed in 0.83s`，ruff、15 文件 format check、compileall、Node 语法及文件/目录指标均通过；零模型 preflight 为 `status=passed`、`storage/http=ready`、`jobs_created=0`、`model_called=false`、`auth_read=false`、`cleanup=verified`，随后独立标签查询确认专属容器、网络和卷为空。下一步使用新增授权第 2 次执行一次且不重试的完整真实流程；若失败先保存安全结果并诊断，不自动消耗第 3 次。
- `-04` 的完整真实运行命令在操作系统进程创建前被安全审批器拒绝：虽然用户已允许使用全量 auth 最多运行三次，但审批器要求用户在被告知风险后，进一步明确同意把固定验收题目和运行请求经 `auth.openai.com` / `chatgpt.com` 发送给 `openai/gpt-5.6-terra`。本次没有启动编排器、容器或网络连接，没有读取 auth、创建 Job、调用模型，也不计入最多三次中的次数；拒绝后独立 Docker 标签查询确认专属容器、网络和卷仍为空。不得绕过或换入口重试；取得这一具体数据到具体目的地的明确同意前，任务 13 保持 `in-progress`，按既定顺序也不提前开始任务 14。
- 用户现已在上述风险说明后逐字明确同意：把固定验收题目和运行请求经 `auth.openai.com` / `chatgpt.com` 发送给 `openai/gpt-5.6-terra`，并使用既有私有 auth 执行任务 13 的隔离真实运行。该具体授权解除 `-04` 的安全审批前置条件；次数与其他边界不变，运行前仍须确认无旧 evidence/专属资源，运行中仅一次模型尝试、零自动重试，退出先清理。
- `-04` 完整真实流程实际以一次模型尝试、零重试通过：Job `82c06c39-567d-4456-a8a1-b6d35898d53f`、Run `7b97e96c-0c3f-4057-991e-e8fbde0a9d58` 均为 `COMPLETED` 且无失败码，固定 Fork `resolved=true`，patch SHA-256 为 `d5fefec345eb335c9b17d6305037ef47214c56d265f1ca11175c88c90d3ad09d`。数据库计数为 Job/Run/`internal_test` Job `1/1/0`，唯一 Harbor Trial、唯一排行榜来源、Judge 分析 0、人工复核/质量决胜为空；最终摘要为 `status=passed/phase=complete/cleanup=verified`。
- 本次真实浏览器已从登录与 Job 详情走到完成报告，并生成 `results/browser-report.png`；该普通文件为 395582 字节，SHA-256 为 `1d1f118a67bdfe947b0f303503e76629b4a658d6517cefc047c7358de711c30e`。运行后独立按 `agentexam.task13=m1-task13-20260914-04` 查询容器、网络和卷均为空；没有输出 auth 或私有 Harbor/Codex 正文。当前只剩相对 `5e39632` 的最终 Standards/Spec 评审、公开任务文档提交和状态关闭，不需要消耗剩余真实运行次数。
- 最终 Standards 首轮复核发现两项文档 P2：行动文件树仍是 `-04` 创建前快照，五份权威文档的更新时间仍为 2026-09-13。已把 `-04` 的私有 evidence/安全 results 分层补入实际文件树，并把架构、数据模型、模块契约、Harbor 与 HTTP 文档同步到 2026-09-14；不涉及产品代码或运行行为。等待原评审者复核关闭。
- 最终 Spec 首轮复核另发现一项 P2：行动把 `database_counts` 的第三项误写为失败事件；源码 SQL 实际统计 `internal_test` Job。现已准确记录为 Job/Run/`internal_test` Job `1/1/0`。针对性复核最终为 Standards `0 findings/PASS`、Spec `0 findings/PASS`，确认实际文件树、五份权威文档日期、计数语义和九项范围均一致。
- 任务 13 收尾只提交本行动与任务 13 任务单两份公开文档；私有 `evidence/`、浏览器截图/日志、auth、混合全局文档和旧缓存均不暂存、不推送。真实闭环及适用门槛已满足，任务状态改为 Completed；任务 14 的私有远程验收仍是独立下一项，不据此宣称 M1/MVP 已完成。
