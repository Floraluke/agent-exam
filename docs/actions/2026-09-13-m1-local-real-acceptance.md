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
│  └─ runtime.py                      # 候选：集中组合正式 PG/MinIO/Harbor/Fork 依赖
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
```

文件树会随红绿循环收敛；若无需 `runtime.py` 或脚本注册将删除候选项。设计模式保持 Ports & Adapters：`ExecutionBackend` / `PatchEvaluator` 是既有 ports，Harbor / SWE-Bench 是 Adapters，Worker runtime 是 composition root；它只隐藏依赖组装，不形成第二条执行链。

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
