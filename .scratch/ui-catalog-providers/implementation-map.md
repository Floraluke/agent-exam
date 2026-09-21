Status: needs-info

# 实现地图与文档联动

> 标签只表示 03–08 的产品阶段仍待后续任务确认；任务 02 已实现。2026-09-20 已先行落地 continuous 规模和跨批次比较后端，但 Web 对比页、五道新题及真实矩阵验收仍未完成。

> 供[执行计划](plan.md)按阶段读取。任务 02 的逐控件契约和实际 Web 文件树已按 2026-09-18 工作区回填；03–08 标有“候选”的内容仍只供后续审阅。后续实现前继续回读源码、锁定当时 HEAD，不得按候选地图重造平行链。

## 1. 责任边界

Web 只改善呈现与交互，复用唯一请求客户端与现有 HTTP；Task Catalog 负责受控题目，Agent Registry 负责受控配置，Job Submission 冻结矩阵及策略，Job Repository 保持事务/幂等/权限，Worker 领取已批准 Job。ExecutionBackend 的 Harbor Adapter 继续执行，PatchEvaluator 的固定 Fork Adapter 继续独立判卷。

本次不新增顶层 Module、公共业务 Interface 或数据库表。代理是 Execution Adapter 内部实现：现有网络侧车只做网络过滤，不能承载秘密注入与预算结算，所以需要专属内部代码和隔离进程。方向已批准；下列精确目录/形状仍是候选，正式实施前确认，不以“内部重构”跳过批准。

设计模式保持 **Adapter（适配器）**：Harbor/Fork 实现原端口；Worker 组合根装配可信私有绑定；内部 provider 配置选择器从有限预设挑选绑定，不接受提交者自定义服务地址。无新的代理业务 API、任务队列或判卷实现。

## 2. 按阶段必读的现有入口

相对路径从仓库根开始；链接仅指向本轮实际存在的源码。每行的相关测试须继续跟读其夹具和错误路径。

| 阶段 | 现有入口与职责 | 相关验证入口 |
|---|---|---|
| 01–03 | [会话壳](../../apps/web/src/features/identity/session.tsx)、[提交与动线](../../apps/web/src/features/jobs/submit.tsx)、[批次报告](../../apps/web/src/features/jobs/batch-report.tsx)、[单次报告](../../apps/web/src/features/jobs/report.tsx)、[Job 客户端](../../apps/web/src/lib/job-client.ts)：替换长页组织，复用鉴权请求；后端已有 `GET /api/v1/reports/comparisons`，Web 尚无客户端或页面 | [浏览器运行器](../../apps/web/tests/run-browser-tests.mjs)、[Web 包脚本](../../apps/web/package.json)、[比较 HTTP/矩阵测试](../../apps/backend/tests/jobs/reporting/) |
| 04 题目 | [受控种子](../../apps/backend/src/eval_platform/delivery/catalog_presets.py)、[Task Source](../../apps/backend/src/eval_platform/adapters/tasks/swe_gym.py)、[目录用例](../../apps/backend/src/eval_platform/application/task_catalog.py)：固定 Parquet/镜像和公开/隐藏数据分离 | [目录 HTTP](../../apps/backend/tests/catalog/test_http.py)、[一致性](../../apps/backend/tests/catalog/test_consistency.py)、[Fork 集成](../../apps/backend/tests/integration/test_swe_bench_integration.py) |
| 04 规模 | [策略组合](../../apps/backend/src/eval_platform/delivery/job_presets.py)、[领域策略](../../apps/backend/src/eval_platform/domain/jobs/policy.py)、[提交用例](../../apps/backend/src/eval_platform/application/job_submission.py)、[Repository](../../apps/backend/src/eval_platform/adapters/persistence/jobs/repository.py)：服务端边界与冻结事务 | [提交 HTTP](../../apps/backend/tests/jobs/test_http.py)、[并发](../../apps/backend/tests/jobs/test_concurrency.py)、[真实 PG](../../apps/backend/tests/jobs/test_postgres.py)、[恢复](../../apps/backend/tests/jobs/recovery/test_retry.py) |
| 05–07 配置 | [配置身份](../../apps/backend/src/eval_platform/domain/agent.py)、[Registry](../../apps/backend/src/eval_platform/application/agent_registry.py)、[目录 SQL](../../apps/backend/src/eval_platform/adapters/persistence/catalog/schema.sql)、[配置 Repository](../../apps/backend/src/eval_platform/adapters/persistence/catalog/agents.py)：当前只接受旧 ChatGPT 的约束需扩展 | [目录安全](../../apps/backend/tests/catalog/test_security.py)、目录 HTTP/PG/一致性测试 |
| 05–07 执行 | [Worker 组合](../../apps/backend/src/eval_platform/delivery/worker/runtime.py)、[编排](../../apps/backend/src/eval_platform/application/execute_job.py)、[Harbor 配置映射](../../apps/backend/src/eval_platform/adapters/execution/harbor/config_mapper.py)、[引导入口](../../apps/backend/src/eval_platform/adapters/execution/harbor_entry.py)：按冻结 Run 解析秘密绑定 | [Worker 测试](../../apps/backend/tests/jobs/runtime/test_worker_runtime.py)、[矩阵编排](../../apps/backend/tests/jobs/execution/batch/test_orchestrator.py)、[租约预算](../../apps/backend/tests/jobs/execution/batch/test_lease_budget.py) |
| 05 安全 | [Codex guard](../../apps/backend/src/eval_platform/adapters/execution/codex/agent.py)、[权限策略](../../apps/backend/src/eval_platform/adapters/execution/codex/policy.py)、[私有上传](../../apps/backend/src/eval_platform/adapters/execution/codex/uploads.py)、[网络](../../apps/backend/src/eval_platform/adapters/execution/network.py)、[清理](../../apps/backend/src/eval_platform/adapters/execution/harbor/lifecycle/cleanup.py) | [完整假 Trial](../../apps/backend/tests/test_codex_trial.py)、[网络合同](../../apps/backend/tests/contract/test_execution_network.py)、[秘密测试](../../apps/backend/tests/test_secret_safety.py)、取消/恢复测试 |

