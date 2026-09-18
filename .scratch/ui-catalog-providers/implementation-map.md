Status: needs-info

# 实现地图与文档联动

> 供[执行计划](plan.md)按阶段读取。现有路径是 2026-09-17 工作区事实；“候选新增”只供审阅，本轮没有创建这些源码目录。实现前回读源码、锁定当时 HEAD；不得按这张地图重造平行链。

## 1. 责任边界

Web 只改善呈现与交互，复用唯一请求客户端与现有 HTTP；Task Catalog 负责受控题目，Agent Registry 负责受控配置，Job Submission 冻结矩阵及策略，Job Repository 保持事务/幂等/权限，Worker 领取已批准 Job。ExecutionBackend 的 Harbor Adapter 继续执行，PatchEvaluator 的固定 Fork Adapter 继续独立判卷。

本次不新增顶层 Module、公共业务 Interface 或数据库表。代理是 Execution Adapter 内部实现：现有网络侧车只做网络过滤，不能承载秘密注入与预算结算，所以需要专属内部代码和隔离进程。方向已批准；下列精确目录/形状仍是候选，正式实施前确认，不以“内部重构”跳过批准。

设计模式保持 **Adapter（适配器）**：Harbor/Fork 实现原端口；Worker 组合根装配可信私有绑定；内部 provider 配置选择器从有限预设挑选绑定，不接受提交者自定义服务地址。无新的代理业务 API、任务队列或判卷实现。

## 2. 按阶段必读的现有入口

相对路径从仓库根开始；链接仅指向本轮实际存在的源码。每行的相关测试须继续跟读其夹具和错误路径。

| 阶段 | 现有入口与职责 | 相关验证入口 |
|---|---|---|
| 01–03 | [会话壳](../../apps/web/src/features/identity/session.tsx)、[提交与动线](../../apps/web/src/features/jobs/submit.tsx)、[批次报告](../../apps/web/src/features/jobs/batch-report.tsx)、[单次报告](../../apps/web/src/features/jobs/report.tsx)、[Job 客户端](../../apps/web/src/lib/job-client.ts)：替换长页组织，复用鉴权请求 | [浏览器运行器](../../apps/web/tests/run-browser-tests.mjs)、[Web 包脚本](../../apps/web/package.json)；跟读 identity/catalog/jobs/job-batch/job-evidence、recovery/leaderboard/retention 用例 |
| 04 题目 | [受控种子](../../apps/backend/src/eval_platform/delivery/catalog_presets.py)、[Task Source](../../apps/backend/src/eval_platform/adapters/tasks/swe_gym.py)、[目录用例](../../apps/backend/src/eval_platform/application/task_catalog.py)：固定 Parquet/镜像和公开/隐藏数据分离 | [目录 HTTP](../../apps/backend/tests/catalog/test_http.py)、[一致性](../../apps/backend/tests/catalog/test_consistency.py)、[Fork 集成](../../apps/backend/tests/integration/test_swe_bench_integration.py) |
| 04 规模 | [策略组合](../../apps/backend/src/eval_platform/delivery/job_presets.py)、[领域策略](../../apps/backend/src/eval_platform/domain/jobs/policy.py)、[提交用例](../../apps/backend/src/eval_platform/application/job_submission.py)、[Repository](../../apps/backend/src/eval_platform/adapters/persistence/jobs/repository.py)：服务端边界与冻结事务 | [提交 HTTP](../../apps/backend/tests/jobs/test_http.py)、[并发](../../apps/backend/tests/jobs/test_concurrency.py)、[真实 PG](../../apps/backend/tests/jobs/test_postgres.py)、[恢复](../../apps/backend/tests/jobs/recovery/test_retry.py) |
| 05–07 配置 | [配置身份](../../apps/backend/src/eval_platform/domain/agent.py)、[Registry](../../apps/backend/src/eval_platform/application/agent_registry.py)、[目录 SQL](../../apps/backend/src/eval_platform/adapters/persistence/catalog/schema.sql)、[配置 Repository](../../apps/backend/src/eval_platform/adapters/persistence/catalog/agents.py)：当前只接受旧 ChatGPT 的约束需扩展 | [目录安全](../../apps/backend/tests/catalog/test_security.py)、目录 HTTP/PG/一致性测试 |
| 05–07 执行 | [Worker 组合](../../apps/backend/src/eval_platform/delivery/worker/runtime.py)、[编排](../../apps/backend/src/eval_platform/application/execute_job.py)、[Harbor 配置映射](../../apps/backend/src/eval_platform/adapters/execution/harbor/config_mapper.py)、[引导入口](../../apps/backend/src/eval_platform/adapters/execution/harbor_entry.py)：按冻结 Run 解析秘密绑定 | [Worker 测试](../../apps/backend/tests/jobs/runtime/test_worker_runtime.py)、[矩阵编排](../../apps/backend/tests/jobs/execution/batch/test_orchestrator.py)、[租约预算](../../apps/backend/tests/jobs/execution/batch/test_lease_budget.py) |
| 05 安全 | [Codex guard](../../apps/backend/src/eval_platform/adapters/execution/codex/agent.py)、[权限策略](../../apps/backend/src/eval_platform/adapters/execution/codex/policy.py)、[私有上传](../../apps/backend/src/eval_platform/adapters/execution/codex/uploads.py)、[网络](../../apps/backend/src/eval_platform/adapters/execution/network.py)、[清理](../../apps/backend/src/eval_platform/adapters/execution/harbor/lifecycle/cleanup.py) | [完整假 Trial](../../apps/backend/tests/test_codex_trial.py)、[网络合同](../../apps/backend/tests/contract/test_execution_network.py)、[秘密测试](../../apps/backend/tests/test_secret_safety.py)、取消/恢复测试 |

