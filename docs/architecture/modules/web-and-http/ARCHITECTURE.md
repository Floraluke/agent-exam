# Web 与 HTTP Module

> 当前状态：M1 身份、目录、Job、批准、取消/恢复、报告、证据和排行榜的 Next.js/FastAPI 路径已实现；六题/continuous 向导与跨批次对比页面已接入。统一浏览器安全头、可关联的安全 500、比较请求竞态防护和 ESLint 质量门禁已补齐。Tailscale 双机负向/VPN/离线及任务 05 provider 端到端呈现仍未完成。
> 权威范围：浏览器、Next.js 和 FastAPI 怎样交接，以及当前页面/路由实现位置。
>
> 配套文件：[接口索引](interface.md)（调用面硬规则与端点族清单）、[进展与未决项](progress.md)、[任务 03 总行动](actions/03-report-catalog.md)。架构事实只在本文维护，那几份不复制。

## 1. 职责与非职责

Web 向 owner 与 collaborator 提供同一个私有站点；FastAPI 把 HTTP 请求翻译成应用用例调用并统一处理认证、输入和错误。Next.js 只把同源 `/api/v1` 转发到本机回环 FastAPI。

本 Module 不直接连接 PostgreSQL/MinIO，不接触 Docker/Harbor/Worker 或模型秘密，不在浏览器计算权威状态，也不因隐藏按钮替代服务器权限检查。

## 2. Interface 与不变量

- 浏览器只请求站点同源 `/api/v1/*`；`credentials: same-origin`，非只读请求带固定写入标记。
- Next.js 的上游目标只接受 `http://127.0.0.1:<port>`，拒绝带凭据、路径或远端主机的地址。
- FastAPI 的正式 `public_origin` 必须是 HTTPS；明文 HTTP 只允许显式本机回环开发。
- 会话 Cookie、同源写入检查、登录限速、`no-store`、`nosniff`、frame/referrer/permissions 策略在 HTTP delivery 统一实施；Next.js 另设 CSP。
- 未预期 HTTP 异常只向客户端返回通用错误，并以同一个 `request_id` 关联不含正文/header/异常消息的服务端结构化日志。
- FastAPI 返回稳定领域错误码；Web 将未知/畸形响应收敛为不可用，而不猜测成功。
- 后端未注册 API 的业务能力不在产品 UI 中显示按钮或交互；导航、菜单、URL 和向导步骤等本地动作不得声称业务事实已改变。

