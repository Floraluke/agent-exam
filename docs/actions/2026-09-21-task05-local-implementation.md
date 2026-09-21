# 任务 05 本机实施开工（S1–S9 + T1）

## 状态与情况

- 状态：进行中（本机部分）。
- 来源请求：用户对[实施方案](../docs/LLY/01-plan/STAGE1_IMPLEMENTATION_PLAN.md)第 6 节三项授权请求回复"同意"，并说明本机 Docker 已启动、可用；要求"把本机可做的做完，再搬去负责人那边继续"。
- 授权依据（如实记录）：本次授权由用户在会话中明确给出，覆盖 ① 任务 05 实施开工、② T1/T2 拆分、③ T1 在本机执行。**注意**：负责人 2026-09-21 的书面回执原写"未授予实施开工许可"，用户本次的同意是对该点的更新；建议在负责人补一句书面确认后，才把任务单第 2 项验收的机器归属同步为"T1 本机 / T2 负责人机器"。
- 已完成的实测（本轮）：
  - **前置核对第 1 项已验证通过**：`docker network create` 成功创建带 `agentexam.task=05` 标签的自定义网络，`docker network ls` 可见；随后按同一标签精确删除，网络/容器/卷残留复核均为 0。Docker Server 29.6.2、Driver overlayfs、CgroupVersion 2。原"虚拟网络风险"未出现，T1 在本机可行。
  - 权威 TOML 字段名有据：`model_providers` / `model_provider` / `base_url` / `env_key` / `wire_api` / `request_max_retries` / `stream_max_retries` 见研究第 1 节；仓库内**无** `config.toml` 样例（探针样例在被 Git 忽略的 `runtime/`，只在负责人机器）。
- 已确认决定：本次按实施方案顺序实施 S2–S9 与 T1；每片遵循"一个失败用例 → 最小实现 → 通过 → 回归"；新增文件遵守单文件 ≤200 行与每层 ≤8 文件指标；不新增数据库表、不新增业务 Module 或公共 Interface。
- 明确排除：不改既有公开 Interface 形状；不读真实 Key（一律假值）；不使用真实供应商；不改共享 Docker/WSL/全局网络；T2（固定 Harbor 集成层）不在本机做。

## 实施措施

1. 按实施方案的文件树建立 `adapters/execution/provider_access/` 与 `tests/providers/`，逐片实现并补测试。
2. 逐片运行 `ruff check`、`ruff format --check`、`mypy` 与定向 `pytest`，记录实际结果；每片完成后再进下一片。
3. T1 用一次性探针（位于被 Git 忽略的 `runtime/prototype/`，不进产品树）验证不依赖 Harbor 的拓扑断言；探针资源只按 `agentexam.task=05` 标签创建与删除，复核残留为 0，禁止全局 prune。
4. 持续更新本行动文档的文件树、偏差与验证结果；文档层变化同步 `docs/LLY/`。
5. 阶段完成后提交推送，并在任务单 Comments 记录本机部分的完成情况与移交给负责人侧的内容。

完成标准：S2–S9 有实现与测试且检查全绿（失败与跳过如实记录）；T1 的每条断言有实际命令与实际输出；不改公开 Interface、不新增表；T1 通过明确标注"不等于任务 05 拓扑验收通过"。

## 受影响文件树

```text
apps/backend/src/eval_platform/adapters/execution/provider_access/
├─ __init__.py          # 内部导出；不向应用暴露新业务端口
├─ secrets.py           # 私有文件校验：普通文件、非链接路径、属主与最小权限、拒绝同步目录（S3）
├─ provider_config.py   # 位于 codex/ 下：TOML 渲染 + 摘要 + 两个重试参数置 0（S2）
├─ request_policy.py    # 路径/字段/模型/工具白名单与出站前拒绝（S4）
├─ budget.py            # A 保守上界账本、原子预留、未知 usage 失败关闭（S5）
├─ binding.py           # Run 绑定与有限 provider 选择（S6）
├─ service.py           # 代理入口、鉴权、流生命周期（S6）
└─ transport.py         # 固定上游、不跟随重定向、不重试、无正文日志（S7）
apps/backend/tests/providers/
├─ policy/              # 策略层测试（本机）
├─ contract/            # 契约层测试（本机；容器需求待确认）
└─ lifecycle/           # 生命周期层替身测试（本机）
runtime/prototype/t05-topology-<日期>-<序号>/   # T1 探针与证据（被 Git 忽略，不进产品树）
```

