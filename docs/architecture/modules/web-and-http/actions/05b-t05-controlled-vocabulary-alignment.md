# 行动：任务 05 受控词汇的契约对齐（E 请求，B 侧只改契约）

> 状态：**已完成**（2026-09-21）。本行动只改 `docs/interfaces/HTTP_API.md` 与 B 的模块文档，**未改任何代码**。请求方是 E（任务 05 的提供方访问链负责人）。

## 1. 情况说明

**来源**：E 已把任务 05 的提供方访问链合入 `main`（PR #24/#25；本地 `1888aa2` → `acbabbf` 共 22 个提交），请求 B 对齐两处契约：

1. `HTTP_API.md` §10.2 把 5 个受控失败码列入枚举（E 称"当前是候选"）：`PROVIDER_CREDENTIAL_UNAVAILABLE`、`PROVIDER_ACCESS_DENIED`、`PROVIDER_REQUEST_REJECTED`、`PROVIDER_BUDGET_EXHAUSTED`，兜底 `PROVIDER_ACCESS_FAILED`。
2. §195 响应示例与 §297/§315 说明补上受控提供方值 `internal_test_fake`，并确认该非秘密元数据在列表/详情公开是否可接受。

**先核实再动笔**（本轮全部结论都来自代码与 git，不采信转述）：

| 待核实项 | 结论 | 证据 |
|---|---|---|
| 五个受控码是否存在、映射是否如述 | ✅ 存在且逐字一致：四类受控码 + `GENERIC_FAILURE = ("PROVIDER_ACCESS_FAILED", "模型访问未完成。")`；未映射的内部码经 `controlled_failure()` 落兜底 | `provider_access/failures.py:91-110` |
| "内部码绝不回显"是否有测试门禁 | ✅ 有词汇表门禁，源码出现新内部码而映射未决定即失败 | `tests/providers/policy/test_controlled_failures.py` |
| "候选"的出处 | ✅ 指该模块 docstring："The codes below are candidates until the HTTP contract lists them." 本次对齐后该句才成立 | `failures.py:14-16` |
| 代理链是否已生效 | ❌ **尚未接线**：`provider_access` 包外**无任何调用方**（全仓仅包内互相 import） | `grep -rn "provider_access" src/` |
| 受控身份是否如 E 转述 | ⚠️ **部分不符**：`model_provider` 公开，但 `authentication_type=provider_run_token` **不在 HTTP 响应里** | `catalog_schemas.py:66-83`；`HTTP_API.md:650` 本就规定"不返回 authentication/credential profile" |
| E 报告的自身缺陷是否已修 | ✅ 已修：`_controlled(...)` 输出 `agent_type`/`model_provider`，超出受控集合抛 `UNCONTROLLED_*`，不再回退默认值（原先的假报告路径消失） | `catalog_schemas.py:85-108` |
| Job 级是否另有失败码 | ✅ 有：`BATCH_PARTIAL_FAILURE` / `BATCH_FAILED`，来源与提供方访问失败不同 | `domain/jobs/policy.py:68`、`execution/finalization.py:69` |

**已确认的决定**：

- **沿用 E 的命名与粒度**：五码，额度与期限合并进 `PROVIDER_BUDGET_EXHAUSTED`，不拆分。理由：与已合入的库级 CHECK、`DATA_MODEL.md`、E 的映射表与门禁完全一致；拆分会同时改代码与用例，而对所有者没有可操作差别。
- **公开 `internal_test_fake` 可接受**，并写入契约说明理由：它让受控预设不可能被误当成真实供应商配置，且本身不含主机、路径、令牌与拓扑信息；真正敏感的固定上游（保留域 `.invalid`）、凭据 profile 与 `authentication_type` 都不在响应中。

**明确不做**：不改 `.py`；不改 E 的映射表与用例；不改 `DATA_MODEL.md`（D 的文档，E 已同步）；不发布任务 05 的其余部分。

## 2. 实施措施

