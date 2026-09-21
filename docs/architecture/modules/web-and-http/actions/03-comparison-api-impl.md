# 子行动 b：对比接口实现（复核与验证计划）

> 状态：**复核与验证已完成**（2026-09-20）。对比接口的 HTTP 翻译层由 D 实现并注册（`bd47925`），本次完成只读复核、环境恢复与契约测试实跑；剩余项见第 6 节。
>
> 契约权威：[`HTTP_API.md`](../../../../interfaces/HTTP_API.md) §10.4（2026-09-20 冻结）。父行动：[任务 03 总行动](03-report-catalog.md)。
>
> 本文件是侦察与验证记录，**没有改动任何 `.py` 文件**。

## 1. 情况说明

对象是跨批次"题目 × 配置"对比接口 `GET /api/v1/reports/comparisons`，对应契约 §10.4：一次请求返回多批次聚合矩阵，五档单元格 + 缺失语义 + `decided`/`total` 计数，权限沿用既有报告授权。

**已存在的实现**（`bd47925`，D 在 B 的 HTTP 层经 B 批准后落地）：

- `apps/backend/src/eval_platform/delivery/http/routes/jobs/report_comparisons.py` — 5 个 DTO 与 `/reports/comparisons` 路由。
- `apps/backend/src/eval_platform/delivery/http/app.py:124` — 注册 `comparison_router`。
- `apps/backend/src/eval_platform/delivery/http/errors.py:84-90` — 为 `EMPTY_COMPARISON_SELECTION` / `COMPARISON_LIMIT_EXCEEDED` / `INVALID_REQUEST` 增加文案。
- `apps/backend/tests/jobs/reporting/test_comparison_http.py` — **4 个**契约用例（第 4 个由 D 在 `cdcb4cf` 加入，见 2.4）。

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
| 去重 | `tuple(dict.fromkeys(job_ids))` —— 去重且保序；服务层有用例 `test_compare_deduplicates_job_ids` | `service.py:70`、`tests/jobs/reporting/test_compare_service.py:100` |
| 上限 | `MAX_COMPARISON_JOBS = 20` | `service.py:26`、`:73-74` |
| 异常 | `JobInputError("EMPTY_COMPARISON_SELECTION")`、`JobInputError("COMPARISON_LIMIT_EXCEEDED")`；权限/不存在/`internal_test` 由复用的 `job()` 抛 `JobNotFound` | `service.py:71-74`、`:53-59` |
| 缺失语义 | 没有 Run → 五字段全 `None`；Run `COMPLETED` 但报告不可读 → `run_id` 非空、`resolved`/`report_path` 为 `None` | `matrix.py:112-116` |
| 五档映射 | `COMPLETED` → 按 `resolved_summary` 分 resolved/unresolved；`FAILED` → infrastructure_error；其余 → incomplete | `matrix.py:126-131` |
| 正常单元格 | `report_path = /api/v1/reports/runs/{run_id}` | `matrix.py:117-123` |

### 2.2 既有 §10.1/§10.2 报告端点（供本接口对齐）

| 项 | 事实 | 位置 |
|---|---|---|
| 路由文件 | §10.2 `GET /reports/runs/{run_id}`；§10.1 `GET /reports/jobs/{job_id}`；对比接口单独放在 `report_comparisons.py` | `routes/jobs/report_routes.py:22`、`:27` |
| DTO 位置 | §10.1 在 `batch_schemas.py`（含 `BatchOutcome` 四档）；§10.2 在 `report_schemas.py`；§10.4 的 5 个 DTO **内联**在 `report_comparisons.py:29-63` | 同左 |
| 错误映射 | 统一在 `errors.py` 的 `job_error`；`JobInputError` → `400` + 具体 code 与文案，其余 `JobError` 子类走状态码表 | `errors.py:82-90` |
| 会话依赖注入 | 路由工厂接收 `IdentityService`；处理函数内 `identity.current_actor(request.cookies.get(config.cookie_name))`，没有中间件隐式注入 actor | `report_comparisons.py:159` |
| 参数校验 | `_reject_foreign_params(request.query_params)` 在会话检查**之前**执行，拒绝未知参数名与重复 `job_ids`，抛 `JobInputError("INVALID_REQUEST")` | `report_comparisons.py:133-139`、调用在 `:158` |
| Cache-Control | 由 `app.py:109` 中间件对响应统一写 `no-store`，**不是各路由自己设置** | `app.py:109` |
| 声明状态码 | 路由声明 `error_responses(400, 401, 404, 503)`；路由器默认含 `401/404/500/503` | `report_comparisons.py:147`、`:153` |

