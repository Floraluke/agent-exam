# M1 任务 12：制品限额与到期清理

## 状态与情况说明

已完成。来源为 M1 规格任务 `12-artifact-retention.md`；用户已批准最小方案：深化既有 Artifact Store、Job Repository、Reporting 和本机 Job 维护入口，只补 `artifact_records` 已规划的保留/截断/删除审计字段，不新增业务表、顶层 Module、定时器或普通 HTTP 删除入口。测试只使用专属合成对象和临时 PostgreSQL/MinIO，不清理既有真实证据、用户服务数据或目录。

已确认阈值保持不变：patch 256 KiB 警告、1 MiB 拒绝且绝不截断；单个原始制品 50 MiB；单 Run 原始制品合计 200 MiB；`raw_30d` 创建 30 天后才可清理。核心配置快照、确定性结果、最终 patch 和公开测试摘要长期保留。清理仅接受可信 owner 身份，并使用固定原因逐对象处理。终审发现“任意对象缺失”不能证明上次删除成功，因此实现已收紧为数据库持久意图 → 精确对象核验 → 意图确认 → 删除 → 最终审计；只有已确认意图能在重试时根据对象缺失补记审计，未确认意图的意外缺失持续显式失败。

实现不修改 M0 `ExecutionBackend` 或 `PatchEvaluator` Interface，不运行真实模型/Harbor，不注册删除路由，不部署长期服务，不 pull/reset/push。当前混合旧文档、未跟踪阅读资料、缓存与 framework/runtime 均保持原状。

## 实施措施

1. 以既有 Artifact Store Interface 为接缝增加有界核验读取和精确删除；原始正文按固定头尾策略生成不超过 50 MiB、含可见标记的保留版本，哈希和大小只描述实际保留正文。
2. 在既有执行证据发布中持久化受控原始引用，固定 `raw_30d` 元数据，并在单 Run 200 MiB 上限处返回可查询的显式拒绝警告；核心长保留证据不受原始制品限额影响。
3. 在既有 `artifact_records` 增加文件名、原始大小、到期与删除审计列及约束；深化 Job Repository 的到期候选/审计写入 Interface，不新增表。
4. 在既有 Job 生命周期内实现 owner-only 本机维护；复用本机交互认证和 `agentexam-jobs` 入口，禁止密码管道、定时触发与普通 HTTP 删除。
5. 深化 Reporting/HTTP/Web：允许授权用户查询受控原始制品的安全元数据，区分正文完整、未就绪、已删除、缺失；已删除正文返回 410，页面不为受限制原始正文提供下载。
6. 每个竖切片执行红灯→最小实现→绿灯；随后运行完整后端、静态检查、Web 类型/构建、浏览器和专属真实存储验证，精确清理临时资源。
7. 以任务 11 关闭提交 `69620b2` 为实现起点提交任务 12；完成后按 code-review 分别做 Standards/Spec 评审，修复、复验、同步权威文档与任务单，再本地提交，不推送。

完成标准是任务单八项验收均有本轮真实证据，数据库/对象单侧失败可恢复，现有报告与排行榜回归不退化，且文档、Schema、Interface 和页面反映同一状态。

## 受影响文件树

