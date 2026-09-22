# 目录与配置 Module

> 当前状态：目录已有六道受控 SWE-Gym 题和一个生产 Codex/ChatGPT 配置；测试专用假提供方配置只在显式 `internal_test` 装配中可用。真实 DeepSeek/Kimi 配置仍未登记。
> 权威范围：任务目录、不可变来源快照和固定 Agent Configuration 的当前代码组成。

## 1. 职责与非职责

Task Catalog 把服务端可信预设转换成可审计的任务记录：先读取固定数据源，校验公开字段与原始记录摘要，把原始任务 JSON 作为不可变对象保存，再以短 PostgreSQL 事务发布任务和对象索引。Agent Registry 只登记代码内受控的配置预设并保存不可变指纹；禁用只影响新提交，不改写历史 Job 快照。

本 Module 不接受用户给出的数据 URL、镜像、任意模型地址、命令、Key 或资源限制；也不执行 Agent、判卷或创建 Job。

## 2. Interface 与不变量

- `TaskCatalog.register/get/list`：owner 才能登记；已认证用户可按受控条件读取。
- `AgentRegistry.register/get/list/disable`：owner 登记/禁用；配置必须通过固定 allowlist 校验。
- `TaskRepository`、`AgentConfigurationRepository`：PostgreSQL persistence seam。
- `TaskSource`：固定数据来源 seam；当前 Adapter 是 `SWEGymTaskSource`。
- `ArtifactStore`：原始任务 JSON 的不可变对象 seam；当前正式 Adapter 是 MinIO。
- PostgreSQL 中的目录记录和 MinIO 对象摘要必须吻合；对象不可验证时不向调用者返回看似正常的任务。
- Agent 身份必须是领域单一清单中的受控 provider/authentication 成对组合；生产 Composition Root 不包含测试假配置，数据库以同一成对 CHECK 防止交叉组合。

精确字段和错误见[模块契约](../../MODULE_CONTRACTS.md)，对象键和表见[数据模型](../../DATA_MODEL.md)。

## 3. 当前 Implementation 文件树

```text
apps/backend/src/eval_platform/
  domain/
    task.py                              # 公开任务、判卷私有数据和 TaskBundle
    agent.py                             # 不可变 AgentConfiguration 与指纹
    catalog.py                           # 目录记录、登记状态和错误
  application/
    task_catalog.py                      # 任务来源校验、对象发布、短事务目录发布
    agent_registry.py                    # 固定配置 allowlist、登记、查询和禁用
    ports/task_source.py                 # TaskSource Interface
    ports/repositories.py                # Task/Agent Repository Interface
    ports/artifacts.py                   # 不可变 ArtifactStore Interface
  adapters/
    tasks/swe_gym.py                     # 固定 Parquet → 公开/私有 TaskBundle Adapter
    tasks/collect_patch.sh               # Harbor 题目侧最终 patch 收集脚本
    persistence/catalog/tasks.py         # PostgreSQL Task Repository Adapter
    persistence/catalog/agents.py        # PostgreSQL Agent Repository Adapter
    persistence/catalog/__init__.py      # 建表及受控身份约束的显式、幂等升级
    persistence/catalog/schema.sql       # tasks、task_artifacts、agent_configurations
    tasks/catalog.py                     # 六题 instance → 固定含摘要镜像身份
    artifacts/minio.py                   # MinIO ArtifactStore Adapter
  delivery/
    catalog_presets.py                   # 六题、生产配置及隔离测试配置；生产 Root 只取正式预设
    catalog.py                           # 显式 init-db / upgrade-api-constraints 本机入口
    http/routes/catalog.py               # 目录查询和 owner 管理的 HTTP 翻译
    http/catalog_schemas.py              # 目录请求/响应 DTO
apps/web/src/
  features/catalog/tasks.tsx             # 任务目录与登记 UI
  features/catalog/agents.tsx            # 配置目录与禁用 UI
  lib/catalog-client.ts                  # 目录 HTTP 客户端与响应校验
```

## 4. 关键数据流

```text
owner 选择可信 preset
  → TaskSource 读取固定记录并分离公开/隐藏视图
  → ArtifactStore.put_immutable(raw task JSON)
  → PostgreSQL 发布任务和对象索引
  → Web/API 只返回允许公开的目录字段
```

Job 提交时，Job Control 通过本 Module 读取当前记录并冻结 `TaskSnapshot` / `AgentSnapshot`。之后即使配置被禁用或显示名变化，旧 Job 仍按冻结身份解释。

## 5. 模式、依赖和深度

TaskSource、Repository 和 ArtifactStore 是三个不同 seam；SWE-Gym、PostgreSQL、MinIO 分别是 Adapter。`TaskCatalog` 把跨两个存储的顺序、摘要校验和失败收敛藏在一个登记 Interface 后；调用者不需要编排对象存储和 SQL。

依赖方向是 Catalog application → domain/ports；Adapter 指向 ports。Job Control 依赖目录 Interface，目录不依赖 Job。

## 6. 当前验证、风险和规划

历史目录验证见[任务 03 行动](../../../actions/2026-09-12-m1-task-agent-catalog.md)与[任务 04 行动](../../../actions/2026-09-19-task-04-catalog-candidates-and-scale.md)。本轮核心修复没有重跑 MinIO，但在隔离真实 PostgreSQL 中验证了身份对约束及旧约束显式迁移；最终命令结果记录在当前[修复行动](../../../actions/2026-09-21-core-diagnostic-remediation.md)。

当前状态（2026-09-22）：**受控题目目录已有 6 道题**——旧题 `python__mypy-15413` 与五道新题（`15131`/`15139`/`15184`/`15208`/`15876`）。五道新题已在隔离容器中逐题跑过三补丁门禁（参考通过、空补丁不通过、可应用但错误的补丁不通过，15/15 场景），白名单实现位于 `adapters/tasks/catalog.py` 的 `FIXED_TASK_IMAGES`（instance → 含 digest 的固定镜像身份），未登记的 instance 一律拒绝。生产配置目录仍只有 `codex-0153-terra-medium`；`INTERNAL_TEST_AGENT_PRESETS` 只能由显式测试装配使用，不会被 `create_catalog` 注册。领域和数据库允许的两对身份为 `openai_chatgpt/chatgpt_auth_json` 与 `internal_test_fake/provider_run_token`，旧库由 `python -m eval_platform.delivery.catalog upgrade-api-constraints` 显式升级；未知约束形状失败关闭。真实 DeepSeek/Kimi 仍是后续任务，不能用测试身份替代。长期 MinIO 风险由[所有者单机运行](../owner-host-runtime/ARCHITECTURE.md)处理，不改变本 Module 的 ArtifactStore Interface。