04 必须继续读取 Job snapshots/factory、PG records/state_validation 与报告可比性校验，避免仅修改 options 后被旧读出校验拒绝。05 必须继续读取 Harbor process_runner/result mapper 与 Codex 安装约定，不用独立脚本绕开正式链。

## 3. 候选文件树：只新增最小内部职责

### 01 原型，不进入产品构建

```text
runtime/prototype/ui-workbench-<date>-<scope>/ # 候选；Git 忽略的静态假数据原型
├─ index.html                               # 结构/角色/场景切换入口
├─ styles.css                               # 浅色响应式样式
├─ scripts/                                 # 每文件 <=200 行；拆事件和渲染，不拼巨大 JS
│  ├─ fixtures.js                           # 明显标识的假 Job/Run/成员
│  ├─ state.js                              # 向导、角色、场景状态
│  └─ views/                                # 候选页面渲染；每层 <=8 文件
└─ evidence/                                # 选定布局与手机/桌面截图，不含真实账号
```

本地静态 HTML 是用户指定形式；可离线打开，需本机预览时仅回环，不启用 Serve。原型不提交成生产功能；确认的交互结论进入后续行动/原型决策记录，生产代码按既有 React 结构重写。

### 02–03 Web 内部整理

```text
apps/web/src/features/
├─ identity/session.tsx                     # 修改：保留会话与身份门禁，组合角色工作台
├─ workbench/                              # 候选新增：布局职责，不是新业务 Module
│  ├─ shell.tsx                            # 导航/当前视图/移动布局
│  ├─ owner.tsx                            # owner 的可见 Job 概览与入口
│  └─ collaborator.tsx                     # 本人评测与新建入口
├─ jobs/
│  ├─ submit.tsx                           # 修改：薄组合，旧组件对外入口兼容
│  ├─ wizard/                              # 候选新增：选题、配置、复核及向导状态
│  ├─ listing/                             # 候选新增：复用游标/筛选、非全局计数
│  ├─ reporting/                           # 候选新增：矩阵/指标/详情呈现
│  └─ lifecycle/recovery.tsx               # 修改仅动线：保留恢复和新 Job 语义
├─ catalog/{tasks,agents}.tsx               # 修改展示/导航，不增加秘密输入
└─ identity/members.tsx                     # 修改展示；服务器权限照旧
apps/web/src/lib/job-client.ts              # 修改：列表参数化/复用 request，保留 API 校验
apps/web/src/lib/jobs/                      # 已有；新增类型若必要在此承载
apps/web/tests/workbench/                   # 候选新增：桌面/手机/角色/导航用例
apps/web/tests/jobs/                        # 候选新增：向导与对比用例，测试入口不重复
```

