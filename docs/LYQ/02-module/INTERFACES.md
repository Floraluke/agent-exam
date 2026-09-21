# 接口清单：目录与配置

> 这是我个人的清单，不是权威正文。权威位置：[HTTP_API.md](../../interfaces/HTTP_API.md)（HTTP）、[MODULE_CONTRACTS.md](../../architecture/MODULE_CONTRACTS.md)（模块 Interface）。

## 1. HTTP 端点（从 `delivery/http/routes/catalog.py` 逐条核对）

| 方法 | 路径 | 成功状态 | 作用 | 谁能调 |
|---|---|---|---|---|
| POST | `/api/v1/tasks/register` | 201 | 按 `preset_id` 登记一道题 | owner |
| GET | `/api/v1/tasks` | 200 | 题目列表（`cursor`、`limit`、`dataset_id`、`split`、`repo`） | 已登录 |
| GET | `/api/v1/tasks/{task_id}` | 200 | 题目详情 | 已登录 |
| POST | `/api/v1/agent-configurations` | 201 | 按 `preset_id` 登记一个配置 | owner |
| GET | `/api/v1/agent-configurations` | 200 | 配置列表（`cursor`、`limit`、`agent_type`、`enabled`） | 已登录 |
| GET | `/api/v1/agent-configurations/{configuration_id}` | 200 | 配置详情 | 已登录 |
| POST | `/api/v1/agent-configurations/{configuration_id}/disable` | 204 | 禁用一个配置 | owner |

两个列表接口都不接受白名单以外的查询参数：出现未知参数会直接拒绝，避免有人拿它当万能查询用。统一错误格式（`code` / `message` / `details` / `request_id`）见 HTTP_API.md 第 3 节。

## 2. 模块内部 Interface（代码里真实存在的调用形状）

```text
TaskCatalog.register(actor, preset_id) -> CatalogTask
TaskCatalog.get(actor, task_id) -> CatalogTask
TaskCatalog.list(actor, filters, cursor, limit) -> (items, next_cursor)

AgentRegistry.register(actor, preset_id) -> RegisteredAgent
AgentRegistry.get(actor, configuration_id) -> RegisteredAgent
AgentRegistry.list(actor, enabled, cursor, limit) -> (items, next_cursor)
AgentRegistry.disable(actor, configuration_id) -> None
```

## 3. 三个可替换的接缝（seam）

| 接缝 | 当前实现 | 职责 |
|---|---|---|
| `TaskSource.load(instance_id)` | `SWEGymTaskSource` | 从固定 Parquet 快照读一条题，拆公开/隐藏视图 |
| `TaskRepository.publish/get/list` | PostgreSQL | 任务与制品索引的原子发布、稳定 UUID 分页 |
| `ArtifactStore.put_immutable/read_verified` | MinIO | 不可变写入与真实字节校验 |

## 4. 任务 04 会碰到的接口

- `GET /api/v1/job-options` 发布四个批次档位：`demo` 1–3 题、`quick` 恰好 5 题、`standard` 10–20 题，以及 **`continuous` 1–20 题**。`continuous` 由成员 D 于 2026-09-20 实现并合入上游 `main`，既有档位区间未改动。这个端点归 Job 控制（D），前端展示归 B；受控选项属公共选项增量，按 D 的行动记录，契约补记留给 B 在 `docs/interfaces/HTTP_API.md` 完成。
- 边界要求：4、6、9 道题的请求必须通过；0 题、21 题、0 个配置、4 个配置、重复题目、未知或停用条目必须拒绝；总数上限是 20 题 × 3 配置 = 60 次 Run。其中 `demo`/`quick`/`standard` 与 4/6/9/0/21 的用例已由 D 覆盖，其余拒绝项已于 2026-09-20 复核：未知/停用条目、0 题、0 个配置均有测试覆盖；「重复项拒绝」一条已于 2026-09-20 定案：**去重是刻意行为**（依据见 [ISSUE-05](../04-issues/KNOWN_ISSUES.md)），只需组长把验证规范 Q7 与 `plan.md` 第 6 节的措辞对齐为「重复项去重后计数」。
