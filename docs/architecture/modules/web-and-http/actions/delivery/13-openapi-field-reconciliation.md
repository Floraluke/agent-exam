# 行动：OpenAPI 字段级 schema 对账

> 状态：**已完成**（2026-09-22）。收口 `progress.md` 里"OpenAPI 字段级 schema 对账 ⬜ 未做"一行（此前只做过 §10.4 正文与实现的 20/20 静态字段对照）。

## 1. 情况说明

**来源**：B 清点自留活时把这条列为"自己能做、不用问人"，用户确认执行。

**目标**：把**实时 OpenAPI 的响应 schema** 与 `HTTP_API.md` 的示例/正文**程序化逐字段比对**，找出契约与实现不一致的地方。

**方法**（工具留在 `runtime/tests/zz-openapi-field-check.py`，gitignored）：
1. 用 **`create_runtime_app()`** 读 OpenAPI——不用测试夹具，因为 `create_app(...)` 按传入服务条件注册路由，**会少算端点**（这与端点计数那条既有结论同源）。
2. 对 11 个读取面，把响应 schema 展平成**点路径**（跟 `properties`/`$ref`/`items`/`anyOf`/`allOf`/`oneOf`）。
3. 契约侧：带 JSON 示例的端点，**按稳定文本锚点**取示例块并展平；无示例的正文小节（§9.2/§10.1/§10.3/§10.4）做**人工逐字段核对**。
4. 报"契约有、schema 没有"与"schema 有、契约示例没写"两侧差异。

## 2. 结果

**逐字段一致（✅）**：`§4.1 TaskSummary`、`§4.2 AgentConfigurationSummary`（8/8）、`§4.3 JobSummary`（19/19）、`§10.1 Job 报告`（人工核对：11 个顶层 + 11 个 Run 字段与 schema **完全一致**）、`§9.2` 制品元数据、`runs/{id}/trajectory`（9/9）。

**修复的三处契约缺口（契约欠账，实现本就如此）**：

| 位置 | 缺口 | 处理 |
|---|---|---|
| §4.3 `JobSummary` 示例 | 缺 `cancel_requested_by`/`cancel_requested_at`/`cancel_reason`/`failure_code`/`failure_summary`/`rerun_of_job_id` **6 个字段**——而实现返回它们、§7 的同一形状示例里也有，属**文档内部不一致** | 补齐示例 + 补一段字段语义说明 |
| §10.2 过程指标 | 示例写成 `"usage": {}, "resources": {}`，**字段名在契约里从未定义**（§10.3 的 `{value, coverage}` 是聚合口径，不是单 Run 字段名） | 写明两组字段名与"不可得为 `null` 不是 0"；并把 `run.warnings` 补进示例 |
| §10.4 对比单元格 | schema 返回 `cells[].failure_code`，契约**没写** | 补一句（受控枚举，无失败为 `null`） |

**修复后复跑**：`/api/v1/tasks`、`/api/v1/agent-configurations`、`/api/v1/jobs` 三个端点**逐字段一致**；运行报告只剩两类残留——`artifact_links.*`（已在 §9.2 文档化）与 `process_metrics.*`（工具限制，见下）。

## 3. 工具自身的两处教训（如实记录，供下次复用）

1. **不要用硬编码行号做锚点**：第一版按行号取示例块，本文档一改（我补写了 §4.3/§10.2/§10.4）锚点全部漂移，三个端点直接变成"契约示例 0 字段"。已改为**按稳定文本锚点**（标题如 `### 4.3`、或端点行）取其后第一个 ```json 块。
2. **解析器读不了单行嵌套对象**：`"usage": {"n_input_tokens": null, ...}` 这种一行写完的嵌套对象只会被识别出外层键，于是 `process_metrics.usage.*` 仍显示为"schema 有、示例没写"——**这是工具限制，不是契约缺口**。
3. 另外试过"正文小节的名称级自动对照"（把反引号标识符与 schema 叶子名比对），**噪声过大已弃用**：它把交叉引用（`artifact_links` 属 Run 报告、`job_ids` 属对比接口）与枚举值（`not_ready`、`raw_30d`）都误判成"缺失字段"。正文部分改为人工核对。

## 4. 实际改动的文件树

| 路径 | 改动 |
|---|---|
| `docs/interfaces/HTTP_API.md` | §4.3 示例补 6 字段 + 字段语义段；§10.2 写明过程指标字段名与 `run.warnings`；§10.4 补 `cells.failure_code`；§15 记变更 |
| `docs/architecture/modules/web-and-http/progress.md` | 对账行改为已完成（含三处缺口与工具限制）；"任务 03 正式 issue"一行按用户决定关闭 |
| `docs/architecture/modules/web-and-http/actions/delivery/13-openapi-field-reconciliation.md` | 本文件（新增） |

## 5. 自验证方式与结果

```bash
cd apps/backend && PYTHONUTF8=1 .venv/Scripts/python.exe ../../runtime/tests/zz-openapi-field-check.py
```

**实际输出**：`OpenAPI：29 个路径，59 个 schema 组件`；修复后 tasks / agent-configurations / jobs **逐字段一致**，其余端点的残留差异均已归因（§9.2 已文档化 / 工具限制 / 正文已人工核对）。相对链接脚本校验 0 断链。

## 6. 未验证 / 局限

- **未逐字段核对**：Job 详情（73 个叶子）、`job-options`、排行榜（67 个叶子）、制品索引（18 个叶子）——它们没有 JSON 示例，只能人工看正文，本轮只核了 §10.1/§10.4/§9.2 三处。
- 只比**字段名与层级**，不比类型、可空性、枚举取值集合（这些需要另一套断言，未做）。
- 工具依赖真实装配能构造成功；若某个依赖缺失导致 `create_runtime_app()` 失败，对账会直接中断（本轮未发生）。
