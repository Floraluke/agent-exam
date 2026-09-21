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

### 未完成与遗留

- **S2、S5–S9 与 T1 尚未实施**；已完成前置验证、S3、S4。
- **S2 暂缓**：Codex TOML 字段名研究第 1 节有据，但仓库内无 `config.toml` 样例（探针样例在被 Git 忽略的 `runtime/`，只在负责人机器）。定稿前须用固定 CLI 在契约层复核一次字段名，不凭文档当已确认。
- **T1 未执行**：本机 Docker 能力已验证，但拓扑探针与 7 条断言仍未做。
- 授权依据：用户会话内明确"同意"，并追加"其它需要开工授权的也同意"；本行动按其**只覆盖 E 本机实施与 T1 执行**理解执行——**不含真实模型/供应商调用**（项目规定须单独授权、历史 ChatGPT 许可不覆盖 DeepSeek/Kimi），**也不含负责人机器的 T2 操作**。负责人书面回执原写"未授予实施开工许可"，建议补一句书面确认后再同步任务单第 2 项验收的机器归属。
