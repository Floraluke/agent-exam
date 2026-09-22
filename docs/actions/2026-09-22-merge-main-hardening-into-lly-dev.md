# 把 `origin/main` 的加固改造合并进 `lly/dev` 并适配 `provider_access/server/`

## 状态与情况

- 状态：**已完成**（合并、适配、全套验证、区分力实测、文档同步）；本地提交待推送 `origin/lly/dev`。
- 来源请求：用户要求把 `origin/main` 合并进 `lly/dev`，让 `provider_access/server/` 适配 main 的加固改造，重跑全套验证，补一条能区分头处理新旧行为的用例，最后提交并推送 `origin/lly/dev`。
- 范围：① 合并 `origin/main`；② 解决 6 处冲突；③ `uv sync`；④ 让 `server/` 适配新接缝；⑤ 重跑全套并记录实际数字；⑥ 提交推送。
- 明确排除：**不碰** `tests/providers/runtime/` 的探针与 T2 相关文档（负责人正在用）；**不做** T2、S10、S11；**不合并进 `main`**（用户自己来）；不新增顶层 Module、不改公共 Interface、不新增数据库表。若发现必须改公共接口或新增顶层模块，停下来报告。

### 合并前基线（本机实测，2026-09-22）

| 检查 | 用户给参考值 | 本机实测 | 结论 |
|---|---|---|---|
| `pytest tests/providers -q` | 165 passed / 1 skipped | **165 passed / 1 skipped**（31.18 秒） | 一致 |
| 默认回归 `pytest -q` | 591 passed / 105 skipped / 2 failed | **591 passed / 105 skipped / 2 failed**（90.10 秒） | 一致 |

2 项失败与基线完全相同：`tests/contract/test_execution_network.py` 的
`test_bootstrap_imports_fixed_harbor_not_the_adjacent_adapter_package` 与
`test_sidecar_exports_traceable_dns_adaptation_and_never_overwrites`，均为缺 `framework/harbor` 的 ISSUE-04。

### 合并前的关键事实（已查证）

- `origin/main` 本次为 `858d30a`（比任务描述里的 `e6a7138` 又前进 4 个提交，全部是文档：
  `docs/architecture/modules/web-and-http/` 与 `docs/interfaces/HTTP_API.md`），合并基点 `4f2c606`，
  `lly/dev` 领先 17 个提交。
- 试合并（`git merge-tree`，未落盘）仍是 **6 个冲突文件**，与任务描述一致。
- main 侧对 `provider_access/` 的改动（`5358b4b` "fix: harden backend execution and validation"）：
  - 新增 `private_file.py`（抗竞态读私有文件：`lstat` → `O_NOFOLLOW` 打开 → `fstat` → 校验 → 读 → 复核签名）。
  - `failures.py` 新增 `ProviderAccessError(ValueError)`（构造时拒绝未知码，未知码不能静默变通用值），
    并把 `PRIVATE_FILE_CHANGED` 加入 `_CREDENTIAL_UNAVAILABLE`、`REQUEST_HEADER_NOT_ALLOWED` 加入 `_REQUEST_REJECTED`。
  - 全部 `raise ValueError(码)` 改为 `raise ProviderAccessError(码)`；`secrets._stat_regular_file` 删除（职责移入 `private_file`）。
  - `secrets.REGISTERED_UPSTREAMS` **收窄为只剩 `internal_test_fake`**（CR-13：任务 05 只允许受控假上游）。
  - `request_policy` 新增 `FORWARDED_CLIENT_HEADERS = {accept, accept-encoding, user-agent}` 与
    `IGNORED_CLIENT_HEADERS = {content-length, content-type}`；`strip_client_auth` 由"只剥认证头"改为
    **白名单放行 + 未列出即拒绝**（CR-11：出站只允许最小业务头集合）。
  - `budget._measured_tokens` 新增：上游报告的 usage **超出本次预留**时按未知处理（整笔计费）。
  - 依据：`docs/reviews/2026-09-21-core-code-diagnostic-report.md` 的 CR-11/CR-13。
