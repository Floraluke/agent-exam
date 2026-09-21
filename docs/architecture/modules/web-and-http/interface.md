# Web 与 HTTP Module：接口索引

> 状态：2026-09-20 建立。本文是 B 模块的接口**索引与调用面约定**，不是契约副本。
>
> 权威边界：[`HTTP_API.md`](../../../interfaces/HTTP_API.md) 是端点、请求/响应形状、字段、错误码、Cookie/Origin 规则的**唯一事实源**；模块职责与依赖方向由 [`MODULE_CONTRACTS.md`](../../MODULE_CONTRACTS.md)、架构与文件树由[本模块架构](ARCHITECTURE.md)维护。本文只回答"哪些接口由 B 的层承接、调用面有哪些硬规则"；**任何字段/错误/权限细节如与 `HTTP_API.md` 冲突，一律以 `HTTP_API.md` 为准**，并按下节流程修正本文。

## 1. 调用面硬规则（不新增重复定义）

1. 浏览器只请求站点同源 `/api/v1/*`；非只读请求带固定写入标记，Cookie 为 `credentials: same-origin`。
2. FastAPI 只做 schema、HTTP 状态和用例调用：不执行 Agent、不拼 SQL、不返回对象键或 MinIO 凭据。
3. 领域错误由 `delivery/http/errors.py` 统一转成稳定 `error.code`（形状见 `HTTP_API.md` 第 3 节）；路由不自定义错误正文。
4. **未知或畸形响应失败关闭**：前端解析器遇到不认识的形状、缺失字段或非预期状态码时，收敛为不可用并提示，**不猜测成功、不用默认值补齐**。缺失一律显示"未知"而不是 0。
5. 后端未注册的能力，产品 UI 不显示按钮或交互；导航、菜单、向导步骤等本地动作不得声称业务事实已改变。
6. 所有业务权限由服务器再次判断；前端隐藏只改善体验，不构成授权。

## 2. B 的 HTTP 层承接的端点（共 32 项）

下表只列**方法 + 路径**这一层标识，用于确认哪些调用面归本模块承接；用途、权限、请求/响应形状、错误码的权威行在 `HTTP_API.md` §2.1 与对应章节，**本文不复制**。

| 族 | 端点数 | 路径 | 权威章节 |
|---|---:|---|---|
| 身份 | 3 | `POST /api/v1/auth/login`、`GET /api/v1/auth/me`、`POST /api/v1/auth/logout` | §2.1、§3.2 |
| 邀请与成员 | 6 | `POST /api/v1/invitations`、`POST /api/v1/invitations/redeem`、`GET /api/v1/invitations`、`POST /api/v1/invitations/{invitation_id}/revoke`、`GET /api/v1/members`、`POST /api/v1/members/{user_id}/disable` | §2.1、§3.3 |
| 任务与配置目录 | 7 | `POST /api/v1/tasks/register`、`GET /api/v1/tasks`、`GET /api/v1/tasks/{task_id}`、`POST /api/v1/agent-configurations`、`GET /api/v1/agent-configurations`、`GET /api/v1/agent-configurations/{configuration_id}`、`POST /api/v1/agent-configurations/{configuration_id}/disable` | §2.1、§5、§6 |
| Job 提交与生命周期 | 9 | `GET /api/v1/job-options`、`POST /api/v1/jobs`、`GET /api/v1/jobs`、`GET /api/v1/jobs/{job_id}`、`POST /api/v1/jobs/{job_id}/approve`、`POST /api/v1/jobs/{job_id}/reject`、`POST /api/v1/jobs/{job_id}/cancel`、`POST /api/v1/jobs/{job_id}/recover`、`POST /api/v1/jobs/{job_id}/retry` | §7 |
| 报告与对比 | 3 | `GET /api/v1/reports/jobs/{job_id}`、`GET /api/v1/reports/runs/{run_id}`、`GET /api/v1/reports/comparisons` | §10.1、§10.2、§10.4 |
| 证据与制品 | 3 | `GET /api/v1/runs/{run_id}/artifacts`、`GET /api/v1/runs/{run_id}/trajectory`、`GET /api/v1/artifacts/{artifact_id}/content` | §9 |
| 排行榜 | 1 | `GET /api/v1/leaderboard` | §10.3 |

族内端点数合计 3+6+7+9+3+3+1 = **32**，与 `HTTP_API.md` §2.1 的已注册端点数一致。族划分只是本文的阅读辅助，不改变 `HTTP_API.md` 的行级权威。

**明确未注册、产品 UI 不得提供入口**：`/agent-submissions*`、`/reviews*`、普通用户 `POST /runs`，以及第 8 节保留形状中的通用 `GET /runs` / `GET /runs/{run_id}`。HTTP 也没有制品删除接口。

## 3. 稳定 DTO 与前端解析

- 后端 DTO 都带显式响应模型，OpenAPI 是前后端的共同形状来源；Web 侧运行时解析器（`apps/web/src/lib/*-shapes.ts`）只做**校验**，不重新定义字段含义、不做业务推断。
- 不透明标识（`{job_id}`、`{run_id}`、`cursor`、`task_instance_id`）一律当字符串传递，不从 UUID 推断创建时间或顺序。
- 写请求使用幂等键；同一未决正文复用同一个键，成功或明确改变输入后才换键。
- 成功后重新读取服务器事实，不用乐观状态冒充完成。

## 4. 契约变更流程

1. 发现需要新端点或字段变化：先在 `HTTP_API.md` 更新契约并说明理由，不在 Web 或路由里先造成既成事实。
2. 需要新增公共 Interface、Module、数据库表或顶层目录：按项目规则先说明现有能力为何不能承载并取得用户确认。
3. 契约与实现不一致时：**先查明真实状态，只报告，不擅自改契约**；确认后在同一变更批次内同步 `HTTP_API.md`、本文件（如需）、任务单与行动记录。