04 必须继续读取 Job snapshots/factory、PG records/state_validation 与报告可比性校验，避免仅修改 options 后被旧读出校验拒绝。05 必须继续读取 Harbor process_runner/result mapper 与 Codex 安装约定，不用独立脚本绕开正式链。

### 2.1 任务 02–03 的逐控件契约门槛

任务 02 已按页面和角色落实完整交互清单；任务 03 开始前沿用同一门槛。每一项必须记录：可见/禁用条件、用户意图、前端事件与状态、URL 行为、HTTP 方法/路径/查询/body/Header、响应解析器、FastAPI 路由、Application 用例与持久化端口、权限与前置状态、稳定错误、成功后的重新读取/导航、浏览器及 HTTP 测试。导航、抽屉开关、向导前后步等纯客户端动作必须写“无后端请求”，不能留空。

以下是从当前源码和 [HTTP API](../../docs/interfaces/HTTP_API.md)核对出的可复用基线，不是对未来页面新增接口的授权：

| A 版交互族 | 前端契约 | HTTP/后端契约 |
|---|---|---|
| 会话恢复、登录、登出 | `api-client.ts` 的 `currentActor/login/logout`；Actor 运行时校验，未知形状关闭为 `UNAVAILABLE` | `GET /api/v1/auth/me`、`POST /api/v1/auth/login`、`POST /api/v1/auth/logout` → `routes/identity.py` |
| 新建向导加载选项、提交 | `job-client.ts` 的 `jobOptions/submitJob`；提交期间锁定动作并复用同一未决幂等键 | `GET /api/v1/job-options`、`POST /api/v1/jobs` + `Idempotency-Key` → `routes/jobs/routes.py` → Job Submission |
| 列表、详情与刷新 | `jobs/jobDetail`；返回值经 `parseJobPage/parseJobDetail` 校验 | `GET /api/v1/jobs`、`GET /api/v1/jobs/{job_id}` → `routes/jobs/routes.py` → Job Repository 查询 |
| 批准、拒绝、取消 | `decideJob/cancelJob`；写请求携带 `Idempotency-Key`，成功后重新读取服务端事实 | `POST /api/v1/jobs/{job_id}/approve|reject|cancel` → `routes/jobs/routes.py` → 生命周期用例/Repository |
| 中断收束、新建重试 | `recoverJob/retryJob`；retry 使用新幂等键，返回新 Job 后按新标识导航 | `POST /api/v1/jobs/{job_id}/recover|retry` → `routes/jobs/lifecycle/routes.py` → Recovery/Retry 用例 |
| 批次报告、单 Run、制品、轨迹 | `jobReport/runReport/runArtifacts/runTrajectory`；各自运行时解析，缺失不伪造 | `GET /api/v1/reports/jobs/{job_id}`、`GET /api/v1/reports/runs/{run_id}`、`GET /api/v1/runs/{run_id}/artifacts|trajectory` → report/artifact routes |
| 跨批次比较 | **Web 尚未接入**，因此当前没有按钮或假结果；任务 03 实施时先补客户端解析和逐控件契约 | `GET /api/v1/reports/comparisons?job_ids=...` → `routes/jobs/reporting/comparisons.py` → `JobReporting.compare` / `matrix.py` |
| 侧栏导航、移动抽屉、向导上一步/下一步 | React 路由或组件内状态；保留可分享 URL、前进后退与选择 | **无后端请求**；浏览器测试断言不产生网络写入 |

