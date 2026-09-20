# 子行动 b：对比接口实现（侦察与验证计划）

> 状态：**未完成**。
>
> 但"未完成"的含义与最初设想不同：**对比接口的 HTTP 翻译层（路由、DTO、错误映射、OpenAPI）已经由 D 实现并注册**，本文因此是"复核 + 验证 + 必要的去重"计划，不是从零实现计划。核对依据见第 2 节，均**只读**取得；本文未改动任何 `.py` 文件。
>
> 契约权威：[`HTTP_API.md`](../../../../interfaces/HTTP_API.md) §10.4（2026-09-20 冻结）。父行动：[任务 03 总行动](03-report-catalog.md)。

## 1. 情况说明

要做的是跨批次"题目 × 配置"对比接口 `GET /api/v1/reports/comparisons`，对应契约 §10.4：一次请求返回多批次聚合矩阵，五档单元格 + 缺失语义 + `decided`/`total` 计数，权限沿用既有报告授权。

**已存在的实现**（`bd47925`，D 在 B 的 HTTP 层经 B 批准后落地）：

- `apps/backend/src/eval_platform/delivery/http/routes/jobs/report_comparisons.py` — 5 个 DTO 与 `/reports/comparisons` 路由。
- `apps/backend/src/eval_platform/delivery/http/app.py:124` — 注册 `comparison_router`。
- `apps/backend/src/eval_platform/delivery/http/errors.py:84-90` — 为 `EMPTY_COMPARISON_SELECTION` / `COMPARISON_LIMIT_EXCEEDED` / `INVALID_REQUEST` 增加文案。
- `apps/backend/tests/jobs/reporting/test_comparison_http.py` — 3 个契约用例。

## 2. 侦察结果

### 2.1 D 的聚合层（`application/reporting/`）

| 项 | 事实 | 位置 |
|---|---|---|
| 五档枚举 | `MatrixCell = Literal["resolved","unresolved","infrastructure_error","incomplete","missing"]` | `matrix.py:17-23` |
| 输入 | `build_matrix(reports: Sequence[JobReport]) -> ReportMatrix` | `matrix.py:67` |
| 输出 | `ReportMatrix(columns, rows, totals)`，元素为 frozen dataclass | `matrix.py:60-64` |
| 列 | `MatrixColumn(job_id, agent_configuration_id, agent_display_name)`；同一 Job 多配置按 Run 顺序展开 | `matrix.py:26-32`、`:76-86` |
| 单元格 | `MatrixCellValue(outcome, run_id, resolved, failure_code, report_path)` | `matrix.py:35-41` |
| 行 | `MatrixRow(task_instance_id, repo, cells)`；行序按 `(repo, instance_id)` 升序 | `matrix.py:44-48`、`:94` |
| 计数 | `MatrixColumnTotals(resolved, unresolved, infrastructure_error, incomplete, missing)` —— **只有 5 个整数**，`decided`/`total` 由 HTTP 层派生 | `matrix.py:51-57` |
| 用例入口 | `JobReporting.compare(actor, job_ids) -> ReportMatrix` | `service.py:62-75` |
| 去重 | `tuple(dict.fromkeys(job_ids))` —— 去重且保序 | `service.py:70` |
| 上限 | `MAX_COMPARISON_JOBS = 20` | `service.py:26`、`:73-74` |
| 异常 | `JobInputError("EMPTY_COMPARISON_SELECTION")`、`JobInputError("COMPARISON_LIMIT_EXCEEDED")`；权限/不存在/`internal_test` 由复用的 `job()` 抛 `JobNotFound` | `service.py:71-74`、`:53-59` |
| 缺失语义 | 没有 Run → 五字段全 `None`；Run `COMPLETED` 但报告不可读 → `run_id` 非空、`resolved`/`report_path` 为 `None` | `matrix.py:112-116` |
| 五档映射 | `COMPLETED` → 按 `resolved_summary` 分 resolved/unresolved；`FAILED` → infrastructure_error；其余 → incomplete | `matrix.py:126-131` |
| 正常单元格 | `report_path = /api/v1/reports/runs/{run_id}` | `matrix.py:117-123` |

