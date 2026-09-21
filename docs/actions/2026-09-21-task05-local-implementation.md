# 任务 05 本机实施开工（S1–S9 + T1）

## 状态与情况

- 状态：进行中（本机部分）。
- 来源请求：用户对[实施方案](../LLY/01-plan/STAGE1_IMPLEMENTATION_PLAN.md)第 6 节三项授权请求回复"同意"，并说明本机 Docker 已启动、可用；要求"把本机可做的做完，再搬去负责人那边继续"。随后用户对"修 T1 探针并重跑七条断言"回复"要"，构成本切片（探针修复与重跑）的直接授权。
- 授权依据（如实记录）：本次授权由用户在会话中明确给出，覆盖 ① 任务 05 实施开工、② T1/T2 拆分、③ T1 在本机执行。**注意**：负责人 2026-09-21 的书面回执原写"未授予实施开工许可"，用户本次的同意是对该点的更新；建议在负责人补一句书面确认后，才把任务单第 2 项验收的机器归属同步为"T1 本机 / T2 负责人机器"。
- 已完成的实测（本轮 + 上一轮）：
  - **前置核对第 1 项已验证通过**：`docker network create` 成功创建带 `agentexam.task=05` 标签的自定义网络，`docker network ls` 可见；随后按同一标签精确删除，网络/容器/卷残留复核均为 0。Docker Server 29.6.2、Driver overlayfs、CgroupVersion 2。原"虚拟网络风险"未出现，T1 在本机可行。
  - **T1 已在本机证成**（探针 run 02，见下"自验证情况"）：七条断言全部测到并通过，含反向对照自检。
  - 权威 TOML 字段名有据：`model_providers` / `model_provider` / `base_url` / `env_key` / `wire_api` / `request_max_retries` / `stream_max_retries` 见研究第 1 节；仓库内**无** `config.toml` 样例（探针样例在被 Git 忽略的 `runtime/`，只在负责人机器）。
- 已确认决定：本次按实施方案顺序实施 S2–S9 与 T1；每片遵循"一个失败用例 → 最小实现 → 通过 → 回归"；新增文件遵守单文件 ≤200 行与每层 ≤8 文件指标；不新增数据库表、不新增业务 Module 或公共 Interface。
- 明确排除：不改既有公开 Interface 形状；不读真实 Key（一律假值）；不使用真实供应商；不改共享 Docker/WSL/全局网络；T2（固定 Harbor 集成层）不在本机做。

## 实施措施

1. 按实施方案的文件树建立 `adapters/execution/provider_access/` 与 `tests/providers/`，逐片实现并补测试。
2. 逐片运行 `ruff check`、`ruff format --check`、`mypy` 与定向 `pytest`，记录实际结果；每片完成后再进下一片。
3. T1 用探针（开发时在被忽略的 `runtime/prototype/`，证成后按用户确认纳入 `apps/backend/tests/providers/runtime/` 供负责人复用）验证不依赖 Harbor 的拓扑断言；探针资源只按 `agentexam.task=05` 标签创建与删除，复核残留为 0，禁止全局 prune。
4. 持续更新本行动文档的文件树、偏差与验证结果；文档层变化同步 `docs/LLY/`。
5. 阶段完成后提交推送，并在任务单 Comments 记录本机部分的完成情况与移交给负责人侧的内容。

完成标准：S2–S9 有实现与测试且检查全绿（失败与跳过如实记录）；T1 的每条断言有实际命令与实际输出；不改公开 Interface、不新增表；T1 通过明确标注"不等于任务 05 拓扑验收通过"。

## 受影响文件树

