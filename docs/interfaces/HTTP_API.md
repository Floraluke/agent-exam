# Web 与后端 HTTP API 契约

> 文档状态：Job/Run 资源边界已确认；HTTP 契约 v0.3。任务 01–13 已验收；六题、continuous 受控选项与跨批次比较页面已接入；提供方策略切片尚未形成新的公开执行端点
>
> 最后更新：2026-09-22（同步受控 Agent 身份、统一安全响应头及安全 500 诊断）
> 权威范围：本文件只维护 Next.js Web 与 FastAPI 交付层之间的 HTTP 契约。内部模块行为见 [`MODULE_CONTRACTS.md`](../architecture/MODULE_CONTRACTS.md)，存储字段见 [`DATA_MODEL.md`](../architecture/DATA_MODEL.md)。

## 规划增量与当前接口

[扩展规格](../../.scratch/ui-catalog-providers/spec.md)已确认角色化 UI、至少五道新题、新提交连续规模以及 Codex 第三方 API 方向。六题、连续规模和对比页面已实现；下面只记录当前真实接口，未接线的提供方代理不产生虚构端点。

- UI首页、列表、向导与对比优先复用现有会话、目录、Job筛选/分页、批次/Run报告和制品接口，不新增Worker健康/全局统计接口。无来源的状态/指标显示未知。
- 合格题和配置以服务端 preset 进入现有目录；前端只提交 ID，仍拒绝 Key、用户 URL、路径、命令与任意资源值。生产目录当前只公开 ChatGPT 配置；`internal_test_fake` 只允许显式测试装配。首版不提供网页 Key 录入/读取/更换端点，秘密策略见认证 4.1。
- `submission-options` 已发布 `continuous(1–20)`；旧 preset ID 语义和旧 Job 冻结内容保留。边界与兼容测试见[验证表](../../.scratch/ui-catalog-providers/verification.md)。
- `POST /jobs`仍只保存并返回等待批准；owner自提交自批准合法，网络/模型问题不改变应用权限。创建/批准均不读模型凭据。Job/Run、恢复重试、internal_test隔离及错误合同保持。
- 报告优先展示同题跨配置，但不新增计费字段或改排行榜；`cost_usd=null`为未知，不用人民币估算代填。实施过程中任何实际字段变化须同时更新本合同与客户端校验。

## 1. 给初学者的解释

浏览器不能直接碰 Docker、数据库和 Agent。它只能给 FastAPI 发 HTTP 请求。HTTP API 就像一张固定菜单：页面只能点菜单上已有的菜，不能把一条任意 shell 命令交给服务器执行。

## 2. 总体规则