## 自验证方式

1. 每片：`ruff check`、`ruff format --check`、`mypy`、定向 `pytest` 全部记录实际输出；失败与跳过如实记录。
2. 拒绝类断言：以"出站计数为 0"或"抛出受控错误码"为证，不凭日志文本推断。
3. 秘密类断言：只用假值，扫描 argv/环境变量/渲染结果/日志中假值命中为 0。
4. 文件指标：新增源文件逐个核对 ≤200 行，每层目录文件数 ≤8。
5. 不做假通过：未运行的检查、跳过的用例、以及"本机通过不等于拓扑验收通过"均如实标注。

## 自验证情况

### 已完成的片

**前置第 1 项（Docker 创建能力）——已验证通过**

- 命令：`docker network create agentexam-t05-capability-probe --label agentexam.task=05 --label agentexam.scope=t05-capability-20260921` → 返回网络 ID，`docker network ls --filter label=agentexam.task=05` 可见（driver `bridge`）。
- 环境：Docker Server 29.6.2、`Driver=overlayfs`、`OS=Docker Desktop`、`CgroupVersion=2`。
- 清理：`docker network rm` 后按同一标签复核，网络/容器/卷残留**均为 0**；未执行全局 prune。
- 结论：阶段 0 记录的"虚拟网络风险"在本机 Docker 上**未出现**，T1 在本机可行。

**S3 `provider_access/secrets.py`——已实现并验证**

- 文件：`secrets.py`（165 行，≤200）、包 `__init__.py`；测试 `tests/providers/policy/test_private_secrets.py`。
- 定向测试：`pytest tests/providers -q` → **18 passed, 1 skipped**（跳过项为"POSIX owner/permission bits only"，本机为 Windows，属设计如此，不计为通过）。
- 静态检查：`ruff check`（全量）→ `All checks passed!`；`ruff format --check`（全量）→ `305 files already formatted`；`mypy` 对新增包 → `no issues found in 2 source files`。
- 全量回归：`435 passed, 102 skipped, 2 failed`；相对上次基线 `417 passed, 101 skipped, 2 failed`，通过数 **+18**（即本片新增用例），失败项**完全相同**（仍为缺 `framework/harbor` 的 ISSUE-04），无新增失败。
- **测试发现并修复了两处真实缺陷**（非测试写错）：
  1. **结构校验被短路**：缺少 `profiles` 键时，原实现因 `not isinstance(profiles, dict) or profile_id not in profiles` 合并判断而误报 `PRIVATE_PROFILE_NOT_FOUND`，掩盖了结构非法。已拆为两个独立判断，缺 `profiles` 报 `PRIVATE_FILE_STRUCTURE_INVALID`。
  2. **上游地址校验过宽**：原实现只用正则校验 `https://` 前缀，**任意主机都能通过**，与设计冻结"上游基址只能是登记值、不接受任意 URL"不符，也不满足研究第 2 节"Kim 中国区 Key 必须匹配 `api.moonshot.cn`、不能拿国际端点试错"的要求。已改为按 `REGISTERED_UPSTREAMS`（`deepseek` → `https://api.deepseek.com`、`kimi` → `https://api.moonshot.cn/v1`）校验 **provider 与上游成对**；该常量标注为候选，S8 与 `delivery/catalog_presets.py` 的登记预置同步。

### 本片的关键设计取舍