控件隐藏不等于授权：协作者看不到 owner 动作，但服务器仍是最终权限边界。任何未在当前接口文档和源码中找到的行为先标“接口缺口”；若要新增公共 Interface、Module 或表，按项目规则说明现有能力为何不能承载并取得用户确认后再继续。

### 2.2 任务 02：A 版逐控件契约清单

下表冻结任务 02 正式页面的控件责任。产品 UI 不得为缺少现存后端 API 的业务能力设置按钮、交互、假数据或假成功状态；发现接口缺口时不展示对应业务控件并报告，不由前端模拟完成。`HTTP` 写“无”只允许改变可见状态、URL 或向导步骤且不得声称业务事实已改变；它必须由浏览器测试断言不会产生写请求。动态 `{id}` 按 [HTTP API](../../docs/interfaces/HTTP_API.md)作为不透明值编码，不从 UUID 推断时间或顺序。

| 页面与控件 | 前端处理 / URL | HTTP Interface | 后端与权限 / 完成后状态 | 验证 |
|---|---|---|---|---|
| 登录：`登录` | 校验原生表单、锁定重复提交；成功保存可信 Actor | `POST /api/v1/auth/login` | IdentityService；任何角色可登录；失败显示稳定错误，成功进入角色首页 | identity 浏览器 + task-02 首页 |
| 登录：`使用邀请码加入` / `返回登录` | 在登录与加入表单间切换并清空一次性提示 | **无** | 无后端请求、无身份变化 | 浏览器断言零写请求 |
| 加入：`加入平台` | 提交后清空 Token/密码并回登录 | `POST /api/v1/invitations/redeem` | MembershipService；成功只建立 collaborator，随后仍需登录 | membership 浏览器 |
| 全局：品牌/侧栏导航 | 设置 `view=home|jobs|new|tasks|agents|members|leaderboard`；保留 `job` 仅在详情 | **无** | 无后端请求；不可见 owner 导航不能替代服务器权限 | URL 前进/后退、刷新恢复 |
| 全局：`打开菜单` / `关闭菜单` | 只切换 390/360 移动侧栏；选中导航后关闭 | **无** | 无后端请求 | 两档移动 viewport |
| 全局：`退出登录` | 锁定动作；成功清空 Actor、当前视图和私有选择 | `POST /api/v1/auth/logout` | IdentityService 撤销当前会话；回到登录页 | identity + task-02 |
| 首页：`新建评测` / `查看全部评测` | 分别进入 `view=new` / `view=jobs` | **无** | 无后端请求 | 角色首页导航 |
| 首页：`刷新工作台` | 读取当前角色可见的第一页；owner 另按待批准、各执行状态、失败/部分出错状态分组读取 | `GET /api/v1/jobs?limit=5`；owner 再按 8 个既有 `status` 值分别请求 `limit=5` | Job Repository；协作者由服务器限制为本人；明确接口不保证创建时间排序，每组数量只是当前页 | 空、错误、两角色首页与状态请求审计 |
| 首页：Job 行 / `打开评测` | 写入 `view=jobs&job={id}` 并读详情 | `GET /api/v1/jobs/{id}` | Job Repository；不可见与不存在统一 404 | owner 优先分组与 collaborator 可见页 |
| 评测列表：状态、范围筛选 / `应用筛选` | 生成 `status`、owner 可选 `created_by`；重置 cursor 历史 | `GET /api/v1/jobs?status=&created_by=&limit=20` | Job Repository；协作者即使伪造 created_by 仍只能看到自己 | 筛选、越权空页、失效输入 |
| 评测列表：`清除筛选` / `刷新列表` | 清空后读第一页，或用当前筛选/当前 cursor 重读 | 同上 | 服务器事实覆盖页面缓存；不猜总数 | 空列表、刷新保持条件 |
| 评测列表：`上一页` / `下一页` | 前端保存已访问 cursor 栈；按钮触发相应页 GET | `GET /api/v1/jobs?...&cursor={cursor}` | Job Repository 不透明游标；无前页时禁用 | 前后翻页、边界禁用 |
| 评测列表：`新建评测` | 进入 `view=new` | **无** | 无后端请求 | URL/焦点 |
| 评测列表：Job 行 / `查看详情` | 写入 `view=jobs&job={id}` 并读详情 | `GET /api/v1/jobs/{id}` | Job Repository 可见性；失败留在列表并提示 | 详情、刷新链接 |
| 三步向导：进入页面 / `刷新可选项` | 并行加载题目、启用配置和限制；剔除已失效选择 | `GET /api/v1/tasks?limit=100`、`GET /api/v1/agent-configurations?limit=100&agent_type=codex&enabled=true`、`GET /api/v1/job-options` | Task Catalog、Agent Registry、Job Submission policy；任一畸形响应整体失败关闭 | options 解析、空目录、错误 |
| 三步向导：任务/配置勾选、批次/限制选择 | 只更新当前会话内向导状态并重算 Run 数 | **无** | 无后端请求；上限提示来自服务端 options | 返回上步保持、空选择禁用 |
| 三步向导：`上一步` / `下一步` | 只变更 1–3 步；进入下一步前做页面可解释校验 | **无** | 无后端请求 | 步骤、焦点、选择保持 |
| 三步向导：`取消新建` | 清除向导私有选择并返回 `view=jobs` | **无** | 无后端请求 | 清理状态、刷新不恢复他人选择 |
| 三步向导：`提交并等待批准` | 同一未决正文复用幂等键；成功写 `view=jobs&job={id}` 并重读详情 | `POST /api/v1/jobs` + `Idempotency-Key`，随后 `GET /api/v1/jobs/{id}` | Job Submission → Job Repository；任何已登录角色可提交；只创建 `AWAITING_OWNER_APPROVAL` | owner/collaborator、重复点击、错误/超时 |
| 详情：`返回评测列表` | 移除 `job`，保留列表筛选 | **无** | 无后端请求 | URL 恢复 |
| 详情：`刷新当前批次` | 重读当前 Job；已打开批次报告时一并刷新 | `GET /api/v1/jobs/{id}`；可选 `GET /api/v1/reports/jobs/{id}` | Job Repository / Reporting；服务器状态覆盖缓存 | 状态推进、404/会话过期 |
| 详情：`批准并排队` / `拒绝批次` | 规范化说明；同一未决决定复用键；成功重读详情 | `POST /api/v1/jobs/{id}/approve|reject` + `Idempotency-Key`，随后详情 GET | OwnerApproval；仅 owner 且待批准；冲突后也重读服务器事实 | 自提交自批、双角色、并发冲突 |
| 详情：`取消批次` | 同一 Job/说明的未决请求复用键；成功重读详情 | `POST /api/v1/jobs/{id}/cancel` + `Idempotency-Key`，随后详情 GET | JobCancellation；owner 任意、collaborator 仅本人；请求态不冒充终态 | 待批/排队/执行、越权 |
| 详情：`检查并收束中断` | 仅租约到期且 owner 可见；成功重读旧 Job | `POST /api/v1/jobs/{id}/recover`，随后详情 GET | Recovery；不运行模型、不自动重试 | interruption-recovery 浏览器 |
| 详情：`新建重试批次` | 同一旧 Job 的未决请求复用键；成功导航新 Job 并重读 | `POST /api/v1/jobs/{id}/retry` + `Idempotency-Key`，随后新详情 GET | Retry；仅 owner/已收束终态；新 Job 重新等待批准 | 新旧 ID、再次批准 |
| 详情：`查看批次进度` | 读取并显示既有简版进度，不在任务 02 重做矩阵 | `GET /api/v1/reports/jobs/{id}` | Reporting；只读、保持缺失/故障语义 | 既有 job-batch 回归 |
| 批次进度：`查看 {任务}/{配置} 运行报告` / 详情：`查看单题运行报告` | 读取选中 Run；不猜测结果 | `GET /api/v1/reports/runs/{run_id}` | Reporting；只读，未知与缺失不填零 | 既有报告/证据回归 |
| 安全证据：下载补丁/摘要 | 浏览器同源下载，文件名固定为公开类型 | `GET /api/v1/artifacts/{artifact_id}/content` | Artifact route / Store；仅公开安全制品，权限与删除状态由服务器判断 | evidence/retention 回归 |
| 安全证据：`查看安全轨迹` / `加载更多轨迹` | 首次 after=0，后续使用返回的 next sequence 追加 | `GET /api/v1/runs/{run_id}/trajectory?after_sequence=&limit=100` | Artifact/trajectory 查询；不显示正文、工具参数或思维链 | evidence 回归 |
| 任务目录：登记、筛选、查看、刷新、下一页 | 复用现有 TasksPanel；筛选/分页只发受控 query | `POST /api/v1/tasks/register`；`GET /api/v1/tasks[/{id}]` | Task Catalog；登记仅 owner，查询为已登录用户 | 既有 catalog 回归 |
| 配置目录：登记、状态筛选、查看、禁用、刷新、下一页 | 复用现有 AgentsPanel；不提供 Key/URL 输入 | `POST /api/v1/agent-configurations[/{id}/disable]`；`GET /api/v1/agent-configurations[/{id}]` | Agent Registry；管理仅 owner，查询为已登录用户 | 既有 catalog 回归 |
| 成员：刷新、创建/关闭/撤销邀请、更多邀请、停用/更多成员 | 复用现有 MembersPanel；关闭邀请码只清本地一次性值 | `GET/POST /api/v1/invitations...`、`GET/POST /api/v1/members...`；`关闭邀请码`为**无后端请求** | MembershipService；整个页面仅 owner；Token 不写日志或 URL | 既有 membership 回归 |
| 排行榜：`查询排行榜` / `加载下一页` | 复用现有筛选与不透明 cursor；来源 Job 链接进入 A 版详情 | `GET /api/v1/leaderboard?...`；来源运行报告为报告 GET | Reporting；只读，不因 UI 改排名/分母 | 既有 leaderboard 回归 |

