# 行动：批次报告非终态契约（D 纠正 + B 复测）

> 状态：**已完成**（2026-09-22）。本行动记录一次**结论被推翻并更正**的过程：B 报的"未完成批次查报告返回 500"在最新 main 上不成立，正确行为就是 `200`。契约由 B 落笔（`HTTP_API.md` 是 B 的文档），**未改任何代码**。

## 1. 情况说明

**来源**：D 复核 B 的报告后答复（[D 的处置记录](../../../../actions/2026-09-22-d-batch-report-nonterminal-contract.md)），指出该 500 在最新 main 上复现不出，并给出代码依据、契约措辞与回归测试。

**B 的初判（错在哪）**：B 在制作"脱离版前端"时录制合成后端的响应，看到两条 `GET /reports/jobs/{id}` 返回 500，当时的归因是"**批次还没跑完**（`AWAITING_OWNER_APPROVAL` / `PREPARING`）时查报告报 500"，并据此提出 409 / 200 全零 / 404 三个候选方案、倾向 409。**这个归因是错的。**

**已核实的事实（本轮全部由 B 自行复核，不采信转述）**：

| 事实 | 证据 |
|---|---|
| 非终态批次查报告返回 200，不是 500 | B 在干净夹具装配上实测：创建批次 → `AWAITING_OWNER_APPROVAL` → `GET /reports/jobs/{id}` **200**，`stage_message="等待所有者批准，不会启动执行。"`、`pending_runs=1`、计数全零；批准后 `QUEUED` → 同样 **200**，`stage_message="已批准，正在等待单机 Worker。"` |
| 该 200 与作用域无关 | 上述批次自身的 `result_scope` 就是 `internal_test`，仍为 200（说明该夹具确实是"显式门控的测试装配"） |
| `_verify` 在无确定性结果时提前返回 | 自行读码：`application/reporting/service.py:121-124` 的 `if result is None: return` |
| `ArtifactUnavailable` 映射为 503 而非 500 | `delivery/http/errors.py` 的 `catalog_error` 对 `CatalogUnavailable` 返回 503 `DEPENDENCY_UNAVAILABLE` |
| 那两条 500 的批次是 `internal_test` 作用域 | 录制文件里两条 500 对应批次的详情与列表条目 `result_scope` 均为 `internal_test`，且都出现在多次列表响应中、状态在录制过程中被反复变更（`AWAITING`→…→`CANCELED`、`PREPARING`→…→`FAILED`） |
| 行为已被回归测试钉住 | D 的 `tests/jobs/reporting/test_job_report_states.py`（4 个用例）已在 `main`（`831c19c`） |

**结论（2026-09-22 最终）**：**这是缺陷，且就在 B 的 HTTP 层**。根因由 D 定位：`delivery/http/routes/jobs/batch_schemas.py` 的 `_JOB_MESSAGES` 只有 9 条，而 `JobStatus` 有 11 个取值——缺的正是 `CANCELED` 与 `CANCEL_REQUESTED`；`stage_message=_JOB_MESSAGES[job.status]` 走到这两个状态抛 `KeyError`，未被捕获 → `500 INTERNAL_ERROR`。其余状态都有条目，所以**只在取消相关的批次上暴露**，D 的 `official` 作用域三态探针（AWAITING/QUEUED/PREPARING）自然打不到。D 已修复（`0eeeb16`）：补齐两条文案、两处取值改为 `.get(..., 中性兜底)`、并新增完整性测试逐个断言每个 `JobStatus` 都有文案。

**B 侧的独立复核（不采信转述）**：① 用 git 里的旧文件与新文件对比，确认旧字典 9 条、缺失的正是那两个键，且旧写法是 `[...]` 直接取值；② 起干净夹具端到端复跑：创建批次 → 取消 → 查报告，得 **200** 与 `"批次已取消；未开始的组合不再执行。"`，计数为 `pending_runs=1`、`outcome=incomplete`、`resolved=null`，与契约一致；③ `CANCEL_REQUESTED` 在这条简单路径上到不了（需有在跑的 Run），其文案与 200 由 D 的两组测试覆盖，B 未端到端复现，如实标注。