```text
apps/backend/src/eval_platform/adapters/execution/provider_access/   # 已建；6 个源文件（上限 8）
├─ __init__.py          # 内部导出；不向应用暴露新业务端口（已完成）
├─ secrets.py           # 私有文件校验：普通文件、非链接路径、属主与最小权限、拒绝同步目录（S3，已完成）
├─ request_policy.py    # 路径/字段/模型/工具白名单与出站前拒绝（S4，已完成）
├─ budget.py            # A 保守上界账本、原子预留、未知 usage 失败关闭（S5，已完成）
├─ binding.py           # Run 绑定与有限 provider 选择（S6，已完成）
├─ transport.py         # 固定上游、不跟随重定向、不重试、无正文日志（S7，已完成）
├─ provider_config.py   # 待建（S2）：位于 codex/ 下：TOML 渲染 + 摘要 + 两个重试参数置 0
├─ service.py           # 待建（S6）：代理入口、鉴权、流生命周期——接线形态取决于 T1/T2 结论
└─ network.py           # 待建（S10）：私有拓扑组合与正反可达性预检
apps/backend/tests/providers/
├─ policy/              # 已建 7 文件：test_private_secrets / test_request_policy / test_budget_ledger /
│                       #   test_run_binding / test_outbound_transport（67 passed, 1 skipped）
├─ contract/            # 待建：契约层（本机；固定 CLI 字段名复核在负责人机器）
└─ lifecycle/           # 待建：生命周期层替身测试（本机）
apps/backend/tests/providers/runtime/       # 已纳入仓库：拓扑探针，供负责人机器复用（5 文件，均 ≤200 行）
├─ topology-probe.sh               # 开机、建网、逐条断言、清理、退出码（189 行）
├─ topology-lib.sh                 # 探针原语与健康门禁：工具链不健康即中止且不输出断言（90 行）
├─ topology-verdicts.sh            # 判定标准：每条断言期望什么（49 行，与探针分开评审）
├─ fake-provider.json              # 假值提供方文件（哨兵值，非真实 Key）；仅挂进代理
└─ README.md                       # 怎么跑、断言清单、已知坑（含 MSYS 假阴性陷阱）
runtime/prototype/t05-topology-20260921-01/   # T1 首次运行：未证成（工具链故障），历史证据保留
runtime/prototype/t05-topology-20260921-02/   # T1 证成时的开发副本（被 Git 忽略），历史证据保留
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

**T1 本机拓扑预证——已证成（探针 run 02；28/28 判定通过，连续两次一致）**

- 探针位置：**已纳入仓库** `apps/backend/tests/providers/runtime/`（`topology-probe.sh` + `topology-lib.sh` + `topology-verdicts.sh` + `fake-provider.json` + `README.md`），供负责人机器复用；运行证据默认写到被忽略的 `<仓库根>/.tmp/t05-topology/`。原始开发副本保留在被忽略的 `runtime/prototype/t05-topology-20260921-02/`（同一脚本逻辑，作为首次运行的历史证据）。
- 结果：`status=verified`、退出码 0。七条断言全部测到并由脚本判定，连同身份记录与清理复核共 **28 项判定**，全部 PASS。
- **run 01 失败的根因已定位并修复**：监听端容器启动即退出（`Exited (1)`）的原因是 `setpriv: setresuid failed: Operation not permitted`（退出码 127）——`--cap-drop ALL` 去掉了 `CAP_SETUID`/`CAP_SETGID`，而镜像入口脚本需要它们把权限降给 redis 用户。**修法是让监听端以镜像内的 redis 用户运行**（入口脚本因此跳过降权分支），`--cap-drop ALL` 与 `no-new-privileges` 全部保留。这也说明 run 01 的 CLOSED 确为工具链假象：容器根本没起来。
- **本轮另修掉 4 处探针工具链缺陷，每一处都会产出假阴性或假证据**：
  1. 监听端镜像（Alpine）**没有 bash**，所有 `docker exec … bash -c` 静默失败——从监听端发起的检查（如断言 4）会一律返回 CLOSED。改用镜像自带的 `redis-cli` 做应用层连通性检查。
  2. 转发替身的脚本**漏了端口号**（`${ENTRY_PORT}` 写在容器侧才展开的位置，容器内无此变量），生成 `exec nc <上游主机> `（无端口），每次转发必然被重置。这是"转发失败"的唯一原因，与拓扑无关。
  3. 一次性 `nc -e` 监听在重生窗口内会重置新连接；改为常驻监听 `nc -lk -e`。
  4. **redis 会改写自己的进程名**（`setproctitle`），拿它 argv 里的标记做 PID 隔离断言恒为 0；改用中继脚本路径作标记，并保留"在代理侧应命中"的正对照（否则 0 无法与坏扫描区分）。
  另有 2 处匹配错误：`grep` 模式以 `-` 开头被当成选项；本版 Docker 的发布端口输出 `{}` 而非 `null`。
- **健康门禁已加入**：任一容器非 running、任一地址为空、任一监听端不应答时，探针以 `harness-failed` 中止并 dump 退出码与日志，**不输出任何断言**。run 01 的教训（坏工具链输出 CLOSED，假阴性最危险）因此被结构性阻止；本轮它实际生效过一次（发现"监听端无 bash"）。
- **反向对照自检已加入并实测**：`NEGATIVE_CONTROL=1` 故意把做题侧接到出网网络，断言 2、3 如预期失败（`status=negative-control-ok`），证明探针**能检出泄漏**——负例断言不是空断言。
- **第 5 条允许的最小挂载已按断言要求记录范围与理由**：仅代理容器有一个**只读**绑定挂载 `fake-provider.json → /run/agentexam-private/provider.json`，理由是设计上代理需读取 owner 私有提供方文件；**做题侧挂载为空 `[]`**，无发布端口、无 Docker 套接字。
- 清理：每次运行后按 `agentexam.task=05` 标签复核，容器/网络/卷残留**均为 0**，未执行全局 prune。
- **边界（不得混淆）**：本次是 T1（纯 Docker/Compose 层）。它与 Harbor 无关，**T1 通过不等于任务 05 的拓扑验收通过**——最终仍须在固定 Harbor 上成立（T2）。转发实现是中继替身，HTTP 语义与"假 Key 请求形状"属 `service.py`，本探针不覆盖。

原始记录（仓库位置探针的 `.tmp/t05-topology/transcript.txt`；制表符分隔，依次为断言组 / 项目 / 值）：

```text
0	mode	normal (no deliberate leak)
0	net agentexam-t05-topology_internal (internal)	workload, proxy
0	net agentexam-t05-topology_egress (egress)	proxy 172.20.0.2, upstream 172.20.0.3
0	net agentexam-t05-topology_other (internal)	other-trial 172.21.0.2
1	workload -> proxy entry 172.19.0.3:6379	OPEN
1	  ping reply byte	+PONG
2	workload -> public 1.1.1.1:443	CLOSED
2	workload -> public 223.5.5.5:53	CLOSED
3	workload -> host gateway 172.19.0.1:80	CLOSED
3	workload -> metadata 169.254.169.254:80	CLOSED
3	workload -> other trial 172.21.0.2:6379	CLOSED
3	workload -> fake upstream 172.20.0.3:6379	CLOSED
4	proxy -> fake upstream 172.20.0.3:6379	PONG
5	workload mounts	[]
5	proxy mounts	[{"Type":"bind","Source":"/d/agent-exam/apps/backend/tests/providers/runtime/fake-provider.json","Destination":"/run/agentexam-private/provider.json","Mode":"ro","RW":false,"Propagation":"rprivate"}]
5	published ports (all four)	/agentexam-t05-topology-workload-1 {} /agentexam-t05-topology-proxy-1 {} /agentexam-t05-topology-fakeupstream-1 {} /agentexam-t05-topology-othertrial-1 {} 
5	docker.sock mount sources (proxy)	0
6	relay script in proxy	#!/bin/sh|exec nc agentexam-t05-topology-fakeupstream-1 6379|
6	proxy listening on :8080	1
6	relay inner connect (proxy -> upstream by name)	+PONG
6	workload -> proxy:8080 raw connect	CONNECTED
6	workload -> proxy:8080 -> upstream reply (1st)	+PONG
6	workload -> proxy:8080 -> upstream reply (2nd)	+PONG
6	upstream log: Accepted from proxy (before -> after)	3 -> 5
6	upstream log line for the forwarded request	1:M 21 Sep 2026 13:45:58.815 - Accepted 172.20.0.2:36659
6	upstream log: cmd=ping from proxy (before -> after)	2 -> 4
7	proxy private file visible in workload	ABSENT
7	workload mounts matching the private file	0
7	proxy process list	PID   COMMAND|    1 nc -lk -p 8080 -e /tmp/agentexam-proxy-marker-relay.sh|    7 redis-server *:6379|   49 ps -o pid,args|
7	processes with proxy marker seen from workload / from proxy (control)	0 / 1
7	sentinel hits in workload env / argv	0/0
8	image identity workload / listener	sha256:74d56e3931e0d5a1dd51f8c8a2466d21de84a271cd3b5a733b803aa91abf4421 sha256:858f009f9709ce576febc734aa78b8f6d624b82571f9ddb6bda4377c833b3499
8	container identity	/agentexam-t05-topology-workload-1 cf370f5b6de4c4cb6f4ce781adc37b6e615c9d079e1c0c58867132d904926fc3 /agentexam-t05-topology-proxy-1 fb3fc5299fff0600181be4fc6dc45065f5492efb5407bfbcd3a3f0ce065aa2d0 /agentexam-t05-topology-fakeupstream-1 530eaa431f25e8e0d98c1f4ca639ccadfd0c7d5ae31d2530efd2ab40c55db2f6 /agentexam-t05-topology-othertrial-1 6ec801f66e5deeec118ac69eac60733f3b1f4d0caa333a64728bf7b15e9ad088 
8	network identity	agentexam-t05-topology_internal d8adbc0b5a816ac3101aad94090066eb5a21e9c491dae6e9727a31eed8663fd8 internal=true agentexam-t05-topology_egress 15f725f3cb30252bdfffafcc2439c6b75b4ce4b9d972dec6435c96fa712fe8ce internal=false agentexam-t05-topology_other 1f5037cea292576ab85128bb535ff9e4cdff0a2cd21553cb048eeca316b2ce39 internal=true 
9	remaining containers with label	
9	remaining networks with label	
9	remaining volumes with label	
```

注：其中出现的宿主路径是本探针自带的**假值文件**（`apps/backend/tests/providers/runtime/fake-provider.json`，只含哨兵字符串），**不是**负责人按第 8 项决定选定的私有提供方文件路径——真实路径按该决定不入 Git。

**S8 首个片段：`agent_type` 筛选接线（已完成并验证）**

- 依据：[HTTP_API 第 315 行](../../docs/interfaces/HTTP_API.md) 要求"合法筛选无匹配返回空列表"，而路由收下该参数后从不传给注册表；`agent_type` 是**执行器类型**（`codex`/`aider`/`claude_code`/`custom`，见 [DATA_MODEL 第 271 行](../../docs/architecture/DATA_MODEL.md)），与 06/07 的 DeepSeek/Kimi 无关（那是 `model_provider`）。**该片段不需要任何产品决定**，三种 S8 放行范围下都要做。
- 改动文件：`delivery/http/routes/catalog.py`（把参数传下去）、`application/agent_registry.py`、`application/ports/repositories.py`、`adapters/persistence/catalog/agents.py`（SQL 条件）、`tests/catalog/memory.py`（替身同步）。
- 验证方式：定向 `pytest tests/catalog`；新增断言 ① 注册表把 `agent_type` 原样传给仓库；② 真实 PG 上按未被登记的合法类型查询返回空列表、按 `codex` 查询返回已登记行；③ HTTP 层 `?agent_type=codex` 行为不变（仍返回全部），非法类型仍 422。最后跑默认回归，失败项必须与基线一致。

**S8 首个片段：自验证情况**

- 改动：`delivery/http/routes/catalog.py`（把参数传下去）、`application/agent_registry.py`、`application/ports/repositories.py`、`adapters/persistence/catalog/agents.py`（SQL 增加 `agent_type=%s` 条件）、`tests/catalog/memory.py`（替身同步）；新增 2 个用例：`tests/catalog/test_http.py::test_agent_type_filter_is_applied_not_ignored`、`tests/catalog/test_postgres.py::test_agent_list_filters_by_type_on_the_real_database`。
- **用例有区分力（实测）**：临时把路由退回旧行为（传 `None`）后，新用例 **FAILED**；还原后通过。因此它不是恒真的空断言。
- 定向：`pytest tests/catalog`（开启 `AGENTEXAM_RUN_IDENTITY_POSTGRES=1`）→ **44 passed / 22 skipped**（跳过项为 MinIO 等未配置依赖，属设计如此）。
- 全量开 PG：**536 passed / 52 skipped / 2 failed**；默认（不开 PG）：**485 passed / 103 skipped / 2 failed**。相对基线 `484/102/2` 多出的正好是新增用例（1 通过 + 1 按开关跳过）。**失败项始终是同一批**：缺 `framework/harbor` 的 ISSUE-04。
- 静态：`ruff check` 通过、`ruff format --check` 313 文件、`mypy` 174 源文件无问题。
- 环境：本机 PostgreSQL 当时未运行（便携版不注册服务），已按 [本地环境文档](../LLY/02-environment/LOCAL_SETUP.md) 的既有命令启动，现为 `accepting connections`；本次未改动上述文档的运行状态段（仍有效）。
- 行为变化：`?agent_type=codex` 对现有调用方不变（仍返回 codex 条目），未知类型仍 422；新增的行为是**合法但无匹配的类型返回空页**，与 HTTP 契约第 315 行一致。
- **顺带发现一处同类隐患（未改）**：`delivery/http/catalog_schemas.py` 的 `AgentDetail.from_record` 把 `agent_type="codex"`、`model_provider="openai_chatgpt"` **写死**而不是从记录读取；今天因两者都是 `Literal` 而一致，但登记第二个提供方时会与记录不符。应与 S8 主体的"响应枚举扩宽"一并处理。

**S8 主体：受控 API 预设的身份与登记（已完成并验证）**

- 范围依据：用户确认方案 A（只放开到受控假提供方）；**身份机制由 E 定稿**（设计冻结第 3 行边界：机制 E 定，数值负责人定），已记入[设计冻结第 3.8 节](../LLY/01-plan/STAGE1_PROXY_DESIGN_FREEZE.md)。
- 身份：provider `internal_test_fake` + authentication `provider_run_token`，成对校验；唯一权威清单是 `domain/agent.py` 的 `CONTROLLED_IDENTITIES`。其"固定上游"登记为 `https://fake-upstream.t05.invalid`——**保留域 `.invalid` 在隔离网络之外永不解析**，故生产误配也只失败关闭。
- 改动文件：`domain/agent.py`（受控身份常量与集合）、`application/agent_registry.py`（按身份对校验，不再只认 Codex）、`delivery/http/catalog_schemas.py`（**按记录如实呈现** + 受控枚举 + 受控检查失败关闭）、`adapters/persistence/catalog/schema.sql`（两条约束放宽并命名）、`adapters/persistence/catalog/__init__.py`（新增 `upgrade_api_constraints`）、`adapters/execution/provider_access/secrets.py`（登记受控上游）、`delivery/catalog_presets.py`（新增 `INTERNAL_TEST_AGENT_PRESETS`，**生产 `AGENT_PRESETS` 不含假服务**）。
- 新增测试 `tests/catalog/agent_identity/test_registration.py`（5 个用例；该子目录沿用 `qualification/` 的分组做法，避免超出每层 8 文件指标）：受控预设能登记且**如实报告身份**、响应枚举与域常量**不可漂移**、生产预设不含假服务、未受控身份对在入仓前被拒、真实 PG 上受控身份可往返且**升级显式且可验证**。
- 自验证（本机实测）：默认回归 **489 passed / 104 skipped / 2 failed**、开启 PG **541 passed / 52 skipped / 2 failed**（相对上一片 `485/103/2` 增量正好是 5 个新用例：4 运行 1 按开关跳过）；`ruff check` 通过、`ruff format --check` 315 文件、`mypy` 174 源文件无问题；2 项失败始终是缺 `framework/harbor` 的 ISSUE-04。
- **用例区分力已实测两处**：① 把 `from_record` 退回写死值 → "如实报告"用例失败，还原后通过；② 升级用例先制造真实失败（旧约束拒绝受控记录）再验证升级为真、再调返回 False、未知形状抛 `CatalogUnavailable`。
- **真实旧库升级已验证**：对本机阶段 0 的 `agentexam_dev`（真实旧约束）调用 `upgrade_api_constraints` → 首次 `True`、再次 `False`，`pg_get_constraintdef` 复核两条约束均已放宽。
- **两处计划偏差（如实记录）**：① 实施方案原写新增 `upgrade_api.sql`，实际**复用 Job 包既有的"读定义→升级→复核"Python 模式**（`upgrade_continuous_preset`），不新增 SQL 文件，理由是与既有约定一致且能校验未知形状；② 原写"响应枚举扩宽待 B 确认"，实际**代码侧先落地**（不落地则链条根本不通），只把**契约正文措辞**留给 B，避免阻塞。