**行号基准**：以上 `report_comparisons.py` 行号取自 D 的分支 `upstream/xinyue-modules`（`c5e036d`），即包含 `cdcb4cf` 的版本。当前 `main` 上该文件的对应行号整体小 1（router 段小 9）。

### 2.3 测试基建：**不需要真实 PostgreSQL**

- 对比接口测试用夹具 `internal_reports_api`：`tests/jobs/conftest.py:147-150` → `job_api(scope_visible=...)`。
- `job_api`（`tests/jobs/conftest.py:71-138`）**全部用内存替身装配**：`MemoryMembershipRepository`、`MemoryTasks`/`MemoryArtifacts`/`FixedSource`、`MemoryAgents`、`ExecutableMemoryJobs`、`RunArtifacts`（= `jobs.execution.support.fakes.MemoryArtifacts`），再 `create_app(...)` + `TestClient`。没有数据库、MinIO 或 Docker。
- 真实存储用例由**显式环境变量**门禁并默认 skip，与本接口无关：
  - `AGENTEXAM_RUN_IDENTITY_POSTGRES=1` + `AGENTEXAM_TEST_DATABASE_URL`（`tests/identity/conftest.py:67-69`）
  - `AGENTEXAM_RUN_CATALOG_MINIO=1`（`tests/catalog/conftest.py:118-120`）
  - `AGENTEXAM_RUN_JOB_MINIO=1`（`tests/jobs/execution/conftest.py:11-14`，普通夹具，非 autouse，不会波及其他测试）
- 可仿照的测试文件：`tests/jobs/reporting/test_comparison_http.py` 本身；同层参考 `tests/jobs/execution/test_reports_http.py`。
- 已有用例（4 个）：成功形状与缺失语义（`:47`）、会话/未知/他人 Job 收敛（`:93`）、空/非法/超限 400 族（`:115`）、未知与重复参数 400（`:132`，D 新增）。

**结论：数据库连不上不阻塞本接口的本地测试。** 本机实测已证实——见第 5 节。

### 2.4 逐条核对本次给出的规则

| 规则 | 现状 | 结论 |
|---|---|---|
| 五档枚举从 D 实现导入，不新建同名枚举 | HTTP 层 `ComparisonOutcome`（`report_comparisons.py:20-26`）**重复声明**了与 D 层 `MatrixCell` 相同的五个字面量 | ⚠️ **未满足，但经双方确认不收敛**（2026-09-20）：HTTP DTO 枚举与 domain 内部枚举分层独立是正常做法；**D 已明确回复不提升为跨模块公开接口**，该问题关闭，**不改 `.py`** |
| `missing` 的 `resolved` 保持 `null`、`report_path` 保持 `null` | 实现即如此（`matrix.py:113-116`） | ✅ 已满足 |
| `totals` 用 `decided` + `total` 两个整数，不引入 `coverage` 字符串 | HTTP 层派生 `decided`/`total`（`report_comparisons.py:99-111`），无 `coverage` | ✅ 已满足 |
| 未知/重复标量参数按 FastAPI 默认行为，本 PR 不新增严格校验层 | **该规则的前提有误**：本仓早有这类严格校验——`leaderboard/routes.py:53-57`、`jobs/routes.py:83-95`、`catalog.py:123-125` 三处，均在会话检查前执行。D 的对比端点是**第 4 处**（`report_comparisons.py:133-139`） | ⚠️ **规则被既有模式取代**：B 最初"本仓无严格 query 校验层"的判断是搜索未递归进 `routes/` 造成的错误，对比端点当时确实缺这条（缺口为真），但机制一直存在。§10.4 按新行为写，见第 6 节 |
| 不改 §10.1 `BatchOutcome` 四档 | `batch_schemas.py` 未被本接口改动，§10.4 用独立五档 | ✅ 已满足 |
| 发现 §10.4 与 D 实现不一致只报告 | §10.4 与实现**字段级 20/20 命中**。D 本次新增的是**行为**（两条 400），字段对照覆盖不到；D 已按其提案实现并补测试 | ✅ 已核对；行为差异由契约文档补充，未擅改 D 的文件 |

