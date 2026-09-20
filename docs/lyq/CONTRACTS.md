# 输入输出契约：目录与配置

> 这是我个人的摘录，不是权威正文。完整契约见[模块契约](../architecture/MODULE_CONTRACTS.md)第 6.2（Task Catalog）、6.3（Agent Registry）节；HTTP 形状见[HTTP_API.md](../interfaces/HTTP_API.md)第 5、6 节。

「契约」就是我和别人约好的事：你给我什么、我还你什么、什么情况我会报错。这三样写清楚，调用方就不用猜。

## 1. Task Catalog（题目目录）

| 项目 | 内容 |
|---|---|
| 调用方 | Job 提交、Job 编排、报告 |
| 输入 | `dataset_id`、`dataset_revision`、`split`、`instance_id`（都来自固定数据集，不接受用户自定义 URL） |
| 输出 | 规范化的 `EvaluationTask`；内容哈希固定的原始任务 JSON 的 `ArtifactRef`；仅供判卷器使用的验证引用 |
| 错误 | 数据集不存在、任务不存在、字段缺失、固定版本校验不一致 |
| 不变量 | 同一数据集版本 + 同一任务 ID，必须永远返回相同的标准字段和相同的原始 JSON 哈希；Agent 能看到的视图里不得包含 gold patch 或测试答案 |

登记时的实际请求（`POST /api/v1/tasks/register`，只有 owner 能调）：

```json
{ "preset_id": "swe-gym-lite-mypy-15413" }
```

成功返回 `201` 与一个 `TaskDetail`，里面有 `task_id`、`instance_id`、`dataset_id`、`dataset_revision`、`split`、`repo`、`base_commit`、题面预览和题面全文。传一个不在白名单里的 `preset_id`，返回 `400`，错误码 `INVALID_REQUEST`。

关键点：`gold_patch`、`test_patch`、测试名单、环境对象键、凭据引用**都不在**上面的返回里。

## 2. Agent Registry（Agent 配置目录）

| 项目 | 内容 |
|---|---|
| 调用方 | Job 提交、Job 编排、执行后端、报告 |
| 输入 | 登记用的配置 ID，或只读筛选条件 |
| 输出 | 固定版本的 `AgentConfiguration`；可展示列表 |
| 错误 | 未登记、已禁用、版本/镜像不存在、配置指纹不匹配 |
| 不变量 | 只返回项目预登记过的配置；**Agent + 提供方 + 模型 + 关键配置**四者共同构成身份；禁用只改状态，不删除也不自动重新启用 |

登记时的实际请求（`POST /api/v1/agent-configurations`，只有 owner 能调）：

```json
{ "preset_id": "codex-0153-terra-medium" }
```

成功返回 `201` 与一个 `AgentDetail`，包含 `agent_configuration_id`、`display_name`、`agent_type`、`agent_version`、`model_provider`、`model`、`configuration_fingerprint`、`enabled`、`public_options`、`limit_profile_id`。

「指纹」（fingerprint）是把关键配置算成一个哈希值。同一份配置永远算出同一个指纹，配置变了指纹就变，这样旧 Job 才能证明自己当时冻的是哪一份配置。

## 3. 我需要记住的边界

- 这两个接口都不是公开 API，都要可信登录会话；登记和禁用另外要求 owner 身份。
- 我不接受用户给的任意数据地址、镜像、模型地址、命令或 Key——只能从服务端代码里的白名单挑。
- 隐藏数据（答案、测试）和秘密永远不出现在 HTTP 返回、网页或做题容器里。
