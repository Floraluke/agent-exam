# M1 任务 05：所有者批准或拒绝

## 状态与情况说明

- 状态：Completed。任务 05 八项验收、完整回归与固定基准双轴评审均已完成；实现提交 `d3148e1`，评审修复 `94ad4b6`、`2dfd427`，开工固定基准为 `8cf5e57`。
- 对应[任务 05](../../.scratch/m1-platform/issues/05-owner-approval.md)与 M1 规格故事 18–21、51。HTTP、应用、领域、合成 Repository、真实 PostgreSQL Adapter 与 Web 均已落地；任务 06 未开始。
- 本任务深化已规划的 Owner Approval 与 Job Repository，不新增数据库表、顶层业务 Module、外部服务或执行后端；不实现任务 06 的 Worker 领取、任务 09 的取消，也不修改 M0 ExecutionBackend/PatchEvaluator。
- M1 规格已确认测试 seam：HTTP Interface 为主、少量浏览器接线、真实临时 PostgreSQL 验证事务/并发。用户已确认决定说明可选；填写时去除首尾空白、限制 1–500 个 Unicode 字符并拒绝控制字符，页面提示不填写凭据、Token 或宿主路径，不使用误判风险高的秘密正则扫描。
- 真实模型、Harbor、凭据读取、长期数据库、远程部署、机器设置和 Git 推送均不在本行动范围。现有混合文档、缓存、framework/runtime 保持原状。

## 实施措施

1. 已同步决定说明策略和任务标签；按 HTTP seam 逐片红绿固定 owner 权限、批准/拒绝状态与安全输出。
2. 在既有领域值与 `JobRepository` Interface 内加入一个原子 Owner 决定，PostgreSQL Adapter 隐藏行锁、状态推进、幂等、事件和拒绝时 Run 取消；合成 Adapter 满足同一 Interface。
3. 扩展显式 Job 建表子集：不新增表，只补决定元数据/幂等字段、任务 05 状态约束、sequence 2 事件及队列索引；服务启动仍不迁移。
4. Web 只向 owner 展示冻结摘要后的批准/拒绝控件；提交者通过现有详情刷新看到真实决定。批准只写 `QUEUED`，拒绝写 `REJECTED` 并取消 `PENDING` Run；两者均不接触执行或凭据。
5. 运行默认回归、Ruff/mypy、Web typecheck/build、完整浏览器及专属真实 PG；记录失败/跳过与精确清理。完成后按 code-review 以开工点 `8cf5e57` 做 Standards/Spec 双轴评审、修复复核并限定范围本地提交；不推送，不进入任务 06。

## 需要修改的文件树

以下为完成后的实际增量树。既有目录均未超过每层 8 文件，本轮动态代码均不超过 200 行。