- **平台相关的属主/ACL 判定做成注入参数**：`load_profile(..., verify_access=...)` **没有默认值**，因此调用方无法在不声明"私有文件如何被证明为仅 owner 可读"的情况下取得 profile——由构造保证失败关闭。POSIX 提供 `owner_only_verifier`；在无法证明属主的平台上它**主动抛 `PRIVATE_ACCESS_UNVERIFIABLE`**，而不是放行。
- 这直接对应负责人核对时指出的第 4 条实现差距（"现有认证文件校验不足以证明 Windows ACL/属主"）：本片只实现**平台中立**的检查（普通文件、路径无链接段、大小上限、同步目录拒绝、结构校验），**Windows ACL 的证明方式仍是未决项**，需在集成层确认，不得据本片声称 Windows 上已完成属主验证。
- 错误只抛固定错误码，不回显路径与密钥；测试用断言钉住"错误信息不含路径、不含假 Key、且形如错误码"。
- `PrivateProfile.secret` 设 `repr=False, compare=False`，另有断言钉住假 Key 不出现在 `repr` / `str`。

**S4 `provider_access/request_policy.py`——已实现并验证**

- 文件：`request_policy.py`（约 140 行，≤200）；测试 `tests/providers/policy/test_request_policy.py`。
- 定向测试：`pytest tests/providers -q` → **28 passed, 1 skipped**（含 S3 的 18 项）。
- 静态检查：`ruff check`（全量）→ `All checks passed!`；`ruff format --check`（全量）→ `307 files already formatted`；`mypy` 对新增包 → `no issues found in 3 source files`。
- 全量回归：`445 passed, 102 skipped, 2 failed`；相对上一片 `435/102/2` 通过数 **+10**（本片新增用例），失败项完全相同，无新增失败。
- **测试又发现一处真实缺陷**：`stream` 键缺失时原实现 `body["stream"]` 抛**裸 `KeyError`** 而非受控错误码——在安全边界上，未受控异常可能被上层误当非拒绝路径处理。已改为 `.get()`，**缺键与值不符统一收敛为 `REQUEST_STREAM_REQUIRED`**；同时修正了我自己写错的一处测试期望（原断言缺 `stream` 会报 `REQUIRED_FIELD_MISSING`）。
- 本片覆盖的拒绝（全部发生在**出站前**、抛固定错误码）：非 `POST`；路径非 `/responses`（含 `/v1/responses`、带查询串、**绝对 URL**、`/`）；正文非对象（含非字符串键）；未知字段（含 `base_url`、`web_search`）；必填空缺；模型与绑定不符；非流式；输入为空或类型非法；`max_output_tokens` 超上限或非法值；未登记工具类型（含 `web_search`、`computer_use_preview`）。
- 另实现 `strip_client_auth`：大小写不敏感地剥离 `Authorization`/`Proxy-Authorization`/`X-Api-Key`/`Api-Key`，由可信侧添加真实凭据；测试断言剥离结果中不含假值。
- 字段集合（`model`/`stream`/`input`/`tools`/`max_output_tokens`/`instructions`/`reasoning`）与研究第 1、2、4 节一致，但**属候选**：仓库内无 `config.toml` 样例，须在契约层用固定 CLI 复核实际请求字段后再定稿。

**S5 `provider_access/budget.py`——已实现并验证**