### 2.2 既有 §10.1/§10.2 报告端点（供本接口对齐）

| 项 | 事实 | 位置 |
|---|---|---|
| 路由文件 | §10.2 `GET /reports/runs/{run_id}`；§10.1 `GET /reports/jobs/{job_id}`；对比接口单独放在 `report_comparisons.py` | `routes/jobs/report_routes.py:22`、`:27` |
| DTO 位置 | §10.1 在 `batch_schemas.py`（含 `BatchOutcome` 四档）；§10.2 在 `report_schemas.py`；§10.4 的 5 个 DTO **内联**在 `report_comparisons.py:28-62` | 同左 |
| 错误映射 | 统一在 `errors.py` 的 `job_error`；`JobInputError` → `400` + 具体 code 与文案，其余 `JobError` 子类走状态码表 | `errors.py:82-90` |
| 会话依赖注入 | 路由工厂接收 `IdentityService`；处理函数内 `identity.current_actor(request.cookies.get(config.cookie_name))`，没有中间件隐式注入 actor | `report_comparisons.py:149` |
| Cache-Control | 由 `app.py:109` 中间件对响应统一写 `no-store`，**不是各路由自己设置** | `app.py:109` |
| 声明状态码 | 路由声明 `error_responses(400, 401, 404, 503)`；路由器默认含 `401/404/500/503` | `report_comparisons.py:138`、`:144` |

### 2.3 测试基建：**不需要真实 PostgreSQL**

- 对比接口测试用夹具 `internal_reports_api`：`tests/jobs/conftest.py:147-150` → `job_api(scope_visible=...)`。
- `job_api`（`tests/jobs/conftest.py:71-138`）**全部用内存替身装配**：`MemoryMembershipRepository`、`MemoryTasks`/`MemoryArtifacts`/`FixedSource`、`MemoryAgents`、`ExecutableMemoryJobs`、`RunArtifacts`（= `jobs.execution.support.fakes.MemoryArtifacts`），再 `create_app(...)` + `TestClient`。没有数据库、MinIO 或 Docker。
- 真实存储用例由**显式环境变量**门禁并默认 skip，与本接口无关：
  - `AGENTEXAM_RUN_IDENTITY_POSTGRES=1` + `AGENTEXAM_TEST_DATABASE_URL`（`tests/identity/conftest.py:67-69`）
  - `AGENTEXAM_RUN_CATALOG_MINIO=1`（`tests/catalog/conftest.py:118-120`）
  - `AGENTEXAM_RUN_JOB_MINIO=1`（`tests/jobs/execution/conftest.py:11-14`，普通夹具，非 autouse，不会波及其他测试）
- 可仿照的测试文件：`tests/jobs/reporting/test_comparison_http.py` 本身；同层参考 `tests/jobs/execution/test_reports_http.py`。
- 已有用例：成功形状与缺失语义（`:47`）、会话/未知/他人 Job 收敛（`:93`）、400 族（`:115`）。

**结论：数据库连不上不阻塞本接口的本地测试。** 真正阻塞本地测试的是环境本身——见第 5 节。

### 2.4 逐条核对本次给出的规则

| 规则 | 现状 | 结论 |
|---|---|---|
| 五档枚举从 D 实现导入，不新建同名枚举 | HTTP 层 `ComparisonOutcome`（`report_comparisons.py:19-25`）**重复声明**了与 D 层 `MatrixCell` 相同的五个字面量 | ⚠️ **未满足，但已决定暂不收敛**（2026-09-20）：HTTP DTO 枚举与 domain 内部枚举分层独立是正常做法；是否把 `MatrixCell` 提升为跨模块公开 Interface 由 **D** 决定，见[进展与未决项](../progress.md)的"向 D 报告与待确认"节。**本轮不改 `.py`** |
| `missing` 的 `resolved` 保持 `null`、`report_path` 保持 `null` | 实现即如此（`matrix.py:113-116`） | ✅ 已满足 |
| `totals` 用 `decided` + `total` 两个整数，不引入 `coverage` 字符串 | HTTP 层派生 `decided`/`total`（`report_comparisons.py:98-110`），无 `coverage` | ✅ 已满足 |
| 未知/重复标量参数按 FastAPI 默认行为，本 PR 不新增严格校验层 | 本仓无严格 query 校验层，用类型化 `Query` 声明 | ✅ 已满足（但见第 6 节：D 的提案声称返回 400） |
| 不改 §10.1 `BatchOutcome` 四档 | `batch_schemas.py` 未被本接口改动，§10.4 用独立五档 | ✅ 已满足 |
| 发现 §10.4 与 D 实现不一致只报告 | §10.4 与实现静态核对 **20/20 字段命中**，无不一致；不一致在 D 的**提案文档** | ✅ 已核对 |