当前 jobs 已有 8 个直接文件、lib 已超过默认指标，不再向这些目录平铺文件。仅把本次被修改的状态/渲染按职责移入子目录，保持旧导出直到调用全部迁移通过；不顺手清理全仓。原有重复/长页耦合在本次 UI 内处理，其他坏味道另报范围。

### 04 目录与规模

```text
apps/backend/src/eval_platform/
├─ adapters/tasks/swe_gym.py                 # 修改：用已资格验证的固定集合替代单题拒绝
├─ adapters/tasks/catalog.py                # 候选新增：instance -> 固定镜像身份清单
├─ delivery/catalog_presets.py              # 修改：新增已合格题的有限 preset
├─ delivery/job_presets.py                  # 修改：新连续范围策略版本，旧版本可解释
├─ domain/jobs/{policy,snapshots,factory}.py # 必要修改：验证、序列化、冻结哈希兼容
└─ adapters/persistence/jobs/               # 必要修改已有读出校验；不新增第九个根文件
apps/backend/tests/catalog/qualification/   # 候选新增：五题参数化资格/隐藏信息/漂移测试
apps/backend/tests/jobs/submission/          # 候选新增：新规模与旧快照兼容矩阵
```

目录清单只保存非秘密固定身份；gold/test patch 与测试名仍在原隐藏判卷数据，不移到可给 Agent 读取的清单。后续准备镜像前才冻结实际 digest，不能凭题号推断镜像已存在。

### 05–07 API 绑定与隔离代理

```text
apps/backend/src/eval_platform/
├─ application/agent_registry.py            # 修改：仅登记已审核的 API 预设
├─ domain/agent.py                          # 必要修改：新身份版本；旧指纹完全兼容
├─ delivery/http/catalog_schemas.py         # 修改：受控目录响应，不接受 Key/URL
├─ delivery/catalog_presets.py              # 修改：非秘密提供方模板
├─ delivery/worker/runtime.py               # 修改：不再无条件要求 ChatGPT auth，按 Run 选绑定
├─ adapters/persistence/catalog/schema.sql  # 修改：新安装约束；不增加表
├─ adapters/persistence/catalog/upgrade_api.sql # 候选：显式升级旧约束，不自动开机迁移
├─ adapters/execution/codex/provider_config.py # 候选：固定 TOML/模型目录渲染及摘要
├─ adapters/execution/provider_access/      # 候选内部实现；不向应用暴露新业务端口
│  ├─ __init__.py                           # 内部导出
│  ├─ binding.py                            # Run 绑定、有限 provider 选择
│  ├─ secrets.py                            # 私有文件权限/结构验证及可信读取
│  ├─ service.py                            # 代理入口、鉴权、流生命周期
│  ├─ request_policy.py                     # 路径/字段/模型/工具白名单
│  ├─ transport.py                          # 固定 HTTPS 上游、无跳转/重试/正文日志
│  ├─ budget.py                             # 原子预留、usage 结算、未知关闭
│  └─ network.py                            # 私有拓扑组合、正反可达性预检
└─ adapters/execution/harbor/                # 修改已有映射/生命周期，根目录保持8文件
apps/backend/tests/providers/               # 候选：policy/、lifecycle/、integration/分层
```

该树是上限内的责任规划，不强迫按文件名造空壳；若代理实现超过单文件指标，在同职责内部拆分并先更新树。真实 Key 通过受控私有输入流进入代理，不经 Docker 环境变量、命令行、镜像层或 Job 参数；实现须有相反攻击测试。

## 4. 关键数据兼容方案（候选实现）

