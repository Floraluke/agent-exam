# Web 与 HTTP Module

> 当前状态：M1 身份、目录、Job、批准、取消/恢复、报告、证据和排行榜的 Next.js/FastAPI 路径已实现；扩展任务 02 的 A「侧栏工作台」、角色首页、列表/游标、三步提交和移动端菜单已落地。Tailscale 双机负向/VPN/离线验收仍未全部完成。
> 权威范围：浏览器、Next.js 和 FastAPI 怎样交接，以及当前页面/路由实现位置。
>
> 配套文件：[接口索引](interface.md)（调用面硬规则与端点族清单）、[进展与未决项](progress.md)、[任务 03 总行动](actions/03-report-catalog.md)。架构事实只在本文维护，那三份不复制。

## 1. 职责与非职责

Web 向 owner 与 collaborator 提供同一个私有站点；FastAPI 把 HTTP 请求翻译成应用用例调用并统一处理认证、输入和错误。Next.js 只把同源 `/api/v1` 转发到本机回环 FastAPI。

本 Module 不直接连接 PostgreSQL/MinIO，不接触 Docker/Harbor/Worker 或模型秘密，不在浏览器计算权威状态，也不因隐藏按钮替代服务器权限检查。

## 2. Interface 与不变量

- 浏览器只请求站点同源 `/api/v1/*`；`credentials: same-origin`，非只读请求带固定写入标记。
- Next.js 的上游目标只接受 `http://127.0.0.1:<port>`，拒绝带凭据、路径或远端主机的地址。
- FastAPI 的正式 `public_origin` 必须是 HTTPS；明文 HTTP 只允许显式本机回环开发。
- 会话 Cookie、同源写入检查、登录限速、`no-store` 和 `nosniff` 在 HTTP delivery 统一实施。
- FastAPI 返回稳定领域错误码；Web 将未知/畸形响应收敛为不可用，而不猜测成功。
- 后端未注册 API 的业务能力不在产品 UI 中显示按钮或交互；导航、菜单、URL 和向导步骤等本地动作不得声称业务事实已改变。

路由、DTO、Cookie、错误及当前 32 项前后端调用清单由[HTTP Interface](../../../interfaces/HTTP_API.md#21-当前前后端-api-清单已注册可由产品-ui-使用)维护；逐控件页面契约由[实现地图](../../../../.scratch/ui-catalog-providers/implementation-map.md#22-任务-02a-版逐控件契约清单)维护。

## 3. 当前 Implementation 文件树

```text
apps/backend/src/eval_platform/delivery/http/
  app.py                              # FastAPI Composition Root、middleware、路由装配
  config.py                           # public origin 与 PostgreSQL 环境配置
  security.py                         # 同源写入检查和登录速率限制
  errors.py                           # 领域/依赖错误 → 稳定 HTTP 错误码
  schemas.py / *_schemas.py           # 公共 DTO
  routes/
    identity.py                       # 登录、登出、当前 actor
    membership.py                     # 邀请和成员管理
    catalog.py                        # 任务/配置目录
    jobs/                             # 提交、查询、批准、取消、恢复和报告
    artifacts.py                     # 制品正文和轨迹
    leaderboard/                     # 基础排行榜
apps/web/
  next.config.ts                      # `/api/v1` → 回环 FastAPI 的受限 rewrite
  src/app/layout.tsx                  # 页面根布局
  src/app/page.tsx                    # 会话入口；身份恢复后进入 A 工作台
  src/app/globals.css                 # A 版设计变量、固定侧栏和 390/360 响应式样式
  src/features/identity/              # 会话、加入和成员 UI
  src/features/catalog/               # 任务/配置目录 UI
  src/features/workbench/
    shell.tsx                         # URL 可恢复导航、角色边界和移动端菜单
    dashboard.tsx                     # 当前可见页与 owner 待审批/执行/异常状态分组
  src/features/jobs/
    listing/                          # 服务端筛选、游标页栈、详情/列表 URL 组合
    wizard/                           # 三步选择、提交幂等和选项重读
    *.tsx                             # 批准、详情、取消、恢复、报告和证据 UI
  src/features/leaderboard/           # 基础排行榜 UI
  src/lib/api-client.ts               # 同源 fetch、错误和 actor 校验
  src/lib/*-client.ts                 # 各 HTTP 子域客户端
  src/lib/*-shapes.ts                 # 运行时响应形状校验
  tests/support/workbench.ts          # 既有验收通过可见导航进入 A 工作台页面
  tests/workbench/                    # 角色、导航、摘要、向导、列表、分页和手机验收
  tests/*.spec.ts                     # 既有身份、目录、Job、报告和排行回归
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

## 5. 模式、依赖和深度

FastAPI routes 是 HTTP Adapter，Next.js 客户端是浏览器侧 Adapter；真正的业务 Interface 位于 application Module，而非路由函数。Composition Root 一次装配用例与 PostgreSQL/MinIO Adapter，使路由保持翻译职责。

Web 依赖 HTTP Interface，不依赖后端源码目录或数据库 schema。所有业务权限必须在应用/HTTP 服务器再次判断，前端隐藏仅改善体验。

## 6. 当前验证与缺口

各 M1 任务的 HTTP/浏览器历史证据见对应行动文档；私有入口当前进展见[远程验收行动](../../../actions/2026-09-14-m1-private-remote-acceptance.md)。扩展任务 02 已通过 TypeScript、Next 生产构建、32 条全量浏览器回归、390/360 无页面溢出、双轴评审，以及当时的文档 31 项与实时 OpenAPI 31 项零差异检查。**该计数此后已变化**：任务 03 的对比端点注册后，`HTTP_API.md` §2.1 的文档侧为 32 项；实时 OpenAPI 的重新对账待后端环境可用时补做（见[进展与未决项](progress.md)）。详细红绿过程和基础设施偏差只由[任务 02 行动](../../../actions/2026-09-18-ui-workbench-implementation.md)维护。

待完成包括扩展任务 03 的对比报告信息结构，以及完整 Tailscale 双机负向/VPN/离线验收；任务 02 没有新增接口、数据库表、Worker/模型或部署行为。当前远程接入规则见[远程接入](../../../operations/REMOTE_TEAM_ACCESS.md)，部署候选见[所有者单机运行](../owner-host-runtime/ARCHITECTURE.md)。