## 3. 实施措施

1. **建依赖环境**（前置，**当前被阻塞**）：项目指定命令是 `uv sync --locked --no-python-downloads`（见[依赖总表](../../../../dependencies/DEPENDENCIES.md)），它会在 `apps/backend` 建立 `.venv`。B 已授权恢复环境，但**本机没有 `uv`**（PATH、常见安装位置、用户目录全盘搜索都没有），并按 B 指示"uv 不在就先报告、不用系统 Python 硬装"，因此**本轮环境未恢复、测试未跑**。解除方式：先在本机取得 `uv`（项目既有做法是 `python -m pip install --user uv`，属机器级变更，需 B 确认后再执行），再在 `apps/backend` 运行上述命令。
2. **跑契约测试**：执行第 5 节命令，确认 3 个既有用例通过；不通过时先判定是环境问题还是回归，再把结果写回本文件。
3. **复核 §10.4 与实现**：以运行时响应为准复核第 2.4 节各条，特别是 `decided`/`total` 与缺失语义。
4. **五档枚举：暂不收敛**（2026-09-20 决定）。不改 `.py`；是否把 `MatrixCell` 提升为跨模块公开 Interface 写成问题交 D 决定（见第 2.4 节与[进展与未决项](../progress.md)）。若 D 同意收敛，等环境恢复、能跑测试后再**单独开一个小 PR**，不并入当前契约 PR。
5. **验证通过后再进入 UI**：子行动 c 必须先补逐控件契约行（门槛见[实现地图第 2.1 节](../../../../../.scratch/ui-catalog-providers/implementation-map.md)），再写代码。

## 4. 预估修改文件（候选，本次一个都没动）

| 文件 | 是否真需要动 | 理由 |
|---|---|---|
| `apps/backend/src/.../routes/jobs/report_comparisons.py` | ⬜ 本轮不动 | 五档枚举已决定**暂不收敛**（见第 3 节第 4 步），因此本文件无需改动 |
| `apps/backend/tests/jobs/reporting/test_comparison_http.py` | ⬜ 暂不需要 | 既有 3 个用例已覆盖主要契约；若复核发现缺口再补 |
| `apps/web/src/features/jobs/reporting/*`（候选新增） | ⬜ 属子行动 c | 对比页 UI；**依赖本行动的复核结论** |
| `apps/web/src/lib/job-client.ts`、`lib/reporting-shapes.ts`（候选） | ⬜ 属子行动 c | 前端调用与形状校验 |
| `docs/interfaces/HTTP_API.md` | ⬜ 暂不需要 | §10.4 已与实现一致；仅当复核发现漂移时才改 |
| `docs/actions/2026-09-20-d-comparison-api-proposal.md` | ❌ 不动 | 属 D 维护；其中的失真只报告（见第 6 节） |

**不新增**后端路由文件：`routes/jobs/` 已有 9 个 `.py` 文件，超过项目"每层不超过 8 个文件"的指标（既有偏差，见[总行动第 3 节](03-report-catalog.md)），本任务不再加文件。

## 5. 验证方案

命令在**实际工作区** `D:\agent-exam\apps\backend` 下执行。

> **路径标注**：本节的 `D:\agent-exam\apps\backend` 是**本地草稿路径，仅写在本文件里，未改任何公共文档**。[分层验收规范](../../../../../.scratch/ui-catalog-providers/verification.md)第 3 节仍指向旧工作区 `E:\9.1agent_exam`，该公共文档的修正**单独处理**，不在本任务范围。命令形式与 `uv sync` 建立的 `.venv` 保持一致（与验收规范同形）。