```text
apps/backend/src/eval_platform/
├─ domain/jobs/
│  ├─ models.py                         # 扩展 Job/Run 状态、决定元数据与事件公开值
│  └─ decisions.py                      # 新增：Owner 决定值、幂等正文与状态错误
├─ application/
│  ├─ owner_approval.py                 # 新增：可信 owner 授权与决定用例（深 Module）
│  └─ ports/repositories.py             # 扩展既有 JobRepository 的单一 decide Interface
├─ adapters/persistence/jobs/
│  ├─ schema.sql                        # 扩展四张既有表的任务 05 子集，不新增表
│  ├─ decisions.py                      # 新增：短事务内行锁、幂等与原子状态推进
│  ├─ repository.py                     # Adapter 实现 decide
│  ├─ records.py                        # 恢复并校验待批/排队/拒绝快照和审计事件
│  └─ publication.py                    # 初始事件改用显式列并恢复可信 actor
├─ delivery/jobs.py                     # 组装 Submission 与 Owner Approval，共用 Repository
└─ delivery/http/
   ├─ app.py / errors.py                # 注入用例并翻译安全错误
   └─ routes/jobs/
      ├─ routes.py / schemas.py         # 批准/拒绝端点与决定后的安全 Job 输出
      └─ decision_schemas.py            # 新增：自由文本策略确认后固定请求 DTO
apps/backend/tests/
├─ jobs/test_approval.py                # 新增：HTTP 权限/状态/备注边界与幂等
├─ jobs/{memory,conftest,test_security,test_concurrency,test_postgres}.py # Adapter、装配与回归
└─ identity/browser_server.py            # 内部浏览器装配同一 Owner Approval 用例
apps/web/src/
├─ features/jobs/{submit,details}.tsx    # 当前角色与决定状态接线
├─ features/jobs/approval.tsx            # 新增：owner 专用批准/拒绝控件
├─ features/identity/session.tsx         # 把可信会话角色传入 Job 页面
└─ lib/{contracts,job-client,job-shapes}.ts # 契约、决定请求与响应运行时校验
apps/web/tests/jobs.spec.ts               # 浏览器批准/拒绝与刷新
docs/actions/2026-09-12-m1-owner-approval.md # 本行动唯一执行记录
.scratch/m1-platform/issues/05-owner-approval.md # 标签、验收和过程说明
docs/architecture/{ARCHITECTURE,DATA_MODEL,MODULE_CONTRACTS}.md # 当前子集同步
docs/interfaces/HTTP_API.md               # 决定输入、输出、错误和任务 06 边界
```

设计模式继续使用 Ports/Adapter、Repository 和 Composition Root。Owner Approval 的小 Interface 隐藏授权、幂等正文与决定规则；PostgreSQL Adapter 在既有存储 seam 内隐藏 SQL/事务；HTTP 和 Web 只消费该 Interface，不知道行锁或执行后端。

## 自验证方式与成功标准

- HTTP：owner 批准为 `QUEUED`、拒绝为 `REJECTED` 且 Run 为 `CANCELED`；决定者/时间/说明/sequence 2 事件可刷新；协作者为 403，正文身份/冻结覆盖为 422；缺失为 404，状态/幂等冲突为 409。
- 不执行不变量：应用构造不依赖 ExecutionBackend、PatchEvaluator 或凭据提供方；批准/拒绝成功立即返回，不创建 Harbor/模型/判卷引用。
- 真实 PostgreSQL：短事务原子更新；故障整体回滚；同键同决定重放，同键异决定冲突；不同键或并发批准/拒绝只有一个最终决定；只有 `QUEUED` 出现在现有状态筛选的队列资格结果，待批/拒绝不出现。
- 浏览器：owner 核对冻结摘要后批准和拒绝，刷新恢复真实状态；协作者不显示决定控件并能看到 owner 决定后的状态/说明策略允许的公开内容。
- 全量：默认 pytest、Ruff、mypy、Web typecheck/build、完整浏览器、专属 PG、文档链接/围栏/diff、文件/目录指标和残留资源均按实际输出记录。未运行或跳过不得记为通过。

## 自验证情况