- `mypy.ini`、`pytest.ini` 为 main 新增（根级），`pyproject.toml` 与 `uv.lock` 有变化 → 需 `uv sync`，
  且静态检查与测试的运行方式可能改变（CR-04：默认 `mypy` 入口过去失败，main 已修）。

### 待确认的接缝判断（本行动要给出结论的地方）

`request_policy.strip_client_auth` 改为白名单后，`server/http.py` 目前把**入站 raw 头（含 `Host`、`Connection`）
原样**交给 `service.decide()`，因此真实 HTTP 客户端（必然带 `Host`）会在策略层被 `REQUEST_HEADER_NOT_ALLOWED` 拒绝。
需要判定：**`Host`/`Connection`/`Transfer-Encoding` 这类"属于入站连接本身"的头应当在入站边界剥离**，
还是让它们失败关闭；以及 `Accept-Encoding` 按 main 的白名单**转发**还是沿用 `egress` 原有的"传输层自己决定"。
判定依据是 CR-11 的验收口径"出站仅允许最小业务头集合、这些头在出站前失败关闭"，即**可观测性质是"不到达上游"**，
而 CR-11 的修复方向原文写的是"拒绝**或剥离**"。

## 实施措施

1. 合并前记录基线（已完成，见上表）。
2. `git merge origin/main`，6 处冲突按以下方向解决：
   - `provider_access/failures.py`、`tests/providers/policy/test_controlled_failures.py`：**取 main 侧**
     （同一份文件的超集）；取完必须确认 `controlled_failure`/`ALL_INTERNAL_CODES`/词表守卫测试都还在且通过。
   - `.scratch/ui-catalog-providers/issues/05-...md`、`docs/LLY/01-plan/PLAN.md`、
     `docs/LLY/01-plan/STAGE1_PROXY_TEST_DESIGN.md`、`docs/LLY/03-progress/PROGRESS_LOG.md`：
     **手工合并，双方条目都保留**，不整段取一侧。
3. `uv sync`，确认工具链与运行方式的实际变化（`mypy.ini`/`pytest.ini`/`uv.lock`）。
4. 让 `server/` 适配新接缝：
   - 异常捕获由 `except ValueError` + `str(error)` 改为按 `ProviderAccessError` 捕获并读 `.code`。
   - 头处理按 `FORWARDED_CLIENT_HEADERS`/`IGNORED_CLIENT_HEADERS` 接线，不自立第二份策略。
   - 核对 `REGISTERED_UPSTREAMS` 收窄对 `binding.py` 调用点的影响。
5. 补一条能区分头处理新旧行为的用例，并**实测其区分力**（改实现让它失败、还原后通过）。
6. 跑全套并记录实际数字；失败必须仍只有那 2 项 ISSUE-04。
7. 把实际数字写回本行动与 `docs/LLY/03-progress/PROGRESS_LOG.md`；提交并推送 `origin/lly/dev`。

**完成标准**：6 处冲突解决且双方条目都在；`server/` 按新接缝接线且无字符串匹配错误码；新增用例有实测区分力；
`tests/providers`、默认回归、开 PG 全量、`ruff check`、`ruff format --check`、`mypy` 全部有实际输出；
失败项与基线完全相同；已推送到 `origin/lly/dev`。

## 受影响文件树（实际结果）