### 未完成与遗留

- **S2、`service.py` 与 S9 尚未实施**；已完成前置验证、S3–S7、T1、S8（筛选接线 + 受控身份与登记）。**代理中所有能以纯逻辑表达的安全不变量均已落地并有测试**：私有文件可信、请求出站前拒绝、额度不超支、未知不记零、令牌不跨 Run、出站目标不由请求决定、重试与重定向结构上不可配。
- **T1 已不再是 `service.py` 的未知项**：拓扑在本机（纯 Docker 层）成立，且七条断言的每一条都有实际输出。**但 `service.py` 仍不应据 T1 直接定稿**，理由有二：① T1 结论只在纯 Docker/Compose 层成立，固定 Harbor 能否替换侧车网络附加仍未回答（T2，负责人机器）；② T1 的转发实现是中继替身，不含 HTTP 语义。可行做法是先实现与拓扑无关的部分（鉴权、令牌生命周期、错误码映射、流收束），把网络形态留到 T2 之后接线。
- **S2 暂缓**：Codex TOML 字段名研究第 1 节有据，但仓库内无 `config.toml` 样例（探针样例在被 Git 忽略的 `runtime/`，只在负责人机器）。定稿前须用固定 CLI 在契约层复核一次字段名，不凭文档当已确认。
- **本轮未改动任何产品代码**，故静态检查与默认回归沿用同一 HEAD（`4c7c4d6`）的实测结果：`ruff check` 通过、`ruff format --check` 313 文件、`mypy` 174 源文件无问题、默认回归 **484 passed / 102 skipped / 2 failed**（失败项仍为缺 `framework/harbor` 的 ISSUE-04），`pytest tests/providers` **67 passed / 1 skipped**。
- **T2 与集成层仍在负责人机器**：资源范围已确认，窗口为空；7 条断言在固定 Harbor 上的成立仍需单独窗口与授权。
- 授权依据：用户会话内明确"同意"，并追加"其它需要开工授权的也同意"；随后对"修 T1 探针并重跑七条断言"回复"要"。本行动按其**只覆盖 E 本机实施与 T1 执行**理解执行——**不含真实模型/供应商调用**（项目规定须单独授权、历史 ChatGPT 许可不覆盖 DeepSeek/Kimi），**也不含负责人机器的 T2 操作**。负责人书面回执原写"未授予实施开工许可"，建议补一句书面确认后再同步任务单第 2 项验收的机器归属。