1. **规模版本：** 为连续范围发新 preset ID（候选 `flexible-v2`）；旧快照仍按原版本解释与验证。若保留旧提交 preset 兼容客户端，其旧边界不变；UI 默认新版本，不能把旧 ID 重新解释为1–20。
2. **模型身份：** 既有字段承载 provider/model/auth_type/非秘密 credential profile；新增受控配置摘要覆盖 provider配置版本、固定 CLI、模型目录/模板、关键请求参数及协议。原指纹算法不能就地改变；缺版本字段的历史配置仍按旧算法校验。秘密值不进入摘要或响应。
3. **请求与限额：** HTTP 仍只选服务端 preset；API 限额版本随新 Job 冻结，旧 Job 不补填未来限额。JSON 快照变化先验证新/旧 schema 与读出校验，再迁移显式 SQL 约束；不连接用户现有库。
4. **费用：** 原 `cost_usd` 保留美元语义。无可信美元费用就为 null；人民币估算、缓存折扣推断、汇率折算不塞进现有字段。本期网页可显示未知，不引入新计费实体；预算证据保存在 owner 私有验收记录。
5. **持久证据：** 原批准、取消、过期恢复/重试与排行榜/保留逻辑不变。新增网络/工具/限制版本须纳入既有可比性校验，旧结果不可被新配置覆写。

## 5. 05 开工必须冻结的安全候选

这些不是新的业务问卷。执行者先查固定源码、以假值证明技术事实；若实现不了已批准边界，再带证据请求方向决定。

- 私有文件候选：仓库之外 owner 选择的普通目录下的 `providers.json`，结构版本1，有限逻辑 profile 到 provider/key 的映射；不含任意上游 URL。权限只允许 owner 和必要系统主体，拒绝链接、共享/同步目录和宽读权限。实际绝对路径不进 Git，未确认该文件存在。
- 读取范围：只读取当个已批准 Run 需要的 profile；Web/提交/审批不读；环境变量最多携带文件定位，绝不携带 Key。缺文件/权限/账户匹配时失败关闭，错误不回显路径/Key。
- 候选网络：每 Trial 一条仅做题侧与代理可达的内部网，代理另有受控出网；无共享 PID/FS、主机端口/socket/可写宿主挂载。DNS、IPv6、代理直连绕过与宿主网关路径须分别验证，不能只测 HTTP 正常。
- 候选预算：私有、非秘密的验收额度账本记录不可复用 Run 配额和已预留上界，写入原子、单作用域锁；代理重启/崩溃无法确认余额则关闭该 Run，不发新满额。账本不包含 Key/令牌，不替代 Job Repository，不自动发起任务，不建设账单平台。
- Token 上界、请求字段白名单和账本具体格式尚未验证。05 行动须冻结实际方案、风险和正反测试；若需要新的持久表/公共端口/长期服务，必须先请用户确认新增范围。

## 6. 权威文档同步点

| 变化 | 唯一技术事实源 | 何时更新 |
|---|---|---|
| 新模块边界/内部树/依赖 | [总架构](../../docs/architecture/ARCHITECTURE.md) | 规划现在标候选；每项实现后更新实际树 |
| 身份、快照、迁移、可比性 | [数据模型](../../docs/architecture/DATA_MODEL.md) | 04/05 冻结方案及实现时同步 |
| 原接口责任与错误边界 | [模块契约](../../docs/architecture/MODULE_CONTRACTS.md) | 04–07 契约测试之前 |
| options/preset/公开请求与结果 | [HTTP API](../../docs/interfaces/HTTP_API.md) | 02–07 行为发生变化的同一切片 |
| Key/网络/代理/限额 | [认证接口](../../docs/interfaces/CODEX_AUTHENTICATION.md) | 05 合同冻结、各轮安全验证之后 |
| 固定 Codex/Harbor/Fork 绑定 | [执行接口](../../docs/interfaces/HARBOR_EXECUTION.md)、[框架接口](../../docs/interfaces/FRAMEWORK_INTERFACES.md) | 04–07 实际接线与证据变化时 |
| 数据/镜像/模型身份 | [依赖总表](../../docs/dependencies/DEPENDENCIES.md) | 候选入选与核验通过时；未取得 digest 不伪填 |
| 当前阶段、停点、授权 | [HANDOFF](../../HANDOFF.md) | 每阶段停止时 |

专题权威文档维护当前合同；计划维护实施步骤，规格维护业务要求，行动维护每轮结果。各处只交叉引用，不复制价格表和历史测试数量。