- 文件：`budget.py`（186 行，≤200）；测试 `tests/providers/policy/test_budget_ledger.py`。
- 定向测试：`pytest tests/providers -q` → **45 passed, 1 skipped**（含 S3/S4 的 28 项）。
- 静态检查：`ruff check`（全量）→ `All checks passed!`；`ruff format --check` → `309 files already formatted`；`mypy` 对新增包 → `no issues found in 4 source files`。
- 全量回归：`462 passed, 102 skipped, 2 failed`；相对上一片 `445/102/2` 通过数 **+17**（本片新增用例），失败项完全相同，无新增失败。
- **复用现有接口，未自造形状**：usage 直接采用既有的 `domain/result.py::UsageSummary`（`n_input_tokens`/`n_cache_tokens`/`n_output_tokens`，均为 `int | None`）。该类型的 `None` 语义恰好就是"未知"，与"未知不得当 0"的要求天然一致。
- **A 保守上界的依据写进代码**：字节级 tokenizer 的最坏情况是**每字节一个 token**，故取请求正文 UTF-8 字节数为上界，再叠加固定框架开销 `FRAMING_ALLOWANCE_TOKENS = 256`。测试用非 ASCII 文本断言宽字符上界**不低于其 UTF-8 长度**且严格大于等长 ASCII。**未经真实 tokenizer 验证**，故只承诺上界、不承诺精确账单（与负责人第 7 项决定一致）。
- **未知 usage 的处理**：`settle` 遇到 usage 为 `None`、或输入/输出任一为 `None` 时，**按整笔预留全额计费**（不退款为零）、`measured=False`，并**关闭该 Run**（`closed_reason="usage-unknown"`），此后 `reserve` 抛 `BUDGET_RUN_CLOSED`；四种未知形态各有参数化用例。
- **重启不重置**：`consumed_input_tokens` / `consumed_output_tokens` 是**必填构造参数、无默认值**，调用方无法在代理重启后无意间从零开始；携带值超出上限直接 `BUDGET_CONSUMED_INVALID` 失败关闭。测试断言缺参会报 `TypeError`。
- **预留原子**：全部状态变更在同一把 `threading.Lock` 下。并发用例用 8 线程同时抢 `max_output_tokens=8000`（上限 32000），断言**恰好 4 个成功、4 个被拒**且剩余额度为 0。
- 其它已覆盖：输入与输出上限分别生效、截止时间按账本起点计时（注入时钟）、非正输出请求拒绝、同一预留只能结算一次（重复结算抛 `BUDGET_RESERVATION_UNKNOWN`）、正文不可序列化、上限参数非法。
- 本片测试暴露的一处**是我自己写错的测试**（注入时钟序列多排了一个值），不是实现缺陷；与前两片不同，如实记录。

**S6 `provider_access/binding.py`——已实现并验证**

- 文件：`binding.py`（134 行，≤200）；`provider_access/` 现有 5 个源文件（上限 8）；测试 `tests/providers/policy/test_run_binding.py`。
- 定向测试：`pytest tests/providers -q` → **56 passed, 1 skipped**（含 S3–S5 的 45 项）。
- 静态检查：`ruff check`（全量）→ `All checks passed!`；`ruff format --check` → `311 files already formatted`；`mypy` 新增包 → `no issues found in 5 source files`。
- 全量回归：`473 passed, 102 skipped, 2 failed`；相对上一片 `462/102/2` 通过数 **+11**（本片新增用例），失败项完全相同，无新增失败。
- **令牌刻意不是一次性码**：一个 Run 含多轮模型请求，故同一令牌可反复 `resolve`；测试断言同一令牌连续 5 次解析均成功。设计冻结第 3.5 节写明"多轮请求共用，不是一次性码"，本片据此实现。
- **三类必须拒绝的情况各有用例**：跨 Run（令牌属于 run-1、以 run-2 呈现 → `PROVIDER_TOKEN_CROSS_RUN`）；过期（注入时钟越过 `expires_at` → `PROVIDER_TOKEN_EXPIRED`，且**同时丢弃该绑定**，再解析报 `UNKNOWN`、活动 Run 列表变空）；撤销（按令牌与按 Run 两种，重复撤销返回 `False`）。
- **令牌不外泄**：`RunBinding.token` 设 `repr=False, compare=False`，测试断言其不出现在 `repr`/`str`；`active_run_ids()` 只返回 Run 身份、绝不列令牌。
- **一个 Run 只签发一个令牌**：重复签发报 `PROVIDER_BINDING_ALREADY_ISSUED`；令牌工厂若返回重复值则报 `PROVIDER_TOKEN_NOT_UNIQUE` 而不是覆盖既有绑定（防止静默顶掉别人的令牌）。
- **有限 provider 选择**：签发时要求 `provider` 属于 `secrets.REGISTERED_UPSTREAMS`（`deepseek`/`kimi`），未登记一律拒绝；复用同一常量而非另立一份注册表。
- 令牌用 `secrets.token_urlsafe(32)` 生成（密码学随机），测试可注入工厂以便断言唯一性。