## 3. 实施措施

1. **建依赖环境**（✅ 已完成，2026-09-20）：`python -m pip install --user uv`（0.12.17，与 D 记录一致）→ 发现本机只有 Python 3.14 而项目要求 `>=3.13,<3.14` → 用 `uv python install 3.13` 装 uv 管理的 Python 3.13.15 → `uv sync --locked --no-python-downloads` 成功建立 `.venv`。详见第 5 节。
2. **跑契约测试**（✅ 已完成）：见第 5 节实测输出。
3. **复核 §10.4 与实现**（✅ 已完成）：字段级 20/20 命中；行为差异（两条 400）记入第 6 节待办。
4. **五档枚举：不收敛**（D 已确认，问题关闭）。不改 `.py`。
5. **§10.4 补两条 400**：⏳ 有意延后，触发条件见第 6 节与[契约行动](../../../../actions/2026-09-20-task03-comparison-api-doc.md)。
6. **`routes/jobs/` schemas 拆分**：⏳ D 已同意方案、由 B 执行，见第 4 节。
7. **验证通过后再进入 UI**：子行动 c 必须先补逐控件契约行（门槛见[实现地图第 2.1 节](../../../../../.scratch/ui-catalog-providers/implementation-map.md)），再写代码。

## 4. 修改文件清单（现状）

| 文件 | 状态 | 理由 |
|---|---|---|
| `apps/backend/src/.../routes/jobs/report_comparisons.py` | ⬜ 不动 | 五档枚举经 D 确认不收敛，本文件无需改动 |
| `apps/backend/tests/jobs/reporting/test_comparison_http.py` | ⬜ 不动 | D 已补第 4 个用例，覆盖 4 类 400 |
| `apps/backend/src/.../routes/jobs/*_schemas.py`（4 个） | ⏳ 待 B 执行 | 移入 `schemas/` 子目录，解 `routes/jobs/` 顶层 9 个 `.py` 超 8 指标的问题；**D 已同意方案并明确由 B 执行、D 不动该目录** |
| `docs/interfaces/HTTP_API.md` | ⏳ 待补 | §10.4 有意延后补两条 400 与优先级说明（触发器见第 6 节） |
| `apps/web/src/features/jobs/reporting/*`（候选新增） | ⬜ 属子行动 c | 对比页 UI |
| `apps/web/src/lib/job-client.ts`、`lib/reporting-shapes.ts`（候选） | ⬜ 属子行动 c | 前端调用与形状校验 |
| `docs/actions/2026-09-20-d-comparison-api-proposal.md` | ❌ 不动 | 属 D；两处失真已由 D 在 `c5e036d` 收口 |

**不新增**后端路由文件。

## 5. 验证方案与实测结果

命令在**实际工作区** `D:\agent-exam\apps\backend` 下执行。

> **路径标注**：本节的 `D:\agent-exam\apps\backend` 是**本地草稿路径，仅写在本文件里，未改任何公共文档**。[分层验收规范](../../../../../.scratch/ui-catalog-providers/verification.md)第 3 节仍指向旧工作区 `E:\9.1agent_exam`，该公共文档的修正**单独处理**，不在本任务范围。

