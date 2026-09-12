# M1 安全证据与轨迹查看行动记录

## 状态

Implementation Complete / Review Pending。实现与分层验收已完成；待以任务 07 关闭提交 `3899e7e` 为固定基准完成双轴评审、修复和关闭核对。

## 情况说明

- 权威任务为 [08-safe-evidence.md](../../.scratch/m1-platform/issues/08-safe-evidence.md)，对应规格故事 5、8、36–41、51。
- 任务 06/07 已保存并复核最终 patch、Harness 报告/输出等受限证据，但 HTTP 目前只返回元数据；Harbor 的原始 ATIF 轨迹尚未进入长期对象或安全查询边界。
- 本任务不新建表、顶层 Module、目录或平行存储 Interface：深化既有 `artifact_records`、Artifact Store、Job Repository、Reporting，并实现架构已规划的 Artifact/Trajectory route。新增的 `public_test_summary` 与 `public_trajectory` 是同一表的受控派生证据类型。
- 原始 Harbor/Fork 内容不直接发布。最终 patch 必须先通过输出保护扫描；测试摘要只从确定性计数生成；轨迹只保留连续序号、时间、受控来源/类型和不含参数或消息正文的摘要。无法证明安全的正文拒绝下载，不以静默裁剪冒充原文。
- 任务 12 再实现到期清理与 410 删除审计；本任务实现不存在/未就绪/损坏的失败关闭语义，不预建清理字段或服务。
- Judge/Review 保持不变；不运行真实模型/真实凭据、不部署、不推送、不修改机器或网络设置。

## 实施措施

1. 先以真实 HTTP 用例写红灯，固定同一会话授权、资源归属、`official`/`internal_test` 隔离、稳定分页/类型筛选、白名单下载和安全错误。
2. 深化 `EvidencePublication`：在写 MinIO 前检查 patch 的 UTF-8、已知凭据形状、私有路径及隐藏答案标记；从确定性结果生成仅含计数的测试摘要；从受信 ATIF 生成不含消息正文/工具参数的规范化 JSONL。
3. 深化既有 Job Repository，用 artifact ID 反查所属 Run 报告；PostgreSQL 查询只返回归属身份，不把对象键交给 HTTP。Reporting 统一做范围、账号、类型、哈希/大小和内容安全校验。
4. 在已规划的 Artifact/Trajectory route 提供 Run 制品分页、轨迹序号分页和受控正文响应；沿用应用身份，不返回 MinIO 凭据、对象键或私有路径。
5. Web 从逐 Run 报告进入 patch、测试摘要和轨迹；运行时解析响应，明确显示未就绪/不可发布，不显示私密思维链或原始日志。
6. 分层执行定向/默认 pytest、Ruff/mypy、真实临时 PostgreSQL+MinIO、Web typecheck/build 和浏览器报告→轨迹/下载；记录全部失败、跳过和资源清理。最后以 `3899e7e` 为基准做 Standards/Spec 双轴评审并修复。

## 需要修改的文件树

```text
apps/backend/src/eval_platform/
├─ domain/jobs/{models,execution}.py                  # 安全错误与证据所属值
├─ application/
│  ├─ execution/{public_evidence,evidence,completion}.py # 扫描、规范化及派生发布
│  ├─ reporting/{evidence,service}.py                 # 授权、分页、下载与完整性门禁
│  └─ ports/repositories.py                          # 深化既有 artifact→Run 归属查询
├─ adapters/
│  ├─ artifacts/{local,minio}.py                     # 新受控类型的读写校验
│  └─ persistence/{catalog/schema.sql,jobs/}.py       # 同表类型约束与归属查询
└─ delivery/http/
   ├─ app.py / errors.py                             # 已有装配与安全错误映射
   └─ routes/artifacts.py                            # 已规划的证据索引/轨迹/正文 route
apps/backend/tests/jobs/execution/
├─ test_evidence_publication.py                      # 输出保护与派生证据
├─ test_storage.py                                   # 双存储完整性/故障
└─ batch/test_http_stages.py                         # 证据 HTTP 与授权
apps/web/src/
├─ features/jobs/{report,evidence}.tsx               # 报告到证据/轨迹入口
└─ lib/{contracts,job-client,report-shapes}.ts        # 同步契约与失败关闭解析
apps/web/tests/job-evidence.spec.ts                   # 浏览器证据导航
docs/{architecture,interfaces}/                      # 当前事实与公开契约
.scratch/m1-platform/issues/08-safe-evidence.md      # 验收状态与证据
```

采用 Ports/Adapter、Repository、Application Service 与派生发布（Derived Publication）模式。原始证据只作为输入，应用层生成可公开的新对象；Reporting 是唯一外发门禁，HTTP 和 Web 不直接访问 MinIO。