```text
apps/backend/src/eval_platform/adapters/execution/provider_access/
├─ failures.py            # 冲突：**手工并集**（main 的 ProviderAccessError / PRIVATE_FILE_CHANGED /
│                         #   REQUEST_HEADER_NOT_ALLOWED ＋ 本分支的 _UPSTREAM_FAILED 组与 4 个被 main 漏掉的码）
├─ private_file.py        # main 新增，未改动
├─ secrets.py             # main 侧改动，未改动
├─ request_policy.py      # main 侧改动，未改动（供 M1 临时改实现做区分力实测，已还原）
├─ transport.py / budget.py / binding.py   # main 侧改动，未改动
└─ server/
   ├─ service.py          # 改：① 按 ProviderAccessError 捕获并读 .code（替换 5 处 str(error)）；
   │                       #     ② 入站先剥连接自有头；③ 头白名单提前到预留之前；④ 200 行上限调整
   ├─ contracts.py        # 改：接收从 service.py 移出的入站归一化（CONNECTION_OWNED_HEADERS /
   │                       #     without_connection_headers / bearer_token），避免 service.py 超 200 行
   ├─ egress.py           # 改：删掉自成一份的 TRANSPORT_OWNED_HEADERS 转发策略，改由 request_policy 决定
   └─ http.py / stream.py / runner.py / closure.py / __init__.py   # 未改动（验证通过）
apps/backend/src/eval_platform/adapters/execution/codex/provider_config.py
                          # 改：补回被 CR-13 收窄弄失效的"真实提供方主机"守卫（REAL_PROVIDER_HOSTS）
apps/backend/tests/providers/
├─ policy/test_controlled_failures.py   # 冲突：**手工并集**（main 侧 ＋ 本分支的递归遍历与更宽的 _NON_CODES）
└─ lifecycle/
   ├─ support.py                        # 改：两个 verify_access 替身改抛 ProviderAccessError（与真实校验器一致）
   ├─ test_request_pipeline.py          # 改：目的地用例改为新语义；新增区分新旧行为的用例；拒绝不动账本用例加头拒绝
   └─ test_egress_and_surface.py        # 改：传输自有头用例去掉已被白名单拒绝的 X-Trace，补描述层断言
apps/backend/tests/catalog/agent_identity/test_uncontrolled_records.py
                          # 改：失败夹具改为绕过领域构造器装配（CR-12 后唯一可能的形态），断言未改
docs/actions/2026-09-22-merge-main-hardening-into-lly-dev.md   # 本文件（新增）
docs/LLY/01-plan/PLAN.md、STAGE1_PROXY_TEST_DESIGN.md、docs/LLY/03-progress/PROGRESS_LOG.md  # 冲突：手工合并
.scratch/ui-catalog-providers/issues/05-fake-provider-secure-execution-chain.md                # 冲突：手工合并
```

## 自验证方式

1. 逐条运行并记录实际输出：`pytest tests/providers -q`、默认 `pytest -q`、开 PG 全量、`ruff check .`、
   `ruff format --check .`、`mypy src`。
2. 冲突解决核对：`controlled_failure`、`ALL_INTERNAL_CODES`、词表守卫存在且通过；4 份文档双方条目都在。
3. 区分力实测：临时改实现让它失败 → 还原后通过（本次共 6 处）。
4. 失败项核对：必须仍只有 ISSUE-04 的 2 项。
5. 未运行或被跳过的检查如实标注。

## 自验证情况

### 冲突解决与合并提交

- 合并提交 **`b8bbc0b`**（`git merge origin/main`，合并基点 `4f2c606`，main 侧 `858d30a`）。
- 6 处冲突的解决方向与结果：
  1. `provider_access/failures.py`：**未按"取 main 侧"执行**，改做**手工并集**。见下"与任务描述不符的实测事实"。
  2. `tests/providers/policy/test_controlled_failures.py`：同上，手工并集（恢复 `rglob` 与更宽的 `_NON_CODES`）。
  3. `.scratch/.../05-fake-provider-secure-execution-chain.md`：手工合并，本分支的 S6a–S6e / 回复 B / T2 诊断条目
     与 main 的"核心诊断修复后对账"都保留；main 那节里"仍未完成 S2、`service.py`"的表述加了状态标注（该两项已过期）。
  4. `docs/LLY/01-plan/PLAN.md`：状态行手工合并（保留本分支较新的状态，并入 main 的"任务 04 资格门禁已完成、06–08 未实施"）。
  5. `docs/LLY/01-plan/STAGE1_PROXY_TEST_DESIGN.md`：两处冲突均为本分支的**实施后**版本对 main 的**实施前**版本，
     采用本分支版本并写明为何；另加一句指向 main 加固的链接。
  6. `docs/LLY/03-progress/PROGRESS_LOG.md`：本分支当日条目全部保留，main 的"核心诊断修复后对账"作为**当日独立小节**保留，
     并标注其中 S2/`service.py` 两项已被本分支同日条目取代。

