# 行动：回复 B 的三问（链路落地时间、超集合记录的 HTTP 表现、夹具控制端点）

> 状态：**已完成**（2026-09-22）。本行动只追加记录与答复，不改代码、不改契约。

## 1. 情况说明

**来源**：B 通过用户转述提出三个问题——① 假提供方链的落地时间（决定 B 的两项呈现验证何时能开工）；② 超受控集合记录的 HTTP 表现要不要包装成受控错误；③ 夹具"强制下一次响应出错"的控制端点何时可以做。

**答复前核实的事实**（本轮实际 grep/读码，不采信转述）：

| 待核实项 | 结论 | 证据 |
|---|---|---|
| 链路是否已接运行主链路 | ❌ **未接** | `provider_access` 包外只有一个导入方（`adapters/execution/codex/provider_config.py:28` 引 `REGISTERED_UPSTREAMS`）；`render_provider_config` 零调用方（仅测试引用） |
| worker 是否还会要求 ChatGPT 认证 | ✅ 仍会 | `delivery/worker/runtime.py:66` 无条件 `validate_auth_file(...)`；`:26` `MODEL_HOSTS = ("auth.openai.com", "chatgpt.com")`；`:80` 只构造一个 adapter |
| 真实 provider 失败今天能否写到 Run | ❌ 不能 | 上述两条：链路的受控文案目前只出现在代理自己对容器内客户端的应答里（`server/http.py:143-144`），未经过平台侧写入方 |
| 问题②是否已解决 | ✅ 已在 `3a5a9b8` 解决 | 见[前一份行动](2026-09-22-t05-uncontrolled-identity-http-error.md) |
| 夹具是否已有控制端点先例 | ✅ 有 | `tests/identity/browser_server.py:194` `POST /__test__/jobs/interrupt-next`、`:182/:188` worker pause/resume、`:206` 制品过期清理 |
| T2 与本问题的关系 | T2 **首次执行已停手**（侧车退出 127，工具链失败，非拓扑结论），七条断言未测得；诊断下一步是取侧车日志 | 任务单 Comments 与[进度日志](../LLY/03-progress/PROGRESS_LOG.md)当日条目 |

**已确认的结论**：① 落地时间由 T2 的结论触发而非日期，且本轮 T2 尚未测得；**两项呈现验证不必等链路**，可在合成夹具上先做；② 已实现 503 受控错误，B 可选择在 §4.2 补一句状态码；③ 夹具控制端点属 B 的测试基建，不依赖 E，现在即可做。

## 2. 实施措施

1. 在任务 05 任务单的 `## Comments` 追加一条答复（E 与 B 的既有对齐渠道，可追溯）。
2. 在[进度日志](../LLY/03-progress/PROGRESS_LOG.md)当日条目追加一行指向本行动。
3. 本文件记录核实依据与结论。

**完成标准**：三个问题各有明确结论与依据；每条结论都能指回代码或当日记录；不产生任何代码或契约改动。

## 3. 受影响文件树

| 路径 | 改动与职责 |
|---|---|
| `.scratch/ui-catalog-providers/issues/05-fake-provider-secure-execution-chain.md` | **改**（仅 Comments）。追加对 B 三问的答复；不动任务正文、验收项与状态标签。 |
| `docs/LLY/03-progress/PROGRESS_LOG.md` | **改**。当日条目追加一行指向本行动。 |
| `docs/actions/2026-09-22-t05-b-scheduling-reply.md` | 本文件（新增）。 |

未改动：任何 `.py`、`HTTP_API.md`（对 B 的契约建议由其自行决定是否落笔）、B 的模块文档、任务单正文。

## 4. 自验证方式

| 检查 | 手段 | 期望 |
|---|---|---|
| 事实有据 | 第 1 节每条均有文件路径或提交号 | 无"据称"式结论 |
| 不越权 | `git diff` 复核：改动只在 Comments 与本行动文档 | 无代码/契约改动 |
| 与最新状态一致 | 与任务单当日两条 Comments（T1 复测、T2 未测得）逐条对照 | 无冲突 |

## 5. 自验证情况

**已执行**：第 1 节六项核实全部来自本轮 `grep`/读码与当日记录，已抄录文件路径与行号；`git diff --stat` 复核确认改动仅落在 Comments、进度日志与本文件（见提交说明）。

**未执行**：未运行 `ruff`/`mypy`/`pytest`——本行动无代码改动。**未推送**：按项目约定推送需单独确认。

**遗留（与本行动有关但不属其范围）**：合并 `origin/main` 的加固改造（需让 `server/` 适配新接缝并重测全套）与 T2 侧车 127 的诊断，均已在进度日志"待办"中登记。
