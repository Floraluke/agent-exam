# 行动：新 main 上的重跑、死代码清理与给 D 的契约缺口

> 状态：**已完成**（2026-09-22）。本行动是收尾性质：不做功能改动，只做验证、一处死代码清理和一条对外报告。

## 1. 情况说明

**来源**：B 清点了自己"现在就能做、不依赖任何人"的事项，用户确认"按你说的顺序来做，一次性做完"。顺序为：① 在新 main 上重跑两套测试 → ② 把批次报告 500 整理给 D → ③ 提 PR → ④ 清死代码 → ⑤ 给 A 补说明 → ⑥ 跑 ruff/mypy。

**背景事实**：`main` 已从 `1888aa2` 前进到 `fb8aadf`（E 的提供方访问链 PR #24/#25 与 B 的契约对齐 PR #26），其中 **B 的界面面从未在这些提交上验证过**；`progress.md` 也挂着"本机在新 main 上重跑 ⬜ 未做"与"ruff/mypy 未在 B 侧运行 ⬜"两条。

**明确不做**：不改后端、不改契约（给 D 的是提案，措辞等他们定）、不动其他模块文件、不碰任务 05 的呈现验证（前置未满足）。

## 2. 实施措施与实际改动

### 2.1 在后端跑（不改代码）

| 检查 | 命令 | 结果 |
|---|---|---|
| 后端全量 | `cd apps/backend && .venv/Scripts/python.exe -m pytest -q -p no:cacheprovider` | **2 failed / 494 passed / 106 skipped**（60.35s） |
| ruff 检查 | `... -m ruff check tests/identity/browser_server.py` | `All checks passed!` |
| ruff 格式 | `... -m ruff format --check tests/identity/browser_server.py` | `1 file already formatted` |
| mypy（项目范围） | `MYPYPATH=src ... -m mypy src/eval_platform` | `Success: no issues found in 175 source files` |

**两个失败项**：`tests/contract/test_execution_network.py::test_bootstrap_imports_fixed_harbor_not_the_adjacent_adapter_package` 与 `::test_sidecar_exports_traceable_dns_adaptation_and_never_overwrites`，即本机缺 `framework/harbor` 的**已知可移植基线**，与文档一致。passed/skipped 相对旧记录（408/86，`fd369cc`）上升到 494/106，来自 E 那批提交新增的测试。

**一处工具链事实（如实记录）**：按项目配置**裸跑 `mypy`**（`[tool.mypy] packages = ["eval_platform"]`、`strict = true`）在本机**不可用**，报 `Package 'eval_platform' cannot be type checked due to missing py.typed marker`（解析到的是未安装 `py.typed` 的包而非 `src/` 树）。改用路径方式（`MYPYPATH=src mypy src/eval_platform`）才是有效信号。另：对**单个测试文件**跑 mypy 会连带检查未纳入项目范围的测试夹具，得到 268 个 `no-untyped-call`/`no-untyped-def` 类错误——**那是范围外的噪声，不是 B 的结论**，不作为指标。

### 2.2 前端死代码清理（唯一代码改动）

`apps/web/src/lib/job-client.ts` 的 `runArtifacts`（`GET /runs/{id}/artifacts?limit=100`）经全仓检索**无任何界面调用**，属死代码；已删除该函数，并同步移除随之无用的 `ArtifactPage` 类型导入与 `parseArtifactPage` 导入。

**刻意不做连锁删除**：`report-shapes.ts` 的 `parseArtifactPage` 与 `contracts.ts` 的 `ArtifactPage` 现在也没有调用方了（唯一调用者就是被删的那个函数），但**保留**——它们定义的是契约 §9 制品索引端点的响应形状，与同文件其它解析器同一模式；删掉会连带改动形状定义文件，超出"删一个未使用的助手"的范围。因此现状是：**§9 制品索引在 Web 侧只有形状定义、没有调用方**，这是有意的，不是遗漏。

### 2.3 给 A 的说明与给 D 的报告

- 脱离版目录补 `README.md`：这是什么、怎么打开、与"跑起来的前端"的差别、已知边界、反馈什么最有价值。
- 起草[给 D 的契约缺口说明](../../../../../runtime/drafts/to-D-report-500-contract-gap.md)（**在 gitignored 的 `runtime/` 下，不入库**）：未完成批次的批次报告返回 500 的证据、已核实的代码路径、三个候选方案与 B 的倾向。

## 3. 实际改动的文件树

| 路径 | 改动与职责 |
|---|---|
| `apps/web/src/lib/job-client.ts` | 删除死代码 `runArtifacts` 与其无用导入（本文档所在 PR 中唯一的代码改动） |
| `docs/architecture/modules/web-and-http/progress.md` | 新增本轮小节；更新"新 main 重跑""ruff/mypy"两条待办状态；新增"批次报告 500"待 D 决定项 |
| `docs/architecture/modules/web-and-http/actions/09-rerun-on-new-main-and-dead-code.md` | 本文件（新增） |

（前一轮的 06/08 与 progress 重写已在同一 PR 之前完成，见[行动 08](08-real-web-detached-build.md)。）

## 4. 自验证方式

```bash
cd apps/backend && .venv/Scripts/python.exe -m pytest -q -p no:cacheprovider
cd apps/web && npm run typecheck
cd apps/web && AGENTEXAM_USE_SYSTEM_CHROME=1 npm run test:e2e
```

**成功标准**：后端失败项仍固定为那两条 Harbor 用例；`typecheck` 通过；浏览器全量全绿（按既有纪律：**必须在全量里跑过才算通过**）。

## 5. 自验证情况

- 后端全量与 ruff/mypy：**已执行**，结果见 2.1。
- `npm run typecheck`：**已执行**，无输出（通过）。
- 浏览器全量：**已执行**，`AGENTEXAM_USE_SYSTEM_CHROME=1 npm run test:e2e` **退出码 0**——22 个 spec 逐个跑过（运行器每遇首个失败即以非零码中止，故 0 即全绿）。作用范围是确认死代码删除没有连带影响。

**未验证 / 局限**：

- 本次改动只有一处死代码删除，**不含产品行为改动**；浏览器全量的作用是确认它没有连带影响。
- 给 D 的方案 A/B/C 是 B 的倾向，不是结论；契约文字等 D 回复后再写。