```powershell
# 恢复环境（项目既有命令）
uv sync --locked --no-python-downloads

# 定向契约测试（本接口，内存装配，不需要 PostgreSQL）
.venv/Scripts/python.exe -m pytest tests/jobs/reporting/test_comparison_http.py -q -p no:cacheprovider

# 聚合层与渲染
.venv/Scripts/python.exe -m pytest tests/jobs/reporting -q -p no:cacheprovider

# 静态检查
.venv/Scripts/ruff.exe check src tests
.venv/Scripts/mypy.exe src
```

### 5.1 环境（2026-09-20 实际恢复）

- `uv 0.12.17`（`python -m pip install --user uv`，直连 PyPI 成功），已加入用户 PATH。
- 本机原只有 Python 3.14.5，不满足 `requires-python = ">=3.13,<3.14"`；已装 uv 管理的 **Python 3.13.15**（用户级，经代理下载）。
- `uv sync --locked --no-python-downloads` 退出码 0，`.venv` 建立于 `apps/backend`，解释器 Python 3.13.15。
- 工具可用：`argon2 25.1.0`、`pytest 9.0.2`、`ruff 0.15.17`、`mypy 1.18.2`。

### 5.2 实测输出（本机，`docs/web-http-module-scaffold` 分支即基于 main 的状态）

```text
$ .venv/Scripts/python.exe -m pytest tests/jobs/reporting/test_comparison_http.py -q -p no:cacheprovider
...                                                                      [100%]
3 passed, 2 warnings in 1.78s

$ .venv/Scripts/python.exe -m pytest tests/jobs/reporting -q -p no:cacheprovider
14 passed, 2 skipped, 2 warnings in 1.36s

$ .venv/Scripts/python.exe -m pytest -q -p no:cacheprovider
2 failed, 404 passed, 84 skipped, 2 warnings in 59.36s
```

两点必须说明：

1. **这里是 3 passed 而不是 4**：当前分支不含 D 的第 4 个用例（只在 `upstream/xinyue-modules`）。合并后应为 4 passed。
2. **那 2 个 skip** 需要 `AGENTEXAM_RUN_IDENTITY_POSTGRES=1` 与可达的 PostgreSQL（`tests/identity/conftest.py:67-69`），本机共享库当前不通。

### 5.3 与 D 基线的交叉验证

| 项 | 结果 |
|---|---|
| 2 failed 的**数量与原因** | ✅ **完全一致**：同在 `tests/contract/test_execution_network.py`，一条 `FileNotFoundError [WinError 2]`、一条 `git -C D:\agent-exam\framework\harbor rev-parse HEAD` 退出码 128 —— 因 `framework/`（gitignored）在本机未恢复。D 的描述成立 |
| 收集总数 | ✅ 可对账：本机 404+2+84 = **490**，D 的 453+2+36 = **491**，差**正好 1** = D 新增的用例 |
| 通过/跳过比例 | ❌ **不可复现**：本机 84 skipped，D 是 36 skipped。原因是本机未启用/不具备 D 机器上的门禁：`AGENTEXAM_RUN_IDENTITY_POSTGRES`、`AGENTEXAM_RUN_CATALOG_MINIO`、`AGENTEXAM_RUN_JOB_MINIO`、`AGENTEXAM_RUN_CODEX_TRIAL_PROBE`，以及 `framework/harbor` 未恢复 |

**因此**：可移植的基线只有"**2 failed，固定是那两条 Harbor 契约用例，原因是本机缺 `framework/harbor`**"；`453 passed / 36 skipped` 与提案文档里旧的 `452 passed / 36 skipped` 都是**环境相关值，不能当作固定基线抄写**。本机实测为 **404 passed / 84 skipped**。

### 5.4 用例覆盖清单

