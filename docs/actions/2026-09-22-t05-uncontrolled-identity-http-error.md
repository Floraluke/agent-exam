# 行动：超受控集合的存量记录以受控错误失败关闭（任务 05 的小片）

> 状态：**已完成**（2026-09-22）。本片只修一处错误映射，不触及任务 05 未完成的 S9/S10/S11（均等 T2）。

## 1. 情况说明

**来源**：B 在[任务 05 受控词汇的契约对齐行动](../architecture/modules/web-and-http/actions/05b-t05-controlled-vocabulary-alignment.md)第 6 节把一处新问题留给 E 决定——`catalog_schemas.py` 的 `_controlled()` 抛裸 `ValueError`，而 `app.py` 只注册了 6 个异常处理器（`AuthenticationRequired`、`CatalogError`、`JobError`、`RequestValidationError`、`IdentityUnavailable`、`HTTPException` 与成员资格错误），**没有 `ValueError` 处理器**。用户 2026-09-22 会话内同意先修此片。

**已核实的事实**（本轮实际读码，不采信转述）：

| 待核实项 | 结论 | 证据 |
|---|---|---|
| `_controlled` 抛裸 `ValueError` | ✅ 属实 | `delivery/http/catalog_schemas.py:9-17`（`raise ValueError(code)`） |
| 无 `ValueError` 处理器 | ✅ 属实 | `delivery/http/app.py:76-88` 六个处理器，无 `ValueError` |
| 该路径可达 | ✅ 可达：仓库读取路径**不重校验身份**，只有 `register()` 校验，故越过注册表与库级 CHECK 的存量记录会走到响应构造 | `application/agent_registry.py:52-70`（`get`/`list` 直接回记录） |
| 契约是否已覆盖这类失败 | ✅ 已覆盖，**无需改契约** | `docs/interfaces/HTTP_API.md` §5：“对象缺失/损坏或依赖故障为 **503 `DEPENDENCY_UNAVAILABLE`**”；§4.2 只把 `UNCONTROLLED_*` 记为失败关闭标记，**未承诺任何状态码**（B 明确该选择属 E） |

**已确认的决定**：改为抛既有的域错误 `CatalogUnavailable`，由 `errors.py` 既有的 `catalog_error` 处理器映射成 **503 `DEPENDENCY_UNAVAILABLE`**。理由：① 契约 §5 已把“目录对象损坏”归类为 503 `DEPENDENCY_UNAVAILABLE`，零契约变更；② 不新增错误码、不新增公开枚举；③ 内部码 `UNCONTROLLED_AGENT_TYPE`/`UNCONTROLLED_PROVIDER` 只留在进程内，不对客户端回显（符合“内部错误码绝不回显”的既有纪律）。

**明确不做**：不改 `HTTP_API.md`（B 的契约唯一事实源，本片无契约变化）；不改 B 的模块文档；不新增错误类型、不新增 Table/Module/Interface；不动 S9/S10/S11；不推送。

## 2. 实施措施

1. `delivery/http/catalog_schemas.py`：`_controlled()` 改为抛 `CatalogUnavailable(code)`，并在 docstring 写明对外表现（503 `DEPENDENCY_UNAVAILABLE`）与内部码不回显。
2. 新增测试 `tests/catalog/agent_identity/test_uncontrolled_records.py`：用“越过注册表与 CHECK 的存量记录”同时钉住 HTTP 层表现（503 + 受控码 + 不泄漏）与域层失败关闭（不回落默认值）。
3. 做**区分力实测**：把实现退回 `ValueError`，确认新用例失败；还原后通过。
4. 同批同步文档：[进度日志](../LLY/03-progress/PROGRESS_LOG.md)追加条目；任务 05 任务单 Comments 记录本片与给 B 的一行回告。

**完成标准**：新用例在修复前失败、修复后通过；超集合记录既不再返回 500，也不回落成 `openai_chatgpt`；静态检查与既有回归无新增失败。

## 3. 受影响文件树

