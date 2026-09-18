# Web 与 HTTP Module

> 当前状态：M1 身份、目录、Job、批准、取消/恢复、报告、证据和排行榜的 Next.js/FastAPI 路径已实现；界面重做仍在规划，Tailscale 双机负向/VPN/离线验收未全部完成。
> 权威范围：浏览器、Next.js 和 FastAPI 怎样交接，以及当前页面/路由实现位置。

## 1. 职责与非职责

Web 向 owner 与 collaborator 提供同一个私有站点；FastAPI 把 HTTP 请求翻译成应用用例调用并统一处理认证、输入和错误。Next.js 只把同源 `/api/v1` 转发到本机回环 FastAPI。

本 Module 不直接连接 PostgreSQL/MinIO，不接触 Docker/Harbor/Worker 或模型秘密，不在浏览器计算权威状态，也不因隐藏按钮替代服务器权限检查。

## 2. Interface 与不变量

- 浏览器只请求站点同源 `/api/v1/*`；`credentials: same-origin`，非只读请求带固定写入标记。
- Next.js 的上游目标只接受 `http://127.0.0.1:<port>`，拒绝带凭据、路径或远端主机的地址。
- FastAPI 的正式 `public_origin` 必须是 HTTPS；明文 HTTP 只允许显式本机回环开发。
- 会话 Cookie、同源写入检查、登录限速、`no-store` 和 `nosniff` 在 HTTP delivery 统一实施。
- FastAPI 返回稳定领域错误码；Web 将未知/畸形响应收敛为不可用，而不猜测成功。

路由、DTO、Cookie 和错误的精确契约由[HTTP Interface](../../../interfaces/HTTP_API.md)维护。

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
  src/app/page.tsx                    # 当前单页会话入口
  src/app/globals.css                 # 当前全局样式
  src/features/identity/              # 会话、加入和成员 UI
  src/features/catalog/               # 任务/配置目录 UI
  src/features/jobs/                  # 提交、批准、详情、取消、恢复、报告和证据 UI
  src/features/leaderboard/           # 基础排行榜 UI
  src/lib/api-client.ts               # 同源 fetch、错误和 actor 校验
  src/lib/*-client.ts                 # 各 HTTP 子域客户端
  src/lib/*-shapes.ts                 # 运行时响应形状校验
  tests/                              # Playwright 浏览器行为验收
```

`src/features/` 是 Web Implementation 的按用户任务组织方式，不表示每个目录都是独立后端 Module。当前 `page.tsx` 仍以 `SessionPanel` 作为单页入口；规划中的多导航工作台尚未实现。

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

## 5. 模式、依赖和深度

FastAPI routes 是 HTTP Adapter，Next.js 客户端是浏览器侧 Adapter；真正的业务 Interface 位于 application Module，而非路由函数。Composition Root 一次装配用例与 PostgreSQL/MinIO Adapter，使路由保持翻译职责。

Web 依赖 HTTP Interface，不依赖后端源码目录或数据库 schema。所有业务权限必须在应用/HTTP 服务器再次判断，前端隐藏仅改善体验。

## 6. 当前验证与缺口

各 M1 任务的 HTTP/浏览器历史证据见对应行动文档；私有入口当前进展见[远程验收行动](../../../actions/2026-09-14-m1-private-remote-acceptance.md)。本轮没有运行 TypeScript、Next build、Playwright、FastAPI 或 Tailscale。

待完成包括：角色化多页面/导航 UI、完整 Tailscale 双机负向/VPN/离线验收、正式长期进程管理。当前远程接入规则见[远程接入](../../../operations/REMOTE_TEAM_ACCESS.md)，部署候选见[所有者单机运行](../owner-host-runtime/ARCHITECTURE.md)。