```powershell
# 先恢复环境（项目既有命令；本机当前无 uv，见第 6 节）
uv sync --locked --no-python-downloads

# 定向契约测试（本接口，内存装配，不需要 PostgreSQL）
.venv/Scripts/python.exe -m pytest tests/jobs/reporting/test_comparison_http.py -q -p no:cacheprovider

# 聚合层与渲染
.venv/Scripts/python.exe -m pytest tests/jobs/reporting -q -p no:cacheprovider

# 静态检查
.venv/Scripts/ruff.exe check src tests
.venv/Scripts/mypy.exe src
```

用例覆盖清单（逐项要有结论，跳过也要写明原因）：

| # | 场景 | 期望 |
|---|---|---|
| 1 | 空选择（`job_ids=""`） | `400 EMPTY_COMPARISON_SELECTION` |
| 2 | 含非 UUID | `400 INVALID_REQUEST` |
| 3 | 去重后超过 20 个 | `400 COMPARISON_LIMIT_EXCEEDED` |
| 4 | 无会话 | `401` |
| 5 | 不存在的 Job | `404`（与不存在收敛，不泄漏存在性） |
| 6 | 协作者访问他人 Job | `404`（整请求收敛） |
| 7 | `result_scope=internal_test` | 按不存在处理 |
| 8 | `missing` 语义 | `resolved` 为 `null`（非 `false`）、`report_path` 为 `null`、不计入未通过、不写成 0 |
| 9 | 五档映射 | `COMPLETED`+成功→`resolved`；`COMPLETED`+未成功→`unresolved`；`FAILED`→`infrastructure_error`；其余非终态→`incomplete` |
| 10 | 计数 | `decided` = 前四档之和；`total` = `decided + missing`；无 `coverage` 字段 |
| 11 | 无正文泄漏 | 响应不含对象键/秘密路径 |

## 6. 未验证项与待确认项

| 项 | 说明 |
|---|---|
| **本机跑不了测试（当前唯一阻塞）** | ① `apps/backend` **没有虚拟环境**（`.venv` 不存在）；② 系统 Python 3.14.5 虽已装 `fastapi`/`pydantic`/`httpx`/`pytest`/`sqlalchemy`，但**缺 `argon2`**，`Argon2Passwords` 导入失败 → 夹具无法装配；③ `ruff`、`mypy` 不在 PATH；④ **本机没有 `uv`**（PATH、常见安装位置、用户目录全盘搜索都没有），因此项目指定的 `uv sync --locked --no-python-downloads` **无法执行**。按 B 指示未用系统 Python 硬装，**环境未恢复、测试未运行**。解除只需先在本机取得 `uv` |
| 数据库不可用的影响 | **不影响本接口的本地测试**（内存替身装配，无需 PostgreSQL）；只影响被 env 门禁的真实存储用例，它们默认 skip |
| 实时 OpenAPI 计数 | §2.1 已改为 32；未启动应用读取实时 OpenAPI 复核（需要可运行的后端环境） |
| 五档枚举重复声明 | **已决定暂不收敛**（2026-09-20）；是否把 `MatrixCell` 提升为跨模块公开 Interface 待 **D** 回答，问题原文与理由见[进展与未决项](../progress.md)的"向 D 报告与待确认"节 |
| `routes/jobs/` 超 8 文件指标 | 既有偏差，已向 D 报告；未擅自拆分，见[进展与未决项](../progress.md)同节 |
| D 文档的两处失真（**只报告，不擅改契约**） | ① [提案](../../../../actions/2026-09-20-d-comparison-api-proposal.md) §2 的示例与字段表仍写 `coverage`，与提案 §6 决定 4 和实现不符；② 提案 §4 声称"未知参数、重复参数返回 400"，实现未做该校验（本仓无严格 query 校验层）。两处均在 D 的文档内，需 D 收口 |
| 对比页 UI | 未开始；开工前须先补逐控件契约行 |
| 任务 03 正式 issue | `.scratch` 下无 `03-*` 任务单，是否发布待 B 确认 |
