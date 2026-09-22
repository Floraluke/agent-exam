# 行动：夹具故障注入 + 任务 05 两项呈现验证

> 状态：**已完成**（2026-09-22）。把 `progress.md` 里"任务 05 的两项呈现验证"与"夹具控制端点"两条从待办做成已实施。

## 1. 情况说明

**来源**：E 答复纠正了 B 记录里的一个前提——那两项验证**不依赖链路可用性**，它们验的是 **Web 层对"给定码 + 给定文案"的行为**：夹具造一条带受控 `failure_summary` 的 Run、再造一条未知码的 Run 就够了。E 另提出一条请求（非前置）：造例要覆盖**两类码**——链路将来会发出的五类 `PROVIDER_*`，与**永不会发出**的未知码；并确认页面不回显内部码或文本。

**背景事实**：E 已确认链路未接线（B 在 main 上核到 `delivery/worker/runtime.py` 的 `MODEL_HOSTS` 写死、`validate_auth_file` 无条件；`provider_config.py`/`render_provider_config` 只在他分支上），因此**今天没有任何真实 provider 失败能写进 Run**——这正是"不依赖链路"的前提。

**明确不做**：不改产品代码（只改测试夹具与新增用例）；不做真实链路的端到端证据（按 E 建议放**任务 08 的矩阵**）。

## 2. 实施措施

1. **夹具控制端点**（`apps/backend/tests/identity/browser_server.py`，+23/−1 行，225 → 247）：新增 `POST /__test__/jobs/fail-next-run`，正文 `{"failure_code": ..., "failure_summary": ...}`，沿用既有 `__test__` 端点的形状与风格。
   - **注入点选在 Run 失败码的唯一下沉处** `job_repository.fail`（`RunResultProcessor.fail` → `memory_results.fail`），把该实例方法包一层、**取走即清空**（一次生效）；同时让 `BrowserBackend.execute` 在有注入时改走现成的 `FailedBackend.execute`，走正常失败收束后由注入值替换码与文案。
   - **未调用端点时行为完全不变**：`forced_failure` 为空时 `if` 短路、包装层原样透传；已用同一进程内的下一个 Run 验证（仍 `COMPLETED`/`resolved: true`/无 `failure_code`）。
2. **两条呈现验证**（新增 `apps/web/tests/jobs/failure-presentation.spec.ts`，101 行、6 条用例，**独立成文件**以避免共享后端状态污染——这是宽矩阵那轮踩过的坑）。
3. **先读组件再写断言**：`features/jobs/report.tsx`、`batch-report.tsx`、`lifecycle/recovery.tsx`、`lib/api-client.ts`。

## 3. 读到并记录的真实呈现行为（与"前端做过滤"的直觉不同）

- `report.tsx`：`deterministic_result` 为 null 时渲染"基础设施错误：本次没有形成确定性成绩。"，并把 `错误码：<code>{failure_code}</code>` 与 `failure_summary` 放在**默认折叠**的"技术详情"里。
- `api-client.ts`：只对 `ApiErrorCode`（HTTP 错误码）做中文映射；`failure_code`/`failure_summary` 作为**任意字符串透传**。
- **结论：Web 层没有"码 → 文案"映射，是纯透传**。因此"未知码失败关闭"在本层的表现是：**只显示码本身、不编造类别文案、呈现状态不受码影响**；**真正拦住内部码的是写入侧**（`provider_access/failures.py: controlled_failure`）——与任务 05 审计的结论一致。

## 4. 实际改动的文件树

| 路径 | 改动 |
|---|---|
| `apps/backend/tests/identity/browser_server.py` | 新增故障注入控制端点与注入点包装（+23/−1，225 → 247 行） |
| `apps/web/tests/jobs/failure-presentation.spec.ts` | 新增：两条呈现验证共 6 条用例 |
| `docs/architecture/modules/web-and-http/actions/05-necessary-error-presentation.md` | "待 E 链条落地后再执行"改为已实施，附证据 |
| `docs/architecture/modules/web-and-http/progress.md` | 两条待办改为已完成 |
| `docs/architecture/modules/web-and-http/actions/delivery/14-fixture-failure-injection-and-presentation-verifications.md` | 本文件（新增） |

## 5. 自验证方式与结果

```bash
cd apps/web && npm install                                   # 上游新增 eslint 依赖后必需
AGENTEXAM_USE_SYSTEM_CHROME=1 npx playwright test tests/jobs/failure-presentation.spec.ts
AGENTEXAM_USE_SYSTEM_CHROME=1 npm run test:e2e               # 全量，仓库的判定标准
```

| 检查 | 实际输出 |
|---|---|
| 新 spec 单独跑 | **6 passed（48.2s）**（五类 `PROVIDER_*` 各一条 + 未知码一条） |
| **全量** | **exit 0**：26 个 spec、**52 passed / 0 failed / 0 skipped**（日志 `runtime/tests/full-e2e.log`，B 已核对该日志内**零失败行**） |
| 断言强度 | `toHaveText(code)`（整串、大小写敏感）+ `getByText(summary, { exact: true })`（**逐字原文**）+ 7 类内部码前缀与 5 条受控短句的**否定扫描** |
| **负控**（证明断言非空转） | 改动注入文案 → 逐字断言**失败**；注入内部码 `PROVIDER_BINDING_ALREADY_ISSUED` → 前缀扫描**失败**（页面确实原样回显内部码） |
| 夹具行为不变 | 不调用端点时同一进程内下一个 Run 仍为 `COMPLETED`/`resolved: true`/无 `failure_code` |
| ruff | `ruff check` + `format --check` 对夹具文件通过 |

## 6. 未验证 / 局限

- **真实链路端到端证据不在本切片**（真实链路 → 真实 DB 行 → 页面），按 E 的建议放任务 08 的矩阵；本轮证据是**夹具注入**层面的。
- "未知码失败关闭"的边界如实说明：页面**原样显示**未知码（实测行为），本层的"失败关闭"= 不编造类别文案、不改变状态呈现；**Web 层不是过滤器**，若上游写入内部码，页面会照实显示——拦截责任在写入侧。
- 夹具文件增至 **247 行**，继续超出"≤200 行"的默认指标（该文件的既有例外此前已获用户确认）；本轮新增 22 行已在任务报告里说明，未拆文件。
- **跑测方式的一个坑（供后续复用）**：直接 `npx playwright test` 会让 Next dev 重建 `apps/web/next-env.d.ts` 与 `tsconfig.json`（留下工作树改动），**仓库自带的 runner（`npm run test:e2e`）会在收尾时还原**；本轮已还原并确认工作树只剩预期文件。
