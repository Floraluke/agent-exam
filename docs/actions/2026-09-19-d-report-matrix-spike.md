# 2026-09-19 D 预研：跨配置对比矩阵与"缺失"语义（原型）

## 状态与情况说明

状态：In progress（2026-09-19 创建）。定位：**预研原型（spike）**——扩展任务 03–08 尚未发布任务单，本项在成员 D 的授权下，按项目规则（行动文档先行、只动本人分支与 D 模块、不改公共契约）先行验证实现路径。

来源请求：成员 D 于 2026-09-19 要求"按我们的规则开始开发"，并明确只负责 08（主责项）。

范围：在「证据与报告 Module」（D 主责）内新增一个**纯内部**能力——把多个 `JobReport` 聚合成"题目 × 配置"对比矩阵，并把"缺失"（没有 Run，或 Run 已完成但报告缺失）作为独立一档，不并入"未通过"、也不写成 0。

依据（项目文档原文，非自拟需求）：

- `plan.md` 第 5 节（任务 03）："复用批次报告建'题×配置'矩阵，汇总确定性通过数、未通过、基础设施故障、未完成；**缺失 Run 或报告标为缺失，不当作未通过或零**"。
- `plan.md` 第 10 节（任务 08）："报告同题对比能展开原始安全证据"。

当前事实：

- 现有 `JobReportResponse`（`delivery/http/routes/jobs/batch_schemas.py:84`）只支持**单个 Job 内部**的矩阵；outcome 四档为 resolved / unresolved / infrastructure_error / incomplete（`:15`），**既没有跨 Job/跨配置的对比视图，也没有"缺失"这一档**。
- 本机后端测试基线：386 passed / 82 skipped / 2 failed（两个失败均因缺固定上游源码 `framework/harbor`，与本项无关）。

已确认决定：本项为**原型**——不改现有文件行为、不改 HTTP 契约、不改数据库表、不新增对外 Interface。任务 03 正式发布后，本原型要么并入正式实现、要么丢弃，由该任务的行动文档记录结论。

未知项：任务 03 正式发布时的字段与形态；本原型只固定"分类口径"与"缺失语义"。

明确排除项：不改 `batch_schemas.py` 与任何路由/契约/表；不连接 PostgreSQL 或 MinIO；不运行真实模型；不动其他成员模块。

## 实施措施

1. 新增 `apps/backend/src/eval_platform/application/reporting/matrix.py`：纯函数 `build_matrix(reports) -> ReportMatrix`，输入现有 `JobReport`（`domain/jobs/execution.py:122`），输出列（每个 Job×配置一列）、行（题目合集）、单元格与每列合计。
2. 分类口径（写死并在测试中断言）：无 Run → `missing`；`COMPLETED` 但无报告/结果 → `missing`；`COMPLETED` 且有结果 → `resolved` / `unresolved`；`FAILED` → `infrastructure_error`；其余 → `incomplete`。缺失单元格不携带 `resolved` 布尔（保持 `None`），避免"缺失被写成 0/false"。
3. 新增 `apps/backend/tests/jobs/reporting/test_matrix.py`（新子目录；`tests/jobs/` 已达 8 个文件的层内上限，按项目规则改用子目录）：覆盖跨 Job/配置对比、缺题 → `missing`、COMPLETED 无报告 → `missing`、失败/未完成分档、每列合计、空输入与行序稳定。
4. 运行新增用例 + 全量回归 + `ruff` + `mypy`，记录真实结果。

完成标准：新增用例全部通过；全量回归不出现新失败（基线仍是 2 failed 于 `framework/harbor`）；`ruff`/`mypy` 无新增错误；除下列新增文件外无其他改动。

## 受影响文件树

```text
apps/backend/src/eval_platform/application/reporting/
  matrix.py                        # 新增：跨 Job/配置的"题×配置"矩阵与"缺失"语义（纯内部，无对外 Interface）
apps/backend/tests/jobs/reporting/
  test_matrix.py                   # 新增：分类、缺失语义、合计、顺序与空输入的单元测试
docs/actions/2026-09-19-d-report-matrix-spike.md   # 本行动文档（新增）
```

不改动：`delivery/**`（含 HTTP DTO 与路由）、`adapters/**`、`domain/**`、数据库 schema、`docs/interfaces/**`、`docs/architecture/**`、其他成员负责的模块与文件。

## 自验证方式

在 `apps/backend` 下执行（只读源码，不改他人文件）：

```text
./.venv/Scripts/python.exe -m pytest tests/jobs/reporting/test_matrix.py -q     # 新增用例
./.venv/Scripts/python.exe -m pytest -q                                         # 全量回归（基线 2 failed / 386 passed / 82 skipped）
./.venv/Scripts/python.exe -m ruff check src/eval_platform/application/reporting/matrix.py tests/jobs/reporting/test_matrix.py
./.venv/Scripts/python.exe -m mypy src/eval_platform/application/reporting/matrix.py
git status --short                                                              # 只应新增上述文件
```

预期：新增用例全部通过；全量回归与基线一致（仅 `framework/harbor` 缺失导致的 2 个失败）；`ruff`/`mypy` 无新增错误。

## 自验证结果

完成时间：2026-09-19（本批次）。逐项实测（命令均在 `apps/backend` 下执行）：

1. 新增用例：`pytest tests/jobs/reporting/test_matrix.py -q` → **3 passed**（0.02s）。
2. 全量回归：`pytest -q` → **2 failed, 389 passed, 82 skipped**（47.01s）。与基线（2 failed / 386 passed / 82 skipped）相比：通过数 +3（本批新增用例），失败集合不变；两个失败仍是缺 `framework/harbor` 造成的环境缺口（`tests/contract/test_execution_network.py:109`、`:129`），与本批无关。
3. `ruff check`（新增两文件）→ **All checks passed**。
4. `mypy`（`matrix.py`，项目 strict 配置）→ **Success: no issues found**。
5. `git status --short` → 只新增 `docs/actions/2026-09-19-d-report-matrix-spike.md`、`apps/backend/src/eval_platform/application/reporting/matrix.py`、`apps/backend/tests/jobs/reporting/`（另有工具目录 `.zcode/`，与本项无关）。**未修改任何既有文件**。

过程中的偏差（如实记录）：

- 首轮 `ruff` 报 1 处 `E501`（`matrix.py:98` 超 88 列）、首轮 `mypy` 报 1 处变量类型收窄问题（`run` 变量名复用）；两者已修复并复验：修复后 `ruff`/`mypy` 通过，全量回归仍为 2 failed / 389 passed。
- 文件规模：`matrix.py` 141 行、`test_matrix.py` 151 行，均在项目 200 行指标内。测试放入新子目录 `tests/jobs/reporting/`，因为 `tests/jobs/` 已达"每层 8 个文件"上限。

结论：本批交付为**原型**且验证通过（仅存在与 `framework/harbor` 缺失相关的 2 个既有失败）。任务 03 正式发布后，由该任务的行动文档决定本原型并入或丢弃。