- HTTP 首个红灯：owner 对冻结 Job 批准预期 200，因端点尚不存在实际 404；实现应用/领域/内存 Repository/路由后，批准、拒绝及队列筛选的第一片为 2 passed。扩充权限、备注边界与幂等后，`test_approval.py` 为 5 passed / 2 warnings；Job HTTP、安全回归合跑为 14 passed / 2 warnings。
- PostgreSQL 首个业务红灯：专属无网络容器内新增审批恢复测试实际 500，批次为 19 passed / 1 failed / 2 warnings；临时容器和 tmpfs 已精确删除。首次以 Windows PowerShell 5.1 调用时，既有脚本的原生命令错误处理在创建容器前遮蔽异常；只读核对该随机名称无残留，改用 PowerShell 7 执行同一脚本后取得上述真实红灯，未据此改业务结论。
- PostgreSQL 实现后第一次回归发现数据库 UUID 未在读出边界转成公开字符串，重启后详情返回 500；修正统一恢复后，扩充批准重放、两 Run 拒绝、事件故障回滚和批准/拒绝并发争抢，最终专属批次 `23 passed / 2 warnings`（12.67 秒）。测试镜像 `sha256:81bbb9d...950c0`，固定 PostgreSQL 镜像仍为 `sha256:5cce759...a6b6`；PostgreSQL 容器 `50c90a28...c0a07`、测试器 `51d44cbd...4d25` 无发布端口、无宿主挂载，完成后均按精确 ID 删除，随机标签复核无残留，tmpfs 数据删除，镜像/构建缓存保留。
- 当前实现只把批准写为 `QUEUED`，拒绝写为 `REJECTED` 并取消 `PENDING` Run；Owner Approval 构造没有 ExecutionBackend、PatchEvaluator、Harbor 或凭据依赖。
- 浏览器首轮普通沙箱因 Playwright 无权删除旧结果文件、第二次因专用结果目录未预建，均未到业务断言；只终止了由该失败批次启动且 PID 已明确的 3100/8875 测试进程，没有删除旧结果。提升后首轮未设置项目浏览器缓存，2 项在 Chromium 启动前失败；未下载内容。按依赖文档复用 `runtime/tools/playwright` 后取得真实红灯：页面缺少决定说明警告，1 failed / 1 passed；实现 owner 控件、三状态解析和决定审计后为 2 passed。
- 扩充浏览器覆盖后，`jobs.spec.ts` 最终 3 passed（13.4 秒）：owner 批准并重载；另一陈旧 owner 页面拒绝收到 409、自动刷新为真实 `QUEUED`；协作者提交后无决定控件，owner 拒绝后协作者刷新可见 `REJECTED` 与说明；畸形嵌套 Job 选项继续失败关闭。测试只使用合成 `internal_test` 后端，没有启动 Agent/Harbor/判卷。
- Web `npm run typecheck` 通过。首次普通沙箱生产构建仅因 Next 无权写用户级配置临时文件失败；禁用遥测并提升构建权限后，编译、类型检查、4 个静态页面和 trace 全部完成，首页 8.89 kB、首载 111 kB；这不是部署。
- 已同步总架构、数据模型、模块契约与 HTTP 契约的任务 05 真实子集；任务单八项验收与最新说明已回填。
- 默认完整后端为 `288 passed / 56 skipped / 2 warnings`（27.79 秒）；56 项均为显式门禁的 PostgreSQL、MinIO、Docker 或真实执行检查，其中任务 05 PG 已由专属批次覆盖，其余不记为本轮通过。Ruff check 通过，156 个 Python 文件 format check 通过，mypy 检查 92 个源文件无问题。
- 完整浏览器按五个 spec 分别启动新合成后端，累计 14 passed：catalog 2、identity-security 6、identity 2、jobs 3、membership 1；各组 8.6–14.4 秒。复用已有只读 Chromium 缓存，结果写入任务 05 专用目录；没有下载浏览器、部署服务或留下 3100/8875 监听。
- 测试整理后再次运行专属 PG，最终仍为 `23 passed / 2 warnings`（12.74 秒）。测试镜像 `sha256:c3bff347...f82d6`；测试器 `e97cf442...9496`、PostgreSQL `dd684070...8938` 由随机标签限定，无发布端口/宿主挂载，结束后按精确 ID 删除并复核无残留，tmpfs 数据不可恢复地删除，镜像/构建缓存保留。
- 指标复核：所有本轮动态源码与测试均不超过 200 个物理行；`application` 7、`ports` 7、`domain/jobs` 4、`persistence/jobs` 6、HTTP jobs 路由目录 4、`tests/jobs` 8、Web jobs 4、Web lib 6 个直接文件，没有新增目录或指标例外。`git diff --check` 通过。
- 固定基准 `8cf5e57` 的第一轮 Standards 评审提出 1 个必须修复与 2 个判断项：HTTP 文档的通用 JobSummary 示例仍是旧字段；三个写端点重复声明幂等请求头；真实/合成 Repository 重复决定到状态、事件和 Run 取消映射。Spec 评审提出 2 项：Web 冻结摘要未显示完整模型/资源/网络工具策略/框架版本及决定者；OpenAPI 未声明说明的 1–500 长度。均纳入当前任务修复，没有扩大到任务 06。
- 评审修复：HTTP 通用示例已同步真实三状态与 `owner_*` 字段；路由共享一个受约束的 `IdempotencyKey`；领域 `OwnerDecision` 统一提供目标状态、原因码和是否取消 Run，两个 Adapter 消费同一映射；决定 DTO 以 `Field` 暴露 OpenAPI 边界，同时仍先规范化输入；Web 展示完整冻结摘要与决定审计，并把请求和响应运行时校验拆成同层 `job-client.ts` / `job-shapes.ts`，避免单文件越过 200 行。新增 OpenAPI 断言后，针对性后端为 `15 passed / 2 warnings`（3.81 秒），Ruff、155 个文件格式检查、mypy 91 个源文件及 Web typecheck 通过。当前窗口首次直接调用 `uv` 因不在 PATH 未运行任何检查，随后改用项目 `.venv` 得到这些真实结果。
- 第一轮复核：Standards 的三项原发现均解决，另发现上述 Web lib 计数仍写 5，已改为真实 6（6≤8）；Spec 的 Web 冻结摘要已解决，但指出标准 OpenAPI `maxLength` 会约束原始字符串，与“先 trim、再限制规范化值”的服务端语义不一致。决定 schema 改用 `x-normalization=trim` 与 `x-normalizedMinLength/MaxLength=1/500` 明示规范化边界，不再让生成客户端误用标准原始长度约束；测试同时断言标准 min/max 不存在及扩展值准确。
- 最终复核：原 Standards 评审者确认文档示例、幂等 Header、决定映射和目录计数全部 resolved，未发现 `2dfd427` 直接回归，Standards 通过；原 Spec 评审者确认 Web 冻结摘要/决定者、OpenAPI 规范化长度及契约测试全部 resolved，无直接规格回归，Spec 通过。
- 评审修复后的最终专属 PostgreSQL 为 `24 passed / 2 warnings`（13.43 秒）。测试镜像 `sha256:15b2ea5453b0c934354c5c5c4f450561022d45071e5802229532009e7e4c8006`；PostgreSQL 容器 `ff7fe897b0296d7d0b8cc05c2b8ee1d3789341eb15fa3693eeb897fc73e8bd20`、测试器 `d3b7680734ef5b92c48a29e4297596f639e5073eed4beab870fe5458fff03f06` 无发布端口/宿主挂载，均按精确 ID 删除，随机标签无残留，tmpfs 数据删除，镜像/构建缓存保留。
- 最终默认后端为 `289 passed / 56 skipped / 2 warnings`（30.10 秒）；56 项仍是显式门禁的 PostgreSQL、MinIO、Docker 或真实执行检查，本任务 PG 由上方专属批次覆盖，其余不记为本轮通过。最终 Ruff check、155 个文件 format check、mypy 91 个源文件与 Web typecheck 通过。Web 生产构建通过，首页 9.6 kB、首载 112 kB；仅构建未部署。
- 最终浏览器五组累计 `14 passed`：catalog 2（10.3 秒）、identity-security 6（13.9 秒）、identity 2（8.6 秒）、jobs 3（13.5 秒）、membership 1（11.1 秒）。复用项目只读 Chromium 缓存，只运行合成 `internal_test` 后端；没有下载浏览器、运行模型/Harbor/判卷或留下测试服务。
- 最终文档/资源审计：本任务 6 份 Markdown 的 102 个本地链接全部存在，代码围栏成对且无尾空白；任务单 8 项已勾、0 项未勾；`git diff --check` 通过。3100/8875 无监听，提升权限只读查询 `agentexam.jobs-test` 标签容器为空。权威架构/数据/接口含有此前混合未提交增量，本任务内容已在现场同步但不混入收尾提交；旧文档、缓存、framework/runtime 均保留。