路由、DTO、Cookie、错误及当前 32 项已注册端点清单由[HTTP Interface](../../../interfaces/HTTP_API.md#21-当前前后端-api-清单已注册可由产品-ui-使用)维护。任务 02/03 的逐控件页面契约由[实现地图](../../../../.scratch/ui-catalog-providers/implementation-map.md#21-任务-0203-的逐控件契约门槛)维护。

## 3. 当前 Implementation 文件树

```text
apps/backend/src/eval_platform/delivery/http/
  app.py                              # FastAPI Composition Root、middleware、路由装配
  config.py                           # public origin 与 PostgreSQL 环境配置
  security.py                         # 同源写入、速率限制、安全响应头和 500 关联日志
  errors.py                           # 领域/依赖错误 → 稳定 HTTP 错误码
  schemas.py / *_schemas.py           # 公共 DTO
  routes/
    identity.py                       # 登录、登出、当前 actor
    membership.py                     # 邀请和成员管理
    catalog.py                        # 任务/配置目录
    jobs/                             # 提交、查询、批准、取消、恢复和报告
      reporting/                     # 跨批次比较 GET 与稳定 DTO
    artifacts.py                     # 制品正文和轨迹
    leaderboard/                     # 基础排行榜
apps/web/
  next.config.ts                      # 受限 rewrite、隔离构建目录与浏览器安全头/CSP
  eslint.config.mjs                   # ESLint 9 flat config 与 Next/TypeScript 规则
  src/app/layout.tsx                  # 页面根布局
  src/app/page.tsx                    # 会话入口；身份恢复后进入 A 工作台
  src/app/globals.css                 # A 版设计变量、固定侧栏和 390/360 响应式样式
  src/features/identity/              # 会话、加入和成员 UI
  src/features/catalog/               # 任务/配置目录 UI
  src/features/workbench/
    shell.tsx                         # URL 可恢复导航、角色边界和移动端菜单
    dashboard.tsx                     # 当前可见页与 owner 待审批/执行/异常状态分组
  src/features/jobs/
    listing/                          # 服务端筛选、游标页栈、详情/列表 URL 组合、对比勾选与「对比所选」
    wizard/                           # 三步选择、提交幂等和选项重读
    reporting/                        # 对比页、矩阵、钻取、冻结配置和按需用量
    *.tsx                             # 批准、详情、取消、恢复、报告和证据 UI
  src/features/leaderboard/           # 基础排行榜 UI
  src/lib/api-client.ts               # 同源 fetch、错误和 actor 校验
  src/lib/reporting/                   # 比较响应校验、有限并发详情/报告读取
  src/lib/*-client.ts                 # 各 HTTP 子域客户端
  src/lib/*-shapes.ts                 # 运行时响应形状校验
  tests/support/workbench.ts          # 既有验收通过可见导航进入 A 工作台页面
  tests/workbench/                    # 角色、导航、摘要、向导、列表、分页和手机验收
  tests/reporting/                    # 对比、混合结果、手机钻取和权限验收
  tests/*.spec.ts                     # 既有身份、目录、Job、报告和排行回归
  tests/run-browser-tests.mjs         # HTTPS 证书门禁、Next 生成文件快照/恢复与 Playwright 启动
```

`src/features/` 是 Web Implementation 的按用户任务组织方式，不表示每个目录都是独立后端 Module。`page.tsx` 仍以 `SessionPanel` 作为唯一会话门禁；可信 Actor 进入 `WorkbenchShell` 后才按 `view`/`job` 查询参数组合页面。`workbench` 是 Web Module 内部的深 Module，只编排现有 feature 与 HTTP 客户端，不形成第二套业务规则。

## 4. 关键数据流

```text
协作者浏览器
  → Tailscale Serve HTTPS（候选正式入口）
  → 127.0.0.1 上的 Next.js
  → 同源 /api/v1 rewrite
  → 127.0.0.1 上的 FastAPI
  → application 用例
  → ports / Adapter
```

耗时评测不会占住 HTTP 请求：提交只创建待批准 Job，批准只入队，Worker 之后从 PostgreSQL 领取。页面轮询或刷新服务器事实，不直接驱动 Docker。

A 工作台的数据流是：侧栏/移动菜单只修改 `view`；列表筛选把 `job_status`/`job_mine` 保存在 URL 并调用 `GET /jobs`；选择 Job 后增加不透明 `job` 并调用详情；三步向导只在浏览器保存未提交选择，最终通过 `POST /jobs` 创建并再次 `GET /jobs/{id}`。owner 决定、取消、恢复和重试成功后同样重读详情，不把乐观页面状态冒充服务器完成。

对比页的数据流是：`view=reports` 先读取当前 actor 可见的 Job 首屏；用户选择后由比较端点返回权威五档矩阵，再以最多 3 个并发详情请求读取冻结配置。用量默认不请求；用户点击后只读取有报告路径的 Run，最多 3 个并发，并把缺失或 `null` 保持为未知。单元格钻取复用既有 Run 报告、轨迹和制品下载，不创建第二套证据规则。

## 5. 模式、依赖和深度

FastAPI routes 是 HTTP Adapter，Next.js 客户端是浏览器侧 Adapter；真正的业务 Interface 位于 application Module，而非路由函数。Composition Root 一次装配用例与 PostgreSQL/MinIO Adapter，使路由保持翻译职责。

Web 依赖 HTTP Interface，不依赖后端源码目录或数据库 schema。所有业务权限必须在应用/HTTP 服务器再次判断，前端隐藏仅改善体验。

## 6. 当前验证与缺口

各 M1 任务的 HTTP/浏览器历史证据见对应行动文档；私有入口当前进展见[远程验收行动](../../../actions/2026-09-14-m1-private-remote-acceptance.md)。历史数字不反向改写；当前核心修复已实际通过 ESLint（零 warning）、TypeScript、Next 生产构建及使用系统 Chrome 的 45 项 Playwright 回归，最终整体验证以当前[修复行动](../../../actions/2026-09-21-core-diagnostic-remediation.md)为准。当前注册端点仍为 32 项。

扩展任务 03（对比报告的契约、后端与 Web 页面）及任务 04 的六题/连续向导已经完成；任务 03 的三个子行动均已收口，本地增强证据见[对比报告 UI 行动](../../../actions/2026-09-21-ui-comparison-report.md)。任务 04 的 B 切片覆盖三步向导在六题与 `continuous(1–20)` 规模下的浏览器动线和网页读取面暴露扫描；任务 05 的 B 切片覆盖必要错误呈现通道审计、§10.2 字段内容约束，以及受控失败码/提供方值的契约对齐。

核心修复为比较加载增加请求代次，使清空或切换选择后迟到响应不能覆盖当前页面；浏览器回归覆盖该竞态。任务 05 的受控失败码已经写入 HTTP 契约，但 provider 策略尚未接入 Worker/HTTP 执行路径，所以“受控文案忠实呈现、未知错误码失败关闭”仍是端到端待办，不能用内部异常单测替代；后者还需给浏览器夹具增加“强制下一次响应出错”的控制端点。其余待完成项是完整 Tailscale 双机负向/VPN/离线验收与 20 列量级的人工滚动手感。任务 02–05 的 B 切片没有新增接口、数据库表、Worker/模型或部署行为；`GET /api/v1/reports/comparisons` 由 `7553ce0` 交付，不在 B 的改动内。当前远程接入规则见[远程接入](../../../operations/REMOTE_TEAM_ACCESS.md)，部署事实见[所有者单机运行](../owner-host-runtime/ARCHITECTURE.md)。