```text
apps/backend/src/eval_platform/
├─ domain/artifacts.py                      # 闭合制品类型、MIME、文件名及公开/原始分类词汇
├─ domain/result.py                         # 扩展 ArtifactRef 的原始大小、到期和删除审计不变量
├─ application/ports/artifacts.py           # 深化有界读取与精确删除 Interface
├─ application/ports/repositories.py        # 深化 Job Repository 的到期候选/删除审计 Interface
├─ application/execution/evidence.py        # 现有证据发布 Implementation：原始制品限额和保留
├─ application/execution/raw_evidence.py    # 内部原始制品身份、配额与 30 天保留策略
├─ application/execution/completion.py      # 把原始制品及显式限额警告装配进原子 Run 结果
├─ application/job_lifecycle/retention.py   # 现有生命周期子目录：编排 owner-only 跨存储清理
├─ adapters/artifacts/
│  ├─ bounded.py                            # 共享固定头尾截断算法
│  ├─ local.py                              # 本地来源有界流式核验 Adapter
│  ├─ policy.py                             # MinIO 接受的闭合类型/路径/大小/保留策略
│  └─ minio.py                              # MinIO 不可变写读与精确对象删除 Adapter
├─ adapters/persistence/catalog/
│  ├─ schema.sql                            # artifact_records 已规划列、类型和约束
│  └─ tasks.py                              # 任务快照长保留元数据写读
├─ adapters/persistence/jobs/
│  ├─ execution/results.py                  # Run 制品完整元数据原子入库
│  ├─ execution/reports.py                  # 删除/截断审计读取
│  ├─ retention/__init__.py                 # 到期维护 SQL 子目录导出
│  ├─ retention/records.py                  # 精确候选和幂等审计 Implementation
│  ├─ retention/repository.py               # 本 Module 的短事务 Repository facade
│  ├─ retention/state.py                    # 持久意图、对象确认与最终审计行校验
│  ├─ reporting/listings.py                 # 拆出的稳定 Job 列表查询，保持 Repository 文件规模
│  └─ repository.py                         # 既有 Postgres Job Repository 转发
├─ delivery/jobs.py                         # 既有本机交互维护入口增加制品清理子命令
└─ delivery/http/routes/artifact_schemas.py # 报告/索引共用的安全元数据和状态响应
apps/backend/tests/jobs/artifacts/
├─ cleanup_support.py                        # 清理测试共用身份、时间和内存双写夹具
├─ test_cleanup.py                           # 过期、长期保留、幂等及单侧失败恢复
├─ test_cleanup_cli.py                       # owner-only 交互式本机 CLI 边界
├─ test_http_limits.py                       # HTTP 层单 Run 总额与超大轨迹降级
├─ test_http_status.py                       # 200/409/404/410 和安全元数据
├─ test_limits.py                            # 50/200 MiB、截断、哈希和 patch 独立阈值
├─ test_policy_metadata.py                   # ArtifactRef 保留/删除领域不变量
└─ test_postgres_minio.py                    # 专属真实 PG/MinIO 删除与恢复
apps/backend/tests/jobs/conftest.py           # 向任务 12 子目录复用既有门控 MinIO 夹具
apps/backend/tests/identity/browser_server.py # 仅显式门控的浏览器清理测试装配
apps/web/src/                                # 同步类型、解析和删除/受限状态页面
apps/web/src/lib/reporting/artifact-shape.ts  # 失败关闭的制品保留/审计状态解析
apps/web/tests/artifact-retention/           # 少量浏览器删除状态验收
.scratch/m1-platform/issues/12-artifact-retention.md # 八项验收与证据回填
docs/architecture/ARCHITECTURE.md            # 当前文件树、模块边界、数据流和风险
docs/architecture/DATA_MODEL.md              # 实际列、约束、保留与一致性规则
docs/architecture/MODULE_CONTRACTS.md        # Artifact Store/Reporting 实际 Interface
docs/interfaces/HTTP_API.md                  # 元数据、410 与无删除入口契约
HANDOFF.md                                   # 当前任务/提交/验收状态
docs/actions/2026-09-13-m1-artifact-retention.md # 本行动的持续记录
```

设计关系：Artifact Store 是深 Module；`ArtifactReader`/`ArtifactStore` 是 Interface，Local/MinIO/内存实现是各 Adapter。Job Repository 仍是数据库事务 Interface，PostgreSQL/内存实现负责精确候选和审计。`ArtifactRetention` 位于既有 Job 生命周期包，编排对象删除与数据库审计而不伪造跨系统原子事务；HTTP Delivery 只读，清理入口只在本机 CLI。

## 自验证方式

- TDD 定向：50 MiB 恰好、超 1 字节头尾截断、实际大小/哈希/标记、200 MiB 恰好与越界拒绝、patch 边界隔离；预期逐项先失败再通过。
- 应用/HTTP：通过既有 Job 执行与 Reporting Interface 检查安全元数据、显式限额警告、200/409/404/410 和越权；OpenAPI 不出现删除路由或对象键。
- 本机维护：owner 交互认证、非 owner/管道输入拒绝、未到期和 `long_term` 保留、精确到期对象、重复调用幂等、对象失败不写审计、数据库失败后重试补审计。
- 真实存储：使用专属临时 PostgreSQL/MinIO 对象验证删除审计、重复维护和两类单侧失败恢复；只按本轮生成的精确身份清理。
- 页面：浏览器完成合成 Job，执行门控测试维护后显示受限/已删除而不提供原始下载；完整公开正文仍可下载。
- 回归：后端全量 pytest、Ruff check/format、strict mypy、Web typecheck/build、完整浏览器套件、`git diff --check`、文件/目录指标与秘密扫描。