**S7 `provider_access/transport.py`——已实现并验证**

- 文件：`transport.py`（109 行，≤200）；`provider_access/` 现有 6 个源文件（上限 8）；测试 `tests/providers/policy/test_outbound_transport.py`。
- 定向测试：`pytest tests/providers -q` → **67 passed, 1 skipped**（含 S3–S6 的 56 项）。
- 静态检查：`ruff check`（全量）→ `All checks passed!`；`ruff format --check` → `313 files already formatted`；`mypy` 新增包 → `no issues found in 6 source files`。
- 全量回归：`484 passed, 102 skipped, 2 failed`；相对上一片 `473/102/2` 通过数 **+11**（本片新增用例），失败项完全相同，无新增失败。
- **目标地址不由请求决定**：只用 `REGISTERED_UPSTREAMS[provider]` 拼 `PATH`；测试用客户端伪造 `Host`、`X-Forwarded-Host`、`Location` 指向 `evil.example.com`，断言实际 URL 仍为注册上游且不含该主机名。
- **"不重试、不跟随重定向"是结构上不可配错的**：`OutboundRequest.__post_init__` 对 `max_attempts != 1` 与 `follow_redirects=True` 直接抛错，因此不存在"忘了配"的路径；另拒绝非 `https://` 上游与空凭据。
- **测试抓到一处真实泄漏（本片最重要的发现）**：原实现把 `Authorization: Bearer <secret>` 直接并进 `headers`，于是 **`repr(request)` 带出秘密**；而且即使给 `payload` 加 `repr=False`，**`repr(request.headers)` 同样会漏**——只要有人打一行日志就泄漏。已改为**认证值与客户端头分开存放**（`authorization` 字段，`repr=False`），并只经 `send_headers()` 合并；`safe_summary()` 只报方法、URL、**头名**与正文长度，不报任何值。测试同时断言 `repr(request)`、`str(request)`、`repr(request.headers)` 三者都不含假值。
- **无正文日志可证**：`safe_summary()` 的断言包含"不含假值、不含 `Bearer`、不含正文内容"。
- 出站正文按 `sort_keys` + 紧凑分隔符序列化，因此同一语义的正文字节确定可复现（测试断言键序不同的两种写法产出相同字节）。

### 未完成与遗留

- **S2、`service.py`、S8–S9 与 T1 尚未实施**；已完成前置验证与 S3–S7。**代理中所有能以纯逻辑表达的安全不变量均已落地并有测试**：私有文件可信、请求出站前拒绝、额度不超支、未知不记零、令牌不跨 Run、出站目标不由请求决定、重试与重定向结构上不可配。剩余部分性质不同——`service.py` 与 `network.py` 是**接线**，其形态取决于 T1 拓扑结论，故按用户确认的顺序把 T1 提前到 `service.py` 之前。
- **S2 暂缓**：Codex TOML 字段名研究第 1 节有据，但仓库内无 `config.toml` 样例（探针样例在被 Git 忽略的 `runtime/`，只在负责人机器）。定稿前须用固定 CLI 在契约层复核一次字段名，不凭文档当已确认。
- **T1 未执行**：本机 Docker 能力已验证，但拓扑探针与 7 条断言仍未做。
- 授权依据：用户会话内明确"同意"，并追加"其它需要开工授权的也同意"；本行动按其**只覆盖 E 本机实施与 T1 执行**理解执行——**不含真实模型/供应商调用**（项目规定须单独授权、历史 ChatGPT 许可不覆盖 DeepSeek/Kimi），**也不含负责人机器的 T2 操作**。负责人书面回执原写"未授予实施开工许可"，建议补一句书面确认后再同步任务单第 2 项验收的机器归属。