### 与任务描述不符的实测事实（重要，两处）

**① main 侧不是"同一份文件的超集"，取main侧会删掉本分支的功能。** 任务描述说冲突的两个代码文件"main 那版是超集"。
实测相反：`_UPSTREAM_FAILED` 组（`PROVIDER_UPSTREAM_FAILED` ＋ 六个 `TRANSPORT_*` 码）与本分支新增的
`PRIVATE_PROFILE_RUN_MISMATCH`、`TRANSPORT_UPSTREAM_UNAUTHORIZED`、`REQUEST_BODY_MALFORMED`、
`REQUEST_BODY_TOO_LARGE` 只存在于本分支（由 `57a18f5` 引入，main 从未有过）。按"取 main 侧"会**静默删除**它们，
后果是 `egress.py` 的六个上游失败码全部落到兜底的 `PROVIDER_ACCESS_FAILED`／500，而不是
`PROVIDER_UPSTREAM_FAILED`／502。已改为**并集**；区分力实测见 M5。

**② main 侧的词表守卫是"子集"，取main侧会失去对 `server/` 的覆盖。** 本分支的守卫用 `PACKAGE.rglob("*.py")`
（递归，覆盖 `server/`），main 用的是 `PACKAGE.glob("*.py")`（不递归）。实测（M6）：把一个未审查的码字面量注入
`server/egress.py`，**本分支的 rglob 版守卫失败并指名该码，main 的 glob 版守卫 7 项全部通过**——即"取 main 侧"
会让整个 `server/` 子包的内部码逃出防漂移门禁。

### 工具链变化（`uv sync` 后实测）

- `uv sync` 成功；`pytest` 9.0.2→9.0.3、`pyarrow` 22.0.0→23.0.1，新增 `pytest-cov`、`pip-audit`、`anyio`、`httpx2` 等。
- **`apps/backend/pyproject.toml` 的 pytest 配置新增 `--cov`，并设 `fail_under = 80`**（根级 `pytest.ini` 另有
  `testpaths = apps/backend/tests infra/tests`、`--strict-markers`）。后果是**只跑子集时会因覆盖率不达 80% 而报一条 FAIL**：
  `pytest tests/providers -q` 的测试结果是 **170 passed / 1 skipped**，但整条命令以
  `FAIL Required test coverage of 80.0% not reached. Total coverage: 31.21%` 结束。这是子集运行的配置后果，
  **不是用例失败**；全量跑时覆盖率为 **86%**，门禁通过。为看清测试结果，子集调试时用 `--no-cov`（仅本地调试用法，未改配置）。
- 根级 `mypy.ini`（`strict = True`、`files = apps/backend/src/eval_platform`）使 `mypy src` 可复现；本次未改任何检查配置。

### `server/` 适配了什么、为什么

1. **错误码不再靠字符串传递**：`service.py` 五处 `except ValueError as error: ProviderRejection(str(error))`
   改为 `except ProviderAccessError as error: ProviderRejection(error.code)`。理由：main 引入的
   `ProviderAccessError` 会校验码是否在 `ALL_INTERNAL_CODES` 内，`.code` 是唯一权威来源，字符串匹配会随措辞漂移。
2. **入站先剥"连接自有头"**（新增 `without_connection_headers`，集合在 `contracts.py`）：`Host`／`Connection`／
   `Transfer-Encoding` 等描述的是**客户端到本代理**这条连接，不是它给上游的请求。main 的白名单会**拒绝**未列出的客户端头，
   而任何真实 HTTP 客户端（`urllib`、`curl`、Codex CLI）都必然发 `Host`，不剥就会让代理**拒绝一切真实请求**（实测见 M2，7 条用例失败）。
   注意 `X-Forwarded-Host`／`Forwarded`／`Proxy-Connection` **故意不在**剥离集合里：它们仍会到达策略层并被拒绝，
   main 的负例因此照旧成立。