| 路径 | 改动与职责 |
|---|---|
| `apps/backend/src/eval_platform/delivery/http/catalog_schemas.py` | **改**。响应构造层；`_controlled()` 是“如实呈现或拒绝”的守门函数，本片把它从裸 `ValueError` 改为受控域错误。与 `delivery/http/errors.py` 的 `catalog_error` 处理器构成“抛出方 → 映射方”关系（前者不决定状态码，后者决定）。 |
| `apps/backend/tests/catalog/agent_identity/test_uncontrolled_records.py` | **新增**。用 `catalog.memory.MemoryAgents` 的替身变体模拟存量损坏记录；断言 HTTP 503 受控响应与域层拒绝。 |
| `apps/backend/tests/catalog/agent_identity/` | 该层原有 2 个文件，新增 1 个后为 3 个，未触及每层 8 文件上限。 |
| `docs/LLY/03-progress/PROGRESS_LOG.md` | **改**。追加 2026-09-22 条目：合并增量、B 的契约对齐（含对我方一处转述的修正）、本片修复与全部实测数字。 |
| `.scratch/ui-catalog-providers/issues/05-fake-provider-secure-execution-chain.md` | **改**（仅 Comments）。记录缺陷关闭与给 B 的回告；不动已批准验收项与状态标签。 |
| `docs/LLY/README.md` | **改**。在"当前状态"的行动记录清单末尾追加本片链接，保持行动链完整。 |
| `docs/actions/2026-09-22-t05-uncontrolled-identity-http-error.md` | 本文件（新增）。 |

未改动（与计划一致）：`HTTP_API.md`、`app.py`、`errors.py`、`domain/catalog.py`、`DATA_MODEL.md`、任何 B 的文档。

## 4. 自验证方式

| 检查 | 命令 | 期望 |
|---|---|---|
| 新用例（修复前） | `pytest tests/catalog/agent_identity/test_uncontrolled_records.py` | **失败**（区分力证据：现在返回 500） |
| 新用例（修复后） | 同上 | 通过 |
| 目录套件 | `pytest tests/catalog` | 无新增失败 |
| 默认回归 | `pytest -q -p no:cacheprovider` | 与基线 587/105/2 一致，2 项失败仍是缺 `framework/harbor` 的 ISSUE-04 |
| 静态检查 | `ruff check`、`ruff format --check`、`MYPYPATH=src mypy src/eval_platform` | 全绿 |

## 5. 自验证情况

**已执行，且实际输出已检查**：

| 检查 | 命令 | 实际结果 |
|---|---|---|
| 新用例（修复后） | `.venv/Scripts/python.exe -m pytest tests/catalog/agent_identity/test_uncontrolled_records.py -q` | **4 passed**（0.53 秒） |
| 新用例（修复前，区分力） | 临时把实现退回 `raise ValueError(code)` 后同上 | **4 failed**：两条域层用例、两条 HTTP 层用例全部失败；还原（`catalog_schemas.py:23` 恢复为 `raise CatalogUnavailable(code)`）后 4 passed |
| 目录套件 | `pytest tests/catalog -q` | **46 passed / 29 skipped**，增量正好是 4 条新用例 |
| 默认回归 | `pytest -q -p no:cacheprovider` | **2 failed / 591 passed / 105 skipped**（89.68 秒）；相对基线 587 通过数 +4，2 项失败完全相同（缺 `framework/harbor` 的 ISSUE-04） |
| 静态检查 | `ruff check` / `ruff format --check` / `MYPYPATH=src mypy src/eval_platform` | 通过 / 342 文件已格式化 / 184 源文件无问题 |

**计划偏差**：无。实施内容与第 2 节一致，未新增错误类型、未改契约、未改 B 的文档。

**未执行与限制（如实记录）**：

- 未在**开启真实 PostgreSQL** 的条件下运行：本机 PostgreSQL（`55432`）当前未监听，故 `tests/catalog` 的 29 条集成用例按设计跳过。"存量损坏记录来自真实库"这一条只以**替身**证明（替身模拟越过注册表与库级 CHECK 的记录），未以真实库证明；库级约束本身在任务 05 的 S8 已用真实旧库实测过。
- 未做浏览器侧验证：该路径的呈现验证（受控文案忠实呈现、未知错误码失败关闭）属 B 的测试基建，触发条件是本任务链条整体落地，未到。
- 未推送：按项目约定推送需单独确认。

## 6. 后续

- 给 B 的回告：本次修复后该路径对客户端的可观察表现是 **503 `DEPENDENCY_UNAVAILABLE`**，内部码不外泄；`HTTP_API.md` §4.2 现把 `UNCONTROLLED_*` 记为失败关闭标记但未写状态码，B 可自行决定是否补一句（本片未改 B 的文档）。
- 本片不改变任务 05 的其余停点：S9/S10/S11 仍等 T2。