任务 01 的角色切换、场景切换、A/B/C 切换、演示 Toast 与“返回演示”均是原型专用控件，正式产品不实现，因此不映射任何生产 Interface。任务 02 当前可操作控件已全部列在本表；后续任务若新增控件，仍须先补契约行，再写测试和 Implementation。

## 3. 文件树：任务 02 实际结构与后续候选

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

### 02 Web 实际结构；03 Web 报告重组仍是候选

```text
apps/web/src/features/
├─ identity/session.tsx                     # 修改：保留会话与身份门禁，组合角色工作台
├─ workbench/                               # 已新增：Web 内部布局职责，不是新业务 Module
│  ├─ shell.tsx                             # 导航、当前视图、角色边界与移动布局
│  └─ dashboard.tsx                         # 当前可见页及 owner 待批/执行/异常状态分组
├─ jobs/
│  ├─ submit.tsx                           # 修改：详情与生命周期动作的薄组合
│  ├─ wizard/view.tsx                      # 已新增：选题、配置、复核、幂等提交
│  ├─ listing/{labels,view,workspace}.tsx  # 已新增：筛选、游标、列表/详情 URL 组合
│  ├─ reporting/                           # 任务 03 候选；任务 02 未创建
│  └─ lifecycle/recovery.tsx               # 修改仅动线：保留恢复和新 Job 语义
├─ catalog/{tasks,agents}.tsx               # 复用：目录管理，不增加秘密输入
└─ identity/members.tsx                     # 复用：服务器权限照旧
apps/web/src/lib/job-client.ts              # 修改：列表参数化/复用 request，保留 API 校验
apps/web/tests/support/workbench.ts          # 已新增：经可见 A 侧栏进入既有验收页面
apps/web/tests/workbench/                   # 已新增：桌面、手机、角色、导航、分页和韧性用例
apps/web/tests/jobs/                        # 已有：审批、取消、恢复等回归入口
```