成功标准：所有命令实际返回成功；失败、跳过和外部限制逐项记录，不用历史证据冒充本轮运行。

## 自验证情况

已完成，最终结果如下（均为本轮实际运行，不复用任务 03 的历史证据）：

- 限额切片首次运行得到 `3 failed`，缺口是证据发布尚无时钟和原始制品发布；实现后边界组 `3 passed`，增加本地大文件流式读取后为 `4 passed`，补全受限文本日志与领域元数据检查后当前为 `6 passed`。已覆盖单文件恰好 50 MiB、越界头尾截断、标记/实际大小/SHA-256 一致，以及单 Run 恰好 200 MiB 后拒绝下一对象。
- 领域保留元数据不变量的新增用例先得到 `1 failed`，确认内存路径能接受带目录文件名、非正到期时间或提前删除审计；补齐 `ArtifactRef` 失败关闭校验后为 `1 passed`。
- HTTP 原始元数据切片先因类型未纳入报告而失败，实现后 `1 passed`；随后单独验证 200 MiB 超限仍保留核心结果，结果 `1 passed, 2 warnings in 1.72s`，运行返回 `RAW_ARTIFACT_RUN_LIMIT_EXCEEDED`，确定性结果仍为真。
- 清理切片先因应用模块不存在而失败；对象/数据库单侧失败恢复和越权用例实现后 `3 passed`，补充非交互密码管道拒绝后为 `4 passed`。
- 第一轮专属真实 PostgreSQL/MinIO 为 `12 failed, 110 passed, 1 error`，确认旧 Schema 与新元数据契约尚未接通；补 Schema/Store 后为 `6 failed, 117 passed`；修正旧断言后为 `123 passed, 2 warnings in 44.65s`，每轮均精确清理本轮临时容器、库和对象。加入两类单侧失败与边界断言后的首轮为 `2 failed, 127 passed`：子进程缺少显式 `PYTHONPATH`，报告链接遗漏 `created_at`。修正产品字段和测试可移植性后复验为 `129 passed, 2 warnings in 51.06s`；三个随机标签容器均无发布端口/宿主挂载，并在结束后精确清理。
- 当前相关后端定向组最近一次为 `13 passed, 1 skipped`；跳过项是无真实临时存储环境时的集成标记，不算通过。任务 12 实现里程碑已提交为 `f55f546`，只包含本任务代码、测试、Web 和本行动文档，未推送或混入既有脏文件。
- Web 类型检查已通过。新增删除状态浏览器用例首次暴露页面未刷新，修复后为 `1 passed in 11.2s`；补充逐对象哈希、大小、创建/删除时间、清理者和原因展示后定向复验为 `1 passed in 10.2s`，仍不出现原始下载。
- `git diff --check` 当前无补丁空白错误，只有既有 Windows 行尾提示。Ruff 首轮审计报告 15 项导入顺序/行宽/测试夹具名问题；同时发现 4 个本轮扩展后的源文件越过 200 物理行指标，当时未记为通过，处理结果见下一条。
- 拆出内部 raw policy、MinIO identity policy、Job listing query、共享 HTTP 制品 DTO 和 Web 制品解析后，当前受影响动态源文件均不超过 200 行、受影响目录均不超过 8 个直属文件。全仓 Ruff check 与 271 文件 format-check 通过；strict mypy 为 `Success: no issues found in 156 source files`，compileall 通过。
- 默认完整后端为 `372 passed, 77 skipped, 2 warnings in 42.86s`。77 项均为显式真实 PG/MinIO、Docker、Fork、Harbor 或 Codex 门禁；任务 12 双存储项由前述专属 129 项套件实际覆盖，其余不冒称通过。
- Web typecheck 通过。Next 生产构建第一次在用户级配置临时文件处分别遇到 EPERM/EXDEV；设置官方无遥测/无更新检查环境后成功构建 4 个静态页面。中途完整浏览器套件曾因沙箱不能覆盖测试结果文件而未执行，改用系统 Chrome 后又在串行高负载下使既有中断恢复用例 5 秒超时，单独复跑为 `1 passed in 9.1s`，当时未冒称全量通过。最终在相同系统 Chrome 和显式合成门控下重新逐文件运行，任务 12、目录、身份、安全、批次、证据、取消、中断恢复、排行榜和成员管理共 `21 passed`；中断恢复本次为 `1 passed in 9.2s`，没有再超时。
- 已同步根领域词典中的原始制品/核心证据定义，并更新总架构当前增量树、跨存储清理边界和风险，数据模型的实际闭合类型/对象键/字段约束/到期索引，以及模块和 HTTP 的 Interface、元数据与 200/409/404/410 契约。文档继续明确区分 M1 临时 PG/MinIO 验证和尚未获准重跑的真实 Harbor 规模测量。
- 按 `code-review` 流程确认固定基准 `69620b2` 可解析且 `git diff 69620b2...HEAD` 非空；首次创建 Standards 子评审时工具返回 `agent thread limit reached`，当时无活动子代理。该限制尚未视为已完成评审，收尾前继续重试并如实记录结果。
- 随后双轴评审成功并行运行。Spec 首轮报告 3 项：P1 超大轨迹在原始截断前被完整读取并导致 Run 失败；P1 任意对象缺失都可能被补记为所有者删除；P2 410 的 OpenAPI/稳定错误码不一致。Standards 首轮报告同一错误码硬违规，并把后端/前端制品类型清单散布标为中等级判断项。新增测试先因缺少 `ArtifactDeletionIntent` 收集失败；实现持久意图和超大轨迹降级、统一 `ARTIFACT_CONTENT_DELETED` 并声明 OpenAPI 410、聚拢后端制品词汇及前端公开类型后，相关组为 `15 passed, 2 warnings in 3.45s`，Ruff 和 strict mypy 通过。
- 评审修复后的专属真实 PostgreSQL/MinIO 套件为 `132 passed, 2 warnings in 53.98s`；三个随机标签容器继续无宿主端口或挂载，并在结束后精确删除，镜像/构建缓存按既有授权保留。该轮覆盖持久意图、对象删除失败、最终审计失败后恢复和删除审计；未确认意图的意外缺失另由应用测试证明不会形成清理审计。
- 文档本地链接目标、Markdown 围栏、`git diff --check`、受影响源码/目录指标和任务差异秘密模式扫描均通过；未发现秘密值。一次在后端目录误运行 Web typecheck 只得到 `package.json` 不存在的 ENOENT，未作为产品失败或通过，并留下的 `%USERPROFILE%` 缓存按交接要求不清理。
- 修复后的最终完整后端为 `375 passed, 77 skipped, 2 warnings in 41.38s`；77 项仍是显式外部门禁，任务 12 的真实存储路径由前述 132 项专属套件覆盖。Ruff check、278 文件 format-check、compileall 均通过，strict mypy 为 `Success: no issues found in 160 source files`。
- Web typecheck 通过；Next 生产构建成功生成 4 个静态页面。第一次构建因沙箱内用户配置临时文件 EPERM、第二次沙箱外跨盘 rename EXDEV 未通过，改用仅对该进程生效的无遥测/隔离配置后成功，不更改机器设置。最终系统 Chrome 合成浏览器套件共 `21 passed`，其中任务 12 删除状态用例通过；测试结束后 3100/8875 无残留监听。
- 固定基准 `69620b2` 的 Spec 与 Standards 复核均为 PASS。Spec 确认超大轨迹降级、持久删除意图和统一 410 契约关闭首轮三项；Standards 确认稳定错误码、集中制品词汇及拆分后的文件/目录指标均关闭，未发现遗留问题。评审修复已精确提交为 `a6a7d72`，没有混入旧文档、缓存或用户增量。
- 任务单八项验收已逐项回填；权威架构、数据模型、模块契约、HTTP 契约和 HANDOFF 已同步为任务 12 验收完成。任务 13 需要单独批准真实模型/凭据/容器网络范围，本行动不自动进入。