**更正记录（保留以免后人重蹈）**：B 中途曾判定“**不是缺陷、那两条 500 来自录制期用 API 造出来的非常规状态**”，并据此写下“录制状态不能当产品行为证据”的教训。**这个判定是错的**：那两条批次的状态变更轨迹（`AWAITING`→…→`CANCELED`、`PREPARING`→…→`FAILED`）里**已经带着取消状态这条线索**，而 B 的复测只验了“是否未完成”这个笼统属性（AWAITING/QUEUED），**没有去复现证据里出现的具体状态**，于是把真实的缺陷误判成了录制噪声。正确的教训是：**复现要打到证据指向的那个具体状态，而不是它所属的宽泛类别**。

## 2. 实施措施与实际改动

1. **落契约**：按 D 的措辞在 `HTTP_API.md` §10.1 补写"批次尚未进入终态时本端点仍返回 `200`"一段（阶段文案与状态计数、`outcome=incomplete`/`resolved=null` 不写入确定结果计数、未完成既不是 404 也不是 409、`report_path` 不代表结果可用），并注明该行为由回归测试钉住、不得当缺陷改回。
2. **记变更**：`HTTP_API.md` §15 新增 2026-09-22 条目，注明依据是 D 的 `official` 作用域三态实测 + `_verify` 提前返回 + B 的 `internal_test` 复测。
3. **更正自己的记录**：`progress.md` 的待办行由"⬜ 已交 D 决定"改为"✅ 已关闭"，并把**"B 原先的归因是错的"**写进该行；同轮小节的对应条目改为"结论与初判相反"；[行动 09](delivery/09-rerun-on-new-main-and-dead-code.md) 的 §2.3 指向同一更正。
4. **流程教训（已按最终结论更正）**：初次复现失败时，不要急于把现象归因为“造数据造出来的”。本案证据里已经写着取消状态，却因为只验了“未完成”这个宽泛类别而误判。**复现要打到证据指向的具体状态上**；另一条纪律仍然成立并值得保留：**报 5xx 之前必须在干净装配上复现一次**——正是这条让 D 拿到了可定位的四项证据。

## 3. 实际改动的文件树

| 路径 | 改动 |
|---|---|
| `docs/interfaces/HTTP_API.md` | §10.1 新增非终态 200 的契约段；§15 新增变更记录 |
| `docs/architecture/modules/web-and-http/progress.md` | 待办行改为已关闭并写明 B 的归因错误；同轮小节条目同步 |
| `docs/architecture/modules/web-and-http/actions/delivery/09-rerun-on-new-main-and-dead-code.md` | §2.3 的 D 报告一条改为"已被复核推翻" |
| `docs/architecture/modules/web-and-http/actions/10-job-report-nonterminal-contract.md` | 本文件（新增，根目录第 8 个文件，正好在 ≤8 上限内） |

## 4. 自验证方式与结果

- **复测（已执行）**：启动合成夹具 → 登录 owner → 登记题目与配置 → `POST /jobs`（202，`AWAITING_OWNER_APPROVAL`，`result_scope=internal_test`）→ 查报告 **200** → 批准 → 查报告 **200**。命令与输出见本轮对话记录；**未能复现 500**。
- **读码确认（已执行）**：`service.py:121-124`、`errors.py` 的 `catalog_error`。
- **相对链接校验（已执行）**：模块文档与新增文档 0 断链。
- **未执行**：未复现那两条 500 的确切成因（无法获得当时的夹具状态与异常栈）；未跑后端全量（本轮无代码改动）。

## 5. 未验证 / 局限

- 那两条 500 的**真实成因仍未定位**。按 D 的规则与现有证据，按"当前 main 已定义"**关闭**，但这一点是"无法复现"，不是"已证明无害"。
- 录制文件里那两条 500 会继续被脱离版回放（原型里那两个批次的"查看批次进度"会显示错误提示）；这是**如实回放**，不需要修，但评审时若被问到要能说清。
