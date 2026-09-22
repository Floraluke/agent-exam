# 2026-09-22 D：最新 main 上的本地门禁实跑与 05 的 D 侧接缝核对

## 状态与情况说明

状态：Completed（2026-09-22）。

来源请求：用户指示"所有能做的都可以开始做，不需要等谁的许可"。本行动把**不依赖他人窗口**的部分全部做掉：在最新 main 上跑完能跑的门禁、把任务 05 的 D 侧接缝（额度/状态/报告）核对清楚，并记录环境缺口。

基线：`ac72d1e`（拉取后本地 main，含 59 个上游提交：E 的任务 05 provider-access 实现与测试、B 的 Web/文档、组长的并发修复与根级门禁配置）。

## 实测结果（本机，全部为实际输出）

| 门禁 | 结果 | 说明 |
|---|---|---|
| 后端默认门禁（`apps/backend`，PG 门禁开启） | **663 passed / 53 skipped / 2 failed**，覆盖率 **86.80%**（阈值 80% 达到） | 2 个失败是缺 `framework/harbor` 的既有缺口 |
| 仓库根统一门禁 | **665 passed / 63 skipped / 11 failed** | 11 个失败全在 `infra/tests/test_compose_config.py`，硬断言要求 Docker CLI，本机未安装 |
| 任务 05 provider 套件（`tests/providers`） | **169 passed / 2 skipped** | 2 个跳过是 POSIX 专属（符号链接、属主/权限位），Windows 无对应能力 |
| Web ESLint（`--max-warnings 0`） | 通过 | — |
| Web TypeScript（`tsc --noEmit`） | 通过 | — |
| Web 生产构建（Next 15.5.25） | 通过 | 静态预渲染完成，共享 JS 103 kB |
| Web 浏览器回归（Playwright） | **44 passed / 1 failed** | 唯一失败是 `artifact-retention/deleted-state.spec.ts` 找不到 `chromium_headless_shell-1243` 二进制（本机未装该浏览器），不是产品缺陷 |
| `mypy`（默认入口，无参数） | Success：186 个源文件 | CR-04 修复后不再需要显式路径 |
| `ruff check` / `ruff format --check` | All checks passed / 347 文件一致 | — |

环境缺口（本机，均为"缺外部依赖"而非缺陷）：

- **Docker CLI 缺失** → `infra/tests/test_compose_config.py` 11 项失败（`infra/` 属所有者单机运行模块）。
- **`framework/harbor` 缺失**（第三方上游源码，按依赖总表不入库）→ 2 项契约用例失败。
- **Playwright headless-shell 未安装** → 1 项浏览器用例失败；其余 44 项走系统 Chrome 通过。按项目规则"不自动下载或升级浏览器"，本行动未安装。
- **MinIO 未安装** → 4 项 Job 制品用例按显式门禁跳过。

为跑浏览器回归，本机生成了 2 天有效的自签测试证书（仓库根 `runtime/tests/identity-https-key.pem` 与 `-cert.pem`），做法与 [`DEPENDENCIES.md`](../../dependencies/DEPENDENCIES.md) 记录的步骤一致（`CN=127.0.0.1` + SAN `IP:127.0.0.1,DNS:localhost`）；证书与结果都在被忽略的 `runtime/` 内，未改动系统信任、未进入 Git。

## 任务 05 的 D 侧接缝核对（额度、状态、报告）

已核对的代码事实：

1. **额度（账本）在 E 的适配器内，不在平台数据库**：`adapters/execution/provider_access/budget.py` 的 `BudgetLedger` 明确写着"per-run token ledger ... upper bounds, never billing"，并且**consumed 总量是无默认值的构造参数**——"无法说明本 Run 已花多少的调用方，不得在代理重启后从零开始新账本"，即任务 05 第 7 项的"计量状态遗失拒绝再用旧额度、不重置为满额"由该设计承接。
2. **失败码是受控词表**：`provider_access/failures.py` 的 `MAPPED_CODES` 把内部码映射成 `(failure_code, failure_summary)`，`ProviderRejection` 是唯一转换点（`server/contracts.py:84`），未知内部码直接拒绝。
3. **D 侧无需新增状态或表**：provider 侧不写 Run 的 stage/status（`server/*.py` 无相关写入），因此 `Stage` 词表未变；`_JOB_MESSAGES`/`_RUN_MESSAGES` 的完整性测试仍然成立。
4. **报告侧已承接未知用量**：`usage`/`cost_usd` 缺值保持 `null`，不写 0；Run `FAILED` 在批次报告映射为"基础设施错误"档（2026-09-22 已加契约回归）。
5. **恢复判断归 worker**：`provider_access/server/closure.py` 明确"能否恢复由持久化的 Job 记录判断，属于 worker"——对应 D 的恢复/重试用例（`tests/jobs/recovery/` 16 个）。worker 的**绑定选择**（按 Run 的 `AgentConfiguration` 选 ChatGPT 或代理绑定）位于 `delivery/worker/runtime.py`，其文档首行写明是"Owner-local production Worker composition"，属所有者单机运行模块；D 本次未改动该文件。

结论：05 里属于 D 的"额度/状态/报告"接口面在平台侧已经就位并有测试；真正待补的是 E 的代理链产物（真实 usage/失败证据）与 worker 侧绑定选择（A 的组合根），以及需要 Docker/Harbor 的端到端窗口。

## 受影响文件树

```text
docs/actions/
  2026-09-22-d-local-gate-run-and-provider-seam-review.md   # 本行动文档（新增）
runtime/tests/                                              # 本机测试证书与浏览器结果（被忽略，不入库）
  identity-https-key.pem / identity-https-cert.pem          # 2 天自签，仅本机浏览器测试用
```

没有改动任何产品代码或他人文档；本行动只读代码并运行既有检查。

## 自验证方式与结果

即上表各命令本身（pytest 三种入口、ruff、mypy、npm lint/typecheck/build/test:e2e），全部为实际执行并读取输出。没有把跳过项当作通过：MinIO 4 项、POSIX 2 项、Docker 11 项、headless-shell 1 项都逐条记录为环境限制。
