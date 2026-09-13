# M1 任务 13：本机真实平台验收

> 状态：实施中；用户已于 2026-09-13 批准本行动的最小真实验收范围。M0 第四场仅作历史基线，不计作本任务证据。

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
├─ src/eval_platform/delivery/worker/
│  ├─ main.py                         # 既有 Worker 外部 Interface；保持 run_once 语义
│  └─ runtime.py                      # 已实现：集中组合正式 PG/MinIO/Harbor/Fork 依赖
├─ tests/jobs/runtime/
│  └─ test_worker_runtime.py          # 通过组合入口验证显式绑定与安全失败
└─ pyproject.toml                     # 仅在需要稳定本机命令时注册既有 Worker 入口
docs/
├─ actions/2026-09-13-m1-local-real-acceptance.md  # 本行动及实际证据
├─ architecture/ARCHITECTURE.md                    # 当前模块边界、数据流与风险
├─ architecture/DATA_MODEL.md                      # 实际 Job/Run/证据身份核对
├─ architecture/MODULE_CONTRACTS.md                # Worker 组合 Interface 与依赖方向
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
