# 身份与成员 Module

> 当前状态：M1 任务 01–02 已实现并有历史 HTTP、浏览器和隔离 PostgreSQL 验证；本轮仅静态核对。
> 权威范围：当前身份/会话/邀请/成员职责、实现位置和依赖关系。字段与 HTTP 细节分别以[数据模型](../../DATA_MODEL.md)和[HTTP Interface](../../../interfaces/HTTP_API.md)为准。

## 1. 职责与非职责

本 Module 负责应用账号、密码校验、会话、所有者本机建立/恢复账号、邀请协作者、撤销邀请和停用成员。它向其他 Module 提供可信的 `AuthenticatedActor`，角色只有 `owner` 与 `collaborator`。

它不负责 Tailscale 设备准入、Codex/API Key、Job 批准、Docker 权限或业务结果可见性。Tailnet 成员身份不能替代应用登录；模型秘密也不能放入应用账号表。

## 2. Interface 与不变量

- `IdentityService`：建立唯一 owner、登录、解析当前会话、登出和本机恢复 owner。
- `MembershipService`：owner 创建/查看/撤销邀请、查看/停用成员；邀请码兑换固定产生 collaborator。
- `IdentityRepository` / `MembershipRepository`：应用层使用的 persistence seam；调用者不需要知道 SQL、哈希或事务细节。
- 密码只以 Argon2 哈希保存；会话和邀请码只保存摘要；恢复 owner 会使旧会话失效。
- 公开注册不存在；owner 不能通过成员管理停用自己。

精确方法、错误和权限见[模块契约](../../MODULE_CONTRACTS.md)，Cookie、CSRF/同源约束及路由见[HTTP Interface](../../../interfaces/HTTP_API.md)。

## 3. 当前 Implementation 文件树

```text
apps/backend/src/eval_platform/
  domain/
    identity.py                    # actor、账号、会话、登录值和身份错误
    membership.py                  # 邀请、成员值和成员权限错误
  application/
    identity.py                    # IdentityService：密码策略、会话签发/解析/撤销
    membership.py                  # MembershipService：邀请和成员用例、owner 门禁
    ports/identity.py              # Passwords、IdentityRepository、MembershipRepository Interface
  adapters/
    identity/passwords.py          # Argon2 Passwords Adapter
    persistence/identity.py        # PostgreSQL 身份 Repository Adapter
    persistence/identity.sql       # accounts、sessions 的显式建表脚本
    persistence/membership.py      # PostgreSQL 邀请/成员 Repository Adapter
    persistence/membership.sql     # invitations 的显式升级脚本
  delivery/
    owner.py                       # 仅本机交互的 init/bootstrap/recover/upgrade 入口
    http/app.py                    # Composition Root：装配身份与成员用例
    http/routes/identity.py        # 登录、登出、当前 actor 的 HTTP 翻译
    http/routes/membership.py      # 邀请兑换及 owner 成员管理的 HTTP 翻译
    http/membership_schemas.py     # 成员请求/响应 DTO
apps/web/src/
  features/identity/session.tsx    # 登录后会话壳与角色入口
  features/identity/join.tsx       # 邀请兑换 UI
  features/identity/members.tsx    # owner 邀请/成员管理 UI
  lib/api-client.ts                # 同源请求、身份错误和 actor 校验
  lib/membership-client.ts         # 成员 HTTP 客户端
```

SQL 文件是显式初始化/升级输入，不由 Web 或 API 启动时自动执行。`delivery/owner.py` 是维护入口，不开放远程注册/找回接口。

## 4. 关键数据流

1. owner 在本机 CLI 显式初始化身份表并建立唯一 owner。
2. 浏览器经 Next.js 同源入口调用 FastAPI；登录成功后仅把随机会话 token 放进安全 Cookie，PostgreSQL 保存摘要。
3. 后续路由用 Cookie 解析 `AuthenticatedActor`，再由目标应用用例决定 owner/创建者权限。
4. owner 创建一次性邀请；协作者通过私有入口兑换后成为 collaborator；停用会使其不能再形成有效身份。

## 5. 模式、依赖和深度

`IdentityService` / `MembershipService` 是应用 Module；Repository 是 seam，PostgreSQL 类是 Adapter。复杂的并发兑换、唯一 owner、会话失效和错误收敛隐藏在 Adapter 后，HTTP 与 Web 不直接写 SQL，因此一个小 Interface 同时服务 CLI、HTTP 和测试。

身份 Module 只向外给 actor，不反向依赖 Catalog、Job、Harbor 或 MinIO。HTTP delivery 负责 Cookie 和同源翻译，不把框架对象带入领域层。

## 6. 当前验证与缺口

历史验证入口见[owner 身份行动](../../../actions/2026-09-11-m1-owner-identity.md)和[协作者邀请行动](../../../actions/2026-09-11-m1-collaborator-invitations.md)。本轮没有重跑测试。

仍缺的是正式长期数据库、备份恢复、长期进程和完整远程双机验收；这些属于[所有者单机运行](../owner-host-runtime/ARCHITECTURE.md)，不是再造身份 Module。五人组人数不需要新增角色或表：当前设计是一个 owner 加若干 collaborator，实际邀请数量由组内安排决定。