| # | 场景 | 期望 | 覆盖位置 |
|---|---|---|---|
| 1 | 空选择（`job_ids=""`） | `400 EMPTY_COMPARISON_SELECTION` | `test_comparison_http.py:115` |
| 2 | 含非 UUID | `400 INVALID_REQUEST` | `test_comparison_http.py:115` |
| 3 | 去重后超过 20 个 | `400 COMPARISON_LIMIT_EXCEEDED` | `test_comparison_http.py:115` |
| 4 | 未知查询参数名 | `400 INVALID_REQUEST` | `test_comparison_http.py:132`（D 新增） |
| 5 | `job_ids` 重复出现 | `400 INVALID_REQUEST` | `test_comparison_http.py:132`（D 新增） |
| 6 | 无会话 | `401` | `test_comparison_http.py:93` |
| 7 | 不存在的 Job | `404`（与不存在收敛，不泄漏存在性） | `test_comparison_http.py:93` |
| 8 | 协作者访问他人 Job | `404`（整请求收敛） | `test_comparison_http.py:93` |
| 9 | `result_scope=internal_test` | 按不存在处理 | 测试装配 `scope_visible` + `§2.3` 门禁 |
| 10 | 去重（同一 Job 只出一列） | 列数不因重复入参增加 | `test_compare_service.py:100`（服务层） |
| 11 | `missing` 语义 | `resolved` 为 `null`（非 `false`）、`report_path` 为 `null`、不计入未通过、不写成 0 | `test_comparison_http.py:47` |
| 12 | 五档映射 | `COMPLETED`+成功→`resolved`；`COMPLETED`+未成功→`unresolved`；`FAILED`→`infrastructure_error`；其余非终态→`incomplete` | `test_comparison_http.py:47`、`test_matrix.py` |
| 13 | 计数 | `decided` = 前四档之和；`total` = `decided + missing`；无 `coverage` 字段 | `test_comparison_http.py:47` |
| 14 | 无正文泄漏 | 响应不含对象键/秘密路径 | `test_comparison_http.py:90`（`object_key` 断言） |

## 6. 未验证项与待确认项

| 项 | 说明 |
|---|---|
| **§10.4 待补两条 400** | ⏳ **有意延后**。实现见 `cdcb4cf`（D，在 `upstream/xinyue-modules`，**尚未合入 main**）。补写触发条件与理由唯一维护在[契约行动](../../../../actions/2026-09-20-task03-comparison-api-doc.md)。不阻塞对比页 UI——UI 自行拼接 `job_ids`，不会触发这两条 |
| 第 4 个契约用例本机未跑到 | 本机分支无该用例（3 passed）；D 的分支上为 4 passed。合并 `xinyue-modules` 后可在 main 上复现 4 passed |
| `routes/jobs/` 超 8 文件指标 | 既有偏差（9 个 `.py`）；**D 已同意拆分方案并明确由 B 执行**，待做。D 不动该目录 |
| 实时 OpenAPI 计数 | §2.1 已改为 32；**环境已恢复**，具备复核条件，但未实际启动应用读取实时 OpenAPI |
| 静态检查未跑 | `ruff` / `mypy` 已可用但本次未运行；新增用例由 D 记录为干净（`ruff check` 改动文件 → passed，`mypy` 新路由文件 → success），未在本机复现 |
| 2 个 skip | 需 `AGENTEXAM_RUN_IDENTITY_POSTGRES=1` + 可达 PostgreSQL；本机共享库不通，**如实记为 skipped**，不记为通过 |
| D 文档两处失真 | ✅ 已由 D 在 `c5e036d` 收口（§2 改 `decided+total`、§4 实现+测试），问题关闭 |
| 五档枚举是否收敛 | ✅ D 已明确不提升为跨模块公开接口，问题关闭 |
| 对比页 UI | 未开始；开工前须先补逐控件契约行 |
| 任务 03 正式 issue | `.scratch` 下无 `03-*` 任务单，是否发布待 B 确认 |