3. **头白名单提前到预留之前**：合并后在 `server/` 上发现一处**真实缺陷**——白名单校验原本发生在 `build_outbound`（第 6 步），
   在 `reserve`（第 5 步）之后。于是"带一个非白名单头"的请求会在**已取走预留**之后才被拒绝，而 `decide` 抛错时不会创建 relay，
   的那笔预留**永远不会结算**，等于凭一个请求头白耗该 Run 的额度。现已把白名单并入第 3 步（策略）在预留前求值。
   这条同时是本模块自己写明的安全不变量（"每次拒绝都发生在什么都没发、账本未被动过时"）的修复。
4. **`egress.py` 不再自持一份转发策略**：删除 `TRANSPORT_OWNED_HEADERS`。经第 2、3 步之后，
   `OutboundRequest.headers` 已由构造成分最小集合，传输层补自己的 `Host`／`Content-Length` 不会冲突。
   按任务要求，转发/忽略客户端的判断统一由 main 的 `FORWARDED_CLIENT_HEADERS`／`IGNORED_CLIENT_HEADERS` 决定。
5. **`provider_config.py` 补回失效守卫**：main 的 CR-13 把 `REGISTERED_UPSTREAMS` 收窄到只剩受控假上游，
   于是 `render_provider_config` 里"拒绝任何登记过的真实上游地址"那条**静默失效**——`https://api.deepseek.com`
   从"被拒绝"变成"被接受"（这正是 CLI 绕过代理直连真实供应商的入口）。已按真实提供方主机名补 `REAL_PROVIDER_HOSTS`
   并把检查改为按主机比对。**注**：该文件只在 `lly/dev` 上（main 没有），所以这是合并才会暴露的跨分支耦合。
6. **4 行上限调整**：新增内容一度把 `service.py` 推到 249 行（超过动态语言单文件 200 行指标）。已把入站归一化
   （常量 ＋ 两个助手）移到同目录的 `contracts.py`，`service.py` 回到 **200 行**；`contracts.py` 94 行；
   `provider_access/` 与 `server/` 各 8 文件，均未破指标。

### 区分力实测（临时改实现让它失败 → 还原后通过）

| # | 临时改动 | 结果 | 还原后 |
|---|---|---|---|
| M1 | `strip_client_auth` 退回"只剥认证头"（合并前行为） | 2 条失败：新增的路由头用例、`test_a_refusal_keeps_the_ledger_untouched` | 通过 |
| M2 | 去掉 `decide` 里的入站头归一化 | **7 条失败**（含经真实 HTTP 表面的三条与客户端消失用例） | 通过 |
| M3 | 把头白名单退回"预留之后"求值 | `test_a_refusal_keeps_the_ledger_untouched` 失败（额度被白耗）；区分力用例亦失败 | 通过 |
| M4 | 去掉 `REAL_PROVIDER_HOSTS` 分支（合并前状态） | `test_entries_that_are_not_the_isolated_proxy_are_refused[deepseek]` 失败 | 通过 |
| M5 | 去掉 `_UPSTREAM_FAILED` 组（即"取 main 侧"） | 3 条失败：502 用例、受控文案端到端、**词表防漂移守卫** | 通过 |
| M6 | 向 `server/egress.py` 注入未审查码 | rglob 版守卫失败并指名；**glob 版（main）7 项全通过** | 通过 |

每处实测后均用 `cmp` 确认还原为字节一致，工作树无残留。

### 全套实测数字（合并后，最终代码）

| 检查 | 合并前基线 | 本机实测 | 结论 |
|---|---|---|---|
| `pytest tests/providers -q` | 165 passed / 1 skipped | **170 passed / 1 skipped**（31.12 秒）＋ 覆盖率门禁 FAIL（见上） | 测试结果无回归；+5 为新用例与 main 侧新增用例 |
| 默认回归 `pytest -q` | 591 passed / 105 skipped / 2 failed | **610 passed / 106 skipped / 2 failed**（98.02 秒） | 失败项完全相同（ISSUE-04） |
| 开 PG 全量 | 计划未记基线 | **664 passed / 52 skipped / 2 failed**（189.02 秒） | 失败项仍只有那 2 项 |
| 覆盖率（全量） | — | **86%**（门禁 80% 通过） | main 新增的门禁 |
| `ruff check .` | 通过 | `All checks passed!` | 一致 |
| `ruff format --check .` | 341 文件 | **348 files already formatted** | 一致 |
| `mypy src` | 184 源文件 | **186 source files no issues** | 一致 |

