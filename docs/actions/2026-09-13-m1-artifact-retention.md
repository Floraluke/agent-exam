# M1 任务 12：制品限额与到期清理

## 状态与情况说明

实施中。来源为 M1 规格任务 `12-artifact-retention.md`；用户已批准最小方案：深化既有 Artifact Store、Job Repository、Reporting 和本机 Job 维护入口，只补 `artifact_records` 已规划的保留/截断/删除审计字段，不新增业务表、顶层 Module、定时器或普通 HTTP 删除入口。测试只使用专属合成对象和临时 PostgreSQL/MinIO，不清理既有真实证据、用户服务数据或目录。

已确认阈值保持不变：patch 256 KiB 警告、1 MiB 拒绝且绝不截断；单个原始制品 50 MiB；单 Run 原始制品合计 200 MiB；`raw_30d` 创建 30 天后才可清理。核心配置快照、确定性结果、最终 patch 和公开测试摘要长期保留。清理仅接受可信 owner 身份，并使用固定原因逐对象处理；对象先经身份/大小/哈希校验后删除，再写数据库审计。若对象已删但数据库审计曾失败，重复维护会补记审计；对象删除失败时数据库保持未删除，不能形成假删除状态。

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
│  ├─ reporting/listings.py                 # 拆出的稳定 Job 列表查询，保持 Repository 文件规模
│  └─ repository.py                         # 既有 Postgres Job Repository 转发
├─ delivery/jobs.py                         # 既有本机交互维护入口增加制品清理子命令
└─ delivery/http/routes/artifact_schemas.py # 报告/索引共用的安全元数据和状态响应
apps/backend/tests/jobs/artifacts/           # TDD：限额、HTTP、CLI、PG/MinIO 与故障恢复
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

实施中，当前结果如下（均为本轮实际运行，不复用任务 03 的历史证据）：

- 限额切片首次运行得到 `3 failed`，缺口是证据发布尚无时钟和原始制品发布；实现后边界组 `3 passed`，增加本地大文件流式读取后为 `4 passed`，补全受限文本日志与领域元数据检查后当前为 `6 passed`。已覆盖单文件恰好 50 MiB、越界头尾截断、标记/实际大小/SHA-256 一致，以及单 Run 恰好 200 MiB 后拒绝下一对象。
- 领域保留元数据不变量的新增用例先得到 `1 failed`，确认内存路径能接受带目录文件名、非正到期时间或提前删除审计；补齐 `ArtifactRef` 失败关闭校验后为 `1 passed`。
- HTTP 原始元数据切片先因类型未纳入报告而失败，实现后 `1 passed`；随后单独验证 200 MiB 超限仍保留核心结果，结果 `1 passed, 2 warnings in 1.72s`，运行返回 `RAW_ARTIFACT_RUN_LIMIT_EXCEEDED`，确定性结果仍为真。
- 清理切片先因应用模块不存在而失败；对象/数据库单侧失败恢复和越权用例实现后 `3 passed`，补充非交互密码管道拒绝后为 `4 passed`。
- 第一轮专属真实 PostgreSQL/MinIO 为 `12 failed, 110 passed, 1 error`，确认旧 Schema 与新元数据契约尚未接通；补 Schema/Store 后为 `6 failed, 117 passed`；修正旧断言后为 `123 passed, 2 warnings in 44.65s`，每轮均精确清理本轮临时容器、库和对象。加入两类单侧失败与边界断言后的首轮为 `2 failed, 127 passed`：子进程缺少显式 `PYTHONPATH`，报告链接遗漏 `created_at`。修正产品字段和测试可移植性后复验为 `129 passed, 2 warnings in 51.06s`；三个随机标签容器均无发布端口/宿主挂载，并在结束后精确清理。
- 当前相关后端定向组最近一次为 `13 passed, 1 skipped`；跳过项是无真实临时存储环境时的集成标记，不算通过。
- Web 类型检查已通过。新增删除状态浏览器用例首次暴露页面未刷新，修复后为 `1 passed in 11.2s`；补充逐对象哈希、大小、创建/删除时间、清理者和原因展示后定向复验为 `1 passed in 10.2s`，仍不出现原始下载。
- `git diff --check` 当前无补丁空白错误，只有既有 Windows 行尾提示。Ruff 首轮审计报告 15 项导入顺序/行宽/测试夹具名问题；同时发现 4 个本轮扩展后的源文件越过 200 物理行指标，当时未记为通过，处理结果见下一条。
- 拆出内部 raw policy、MinIO identity policy、Job listing query、共享 HTTP 制品 DTO 和 Web 制品解析后，当前受影响动态源文件均不超过 200 行、受影响目录均不超过 8 个直属文件。全仓 Ruff check 与 271 文件 format-check 通过；strict mypy 为 `Success: no issues found in 156 source files`，compileall 通过。
- 默认完整后端为 `372 passed, 77 skipped, 2 warnings in 42.86s`。77 项均为显式真实 PG/MinIO、Docker、Fork、Harbor 或 Codex 门禁；任务 12 双存储项由前述专属 129 项套件实际覆盖，其余不冒称通过。
- Web typecheck 通过。Next 生产构建第一次在用户级配置临时文件处分别遇到 EPERM/EXDEV；设置官方无遥测/无更新检查环境后成功构建 4 个静态页面。完整浏览器套件第一次因沙箱不能覆盖测试结果文件而未执行；改用系统 Chrome 后任务 12、目录、身份、安全、批次、证据和取消均通过，既有中断恢复用例在串行高负载下 5 秒超时，单独复跑为 `1 passed in 9.1s`。因此完整浏览器套件仍须在最终收尾再跑一次，不能把本次中途停止记为全量通过。

尚未完成：最终完整浏览器回归、权威架构/数据/HTTP/任务单同步、文档链接与秘密扫描、实现提交和以 `69620b2` 为基准的 Standards/Spec 双轴评审及修复复验。