## 自验证方式与成功标准

- 授权：owner 可读全部 official；协作者只读自己创建的 official；其他账号、未知 artifact/run 及 internal_test 在生产装配统一 404。
- 输出保护：合成 Token、私有路径、`auth.json`、gold/reference/test patch 标记在共享写入前被拒绝；正常相似文本不误拒；原始消息、工具参数、隐藏测试详情和对象键不出现在响应、错误或页面。
- 完整性：artifact ID 必须属于目标 Run，种类/内容类型/大小/SHA-256 一致；不存在、未就绪、损坏、断流明确失败，不返回空成功；写入不可覆盖。
- 查询：制品按稳定 cursor 分页和类型筛选；轨迹按连续 sequence 与可选 type 分页，`next_after_sequence/complete` 准确。
- 展示：最终 patch 保持原始字节，不为展示截断；超过 256 KiB 的既有 warning 可见，超过 1 MiB 仍由执行门禁拒绝；页面能打开 patch、测试摘要与轨迹。
- 分层证据按实际记录；真实临时容器无发布端口/宿主挂载并按精确 ID 清理。动态源码每文件不超过 200 行，受影响目录每层不超过 8 个直接文件，`git diff --check` 无错误。

## 自验证情况

- 输出保护先红后绿：新增 6 个单元用例，最初 4 失败/2 通过；实现安全扫描和规范化后 6 个全部通过。
- 首轮证据 HTTP 用例因 `JobReporting` 的字段/方法同名返回 500；拆分为 `artifact_reader` 后转绿，证明路由实际经过应用门禁。
- 首轮定向回归为 24 通过、1 跳过；Ruff 修复导入/行宽后通过，mypy 检查 122 个源码文件通过。后续增量、完整套件、真实依赖和浏览器仍待执行。
- 首次浏览器验收走通至下载，但发现空 `download` 属性使建议文件名成为 `content` 而非 `agent.patch`；已改为按公开证据类型提供受控文件名，等待重跑确认。
- 完整默认后端回归 329 通过、63 跳过、2 个依赖弃用警告；Web typecheck/build 通过。浏览器修复后报告→安全轨迹→补丁下载 1/1 通过。
- 首次真实临时 PostgreSQL+MinIO 为 71 通过、1 失败：失败是故障注入用例仍断言旧的 3 个孤立对象，新安全摘要使实际为 4 个；数据库仍保持无半成品且三个容器已精确清理。已把断言深化为四种精确对象类型，等待重跑。
- 真实依赖重跑 72 通过、2 个依赖弃用警告；覆盖不可覆盖、断流、对象缺失、数据库单侧失败及公开证据，同轮所有专属容器和 tmpfs 数据已精确清理，镜像/构建缓存保留。
- 权威架构、数据模型、模块契约和 HTTP 接口已同步当前公开三类证据、同一授权边界及任务 12 才实现的删除/410；这些文件含此前未提交增量，按交接纪律暂不混入本任务实现提交，评审须读取现场。
- 固定基准 `3899e7e` 首轮双轴评审：Spec 为 2 个 P1、2 个 P2，Standards 为 1 个 P1、1 个 P2（断流项重叠）。问题为原始 Harness 写入共享 MinIO、跨 Run 归属复核缺失、Web 未继续翻页、短读测试只改长度头，以及数据模型枚举文字矛盾；均在已批准范围内，无需新增决定。
- 修复中：共享对象改为从已核验 Harness 结果派生最小确定性审计内容，原始报告/输出只在私有源侧校验；真实 Fork Mapper 补齐不含测试 ID 的计数；Reporting 复核 Run 字段及对象键前缀；Web 累积轨迹页；短读改为正文实际少一字节并在真实 MinIO 对象上注入传输截断；数据模型明确完整枚举和公开三类。
- 修复后定向后端 42 通过、1 个真实 MinIO 项按门控跳过；浏览器通过路由把页长压到 1，实际验证“查看→加载更多→第二事件→下载”为 1/1 通过；Ruff、mypy 123 源码、Web typecheck/build 和 `git diff --check` 通过。
- 修复后真实临时 PostgreSQL+MinIO 最终 72 通过、2 个依赖弃用警告：真实对象经过声明原长度但正文少 1 字节的传输包装后明确失败；共享 bucket 在数据库失败时只含 `agent_patch/harness_report/harness_test_output/public_test_summary/public_trajectory` 五类派生/公开对象，不含私有原文。中间两次清单断言失败均如实记录且每次容器均已精确清理；最终同样清理，镜像/构建缓存保留。
- 修复后完整默认后端 329 通过、63 个未启用重型项跳过、2 个依赖弃用警告；Web 最终生产构建通过。待提交修复并复做双轴评审。