- 2 项失败始终是 `tests/contract/test_execution_network.py` 的
  `test_bootstrap_imports_fixed_harbor_not_the_adjacent_adapter_package` 与
  `test_sidecar_exports_traceable_dns_adaptation_and_never_overwrites`（缺 `framework/harbor`，ISSUE-04）。
- PostgreSQL 按 `LOCAL_SETUP.md` 第 2 节既有命令启动（便携版、不注册服务），跑完仍为 `accepting connections`；
  未改写该文档的运行状态段（仍有效）。

### 已知遗留与未验证项

- **`Accept-Encoding` 的语义后果（交给集成层 S11 判定）**：main 把 `accept-encoding` 归入**转发**集合，
  因此 `egress` 不再强制 `identity`。实测（隔离探针，不涉及真实供应商）：客户端送 `gzip` 时上游收到
  `Accept-Encoding: gzip`，客户端不送时库自补 `identity`。后果是**若真实上游按 gzip 压缩 SSE**，
  `stream.py` 的终止事件扫描会找不到 usage → 按整笔预留计费并关闭该 Run（`usage-unknown`）。
  这是**失败关闭**（绝不会少计费），但会多计费并提前收束 Run。按"不自己再写一份转发策略"的要求，
  本次**不覆盖 main 的决定**，只如实记录并建议 S11 用真实上游复核。
- **`PROVIDER_UPSTREAM_FAILED` 仍未列入 `HTTP_API.md` §10.2**：该节目前只有 5 个受控码，本分支的第六个码
  （及其 502 映射）仍是**候选**。此为合并前既有的待办（原记录写"待 B 列入枚举"），**本次未新增、也未关闭**。
- **`serve_proxy.py`（未跟踪）**：`apps/backend/tests/providers/lifecycle/serve_proxy.py` 是**别人**留在工作树的未跟踪辅助脚本
  （按端口起一个真实代理，供手验受控拒绝）。**我没有创建它，也没有提交它**；它不参与 pytest 收集。
  本次未改动它——附带发现：它用 `curl` 演示，而 `curl` 必然发 `Host`，所以它**只有在本分支的入站剥离存在时才能工作**。
- **未运行**：T2／S10／S11（等负责人机器）；Harbor 相关 2 项失败未处理（ISSUE-04）；MinIO 等档位按开关跳过。
- **未改动**：`tests/providers/runtime/` 的探针与 T2 相关文档（负责人正在用）。

### 计划偏差（如实记录）

1. **冲突解决方向偏离任务描述**：两个代码文件没有"取 main 侧"，改为手工并集；理由与实测见上（① 与 ②）。
2. **新增了一条用例**：`test_a_routing_header_is_refused_where_it_used_to_be_forwarded`（任务要求的"能区分新旧行为的用例"），
   并在 `test_a_refusal_keeps_the_ledger_untouched` 里补了头拒绝这一种拒绝。
3. **修改了两条既有用例的期望与一条测试夹具**（都是被 main 的语义变更取代的部分，不是为了让它们变绿）：
   传输自有头用例去掉 `X-Trace` 必须转发的断言、目的地用例改按新语义、受控记录夹具改绕过领域构造器。
   每一条都对应 main 库里同名的负例（`test_client_routing_headers_never_reach_the_fixed_upstream`、
   `test_identity_pairs.py` 用 `object.__new__` 装配）。
4. **移动了 `service.py` 的部分内容到 `contracts.py`**（入站归一化），以符合 200 行指标；模块职责说明已同步更新。
5. **新增常量 `REAL_PROVIDER_HOSTS`**（`provider_config.py`）：不是新顶层模块、不改公共接口，但属于"补回被 main 弄失效的守卫"，
   请在合并评审时留意这是跨分支耦合暴露出的问题。