阶段范围见[总架构第 3.1 节](../architecture/ARCHITECTURE.md#31-m1-交付边界2026-09-09-已确认)。M1 不注册 Judge/复核触发或 `/reviews` 路由，页面与 OpenAPI 不提供复核入口；保留以下后续契约，不把所有者批准接口一并关闭。

| 项目 | 候选 v0.1 |
|---|---|
| 基础路径 | `/api/v1` |
| 内容类型 | JSON 接口使用 `application/json; charset=utf-8` |
| ID | 对浏览器语义均为不透明字符串；当前资源 ID 使用 UUID 格式并由服务端校验，前端不得从值中猜数据库结构 |
| 时间 | ISO 8601 UTC，例如 `2026-09-01T10:00:00Z` |
| 分页 | `limit` + 不透明 `cursor`；默认 20，候选上限 100 |
| 创建幂等 | Job 创建/批准/拒绝按对应章节支持 `Idempotency-Key`；身份/邀请不使用该键，重复创建邀请会生成独立邀请，不自动重试 |
| 长任务 | `POST /jobs` 只创建待所有者批准的 Job 和逐题运行后立即返回 `202`；批准请求只排队，也不等待 Harbor/Agent 完成 |
| 状态刷新 | 首版候选用前端轮询；不先引入 WebSocket/SSE |
| 字段命名 | JSON 使用 `snake_case`，与后端 schema 保持一致 |
| 未知字段 | 写请求默认拒绝，防止拼写错误被静默忽略 |
| OpenAPI | FastAPI 生成的 schema 上线时必须与本文契约检查一致 |

### 2.1 当前前后端 API 清单（已注册、可由产品 UI 使用）

本表以当前 FastAPI 路由装配和 `apps/web/src/lib` 调用代码为准，列出已经注册的 32 个 HTTP 端点及其 Web 接线。详细请求/响应形状仍由本文件后续对应章节维护，本表只维护“Web 从哪里调用、页面为什么调用、谁能调用”的追踪关系，避免复制 schema。

硬规则：产品 UI 只有在本表存在对应端点时才可提供改变业务事实的按钮或交互；不得用前端假数据、假成功或占位动作模拟未完成能力。导航、菜单开关、URL 切换和向导前后步不改变业务事实，明确属于无 HTTP 请求的本地界面动作。

| 方法与路径 | Web 调用函数 | 当前页面/用途 | 权限 |
|---|---|---|---|
| `POST /api/v1/auth/login` | `api-client.login` | 登录表单建立会话 | 未登录用户；同源写请求 |
| `GET /api/v1/auth/me` | `api-client.currentActor` | 首次载入/刷新恢复可信 Actor | 有效会话；无会话返回 401 |
| `POST /api/v1/auth/logout` | `api-client.logout` | 退出并清除本地私有 URL 状态 | 有效会话；重复退出幂等 |
| `POST /api/v1/invitations` | `membership-client.invite` | 成员管理创建一次性邀请 | owner |
| `POST /api/v1/invitations/redeem` | `membership-client.redeem` | 登录页使用邀请建立 collaborator | 未登录用户；同源写请求 |
| `GET /api/v1/invitations` | `membership-client.invitations` | 成员管理读取/翻页邀请 | owner |
| `POST /api/v1/invitations/{invitation_id}/revoke` | `membership-client.revoke` | 成员管理撤销邀请 | owner |
| `GET /api/v1/members` | `membership-client.members` | 成员管理读取/翻页协作者 | owner |
| `POST /api/v1/members/{user_id}/disable` | `membership-client.disable` | 成员管理停用协作者 | owner |
| `POST /api/v1/tasks/register` | `catalog-client.registerTask` | 任务目录登记固定 preset | owner |
| `GET /api/v1/tasks` | `catalog-client.tasks` | 任务目录筛选/翻页；新建向导读取题目 | 已登录用户 |
| `GET /api/v1/tasks/{task_id}` | `catalog-client.taskDetail` | 任务目录查看公开详情 | 已登录用户 |
| `POST /api/v1/agent-configurations` | `catalog-client.registerAgent` | 配置目录登记固定 Codex preset | owner |
| `GET /api/v1/agent-configurations` | `catalog-client.agents` | 配置目录筛选/翻页；新建向导读取启用配置 | 已登录用户 |
| `GET /api/v1/agent-configurations/{configuration_id}` | `catalog-client.agentDetail` | 配置目录查看公开详情 | 已登录用户 |
| `POST /api/v1/agent-configurations/{configuration_id}/disable` | `catalog-client.disableAgent` | 配置目录禁用配置，保留历史 | owner |
| `GET /api/v1/job-options` | `job-client.jobOptions` | 新建向导读取服务端批次、赛道和资源限制 | 已登录用户 |
| `POST /api/v1/jobs` | `job-client.submitJob` | 三步向导创建等待批准的 Job | 已登录用户；要求幂等键 |
| `GET /api/v1/jobs` | `job-client.jobs` | 角色首页当前可见页、owner 按状态分组、评测列表筛选/游标翻页；接口不承诺按创建时间排序 | owner 可见全部；collaborator 仅本人范围 |
| `GET /api/v1/jobs/{job_id}` | `job-client.jobDetail` | Job 详情、刷新、可分享 URL 恢复 | owner 可见全部；collaborator 仅本人 Job |
| `POST /api/v1/jobs/{job_id}/approve` | `job-client.decideJob(approve)` | 所有者批准并排队 | owner；待批准状态；要求幂等键 |
| `POST /api/v1/jobs/{job_id}/reject` | `job-client.decideJob(reject)` | 所有者拒绝 Job | owner；待批准状态；要求幂等键 |
| `POST /api/v1/jobs/{job_id}/cancel` | `job-client.cancelJob` | 详情页请求取消 | owner 任意可见 Job；collaborator 仅本人；要求幂等键 |
| `POST /api/v1/jobs/{job_id}/recover` | `job-client.recoverJob` | 所有者检查并收束租约已过期的中断 Job | owner；限定状态/过期租约 |
| `POST /api/v1/jobs/{job_id}/retry` | `job-client.retryJob` | 从已显式收束的旧 Job 新建重试 Job | owner；要求幂等键；新 Job 重新待批准 |
| `GET /api/v1/reports/jobs/{job_id}` | `job-client.jobReport` | Job 详情读取批次进度 | 与 Job 可见范围相同 |
| `GET /api/v1/reports/runs/{run_id}` | `job-client.runReport` | 批次/详情读取单题运行报告 | 与来源 Job 可见范围相同 |
| `GET /api/v1/reports/comparisons` | `reporting/comparison-client.comparison` | 对比报告按所选可见 Job 读取题目×配置矩阵；页面另复用 Job 详情和 Run 报告，不在浏览器改写结论 | owner 可读全部；collaborator 仅本人创建的 Job |
| `GET /api/v1/runs/{run_id}/artifacts` | —（Web 当前未接线） | 后端保留独立的制品元数据/保留状态索引；当前报告页改用 `job-client.runReport` 响应中的 `artifact_links` | 与来源 Job 可见范围相同 |
| `GET /api/v1/runs/{run_id}/trajectory` | `job-client.runTrajectory` | 安全证据分页读取脱敏轨迹 | 与来源 Job 可见范围相同 |
| `GET /api/v1/artifacts/{artifact_id}/content` | 报告页同源下载链接 | 下载公开补丁/测试摘要/公开轨迹正文 | 与来源 Job 可见范围相同；仅公开白名单类型 |
| `GET /api/v1/leaderboard` | `leaderboard/client.leaderboard` | 排行榜按完整冻结条件查询/翻页 | 任一已登录用户；仅正式结果 |

当前明确**未注册、产品 UI 不得提供入口**：`/agent-submissions*`、`/reviews*`、普通用户 `POST /runs`，以及第 8 节保留形状中的通用 `GET /runs` / `GET /runs/{run_id}`。这些是后续契约或历史候选，不是当前已完成 API。HTTP 也没有制品删除接口；到期清理由 owner 在评测机执行本地维护命令，因此 Web 不显示“删除制品”按钮。

## 3. 统一错误格式

```json
{
  "error": {
    "code": "RUN_STATE_CONFLICT",
    "message": "当前运行状态不允许执行此操作",
    "details": {
      "run_id": "01J...",
      "current_status": "VERIFYING"
    },
    "request_id": "req_01J..."
  }
}
```

| HTTP 状态 | 使用场景 | 示例 `error.code` |
|---:|---|---|
| `400` | 请求语义无效 | `INVALID_REQUEST`、`LIMIT_OUT_OF_RANGE` |
| `401` | 没有可信登录会话 | `AUTHENTICATION_REQUIRED` |
| `403` | 已登录但没有操作权限 | `OWNER_APPROVAL_REQUIRED`、`FORBIDDEN` |
| `404` | 资源或路由不存在 | `RESOURCE_NOT_FOUND`（框架路由）、`MEMBER_NOT_FOUND`、`TASK_NOT_FOUND`、`JOB_NOT_FOUND`、`RUN_NOT_FOUND` |
| `405` | 已有路由不支持该 HTTP 方法 | `METHOD_NOT_ALLOWED`，保留 `Allow` 响应头 |
| `409` | 状态或幂等冲突 | `IDENTITY_CONFLICT`、`JOB_STATE_CONFLICT`、`RUN_STATE_CONFLICT`、`IDEMPOTENCY_CONFLICT` |
| `410` | 邀请不可用，或制品正文已清理 | `INVITATION_UNAVAILABLE`、`ARTIFACT_CONTENT_DELETED` |
| `422` | JSON 字段/schema 不合格 | `VALIDATION_ERROR` |
| `429` | 单进程登录或邀请码兑换预算耗尽 | `RATE_LIMITED`，`Retry-After: 60` |
| `503` | 数据库、对象存储等暂不可用 | `DEPENDENCY_UNAVAILABLE` |
| `500` | 未预期平台错误 | `INTERNAL_ERROR` |

错误 `message` 面向人类；前端分支判断只使用稳定的 `code`，不能解析中文文案。

已实现的统一错误由 Delivery 的 `ApiError` / `ErrorDetails` 同时用于实际响应与 OpenAPI，不维护另一份框架默认 `HTTPValidationError`。框架 `HTTPException` 的 404/405 按上表转换，其他状态保留状态码并使用安全通用 `HTTP_ERROR`（例如框架请求解析失败的 400）；不回显异常 detail，按需保留 `Allow`、`WWW-Authenticate`、`Retry-After`。当前错误的 `details` 为空对象。

未预期异常返回通用 `500 INTERNAL_ERROR`，响应和服务端结构化日志使用同一个随机 `request_id`。日志只记录 request ID、HTTP 方法、路径和异常类型，不记录异常消息、请求正文、header 或秘密；客户端也不接收内部异常文本。

FastAPI 对所有成功、业务错误、限流和未预期异常响应统一设置 `Cache-Control: no-store`、`X-Content-Type-Options: nosniff`、`X-Frame-Options: DENY`、`Referrer-Policy: no-referrer` 与禁用摄像头/麦克风/定位的 `Permissions-Policy`。Next.js 对所有页面/代理入口设置相同浏览器安全头，并额外设置限制为同源、禁止 object/frame ancestor 的 CSP；尚未确认生产 HTTPS 终止边界，因此不在应用层提前声明 HSTS。

### 3.1 身份与角色边界

平台没有公开注册，只存在两类应用角色：

| 角色 | 允许行为 | 明确禁止 |
|---|---|---|
| `collaborator`（协作者） | 登录、查看任务/已登记 Agent、提交 Job、查看自己有权访问的非秘密结果、取消自己提交的 Job | 批准/拒绝、成员和配置管理、清理制品、人工复核 |
| `owner`（评测所有者） | 协作者全部能力，以及批准/拒绝任意 Job、邀请协作者、成员/配置管理、清理制品和人工复核 | 把所有者权限委托给请求正文或网络设备身份 |

唯一 `owner` 由评测机本地引导建立和恢复，之后由其邀请协作者；不接入邮件服务。受保护请求从可信会话获得 `AuthenticatedActor`，route 不能接受 `role`、`owner_id`、`reviewer_id` 等正文提权字段。Tailscale/校园网/VPN只解决“能否到达页面”，不能代替应用登录。用户于 2026-09-11 确认最小账号方案，存储见[数据模型身份表](../architecture/DATA_MODEL.md#40-身份表accounts-与-sessions)。任务 02 已实现的邀请和成员契约见第 3.3 节，任务验收已完成。

### 3.2 任务 01 身份 HTTP 切片

| 端点 | 输入 | 成功响应 |
|---|---|---|
| `POST /api/v1/auth/login` | `username`：3–64 位小写字母/数字/`_.-`，首位字母或数字；`password`：1–128 字符；未知字段拒绝 | `200`，公开身份对象，并设置会话 Cookie |
| `GET /api/v1/auth/me` | 浏览器会话 Cookie | `200`，公开身份对象；缺少/过期/撤销会话为 `401` |
| `POST /api/v1/auth/logout` | 会话 Cookie；无正文或空 JSON 对象，未知字段拒绝 | `204` 空正文，撤销该会话并清除 Cookie；重复退出幂等 |

公开身份仅为 `user_id`、`username`、`role`（`owner`/`collaborator`），不返回密码哈希或 token。登录失败与账号不存在使用相同 `AUTHENTICATION_REQUIRED` 文案，不回显输入；schema 错误仍使用统一 `error` 包装和空 `details`，不采用框架含原始输入的默认错误正文。

三个已实现端点的 OpenAPI 错误声明均引用 `ApiError`：登录为 `400/401/403/422/429/500/503`，当前身份为 `401/500/503`，退出为 `400/403/422/500/503`；429 声明 `Retry-After`。框架未知路由与错误方法适用第 3 节，不为不存在的路由增加业务端点；退出成功的 `204` 不声明正文。

- 所有写请求要求 `Origin` 与服务端配置的 `AGENTEXAM_PUBLIC_ORIGIN` 完全一致，并带 `X-AgentExam-Request: 1`；不启用 CORS。Next.js 只将同源 `/api/v1/*` 转发到配置的本机回环 FastAPI，不承担身份判定。
- HTTPS 使用 `__Host-agentexam_session`：`Secure`、`HttpOnly`、`SameSite=Strict`、`Path=/`，无 Domain，最大存活 8 小时；服务端独立检查过期和撤销，不信任客户端过期时间。身份响应 `Cache-Control: no-store`。
- 仅显式设置 `AGENTEXAM_ALLOW_INSECURE_LOOPBACK=1` 且公开 Origin 为 HTTP 回环地址时，允许开发 Cookie `agentexam_development_session` 不设置 Secure；该开发模式不能用于校园网或远程设备访问。
- 单个 HTTP 进程在滚动 60 秒内最多受理 10 次登录尝试，计入正确与错误凭证，不依赖不可信转发 IP；超限 `429`。这是小团队本机保护，会让同进程用户共享预算，不是跨进程防滥用系统；上线前须按单进程约束和私有接入方案验证。
- 没有注册/远程引导/远程恢复端点。密码建立/恢复要求 15–128 字符，不以登录端点的输入下限代替密码设置策略。本机命令和运行配置见[依赖与恢复入口](../dependencies/DEPENDENCIES.md#22-m1-身份切片的依赖与本机入口)。
- 本切片不创建 Job、批准或执行 Agent，不引入 Judge/Review。原始实现及 PostgreSQL 证据在[身份行动](../actions/2026-09-11-m1-owner-identity.md)，评审修复与最新 HTTP/HTTPS 浏览器证据在[独立修复行动](../actions/2026-09-11-m1-identity-review-fixes.md)维护。

上表的人工复核权限只在后续启用第 11 节时适用；M1 所有者批准/拒绝 Job、管理成员及清理的权限不变。

### 3.3 任务 02 邀请与成员 HTTP 切片

用户确认：邀请 24 小时有效、一次性、可撤销。所有者创建后手动交付，不发邮件；受邀者设置自己的账号/密码，只产生 collaborator。

| 端点 | 输入/权限 | 成功响应 |
|---|---|---|
| `POST /api/v1/invitations` | owner；无正文或空对象 | `201` 邀请元数据和仅此一次的 `invitation_token` |
| `POST /api/v1/invitations/redeem` | 无需登录，但仍需可信同源写请求；`invitation_token` 1–128 字符、`username` 同登录规则、`password` 15–128 字符，未知字段拒绝 | `201` 公开身份；不自动登录/设置 Cookie |
| `GET /api/v1/invitations` | owner；通用分页 | `200` 邀请元数据分页，不含邀请码或摘要 |
| `POST /api/v1/invitations/{invitation_id}/revoke` | owner；UUID 路径；无正文或空对象 | `204`；重复撤销幂等，已兑换为 `409 IDENTITY_CONFLICT`，未知 ID 为 `410` |
| `GET /api/v1/members` | owner；通用分页 | `200` collaborator 列表，含已停用成员、不含 owner |
| `POST /api/v1/members/{user_id}/disable` | owner；UUID 路径；无正文或空对象 | `204`；重复停用幂等；禁止停用 owner（403），不存在成员为 `404 MEMBER_NOT_FOUND` |

邀请元数据：`invitation_id/created_by/created_at/expires_at/revoked_at/redeemed_at/redeemed_by/status`；时间为 UTC，可空字段按数据契约。`status` 由时间/兑换事实派生为 `pending/expired/revoked/redeemed`。成员只返回 `user_id/username/active`。两种分页均为 `items/next_cursor`，默认 20、范围 1–100，游标为上页返回的 UUID 字符串；不接受任意 SQL/排序条件。按 ID 稳定排序，翻页中并发新增不保证快照一致，刷新重新取首屏。

无效、到期、撤销或已用邀请码统一 `410 INVITATION_UNAVAILABLE`；账号名冲突为 `409 IDENTITY_CONFLICT`，不消耗邀请。停用提交后，旧会话不能通过后续身份校验，也不能再用旧密码登录；不删除历史账号，不承诺撤回已经完成授权的在途请求。兑换/停用原子性见[数据契约](../architecture/DATA_MODEL.md#401-邀请表invitations)。

这些端点沿用同源写检查、统一 `ApiError`、空错误 details 和 `no-store`；OpenAPI 声明 `400/401/403/404/409/410/422/429/500/503`，204 无正文。单进程兑换预算独立于登录：滚动 60 秒最多 10 次（含无效/成功尝试），超限 429；共用预算的部署限制同第 3.2 节。页面只在 owner 视图显示管理入口，权限仍由后端检查。

邀请码不进入 URL、普通列表、持久浏览器存储或日志；创建响应是唯一明文交付例外，页面刷新/退出/关闭即不再显示。响应丢失时只能由所有者撤销后新建，不自动重试生成多份邀请。HTTP/浏览器与真实 PG 的分层验收证据见[任务 02 行动](../actions/2026-09-11-m1-collaborator-invitations.md)。

## 4. 只读资源形状

### 4.1 `TaskSummary`

```json
{
  "task_id": "SWE-Gym/SWE-Gym@revision:train:instance-id",
  "instance_id": "instance-id",
  "dataset_id": "SWE-Gym/SWE-Gym",
  "dataset_revision": "fixed-revision",
  "split": "train",
  "repo": "owner/repo",
  "base_commit": "commit",
  "problem_statement_preview": "Issue 的截断预览"
}
```

不返回 gold patch、`test_patch`、`FAIL_TO_PASS` 或 `PASS_TO_PASS`。

### 4.2 `AgentConfigurationSummary`

```json
{
  "agent_configuration_id": "codex-model-config",
  "display_name": "Codex / fixed-model / fixed-config",
  "agent_type": "codex",
  "agent_version": "fixed-version",
  "model_provider": "openai_chatgpt",
  "model": "fixed-model",
  "configuration_fingerprint": "sha256-hex",
  "enabled": true
}
```

不返回 API key、凭据配置引用、命令模板、宿主路径或私有环境变量。`model_provider` 是非秘密的受控身份字段：生产 `create_catalog` 当前只公开 `openai_chatgpt`；`internal_test_fake` 只能出现在显式 `internal_test` 装配和测试数据中，不能进入正式目录或排行榜。provider 必须与 authentication type 按领域/数据库约束成对，HTTP 不返回认证类型、逻辑凭据引用或任何 Key。MVP 先登记 Codex；闭环通过后登记 Aider、Claude Code。P2 同一自研 Agent 使用 DeepSeek 与 Kimi 时返回两个独立配置。

`agent_type` 与 `model_provider` 都是**受控集合**，唯一权威清单是 `domain/agent.py` 的 `CONTROLLED_IDENTITIES`：M1 的 `agent_type` 只有 `codex`；`model_provider` 有 `openai_chatgpt` 与 `internal_test_fake` 两个值。响应**按记录如实呈现**，不写死默认值；存量记录超出受控集合时**失败关闭**（`UNCONTROLLED_AGENT_TYPE` / `UNCONTROLLED_PROVIDER`），绝不回退成 `openai_chatgpt` 之类的默认值——那会让页面显示一条假身份。`internal_test_fake` 只在 `internal_test` 用途下登记（受控 API 预设，生产 `AGENT_PRESETS` 不含假提供方，见第 6 节）；该身份成对使用的 `authentication_type=provider_run_token`、凭据 profile 与固定上游**都不在 HTTP 响应中**，沿用第 10.3 节“不返回 authentication/credential profile”的同一规则。公开 `internal_test_fake` 是有意的：它让受控预设不可能被误当成真实供应商配置，且本身不含主机、路径、令牌或 topo 信息。

### 4.3 `JobSummary`

```json
{
  "job_id": "00000000-0000-0000-0000-000000000003",
  "evaluation_track": "closed_book",
  "result_scope": "official",
  "status": "QUEUED",
  "batch_preset": "demo",
  "limit_profile_id": "default-single-host-v1",
  "trial_count": 1,
  "run_ids": ["00000000-0000-0000-0000-000000000004"],
  "estimated_finish_at": null,
  "created_at": "2026-09-03T10:00:00Z",
  "owner_decided_by": "00000000-0000-0000-0000-000000000001",
  "owner_decided_at": "2026-09-03T10:00:02Z",
  "owner_decision_reason": "已检查冻结范围",
  "cancel_requested_by": null,
  "cancel_requested_at": null,
  "cancel_reason": null,
  "failure_code": null,
  "failure_summary": null,
  "rerun_of_job_id": null
}
```

`estimated_finish_at=null` 表示没有足够真实历史数据，不能理解成“马上完成”。待批 Job 的三个 `owner_*` 字段均为 null；批准/拒绝后由可信决定事务填写，不在正文中接受决定者。`cancel_requested_by`/`cancel_requested_at`/`cancel_reason` 在取消流程中填写；`failure_code`/`failure_summary` 只在批次级失败时非空（受控枚举与受控短文案，见第 10.2 节）；`rerun_of_job_id` 指向本批次的**重试来源**旧 Job，非重试批次为 `null`。任务 07 的细粒度进度在 Job 报告中按持久化 Run 状态返回；Job 详情仍不返回猜测的预计完成时间。

### 4.4 `RunSummary`

```json
{
  "run_id": "01J...",
  "job_id": "job_01J...",
  "task_id": "opaque-task-id",
  "agent_configuration_id": "codex-model-config",
  "evaluation_track": "closed_book",
  "network_policy_id": "provider-only-v1",
  "tool_profile_id": "no-web-tools-v1",
  "status": "RUNNING_AGENT",
  "resolved": null,
  "termination_reason": null,
  "review_status": "NOT_REQUIRED",
  "created_at": "2026-09-01T10:00:00Z",
  "started_at": "2026-09-01T10:00:03Z",
  "finished_at": null
}
```

`resolved=null` 表示确定性验证尚未产生结果；不能解释为失败。超过 1 MiB 的文本 patch 或任何二进制 patch 不进入 Harness，分别以 `PATCH_TOO_LARGE` / `BINARY_PATCH_NOT_ALLOWED` 记录为明确的无效 Agent 输出；patch 不会被静默截断。

M1 的 `review_status` 使用既有 `NOT_REQUIRED`，不产生虚假的待复核队列。

## 5. Task API

任务 03 已实现：任务与配置端点、生产存储组装、真实集成和 Web 目录流程已有验证。所有端点要求有效登录；沿用第 3 节同源写检查、no-store 与空 details 安全错误。ID/游标采用不透明 UUID 字符串，分页按 ID 稳定排序，不承诺跨页快照一致。无效格式为 422；未知预置为 400 INVALID_REQUEST；固定身份内容冲突为 409 CATALOG_CONFLICT；对象缺失/损坏或依赖故障为 503 DEPENDENCY_UNAVAILABLE，不回显对象键、连接、SDK 异常或原始数据。

已批准的 `POST /api/v1/tasks/register` 仅 owner 可调用；正文仅 `{"preset_id":"swe-gym-lite-mypy-15413"}`，拒绝额外字段。成功或同内容重入均为 201 TaskDetail，重入保留原 task_id；普通用户不能上传任务 JSON、命令、镜像或来源路径。正式 preset 复用现有固定单题，不代表整个题库可执行。合成测试使用独立 preset 和数据，不能进入正式目录。

### 5.1 查询任务列表

`GET /api/v1/tasks`

| 输入 | 类型 | 说明 |
|---|---|---|
| `dataset_id` | query string，可选 | 1–128 字符，精确匹配目录中的数据集；无匹配为空列表 |
| `split` | query string，可选 | 1–64 字符，精确匹配真实 split；无匹配为空列表 |
| `repo` | query string，可选 | 1–128 字符，精确筛选仓库 |
| `cursor` | query string，可选 | 下一页游标 |
| `limit` | query integer，可选 | 1–100 |

成功 `200`：

```json
{
  "items": [],
  "next_cursor": null
}
```

### 5.2 查询任务详情

`GET /api/v1/tasks/{task_id}`

- 输入：不透明 `task_id`。
- 成功 `200`：`TaskSummary` 加完整 `problem_statement`。
- 错误：`404 TASK_NOT_FOUND`。
- 保密：仍不返回 gold patch 和判分测试答案。

## 6. Agent Configuration API

### 6.1 查询已登记配置

`GET /api/v1/agent-configurations`

| 输入 | 类型 | 说明 |
|---|---|---|
| `agent_type` | query，可选 | MVP 为 `codex`；后续加入 `aider`、`claude_code`；P2 才启用 `custom`。`custom_process` 是 Adapter 类型，不是 Agent 类型 |
| `enabled` | query boolean，可选 | 页面发起评测默认只查 `true` |
| `cursor` / `limit` | query，可选 | 通用分页 |

成功 `200`：分页的 `AgentConfigurationSummary[]`。

### 6.2 查询配置详情

`GET /api/v1/agent-configurations/{agent_configuration_id}`

- 成功 `200`：公开配置、版本、模型、限制模板和指纹。
- 错误：`404 AGENT_CONFIGURATION_NOT_FOUND`。
- MVP 不提供上传压缩包、源码仓库、shell 命令或未审核代码运行接口。

登记/修改 Agent 配置属于 `owner` 流程；协作者只能选择项目已经登记并启用的配置。

任务 03 已落地的管理切片：`POST /api/v1/agent-configurations` 仅 owner 接受 `{"preset_id":"codex-0153-terra-medium"}`，不接受其他字段；201 返回配置详情，同指纹重入仍返回原记录。`POST /api/v1/agent-configurations/{configuration_id}/disable` 仅 owner，正文无或空对象，成功 204；重复禁用幂等、不删除历史、重新登记不恢复启用。详情的 public_options 当前仅 reasoning_effort，limit_profile_id 未绑定时为 null。未知预置、身份冲突、依赖失败沿用第 5 节目录错误，缺失配置为 404 AGENT_CONFIGURATION_NOT_FOUND。列表/详情不返回凭据逻辑引用，原始快照也没有下载端点。

两类目录列表均拒绝未知或重复 query 字段（400 INVALID_REQUEST），字段/UUID 格式和数值边界错误为 422。配置列表 agent_type 仅 codex；未知类型拒绝，合法筛选无匹配返回空列表。`model_provider` 是第 4.2 节的受控集合，列表与详情都按记录如实呈现；受控 API 预设 `internal-test-provider-proxy` 只在 `internal_test` 装配下登记，出现时其 `model_provider` 为 `internal_test_fake`。

### 6.3 P2：提交 Agent 源码供审核（MVP 不开放）

以下契约只保留扩展接缝，不注册为 MVP 路由；浏览器和 OpenAPI 都不应在 MVP 中出现这些入口。

`POST /api/v1/agent-submissions`

P2 请求需要可信登录会话。请求：

```json
{
  "git_url": "https://example.com/group/agent.git",
  "commit_sha": "40-character-full-commit-sha",
  "display_name": "My Agent",
  "description": "供组内评测的固定版本"
}
```

仓库根必须存在同一 commit 中的 `agent-exam.yaml`。成功 `202`：

```json
{
  "submission_id": "submission_01J...",
  "status": "PENDING_REVIEW",
  "created_at": "2026-09-03T10:00:00Z"
}
```

提交成功不会启动 Harbor、构建镜像或执行仓库代码。分支、tag、`latest`、请求内 `import_path`、环境变量或 shell 命令均拒绝。

评测所有者审核候选接口：

- `GET /api/v1/agent-submissions`：提交者看自己的记录，所有者看待审列表；
- `GET /api/v1/agent-submissions/{submission_id}`：查看安全元数据和审核状态；
- `POST /api/v1/agent-submissions/{submission_id}/approve`：所有者批准并生成新的已登记 Agent 配置；
- `POST /api/v1/agent-submissions/{submission_id}/reject`：所有者拒绝并记录原因。

P2 自研 Agent 只支持 Python 固定进程 Interface；`agent-exam.yaml` 不得接收 shell、API Key、自定义模型提供方/Base URL、代理或宿主路径。完整字段、Python 版本和依赖锁格式尚未验证，因此不能在 schema 未确定时实现猜测式解析。审核通过后，所有者只能从平台登记的 DeepSeek/Kimi 模型配置中生成自研 `AgentConfiguration`；提交者不填写凭据。这一节不阻塞 Codex MVP。

## 7. Job API

任务 04 已实现创建、列表、详情及只读选项；任务 05 已注册第 7.4、7.5 节批准/拒绝路由；任务 06–08 已接通 Worker 执行、批次报告和安全证据。任务 09 已注册第 7.6 节取消路由并通过终审；任务 10 已注册第 7.7 节显式恢复/重试路由，HTTP、受控故障、隔离真实 PostgreSQL、Web build、浏览器和完整回归均已验证，证据见[任务 10 行动](../actions/2026-09-13-m1-interruption-recovery.md)。

### 7.0 查询受控提交选项

`GET /api/v1/job-options`

需要可信登录会话。成功 `200` 只返回服务端登记项：

- `batch_presets`：`demo` 1–3 题、`quick` 5 题、`standard` 10–20 题、`continuous` 1–20 题；旧预设区间不变；
- `evaluation_tracks`：当前只有 `closed_book`；
- `maximum_agent_configurations=3`、`maximum_runs=60`；
- 唯一 `limit_profiles[0].limit_profile_id=default-single-host-v1`：Agent 900 秒/1 CPU/4096 MiB/8192 MiB storage，Evaluator 300 秒/1 CPU/4096 MiB，PID 64，patch 256 KiB 警告/1 MiB 拒绝，单原始制品 50 MiB、单 Run 原始制品合计 200 MiB，并发 1、重试 0。

选项是只读公开限制，不返回凭据逻辑引用或宿主路径；页面不自行维护第二套规模/资源数字。

### 7.1 创建评测 Job

`POST /api/v1/jobs`

Header：`Idempotency-Key: <客户端生成的不透明值>`。当前接受 8–128 位 ASCII 字母、数字、点、下划线、波浪号或短横线；数据库只保存 SHA-256，不保存原值。缺少或格式错误由统一字段校验返回 422。

请求：

```json
{
  "task_ids": ["00000000-0000-0000-0000-000000000001"],
  "agent_configuration_ids": ["00000000-0000-0000-0000-000000000002"],
  "evaluation_track": "closed_book",
  "batch_preset": "demo",
  "limit_profile_id": "default-single-host-v1"
}
```

成功 `202`：

```json
{
  "job_id": "00000000-0000-0000-0000-000000000003",
  "status": "AWAITING_OWNER_APPROVAL",
  "evaluation_track": "closed_book",
  "result_scope": "official",
  "batch_preset": "demo",
  "limit_profile_id": "default-single-host-v1",
  "trial_count": 1,
  "run_ids": ["00000000-0000-0000-0000-000000000004"],
  "estimated_finish_at": null,
  "created_at": "2026-09-05T10:00:00Z",
  "owner_decided_by": null,
  "owner_decided_at": null,
  "owner_decision_reason": null,
  "cancel_requested_by": null,
  "cancel_requested_at": null,
  "cancel_reason": null,
  "failure_code": null,
  "failure_summary": null,
  "rerun_of_job_id": null
}
```

错误：

- `404 TASK_NOT_FOUND`；
- `404 AGENT_CONFIGURATION_NOT_FOUND`；
- `409 AGENT_CONFIGURATION_DISABLED`；
- `409 IDEMPOTENCY_CONFLICT`；
- `400 EMPTY_JOB_SELECTION`；
- `400 BATCH_PRESET_EXCEEDED`；
- `400 LIMIT_PROFILE_NOT_ALLOWED`；
- `400 EVALUATION_TRACK_NOT_ENABLED`。

任务和 Agent 列表必须非空、去重，并且所有 Agent 已登记启用。MVP 只接受 `closed_book`；`open_book_experimental` 仅保留 schema 接缝，请求时返回 `400 EVALUATION_TRACK_NOT_ENABLED`。每个组合只尝试一次，所以 `trial_count = task 数 × Agent 数`。预设规模：`demo` 为 1–3 题、`quick` 为 5 题、`standard` 为 10–20 题；Agent 选择上限固定为 3 个，去重后最多生成 60 条 Run。

`task_ids` 与 `agent_configuration_ids` 的每一项必须是 UUID 格式；格式错误在进入目录或 Repository 前返回 422，格式正确但未登记才返回对应 404。页面提交后把服务端返回的 `job_id` 保留在当前 URL 的 `job` 查询参数中，整页刷新按该 ID 从后端详情端点恢复，不依赖随机 UUID 的列表排序猜测“最新一批”。

幂等范围是可信 `created_by` + 哈希键。任务/配置列表在规范正文中去重并排序；相同规范正文返回原 Job，即使其配置随后禁用也不产生第二批；同键不同规范正文返回 `409 IDEMPOTENCY_CONFLICT`。新键提交仍会按当前目录状态复核，已禁用配置返回冲突。

创建事务会冻结配置并生成 `PENDING` runs，但初始 Job 必须是 `AWAITING_OWNER_APPROVAL`。这一步既不创建 Harbor Job，也不唤起 Codex。协作者能通过远程入口到达页面，不代表拥有批准权限；网络准入与应用授权是两层不同控制，远程拓扑见 [`REMOTE_TEAM_ACCESS.md`](../operations/REMOTE_TEAM_ACCESS.md)。

前端不能提交任意 CPU/内存/网络值、Harbor 并发数、代理地址、工具命令或启动命令。后端固定单机 `n_concurrent_trials=1`，根据赛道与登记配置冻结网络策略和工具配置。

### 7.2 查询 Job 列表

`GET /api/v1/jobs`

筛选：`status`、`created_by`、`evaluation_track`、`result_scope`、`cursor`、`limit`。成功 `200` 返回分页 `JobSummary[]`。

所有者可查全部或用 `created_by` 收窄；协作者始终只能得到自己提交的记录，对别人的 `created_by` 筛选返回空页。未知或重复 query 返回 `400 INVALID_REQUEST`，字段格式/枚举错误为 422。

### 7.3 查询 Job 详情

`GET /api/v1/jobs/{job_id}`

当前成功 `200` 返回：

- `JobSummary`，含可空安全失败码/摘要和 `rerun_of_job_id`；
- 冻结的任务 ID 和 Agent 配置 ID 列表；
- `limit_snapshot`、网络/工具策略 ID 与安全快照、三项固定 framework revision；
- Job 状态事件；待批只有 sequence 1 `JOB_SUBMITTED`，决定后追加批准/拒绝事件，恢复后追加 `INTERRUPTION_RECOVERED`，包含可信操作人、时间和可选安全说明；
- Run 的 ID、任务/配置 ID、状态、后端种类/revision、执行契约版本及事件；拒绝后为 `CANCELED` 并追加 `JOB_REJECTED`；
- 任务公开正文快照和配置公开身份/指纹快照。

详情另返回可空 `lease_expires_at`，供页面判断是否等待 owner 收束；它不等于失败结论。详情不返回 Worker 身份、配置凭据逻辑引用、任务源对象键、环境镜像或数据库幂等哈希。内部浏览器/存储测试由服务端装配为 `internal_test`/`mock`，客户端提交这些字段会因额外字段返回 422。协作者读取别人的 Job 与记录不存在同样返回 `404 JOB_NOT_FOUND`，所有者可读取全部。

错误：`404 JOB_NOT_FOUND`。

### 7.4 评测机所有者批准 Job

`POST /api/v1/jobs/{job_id}/approve`

Header：`Idempotency-Key: <客户端生成的不透明值>`。请求：

```json
{"reason":"已检查任务、Agent、赛道和运行数量"}
```

`reason` 可省略；填写时服务端去除首尾空白，之后必须为 1–500 个 Unicode 字符且不能含控制字符。OpenAPI 用 `x-normalization=trim` 和 `x-normalizedMinLength/MaxLength=1/500` 表达规范化后边界，不用会错误约束原始带空白输入的标准 `minLength/maxLength`。其他字段（包括 `owner_id` 或冻结值）返回 422。页面明确警告不要粘贴凭据、Token 或宿主机路径；后端不使用容易误判的启发式秘密正则扫描。

- 只接受可信登录会话中的评测机所有者；`owner_id` 不得放在请求正文中。
- 只有 `AWAITING_OWNER_APPROVAL` 可批准。成功 `200` 在一个短事务中写入 `QUEUED`、决定者、决定时间和状态事件，然后立即返回更新后的 `JobSummary`。
- 批准只开放排队资格，不读取 `auth.json`、不启动 Docker/Harbor，也不等待 Worker。评测机本地 Worker 下一次轮询时才可能领取。
- 非所有者返回 `403 OWNER_APPROVAL_REQUIRED`；记录不存在为 `404 JOB_NOT_FOUND`；Job 已被批准、拒绝或取消返回 `409 JOB_STATE_CONFLICT`。相同幂等键和相同决定正文返回原结果；同键改决定或说明返回 `409 IDEMPOTENCY_CONFLICT`。

### 7.5 评测机所有者拒绝 Job

`POST /api/v1/jobs/{job_id}/reject`

Header：`Idempotency-Key: <客户端生成的不透明值>`。请求：

```json
{"reason":"当前不批准本次真实资源消耗"}
```

- 只接受可信登录会话中的评测机所有者；只有 `AWAITING_OWNER_APPROVAL` 可拒绝。
- 成功 `200` 在同一事务中把 Job 写为 `REJECTED`、把其 `PENDING` runs 写为 `CANCELED`，并保存决定者、时间和状态事件。
- `REJECTED` 是授权决定，不是 Agent 失败或平台故障，不能进入 Worker 队列，也不能产生正式运行证据。
- 权限、状态冲突和幂等规则与批准接口相同。

### 7.6 取消 Job

`POST /api/v1/jobs/{job_id}/cancel`

Header：`Idempotency-Key: <客户端生成的不透明值>`。

请求：

```json
{"reason":"用户请求取消"}
```

- `reason` 可省略；填写时去除首尾空白，规范化后必须为 1–500 个 Unicode 字符且不能含控制字符。正文不接受其他字段。
- 成功 `202`：返回实际更新后的 `JobSummary`，包含可空的 `cancel_requested_by/cancel_requested_at/cancel_reason`。响应为 `CANCEL_REQUESTED` 只表示请求已持久化，不宣称当前 Trial 已停止；只有 `CANCELED` 才是终态。
- 协作者只能取消自己提交的 Job；`owner` 可取消任意 Job。权限来自可信会话，不接受正文中的用户或角色字段。
- 协作者访问别人的 Job 与记录不存在统一返回 `404 JOB_NOT_FOUND`，避免泄漏资源存在性。
- `AWAITING_OWNER_APPROVAL`、`QUEUED` 以及尚未启动 Trial 的 `PREPARING` 可直接变为 `CANCELED`。
- `EXECUTING` 时成功响应把 Job 置为 `CANCEL_REQUESTED`：不再启动后续 Trial，当前 Trial 不强杀，只运行到创建 Job 时冻结的超时上限并保存真实证据；随后剩余 `PENDING` runs 变为 `CANCELED`，Job 经 `FINALIZING` 收束为 `CANCELED`。
- Worker、宿主机或 Harbor 中断时不自动续跑或重试；若所有者决定重试，必须创建有 `rerun_of_job_id` 的新 Job 和新证据链。
- 相同幂等键和规范化正文返回原结果；同键异正文返回 `409 IDEMPOTENCY_CONFLICT`。使用新键重复取消、终态请求或并发状态已越过可取消窗口时返回 `409 JOB_STATE_CONFLICT`。

### 7.7 显式收束中断并新建重试

`POST /api/v1/jobs/{job_id}/recover`

请求正文必须为 `{}`，成功 `200` 返回收束后的原 `JobSummary`。只有可信 owner 可调用；仅接受 `PREPARING/EXECUTING/CANCEL_REQUESTED/FINALIZING` 且 `lease_expires_at` 已到期的 Job。事务保持已有 `COMPLETED` Run 和确定性结果，活跃 Run 写为 `FAILED / INFRASTRUCTURE_INTERRUPTED`，`PENDING` Run 写为 `CANCELED`，并追加一条 `INTERRUPTION_RECOVERED` Job 事件。取消请求中的 Job 最终为 `CANCELED`；否则有已完成结果和中断项时为 `COMPLETED_WITH_ERRORS`，没有完成结果时为 `FAILED`，全部已有可信结果时为 `COMPLETED`。重复调用同一已收束 Job 只返回当前记录，不增加事件。

该入口不会调用 ExecutionBackend、PatchEvaluator、Harbor 或模型，也不会自动重新排队。租约仍有效、状态不允许或并发已改变返回 `409 JOB_STATE_CONFLICT`；Run 完成状态与结果行、`resolved_summary`、Job 冻结的 Harness revision 或 `resolved ⇒ patch_successfully_applied ⇒ patch_exists` 任一错配时整笔回滚并返回 `503 DEPENDENCY_UNAVAILABLE`；非 owner 为 `403 OWNER_APPROVAL_REQUIRED`，未知 Job 为 404。

`POST /api/v1/jobs/{job_id}/retry`

Header：`Idempotency-Key: <客户端生成的不透明值>`；正文必须为 `{}`。只允许 owner 对含 `INTERRUPTION_RECOVERED` 事件且终态为 `FAILED/COMPLETED_WITH_ERRORS/CANCELED` 的旧 Job 手动新建重试。成功 `202` 返回全新 `AWAITING_OWNER_APPROVAL` Job：重新核对当前有效任务/配置并冻结当前快照，生成全新 Run ID，以 `rerun_of_job_id` 关联旧 Job；旧 Job 和证据不改变。新 Job 保留原 `created_by`，因此原提交者仍可按既有范围查询，首个 `JOB_SUBMITTED` 事件的操作人为发起重试的 owner。新 Job 必须再次由 owner 批准，不能复用旧执行租约。

相同幂等键和同一重试来源返回原新 Job；同键指向其他规范正文返回 `409 IDEMPOTENCY_CONFLICT`。原配置已禁用时返回 `409 AGENT_CONFIGURATION_DISABLED`。请求不能指定用户、Worker、状态、旧 Job、资源、目录快照或任何执行参数。

## 8. Run API（逐题只读）

`GET /api/v1/runs`

筛选：`job_id`、`status`、`task_id`、`agent_configuration_id`、`resolved`、`review_status`、`cursor`、`limit`。成功 `200` 返回分页 `RunSummary[]`。

`GET /api/v1/runs/{run_id}`

成功 `200` 至少返回：`RunSummary`、冻结任务/Agent 快照、后端 Job/Trial 安全引用、限制、确定性结果、版本化 Judge 分析列表、人工复核和制品链接。错误：`404 RUN_NOT_FOUND`。

普通用户不能直接 `POST /runs`。运行只能由创建 Job 的同一事务按任务×Agent 组合生成，避免绕过规模、赛道和并发规则。

## 9. Trajectory 与 Artifact API

### 9.1 分页读取规范化轨迹

`GET /api/v1/runs/{run_id}/trajectory`

输入：`after_sequence`（可选，默认 0）、`limit`（1–500）、`type`（可选）。

成功 `200`：

```json
{
  "items": [
    {
      "sequence": 1,
      "occurred_at": "2026-09-01T10:00:01Z",
      "source": "codex",
      "type": "tool_call",
      "summary": "执行仓库搜索",
      "payload": {}
    }
  ],
  "next_after_sequence": 1,
  "complete": false
}
```

页面展示的是已脱敏规范化事件，不直接返回思维链或未经审查的原始日志。

### 9.2 查询制品索引

`GET /api/v1/runs/{run_id}/artifacts`

输入：可选 `artifact_type`（当前数据库闭合枚举中的任一 Run 制品类型）、UUID `cursor`、`limit`（1–100）。成功 `200` 返回 `items/next_cursor`；每项含 `artifact_id/artifact_type/content_type/size_bytes/sha256/created_at/redaction_status/warnings/retention_class/original_size_bytes/truncated/expires_at/deleted_at/deleted_by/deletion_reason/content_status`。`content_status` 只允许 `available/not_ready/deleted`；原始 `raw_30d` 的正文始终是 `not_ready` 或 `deleted`，但有权用户仍可查询上述安全元数据。响应不返回原文件名、对象键、MinIO secret、宿主路径或正文片段。

### 9.3 下载制品

`GET /api/v1/artifacts/{artifact_id}/content`

- 成功 `200`：后端只返回 `agent_patch/public_test_summary/public_trajectory` 三种公开证据，并设置受控 `Content-Type`/`Content-Disposition`；当前实现以完整校验后的响应返回，未来有数据量证据再改流式传输。
- 错误：不存在或无权查看统一 `404 ARTIFACT_NOT_FOUND`；受限制原始/私有类型统一 `409 ARTIFACT_NOT_READY`；已按保留策略删除的正文返回 `410 ARTIFACT_CONTENT_DELETED`，不返回假空文件；记录宣称正文存在但对象错配、损坏、缺失或存储不可用时返回 `503 DEPENDENCY_UNAVAILABLE`。
- 候选 v0.1 不把 MinIO 管理凭据交给浏览器；未来若改为短时预签名 URL，需要单独记录安全决定。
- HTTP API 不提供制品删除入口；MVP 仅允许 `owner` 在评测机执行本机维护命令清理到期原始制品。

## 10. Report 与 Leaderboard API

### 10.1 Job 报告

`GET /api/v1/reports/jobs/{job_id}`

任务 07 的成功 `200` 返回 `job_id/status/stage_message/failure_code/trial_count/completed_runs/failed_runs/pending_runs/resolved_runs/unresolved_runs/runs`。每个 Run 项包含 `run_id/status/stage/stage_message/task_instance_id/agent_configuration_id/agent_display_name/outcome/resolved/failure_code/report_path`。`outcome` 只允许 `resolved/unresolved/infrastructure_error/incomplete`；安全阶段来自持久化状态，不回传 Harbor 日志、秘密路径或凭据。

全部 Run 形成可信确定性结果时 Job 为 `COMPLETED`；至少一个可信结果且另有运行或协议错误时为 `COMPLETED_WITH_ERRORS`；完全没有可汇总结果才为 `FAILED`。`resolved=false` 仍是正常完成，不计入 `failed_runs`；`CANCELED` 属于 `incomplete` 并计入 `pending_runs`。终态 Run 的 `report_path` 可进入既有单次运行报告；报告服务在返回确定性成功前继续复核全部关联对象正文。生产报告查询默认只接受 `result_scope=official`，对 `internal_test` 的 Job 与 Run 均按不存在返回 404；仅显式门控的测试装配可注入内部范围谓词，正式运行配置不能切换该边界。

批次尚未进入终态时，本端点仍返回 `200`：`stage_message` 说明当前阶段，`completed_runs`/`failed_runs`/`pending_runs` 按 Run 状态计数；尚无确定性结果的 Run 记 `outcome=incomplete`、`resolved=null`，不写入 `resolved_runs`/`unresolved_runs`。未完成**不是** `404`（那表示不存在或无权，含 `internal_test`），也**不是** `409`。`report_path` 是通往单 Run 报告的链接，不代表结果已经可用。已取消与已请求取消的批次同样返回 `200` 与明确的 `stage_message`。该行为由 `tests/jobs/reporting/test_job_report_states.py` 钉住（`AWAITING` 的 200 形状与 `incomplete`/`resolved=null`、`QUEUED` 与 `PREPARING` 仍可读、对比接口接受未出结果的批次、`internal_test` 仍是 404、`CANCELED` 与 `CANCEL_REQUESTED` 的 200 与文案），不要把它当缺陷改回去。

`stage_message` 的状态映射**必须覆盖 `JobStatus` 的每一个取值**：映射在 `routes/jobs/batch_schemas.py`，漏掉任何一个都会让只读端点抛未捕获异常并返回 `500 INTERNAL_ERROR`（2026-09-22 的 `CANCELED`/`CANCEL_REQUESTED` 即如此）。完整性由 `tests/jobs/reporting/test_batch_status_messages.py` 逐个断言，运行时另有一句中性兜底文案。

### 10.2 单次运行报告

`GET /api/v1/reports/runs/{run_id}`

成功 `200` 分层返回：

```json
{
  "run": {
    "run_id": "...",
    "job_id": "...",
    "status": "COMPLETED",
    "stage": "completed",
    "task_instance_id": "example__repo-1",
    "agent_configuration_id": "...",
    "backend_job_ref": "harbor-job-one",
    "backend_trial_ref": "harbor-trial-one",
    "failure_code": null,
    "failure_summary": null,
    "started_at": "2026-09-12T12:00:00Z",
    "finished_at": "2026-09-12T12:00:00Z",
    "warnings": []
  },
  "deterministic_result": {
    "patch_exists": true,
    "patch_successfully_applied": true,
    "resolved": true,
    "tests_status_summary": {},
    "harness_revision": "fixed-fork-commit",
    "duration_ms": 125
  },
  "process_metrics": {
    "usage": {"n_input_tokens": null, "n_cache_tokens": null, "n_output_tokens": null, "cost_usd": null},
    "resources": {"wall_time_sec": null, "cpu_time_sec": null, "peak_memory_bytes": null}
  },
  "judge_analyses": [],
  "human_review": null,
  "quality_tiebreak": null,
  "review_status": "NOT_REQUIRED",
  "artifact_links": []
}
```

`judge_analyses` 中每项显式区分 `failure_diagnosis` 与 `quality_tiebreak`，并返回状态、模型/Prompt/输入策略版本和证据引用。规则：`deterministic_result`、`process_metrics`、`judge_analyses`、`human_review` 不合并为一个模糊的“总评价”；确定性结果是第一排序事实，Quality 只作为严格并列次序，Failure 不参与排名。

`process_metrics.usage` 的字段是 `n_input_tokens`/`n_cache_tokens`/`n_output_tokens`/`cost_usd`，`process_metrics.resources` 的字段是 `wall_time_sec`/`cpu_time_sec`/`peak_memory_bytes`；任一项不可得时为 `null`（**不是 0**，聚合口径见第 10.3 节的覆盖率三档）。`run.warnings` 是本次运行的非致命告警列表，无告警时为空数组。

M1 保留上述响应兼容形状，但 `judge_analyses=[]`、`human_review=null`、`quality_tiebreak=null`、`review_status=NOT_REQUIRED`；不为填充字段调用模型或新建分析/复核表。基础设施失败时 `deterministic_result=null`，并在 `run.failure_code/failure_summary` 明确说明，不能冒充普通 `resolved=false`。

`failure_code` 是受控枚举；`failure_summary` 与 `stage_message` 是**面向用户的受控短文案**，只允许说明失败类别与阶段，不得包含上游主机名或 URL、文件系统路径、凭据 profile 名、令牌或 Key 的任何片段、容器与网络拓扑。这两个字段会被网页原样呈现（恢复页把 `failure_summary` 标为“安全原因”），**内容安全由写入方负责**；Web 层不猜测自由文本是否安全，只按本节契约呈现。

任务 05 策略切片当前固定的 provider 失败码为 `PROVIDER_CREDENTIAL_UNAVAILABLE`、`PROVIDER_ACCESS_DENIED`、`PROVIDER_REQUEST_REJECTED`、`PROVIDER_BUDGET_EXHAUSTED` 与兜底 `PROVIDER_ACCESS_FAILED`。它们已由内部异常映射测试约束，但策略尚未接入 Worker/HTTP 执行路径，因此当前公开 API 不会因为真实第三方调用产生这些码；后续接线必须沿用这些安全码，不回显原始异常。

提供方访问失败在 Run 上只有五个受控 `failure_code`，与固定短句一一对应；映射表是 `provider_access/failures.py` 的 `_GROUPS` 与 `GENERIC_FAILURE`：

| `failure_code` | `failure_summary` | 归入此码的内部错误族 |
|---|---|---|
| `PROVIDER_CREDENTIAL_UNAVAILABLE` | 模型凭据不可用，运行未开始。 | `PRIVATE_FILE_*`、`PRIVATE_PROFILE_*`、`PRIVATE_SECRET_EMPTY`、`PRIVATE_ACCESS_UNVERIFIABLE`、`PRIVATE_UPSTREAM_NOT_REGISTERED`、`TRANSPORT_CREDENTIAL_EMPTY` |
| `PROVIDER_ACCESS_DENIED` | 模型访问未获授权。 | `PROVIDER_UNREGISTERED`、`PROVIDER_BINDING_*`、`PROVIDER_TOKEN_*`、`TRANSPORT_PROVIDER_UNREGISTERED` |
| `PROVIDER_REQUEST_REJECTED` | 模型请求不符合受限策略。 | `REQUEST_*`、`TRANSPORT_PAYLOAD_NOT_SERIALIZABLE`、`TRANSPORT_REDIRECT_NOT_PERMITTED`、`TRANSPORT_RETRY_NOT_PERMITTED`、`TRANSPORT_UPSTREAM_NOT_ENCRYPTED` |
| `PROVIDER_BUDGET_EXHAUSTED` | 运行额度或期限已用尽。 | `BUDGET_*` |
| `PROVIDER_ACCESS_FAILED` | 模型访问未完成。 | 兜底：任何未映射的内部错误码 |

规则：①**内部错误码绝不回显**——它未经发布审查，部分就在文件路径与凭据 profile 名旁边抛出；未映射的内部码一律落到 `PROVIDER_ACCESS_FAILED`。②只在代理自身配置阶段可能抛出、运行无法触发的码（`BUDGET_LIMITS_INVALID`、`REQUEST_POLICY_*`）**不在本表**。③新增内部码必须先在本节做出归类决定，再由 `tests/providers/policy/test_controlled_failures.py` 的词汇表门禁守住。④本表只管**提供方访问**失败；Job 级的 `BATCH_PARTIAL_FAILURE` / `BATCH_FAILED` 是另一来源，不在本表。

实现状态：映射表与词汇表门禁已在 `main`；代理链本身尚未接入运行主链路，属任务 05 未完成部分——本表是已冻结的契约词汇，不代表已生效。

`artifact_links` 返回当前 Run 全部闭合类型的第 9.2 节安全元数据形状，便于页面同时展示核心证据与受限原始制品的保留状态；这不扩大正文权限，下载仍只允许 `agent_patch/public_test_summary/public_trajectory` 三种公开类型。两个报告端点及制品索引、轨迹和下载采用同一授权：owner 可读全部，协作者只读自己创建的 official Job/Run，其他资源按不存在处理，`internal_test` 只允许显式测试装配。对象键、文件名、正文、消息正文、工具参数、私密轨迹和原始配置均不在元数据响应中。

### 10.3 排行榜

任务 11 已注册本节 GET；任一有效 owner/collaborator 会话可读正式团队汇总。M1 的 `quality_tiebreak=null`，确定性并列保持并列；以下 Quality 触发/比较细节属于后续契约。过程指标继续只展示、不参与排序。

`GET /api/v1/leaderboard`

输入：必需的 `evaluation_track=closed_book`、`dataset_id`、`dataset_revision`、`split`；可选 `repo`、`tool_profile_id`、64 位小写十六进制不透明 `cursor` 和 `limit`（默认 20，1–100）。未知参数、重复参数、未知游标或未启用赛道返回 `400`；字段缺失/格式错误返回 `422`；无会话返回 `401`；数据库或冻结证据损坏返回安全 `503`。查询 SQL 固定排除 `result_scope=internal_test`，并先用目录 Task 范围筛选、再核对完整冻结 Task/Agent/策略/限制和 Harbor 执行身份；HTTP 没有打开内部范围的参数。

比较范围是数据集 ID/revision/split/repo、赛道、网络/工具/限制 ID 与完整快照、Harbor/SWE-Gym/SWE-Bench Fork revision 和执行契约版本的精确组合；不同组合各自排名。完整 Agent 身份包含配置 ID、公开显示名、Agent 类型/版本、模型提供方/模型、reasoning effort 与配置 fingerprint，不返回 authentication/credential profile。

只有 `started_at` 非空的正式 Run 才能让完整 Agent 配置进入榜单；待批准即取消或从未启动的配置不产生参赛行。同一配置未开始的其他题仍留在全题分母并记 unknown，但不产生来源或过程指标。对同一比较范围、题目和完整 Agent 配置，最早的可信确定性结果固定为该题结果；后续重复 Job 或关联重试不能覆盖它，只能填补原来没有确定性结果的题。仍没有确定性结果时使用最新已开始终态 Run 分类，`FAILED` 为基础设施错误，取消或没有尝试为未知。分母是该数据集范围的全部不同目录题目，不只统计完成项；`resolved_rate=resolved_count/total_tasks`。同一范围只按 `resolved_count` 排名，同分共享名次；游标的稳定顺序不产生胜负。

响应为 `{items, next_cursor}`；每行当前包含：

- `rank`、完整 `agent` 与完整 `comparison_scope`；
- `total_tasks/deterministic_count/resolved_count/unresolved_count/infrastructure_error_count/unknown_count/resolved_rate`；
- `sources[]`，逐个列出纳入尝试的 `task_id/instance_id/job_id/run_id/rerun_of_job_id/classification`；
- 可空 `quality_tiebreak`：只在严格可比且逐题 `resolved` 向量完全相同的并列组中返回；包含匿名比较映射的安全摘要、四项 rubric、A/B 与 B/A 两次结论、胜/平/负和循环赛积分、版本与状态；不适用或 Judge 不可用时为 `null` 并保持并列；
- `process_metrics.selected_runs`，以及 input/cache/output token、cost、wall/cpu time、peak memory 的 `{value, coverage}`；任一选中 Run 缺该字段时 `value=null`，coverage 仍返回实际覆盖数；
- `generated_at` 和分页 `next_cursor`。空结果是 `200 {"items":[],"next_cursor":null}`。

同一 Agent 使用不同模型提供方、模型或关键配置时必须分行。

Quality Judge 的触发由后端判定，浏览器不能通过 query 强迫运行。严格可比要求数据集/版本、题目集合、赛道、Harness、尝试数和限制一致；候选 Agent 的逐题 `resolved` 向量完全相同，并且至少存在一道共同通过且有有效 patch 的题。仅总通过率相同但失败题不同，不触发 Quality Judge。输入只包含共同通过题上经过裁剪、脱敏、去重和限量的任务需求、最终 patch、确定性测试摘要与必要轨迹摘要；不把候选身份或顺序映射交给 Judge。

每对候选按“任务匹配与最小修改、可读性与可维护性、稳健性、副作用风险”四项 rubric 比较，并以 A/B 和 B/A 反序各运行一次；两次都指向同一候选才产生胜者，否则该对并列。三个及以上候选采用循环赛，胜 1 分、平 0.5 分、负 0 分。证据清洗失败、模型超时或输出无效时不产生并列次序。

MVP 排行榜只接受 `evaluation_track=closed_book`。数据模型保留 `open_book_experimental`，但创建和查询均返回未启用；未来启用时只允许平台统一 Web 工具并与闭卷严格分榜，不使用各 Agent 各自的原生搜索工具。

### 10.4 跨批次对比报告

`GET /api/v1/reports/comparisons?job_ids=<uuid>,<uuid>,...`

该端点已经注册并由扩展任务 03 的“对比报告”页接入，用于把已有 Job 报告只读聚合成题目×配置矩阵。页面只允许选择 `GET /jobs?limit=20` 返回的当前可见首屏，不宣称按创建时间排序；刷新、选择和生成对比均不改变 Job。

- query 必须且只能出现一次 `job_ids`；未知参数、重复参数、空选择或非法 UUID 返回 `400`。逗号分隔项会去首尾空白、规范化为小写 UUID，并按首次出现顺序去重；去重后最多 20 个 Job。
- owner 可比较全部 official Job；collaborator 只能比较自己创建的 Job。任一 Job 不存在、无权访问或为 `internal_test` 时，整个请求返回 `404 JOB_NOT_FOUND`，不泄漏具体哪一项存在。
- 成功 `200` 返回 `{columns, rows, totals}`。`columns[]` 包含 `job_id/agent_configuration_id/agent_display_name`；`rows[]` 按 `(repo, task_instance_id)` 稳定排序，并包含同序 `cells[]`；不同仓库的同名实例不得合并。
- `cells[].outcome` 只允许 `resolved/unresolved/infrastructure_error/incomplete/missing`。`missing` 表示该列没有对应 Run，或 Run 已完成但报告不可用；其 `resolved` 和 `report_path` 必须为 `null`，不能冒充未通过或零。没有 Run 时 `run_id=null`，有 Run 但报告缺失时保留该 `run_id`。单元格另带 `failure_code`（受控枚举，见第 10.2 节；无失败时为 `null`）。
- `totals[]` 与列一一对应，包含五档计数以及整数 `decided`、`total`；`decided=resolved+unresolved+infrastructure_error+incomplete`，`total=decided+missing`。v1 不返回字符串覆盖率，也不包含计费或 Judge 分。
- 无会话返回 `401`；数据库或报告读取不可用返回 `503 DEPENDENCY_UNAVAILABLE`。响应沿用 `Cache-Control: no-store` 与统一错误形状。
- Web 在矩阵成功后以最多 3 个并发请求读取所选列的 `GET /jobs/{job_id}` 冻结快照；用量须由用户明确点击后，才以最多 3 个并发请求读取有 `report_path` 的 `GET /reports/runs/{run_id}`。矩阵缺失单元格及任一 Run 指标 `null` 都保持未知；只有每个组成单元格都有值才显示“总量”，否则显示“部分”或“未知”。
- 单元格只有同时具有 `run_id` 与 `report_path` 时提供“查看单次证据”，随后复用第 10.1 节 Run 报告、第 9 节轨迹与公开制品下载；`missing` 没有伪造按钮。成本只显示报告中的 USD，墙钟明确为各 Run 用时之和而非整批墙钟。

## 11. Human Review API

本节全部接口在 M1 后启用；M1 不注册这些路由，也不显示工作台或要求相应数据库表。普通安全证据查看仍由 Run/Report/Artifact 接口提供。

### 11.1 查询待复核队列

`GET /api/v1/reviews`

输入：`status`、`review_kind=failure|quality`、`cursor`、`limit`。成功 `200` 返回待复核运行或 Job 级质量比较摘要和证据链接。

### 11.2 提交或修订人工复核

`PUT /api/v1/reviews/{run_id}`

Header：`Idempotency-Key`。

请求：

```json
{
  "judge_assessment": "CONFIRMED",
  "corrected_failure_category": null,
  "notes": "确定性测试和轨迹证据一致",
  "expected_version": 1
}
```

成功 `200` 返回版本化 `HumanReviewRecord`。错误包括：

- `404 RUN_NOT_FOUND`；
- `409 REVIEW_NOT_PENDING`；
- `409 REVIEW_VERSION_CONFLICT`；
- `422 VALIDATION_ERROR`。

上例只覆盖 `failure_diagnosis` 的复核。只有 `owner` 可以人工复核；`reviewer_id` 来自可信会话。

Quality Judge 使用 Job 级接口 `PUT /api/v1/reviews/jobs/{job_id}/quality/{comparison_key}`，请求只允许 `judge_assessment=CONFIRMED|INVALIDATED`、`notes` 和 `expected_version`。`CONFIRMED` 保留自动结论；`INVALIDATED` 把该比较恢复为并列并保留原始 Judge 证据。所有者不能手工指定胜者、修改循环赛分数或把 Failure 字段复用于质量比较。

任务 01 的身份实现见第 3.2 节；邀请、业务授权和真实平台验证尚未完成前，不开放后续业务接口到远程环境。此处保留的复核接口在 M1 不注册。

## 12. HTTP interface 到内部模块的映射

| HTTP 资源 | 只允许调用的应用模块 |
|---|---|
| `/auth/login`、`/auth/logout`、`/auth/me` | 既有单体内的身份用例，只获取可信应用身份，不操作评测凭据 |
| `/tasks` | Task Catalog 查询 |
| `/agent-configurations` | Agent Registry 查询 |
| `/agent-submissions` | P2 Agent Source Review；MVP 不注册路由，P2 批准/拒绝只允许所有者 |
| `POST /jobs` | Job Submission |
| `GET /jobs*` | Reporting / Job Repository 只读查询 |
| `POST /jobs/{id}/approve`、`POST /jobs/{id}/reject` | Owner Approval；只允许评测机所有者 |
| `POST /jobs/{id}/cancel` | Job lifecycle 用例 |
| `POST /jobs/{id}/recover`、`POST /jobs/{id}/retry` | Job Recovery；仅 owner 显式收束过期执行或创建关联新 Job |
| `GET /runs*` | Reporting / Run Repository 只读查询；不存在普通用户创建接口 |
| `/trajectory`、`/artifacts` | Reporting + Artifact Store 只读读取 |
| `/reports`、`/leaderboard` | Reporting |
| `/reviews` | M1 后的 Human Review；启用后只允许所有者 |

FastAPI route 文件只做 schema、HTTP 状态和用例调用，不能直接启动 Docker 或调用 SWE-Bench-Fork。

## 13. 接口验证

实现后至少执行：

1. OpenAPI schema 快照检查；本文示例与 schema 的字段/状态码对照。
2. Next.js 使用由 OpenAPI 生成或同步的 TypeScript 类型，避免手写两套字段。
3. 每个端点覆盖成功、资源不存在、schema 错误和状态冲突。
4. 确认 Task/Agent 接口不泄漏 gold patch、隐藏测试、任务原始快照中的评测专用字段、启动命令和秘密；MVP 的 OpenAPI 不出现 `/agent-submissions`，只能选择项目已登记 Agent。
5. 创建 Job 响应不等待 Worker；任务×Agent 生成正确 `trial_count` 和 `run_id`，初始状态只能是 `AWAITING_OWNER_APPROVAL`。
6. 排行榜按完整 Agent 配置分组并单列基础设施错误；`internal_test` 永远被排除。
7. 原始制品下载不暴露 MinIO 管理凭据，轨迹默认已脱敏。
8. 创建 Job 冻结赛道/网络/工具/Harbor/Fork 版本；MVP 只允许 `closed_book`，`open_book_experimental` 创建和查询均明确返回未启用。
9. 普通用户无法 `POST /runs`、设置 Harbor 并发或提交任意资源值；单机并发 1 由后端配置。
10. 没有公开注册；协作者不能批准自己的正式真实 Job、管理成员/配置或清理制品；只有绑定的唯一评测所有者会话能执行这些操作，并发决定只有一个成功，决定者和时间可审计。M1 不开放任何人工复核路由。
11. 批准只产生 `QUEUED`，不会在 HTTP 请求中运行 Harbor；拒绝后 Worker 永远领取不到，批准后轮询可观察后续状态。
12. Job 请求不能携带模型 Key、任意提供方/Base URL 或 shell；MVP 不提供自研源码提交路由。P2 自研配置只由所有者登记为 DeepSeek/Kimi，二者分别排行。
13. M1 验证分析列表为空、复核与质量比较字段为空、`review_status=NOT_REQUIRED`，且无 Judge 调用或复核路由；后续启用时另验第 10.3/11 节的触发、比较和复核规则。
14. 过程指标永不参与排序，缺失显示未知而不是 0；M1 确定性并列保持并列，后续所有者作废 Quality 结论也不得指定胜者。
15. 执行中取消进入 `CANCEL_REQUESTED`、不再启动新 Trial，当前 Trial 只到冻结超时；宿主/Worker/Harbor 中断不自动续跑或重试。过期 Job 只由 owner 显式收束；完成结果保持不变、未完成 Run 记基础设施中断，关联新 Job 重新等待批准。
16. patch 超过 256 KiB 有警告、超过 1 MiB 或为二进制时明确拒绝且不截断；原始日志 50 MiB、每运行原始制品 200 MiB 的边界和截断标记可由接口观察。
17. 到期原始制品只能由所有者本机清理；正文删除返回 `410`，索引仍保留哈希、大小与删除审计。

## 14. 待技术核验

1. 任务 01/02 验收及评审发现处理已完成；任务 02 的真实 PostgreSQL 并发/回滚证据，见第 3.3 节行动指针。长期数据库/远程入口验收仍未完成。
2. 任务 09 已实现 `CANCEL_REQUESTED` 的固定 Harbor 协作式准入；任务 10 已实现 owner 显式过期租约收束与关联新 Job，分层验收与双轴终审均已通过并记录在独立行动中，业务行为不改为强杀或自动重试。
3. M1 后再核验 Quality Judge 的具体模型、Prompt 和结构化响应 Schema；原触发与复核规则保留，不阻塞当前 M1。
4. 轨迹刷新是否在数据量证明轮询不足后升级 SSE；当前不提前引入。
5. 任务 12 已用合成 HTTP/Web、临时 PostgreSQL/MinIO 和本机 CLI 验证 patch/原始制品边界、状态与清理参数；真实 Harbor 制品规模仍待后续获准运行测量。
6. 任务 13 的 `-04` 真实 HTTP 提交只创建等待批准 Job，owner 批准后 Worker 才执行；同一 HTTP Interface 读回 Job/Run `COMPLETED`、固定 Fork `resolved=true`、一个正式排行来源及安全制品元数据。真实浏览器随后完成登录、Job 详情和报告核对，最终摘要 `status=passed/phase=complete/cleanup=verified`；这证明固定单题本机闭环，不扩展为长期远程部署或全部网络风险通过。
7. P2 自研 Agent 提交 schema 和受控 DeepSeek/Kimi 访问；不阻塞 MVP。

## 15. 变更记录

- 2026-09-22：OpenAPI 字段级对账。用 `create_runtime_app()` 读实时 OpenAPI（29 个路径、59 个 schema 组件），与 §4.1/§4.2/§4.3/§9.2/§10.1–§10.4 的示例和正文逐字段比对；补写三处契约缺口：§4.3 的 `JobSummary` 示例补上 `cancel_*`/`failure_*`/`rerun_of_job_id` 六个字段（实现与第 7 节示例本就有，属文档内部不一致）、§10.2 写明 `process_metrics` 两组字段名与 `run.warnings`（原文示例是空对象、字段名在契约里没有定义）、§10.4 写明单元格的 `failure_code`。
- 2026-09-22：修复只读端点 500——批次报告的 `stage_message` 映射漏了 `CANCELED` 与 `CANCEL_REQUESTED`（`JobStatus` 有 11 个取值、映射只有 9 条），取 `_JOB_MESSAGES[job.status]` 抛未捕获 `KeyError`。已补齐两条文案并把两处取值改为带中性兜底（展示文案不该让只读端点 500）；第 10.1 节补写“已取消与已请求取消同样返回 200”，并注明映射完整性由测试逐个钉住。定位依据是 B 在脱离版录制中留下的两份 500 响应。
- 2026-09-22：第 10.1 节补写"批次未进入终态仍返回 `200`"的契约（阶段文案与状态计数、`outcome=incomplete`/`resolved=null`、未完成既不是 404 也不是 409、`report_path` 不代表结果可用），并注明该行为由回归测试钉住。依据：D 用同一装配在 `official` 作用域实测 `AWAITING`/`QUEUED`/`PREPARING` 三种状态均 200，且 `application/reporting/service.py` 的 `_verify` 在 `deterministic_result is None` 时提前返回；B 在 `internal_test` 作用域复测同样 200。
- 2026-09-21：任务 05 对齐受控词汇——第 10.2 节列出提供方访问失败的五个受控 `PROVIDER_*` 码、各自归入的内部错误族与“内部码绝不回显、未映射落兜底”规则；第 4.2 节与第 6 节把 `agent_type`/`model_provider` 记为受控集合、按记录如实呈现（含 `internal_test_fake`）、超出集合失败关闭，并明确 `authentication_type`/凭据 profile/固定上游不在响应中。
- 2026-09-13：任务 12 扩展制品安全元数据，增加 `available/not_ready/deleted` 和已删除正文 410；保留公开三类正文白名单，未增加 HTTP 删除入口。
- 2026-09-09：按总架构阶段决定标注后续 Judge/复核接口；M1 保留兼容空字段、关闭复核路由与工作台，所有者批准和安全证据查看不变。

- 2026-09-01：创建候选 v0.1；定义任务、Agent 配置、运行、轨迹、制品、报告、排行榜和人工复核接口，并明确错误、幂等、防泄漏和模块映射。
- 2026-09-02：创建运行与排行榜加入评测赛道；闭卷主榜、开卷实验榜及不同网络/工具配置禁止混合聚合。
- 2026-09-03：以 `/jobs` 作为批量提交与排队主资源，`/runs` 改为逐题只读资源；加入可信 Agent 源码提交审核、Job 报告、组合规模与 `internal_test` 隔离规则。
- 2026-09-05：远端提交改为创建 `AWAITING_OWNER_APPROVAL`；新增评测机所有者批准/拒绝接口，只有批准才进入 `QUEUED`，网络成员身份不替代应用授权。
- 2026-09-05：Agent 提交收窄为首版 Python 进程 Interface，自研配置只允许 DeepSeek/Kimi 且不接收 Key；报告与排行榜区分 Failure/Quality Judge，并固定严格并列触发和 Judge 失败保持并列。
- 2026-09-05：MVP 收窄为 Codex 闭卷平台闭环；固定协作者/唯一评测所有者两类角色、执行中取消与不自动重试、Quality 匿名反序比较、过程指标仅展示、制品限额/保留和 P2 自研 Agent 接缝。
