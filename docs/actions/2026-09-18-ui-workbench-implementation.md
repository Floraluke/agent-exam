# 任务 02：A 版 Web 工作台真实闭环

> 状态：Completed。任务 02 的实现、全量浏览器回归、类型检查、生产构建、响应式截图、API 清单核对及 Standards/Spec 双轴评审均已完成；任务 03 未启动。

## 状态与情况说明

- 来源请求：用户在 `fengyy-fixweb` 分支选择纯 A「侧栏工作台」后，明确要求开始任务 02。
- 当前基准：分支 `fengyy-fixweb`，HEAD `625d02b`。任务 01 的规格、计划、实现地图、任务单、团队分工与 HANDOFF 增量尚未提交；本任务保留这些变化。
- Module 定位：深化现有「Web 与 HTTP」Module。Next.js 页面和浏览器侧 HTTP Adapter 负责呈现与请求；FastAPI、application 用例、Repository 与现有权限/幂等规则保持权威，不新增平行业务链。
- 已确认产品方向：正式 UI 采用纯 A 侧栏工作台；owner 与 collaborator 使用角色化首页；提供真实评测列表、三步提交、详情、批准/拒绝、取消、恢复/重试及手机完整操作。
- 已确认测试 seam：一是浏览器中用户可观察的 A 版流程，二是既有 `/api/v1` HTTP 行为。测试不调用 React 私有函数，不通过数据库旁路验证页面结果。
- 契约门槛：每个按钮、链接、表单提交、筛选、分页和可操作状态必须映射到前端处理、HTTP/后端契约、权限、错误、成功后状态与测试；纯前端动作明确标注“无后端请求”。
- 真实性硬规则：后端未提供现存 API 的业务能力不展示按钮或页面交互，不用前端假数据、假成功或占位动作造成“任务已完成”的误解；纯导航、菜单和向导步骤只改变本地 UI，且不声称改变业务事实。
- 明确排除：不新增题目或配置规模，不实现任务 03 的完整对比报告/目录管理重做，不接 DeepSeek/Kimi，不运行真实 Worker/模型，不修改数据库 schema，不部署、不推送。
- 工作区保护：不读取、不修改、不清理与本任务无关的未跟踪 `docs/actions/2026-09-18-unified-local-env.md`，也不覆盖用户或既有混合增量。

## 实施措施

1. 发布本地任务 02，并在实现地图中完成 A 版逐控件契约表；找不到现有契约的动作先标缺口，不写代码绕过。
2. 以现有会话和 HTTP 客户端为 seam，先写失败的浏览器行为用例，覆盖角色化首页、侧栏导航、列表/详情、三步向导选择保持与提交。
3. 最小实现 A 版工作台壳、角色首页和 URL 可恢复导航；登出清理私有页面状态，移动端提供不被截断的导航和主操作。
4. 按纵向切片接入列表筛选/游标、提交幂等、owner 批准/拒绝、提交者取消、owner 恢复/新建重试；写操作成功后重新读取服务器事实。
5. 覆盖未登录、协作者无 owner 控件、空列表、错误响应、重复点击、刷新链接、会话过期和移动端布局；服务器继续承担最终权限判断。
6. 同步 Web Module 架构树、任务/计划/HANDOFF 与实际实现；完成 Standards/Spec 双轴评审，修复并复验后停在任务 02，不自动开始任务 03。

完成标准：A 版正式页面连接现有后端；两角色核心流程可在桌面和 390/360 手机完成；逐控件契约无空项；HTTP 身份、越权与幂等语义不变；类型检查、构建、定向及全量浏览器检查按可用环境通过；产品代码不直接依赖后端源码或存储。

## 受影响文件树

```text
docs/actions/
└─ 2026-09-18-ui-workbench-implementation.md     # 本行动：范围、红绿证据、验证和停点
docs/architecture/modules/web-and-http/
└─ ARCHITECTURE.md                               # 同步 A 版实际文件树、依赖和交互 seam
docs/interfaces/
└─ HTTP_API.md                                   # 增加当前注册端点与 Web 调用位置总清单
.scratch/ui-catalog-providers/
├─ implementation-map.md                        # A 版逐控件前端/HTTP/后端映射
├─ plan.md                                      # 任务 02 实际状态与停点
└─ issues/
   └─ 02-role-workbench-submission-approval.md   # 本地任务单与验收项
apps/web/src/
├─ app/{page.tsx,globals.css}                    # A 版入口与响应式设计系统
├─ features/identity/session.tsx                 # 会话门禁与登录/登出组合
├─ features/workbench/
│  ├─ shell.tsx                                  # A 版壳、URL 导航、角色边界与移动菜单
│  └─ dashboard.tsx                              # 当前可见页与 owner 待批/执行/异常分组
├─ features/jobs/
│  ├─ listing/{labels,view,workspace}.tsx         # 服务端筛选、不透明游标与详情/列表组合
│  ├─ wizard/view.tsx                            # 三步选择、服务端选项、幂等提交与详情重读
│  └─ {controls,submit}.tsx                      # 既有生命周期动作和向导兼容入口
├─ features/leaderboard/view.tsx                 # 来源 Job 链接回到 A 版详情
└─ lib/job-client.ts                             # 参数化列表 Adapter；保持运行时响应校验
apps/web/tests/
├─ support/workbench.ts                          # 既有验收通过可见侧栏进入目标页面
├─ workbench/
│  ├─ task-02.spec.ts                            # 首页、目录、向导、提交/审批主路径
│  ├─ roles.spec.ts                              # collaborator 角色边界
│  ├─ pagination.spec.ts                         # 筛选与不透明游标前后翻页
│  ├─ dashboard.spec.ts                          # 真实状态分组、当前页声明与桌面截图
│  ├─ navigation.spec.ts                         # 排行榜、取消和登出 URL 状态
│  ├─ mobile.spec.ts                             # 390/360 菜单、向导和无溢出检查
│  └─ submission-resilience.spec.ts              # 新建历史隔离、重复锁定与幂等重试
└─ {artifact-retention,catalog,jobs,...}         # 既有验收改由 A 壳的可见导航到达
HANDOFF.md                                       # 同步任务 02 当前真实停点
```

