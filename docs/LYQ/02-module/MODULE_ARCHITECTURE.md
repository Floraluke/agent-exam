# 模块架构：目录与配置

> 这是 lyq 的个人视图，不是权威正文。权威版本是[模块架构文档](../../architecture/modules/catalog-and-configuration/ARCHITECTURE.md)；字段与错误见[模块契约](../../architecture/MODULE_CONTRACTS.md)第 6.2、6.3 节。

## 1. 这个模块用一句话说

把服务端**写死的可信预设**，变成数据库里可审计的目录记录。

打个比方：题目和 Agent 配置不允许用户自己上传。代码里先有一份「白名单」（预设），用户只能从白名单里挑；系统拿着这个预设去读固定数据、校验内容、把原始记录存成不可改的对象，最后在数据库里发布一条记录。任何人看到的目录，都是这条记录。

## 2. 它负责什么、不负责什么

负责：

- 可信 Task Catalog（题目目录）、Agent Registry（Agent 配置目录）。
- 题目公开数据与隐藏数据分离（参考答案、测试名单不能泄漏出去）。
- 目录记录与对象存储里的摘要必须一致；不可变摘要和禁用语义。
- 新规模/配置版本的兼容，历史配置指纹和旧 Job 快照不能被改写。

不负责（重要）：

- **不接受**用户给的数据 URL、镜像、任意模型地址、命令、Key 或资源限制。
- 不执行 Agent、不判卷、不创建 Job。这些是「执行与判卷」和「Job 控制」的事。
- 禁用配置只影响新提交，不改写历史 Job 快照。

## 3. 两个 Interface

| Interface | 谁调用 | 干什么 |
|---|---|---|
| `TaskCatalog.register/get/list` | Job 控制、报告 | 登记题目、按条件读取；只有 owner 能登记 |
| `AgentRegistry.register/get/list/disable` | Job 控制、执行、报告 | 登记/读取/禁用固定 Agent 配置；登记和禁用要 owner |

背后还有三个「接缝」（seam，就是可替换的接口点），实现分别可替换：

- `TaskSource`：固定数据来源。当前实现是 `SWEGymTaskSource`，从固定的 Parquet 快照按 instance id 读一条题。
- `TaskRepository` / `AgentConfigurationRepository`：PostgreSQL 持久化。
- `ArtifactStore`：原始任务 JSON 的不可变对象存储。当前正式实现是 MinIO。

`TaskCatalog` 的价值在于：它把「跨两个存储的顺序、摘要校验、失败收敛」藏在一个登记接口后面，调用者不用自己去编排对象存储和数据库。

## 4. 关键文件（完整树见权威文档第 3 节）

```text
apps/backend/src/eval_platform/
├─ domain/task.py, agent.py, catalog.py      # 领域对象：公开/私有任务、配置指纹、目录错误
├─ application/task_catalog.py               # 登记用例：校验 → 存对象 → 短事务发布
├─ application/agent_registry.py             # 固定配置 allowlist、登记、查询、禁用
├─ adapters/tasks/swe_gym.py                 # 固定 Parquet → 公开/私有 TaskBundle
├─ adapters/persistence/catalog/             # PostgreSQL：tasks、task_artifacts、agent_configurations
├─ adapters/artifacts/minio.py               # MinIO 不可变对象
└─ delivery/catalog_presets.py               # 服务端可信预设 + 组装入口（我主要改这里）
```

## 5. 数据流

```text
owner 选一个可信 preset
  → TaskSource 读固定记录，拆成「公开」和「隐藏」两个视图
  → ArtifactStore 不可变写入原始任务 JSON
  → PostgreSQL 短事务发布任务记录和对象索引
  → Web / HTTP 只返回允许公开的字段
```

Job 提交时，Job 控制通过本模块读当前记录，冻结成 `TaskSnapshot` / `AgentSnapshot`。之后即使配置被禁用或改了显示名，旧 Job 仍按冻结的身份解释。

## 6. 依赖方向

```text
Catalog application → domain / ports
Adapter → ports
Job 控制 → 目录 Interface（目录不反向依赖 Job）
```

代码不能反向依赖 Web、数据库 Adapter 或具体 Harbor 对象。

## 7. 当前状态（2026-09-20 核对）

- 目录里**只有一道题**：`swe-gym-lite-mypy-15413`；**只有一个配置**：`codex-0153-terra-medium`（Codex 0.153.0 / gpt-5.6-terra / medium）。
- 出处是 M1 任务 03，已完成。
- 五道新题（任务 04）与 DeepSeek、Kimi 配置（任务 05–07）都还只是计划，未登记。
- 我的任务 04 要做的两件事：把五道新题验证合格后加进白名单；把「连续 1–20 道题」的规模档位加上。