当前 Web `jobs` 有 8 个直接文件；`workbench` 2 个文件，测试工作台目录 7 个文件。Web 任务 03 的 `reporting/` 仍是候选，不得从后端端点推断页面已经实现。后端比较路由现位于 `apps/backend/src/eval_platform/delivery/http/routes/jobs/reporting/`，使后端 `routes/jobs/` 直属文件维持 8 个；应用聚合位于 `application/reporting/matrix.py`。URL 读写目前散落在壳、列表组合、恢复和登出代码，是评审记录的 Shotgun Surgery 判断项；后续动导航时再收敛。

### 04 目录与规模

```text
apps/backend/src/eval_platform/
├─ adapters/tasks/swe_gym.py                 # 修改：用已资格验证的固定集合替代单题拒绝
├─ adapters/tasks/catalog.py                # 候选新增：instance -> 固定镜像身份清单
├─ delivery/catalog_presets.py              # 修改：新增已合格题的有限 preset
├─ delivery/job_presets.py                  # 已修改：continuous 1–20；旧预设区间不变
├─ domain/jobs/{policy,snapshots,factory}.py # 必要修改：验证、序列化、冻结哈希兼容
└─ adapters/persistence/jobs/               # 已有显式旧库约束升级；HTTP 启动不自动迁移
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