设计关系：`workbench` 是 Web Module 内部的深 Module，Interface 只接收可信 Actor 与页面动作，Implementation 组合现有 feature；`job-client.ts` 是浏览器侧 HTTP Adapter。FastAPI routes 仍是 HTTP Adapter，application 用例仍是业务 Interface。本轮未新增后端 Module、公共 Interface、数据库表或目录。

## 自验证方式

- 红→绿：`npm run test:e2e -- workbench/task-02.spec.ts`；每个用例先确认因缺少目标行为失败，再做最小实现并复验。
- 静态：`npm run typecheck`、`npm run build`；成功标准为退出码 0，无 TypeScript 或 Next 构建错误。
- 浏览器：`npm run test:e2e`；现有身份、成员、目录、Job、恢复、证据、排行、保留清理及新增工作台用例全部通过。
- HTTP：仅在前端实现暴露现实契约差异时运行后端定向 HTTP 测试；不为纯布局修改制造后端变更或重型数据库运行。
- 人工/结构：核对 1440、390、360 宽度，主导航/提交/审批不截断；逐控件表与实际 DOM/请求一致；动态语言源文件默认不超过 200 行，每层目录不超过 8 个文件。
- 边界：`git diff --check`，确认无 `apps/backend`、schema、真实凭据、模型调用、部署或无关文件变化。

## 自验证结果

- 第一个定向浏览器命令在普通沙箱因 Windows `EPERM` 无法创建结果目录/启动子进程，属于检查基础设施失败，未到达页面断言；获准受控运行后后端与 Next.js 可启动。
- 受控运行第一次仍因 Playwright bundled Chromium 不存在而失败，属于本机测试依赖缺失；项目配置已有 `AGENTEXAM_USE_SYSTEM_CHROME=1` 后备路径，改用已安装 Chrome，未下载浏览器或修改配置。
- A 壳红灯成立：使用 system Chrome 后，新用例因找不到“所有者工作台”在目标断言失败，证明测试能检测任务 02 尚未实现。
- 之后按纵向切片依次得到并消除以下红灯：目录入口缺失、三步向导缺失、提交后 URL 未进入详情、列表缺失、协作者角色边界、游标分页、真实首页摘要、排行榜/取消/登出导航、移动菜单、取消目的地和筛选回退。每个目标用例都在失败后做最小实现并复验；角色切片曾发现测试把 `Page` 当 `Locator`、中断恢复曾发现测试未等待批准响应，两处均只修正测试同步方式，没有为通过测试改业务规则。
- 新增 11 条任务 02 浏览器用例；既有验收改为从 A 版可见导航进入原页面。最终完整 `npm run test:e2e` 为 `32 passed`：身份、成员、目录、Job、报告/证据、取消/恢复、排行榜、保留清理、工作台状态分组、新建历史隔离与幂等失败重试全部通过。
- `npm run typecheck` 最终退出码 0。早期生产构建曾分别因沙箱用户配置 `EPERM` 和跨盘临时 rename `EXDEV` 失败；最终设置 `NEXT_TELEMETRY_DISABLED=1` 并在获准环境运行 `npm run build`，退出码 0，根路由产物为 20 kB、First Load JS 123 kB。环境失败均未描述为产品通过。
- 390 与 360 viewport 的浏览器断言均确认页面宽度不溢出；人工查看桌面证据 `runtime/tests/task-02-workbench-desktop.png` 和 390 手机证据 `runtime/tests/task-02-workbench-mobile-390.png`，固定侧栏/移动菜单、向导和主操作未被截断。截图中的 Next 开发指示器只来自测试开发服务器，不是产品控件。
- 当前 FastAPI 实时 OpenAPI 与 [HTTP API 清单](../interfaces/HTTP_API.md#21-当前前后端-api-清单已注册可由产品-ui-使用)逐项比较：文档 31、OpenAPI 31、差异 0。清单同时明确未注册的 Agent 源码提交、人工复核、通用 Run 查询/创建和制品删除不得出现产品按钮。
- 文件指标检查：排除依赖目录后，本轮 TypeScript/TSX/CSS/MJS 均未超过 200 行；`jobs` 根层 8 个文件，`listing` 3 个、`workbench` 2 个、`tests/workbench` 7 个、`tests/support` 1 个，均未超过每层 8 个文件。
- `git diff --check` 未发现空白错误，只报告工作区既有 LF→CRLF 提示。本轮没有修改 `apps/backend`、数据库 schema、Worker、模型、部署、凭据或无关的 `%USERPROFILE%` 缓存；没有提交或推送。
- 双轴初审发现并修复：把无排序保证的页误称“最近”、新建页夹带旧 Job 控件、owner 首页缺执行/异常分组、幂等失败重试缺行为测试，以及实现地图候选树过期。第二轮复审又补齐直接 `view=new&job=...` 的 URL 归一化和待批准页数声明；对应断言均先红后绿。
- 最终 Spec 复审为 PASS；Standards 原 3 项 hard finding 均关闭，最终只保留“URL 读写分散”的 Shotgun Surgery 判断项并记录到实现地图，不在本任务扩大成路由重构。最终 32 条浏览器回归、类型检查、生产构建、31/31 API 对账及 `git diff --check` 均通过或仅有行尾提示；任务 03 保持未发布、未授权。