1. 核实现状：拉取 `upstream/main`（快进 22 个提交），确认这批提交**未触碰** `HTTP_API.md`、B 的模块文档与 `apps/web`。
2. 读 `failures.py`、`catalog_schemas.py`、`catalog_presets.py`、`domain/jobs/policy.py`，取得逐字依据。
3. 改 `HTTP_API.md` 四处：§4.2 受控集合段、§6 目录段、§10.2 五码表与规则、§15 变更记录。
4. 同步 B 的模块文档（进展、架构状态行）与行动记录，并补一条新待办。

**完成标准**：文档里每一句都能指回代码或 git；实现状态（已接线/未接线）如实标注，不含"已生效"的夸大。

## 3. 实际改动的文件树

| 路径 | 改动与职责 |
|---|---|
| `docs/interfaces/HTTP_API.md` | 契约唯一事实源。§4.2 新增"`agent_type`/`model_provider` 是受控集合、如实呈现、超出集合失败关闭、`authentication_type` 不返回、公开 `internal_test_fake` 是有意的"；§6 补受控预设 `internal-test-provider-proxy` 与 `internal_test_fake` 的出现条件；§10.2 新增五码映射表、归入的内部错误族、四条规则与**实现状态注记**；§15 新增变更记录 |
| `docs/architecture/modules/web-and-http/progress.md` | 新增"任务 05 的受控词汇对齐"节（含与 E 转述的两处差异）；新增 B 侧待办（浏览器夹具控制端点） |
| `docs/architecture/modules/web-and-http/ARCHITECTURE.md` | 状态行补上本次契约对齐；"待完成"里明确失败关闭验证需先加夹具控制端点 |
| `docs/architecture/modules/web-and-http/actions/05b-t05-controlled-vocabulary-alignment.md` | 本文件（新增） |

## 4. 自验证方式

- 逐条把文档新句与代码对照：五个码与短句、内部错误族、`CONFIGURATION_ONLY` 不入表、Job 级码另有来源、`Literal` 受控集合、`_controlled` 失败关闭。
- 相对链接脚本校验：`python runtime/tests/check-links.py <改动的 md>`。
- `git diff` 人工复核：确认改动只落在上表四个文件内，且**没有**触碰 `.py`。

## 5. 自验证情况

- 逐条对照**已执行**：上表"先核实再动笔"的七项全部来自实际 grep/读码，未采信转述；两处与 E 的转述不符的地方已按代码修正（`authentication_type` 不在响应中；"候选"指代码 docstring 而非文档正文）。
- 相对链接校验**已执行**：见下条外部证据（同一批次的链接检查）。
- `git diff --stat` **已执行**：确认改动文件集合与上表一致。
- **未执行**：未运行 `ruff`/`mypy`（本轮无代码改动）；未运行后端或浏览器测试（契约文档改动不影响可执行行为）。

## 6. 未验证项与风险

| 项 | 说明 |
|---|---|
| 代理链未接入运行主链路 | 五码目前是**已冻结的契约词汇**，不是已生效行为；文档已就地标注，避免被读成"已实现" |
| 文档与实现的字段级对账 | 仍只做过人工对照；OpenAPI 字段级 schema 程序化比对依旧未做（与既往记录一致） |
| "未知错误码失败关闭"的呈现验证 | 待代理链落地，且需先给浏览器夹具加"强制下一次响应出错"的控制端点 |
| 受控集合以外记录的 HTTP 表现 | **发现的新问题，交 E 决定**：`_controlled` 抛裸 `ValueError`，而 `app.py:76-88` 只注册了 `AuthenticationRequired`/`CatalogError`/`JobError`/`RequestValidationError`/`IdentityUnavailable`/`HTTPException`（及成员资格错误），**没有 `ValueError` 处理器**，因此当前表现为 500、不带受控错误码。数据层"拒绝而不误报"是对的；是否要包装成受控错误（如沿用 503 `DEPENDENCY_UNAVAILABLE`）属 E 的实现选择，B 的契约文字**未承诺任何状态码** |
