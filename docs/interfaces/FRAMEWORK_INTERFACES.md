# 上游框架与 Agent CLI 接口清单

> 文档状态：持续维护；M0 固定真实 Codex 单题与独立 Fork 判卷通过，完整阶段验收未完成
>
> 最后更新：2026-09-17（固定CLI配置探针与新提供方规划）
> 权威范围：本文件维护 SWE-Gym、Harbor、SWE-Bench-Fork 和目标 Agent CLI 的真实上游接口入口。Harbor 字段级映射见 [`HARBOR_EXECUTION.md`](./HARBOR_EXECUTION.md)；Codex 与自研 Agent 凭据政策见 [`CODEX_AUTHENTICATION.md`](./CODEX_AUTHENTICATION.md)；依赖来源与固定版本见 [`DEPENDENCIES.md`](../dependencies/DEPENDENCIES.md)。

## Codex 新提供方规划与接口证据

[扩展规格](../../.scratch/ui-catalog-providers/spec.md)仍用固定Codex CLI，不实现P2 Python Agent或协议桥。官方原生Responses、模型/地区端点及价格来源见[研究](../research/2026-09-17-codex-provider-config-and-budget.md)；当前固定Harbor的Kimi内置配置偏向订阅端点，不能直接用作用户选择的开放平台预设。

固定CLI `0.153.0` 已在禁外网/假令牌环境证明：用户级TOML配置可发出模型名匹配的Responses请求，`-c`可覆盖模型，`wire_api=chat`与缺少指定令牌变量在请求前拒绝。故意401只是请求到达证据，真实工具循环、返回usage、重试关闭和代理安全未验证；准确结果唯一见研究6.1。

计划深化既有Guarded Codex配置渲染/安装/网络与Worker绑定，不修改固定第三方源码。模型目录、工具描述、关键请求参数与配置摘要须核验冻结；公开文档的新字段不能直接推定固定版本支持。五道题扩展继续用固定Parquet/Fork，其镜像及gold/负例门禁见[计划04](../../.scratch/ui-catalog-providers/plan.md#6-04五道新题合格入库打通六题提交)。

## 1. 先把最容易混淆的事说清楚

“直接使用 SWE-Gym”不是把整个 Web 平台写进 SWE-Gym 仓库，也不是寻找一个不存在的 `swe_gym.run_agent()` 函数。

当前上游事实是：

1. SWE-Gym 主仓库提供数据、模型与复现实验材料；官方 README 把数据放在 Hugging Face，并明确把环境常量指向 SWE-Bench-Fork。
2. 配套 SWE-Bench-Fork 提供实际的任务字段、Docker 环境构建和 `swebench.harness.run_evaluation` 判卷入口。
3. 因此本项目“直接使用框架”的运行含义是：**读取真实 SWE-Gym 任务 → 让 Agent 在固定仓库快照生成 patch → 把真实 prediction 交给固定版本 SWE-Bench-Fork 判卷**。
4. 本项目用 Harbor 统一运行 Agent 和 Docker 环境，在外面增加平台 Job 队列、长期制品、固定 Fork 判卷和 Web，不重写上游判卷语义；后续 Judge/人工复核的启用阶段见[总架构第 3.1 节](../architecture/ARCHITECTURE.md#31-m1-交付边界2026-09-09-已确认)。

SWE-Gym 本身没有提供 Codex/Aider/Claude Code 的统一 Runner；固定 Harbor 已核验包含多 Agent、Environment、Job/Trial 与轨迹能力，因此项目通过 `HarborExecutionAdapter` 复用它，而不是重复自研同一层。当前固定单题的补丁出口和本机执行/判卷链路已有[第四场真实证据](./HARBOR_EXECUTION.md#第四次授权运行真实补丁与独立判卷通过2026-09-08)，不等于完整平台完成。

## 2. 事实状态

| 状态 | 含义 |
|---|---|
| 已核验源码 | 已从当前本地固定提交读取到接口定义 |
| 已核验官方文档 | 已从工具供应商官方文档/官方源码确认 |
| 架构已确认 | 项目已决定采用该映射，但不等于本机运行通过 |
| 候选映射 | 本项目怎样使用真实接口的设计；未标为“Adapter 契约通过”前仍可能尚未实现 |
| Adapter 契约通过 | 固定版本通过本项目统一协议测试 |
| 真实账号通过 | 使用真实模型凭据在小仓库运行通过 |
| SWE-Gym E2E 通过 | 真实任务从 Issue 到 SWE-Bench-Fork 结果完整跑通 |

后三级都需要实际运行证据，不能从文档可行性直接推导。

Codex 相关状态必须再区分三层：官方 `codex exec` 接口已核验；认证政策已经由项目确认；宿主 CLI 与 Harbor 容器运行能力必须分别用本机证据验证。任一层通过都不能替代另外两层。

2026-09-04 的宿主探针只证明当前 npm 安装的 CLI 能输出版本和帮助；它没有发起模型请求、没有检查登录状态，也不证明 Harbor 容器 E2E 可用。

## 3. 上游身份与固定版本

依赖身份、官方来源、完整提交哈希、本地恢复命令和当前验证状态只在 [`DEPENDENCIES.md`](../dependencies/DEPENDENCIES.md) 维护。本文件中的接口结论必须针对那里记录的固定快照核验，不得默认跟随上游 `main` 漂移。

任何升级先更新依赖事实源，再重新核验本文字段与 CLI，最后执行契约/E2E 测试。

## 4. SWE-Gym Task Source

### 4.1 已核验接口事实

SWE-Gym README 说明任务数据在 Hugging Face，环境常量位于 SWE-Bench-Fork；复现实验分别通过项目固定的 OpenHands/MoatlessTools 流程完成。来源：[固定提交的 SWE-Gym README](https://github.com/SWE-Gym/SWE-Gym/blob/b681068ca20628c6987b7416cc4cf03f06b77ba5/README.md)。

固定 SWE-Bench-Fork 中：

- `load_swebench_dataset(name, split, instance_ids)` 支持 Hugging Face 数据集名称，也支持本地 `.json`/`.jsonl`；来源：[固定提交的 `utils.py`](https://github.com/SWE-Gym/SWE-Bench-Fork/blob/242429c188fcfd06aad13fce9a54d450470bf0ac/swebench/harness/utils.py)。
- `SWEbenchInstance` 在固定提交中列出以下字段；来源：[固定提交的 `constants.py`](https://github.com/SWE-Gym/SWE-Bench-Fork/blob/242429c188fcfd06aad13fce9a54d450470bf0ac/swebench/harness/constants.py)。

| 上游字段 | 用途 | Agent 是否可见 |
|---|---|---:|
| `instance_id` | 任务唯一身份 | ✅ |
| `repo` | 目标仓库 | ✅ |
| `base_commit` | 固定仓库快照 | ✅（审计信息） |
| `problem_statement` | Issue 题目 | ✅ |
| `patch` | gold 修复补丁 | ❌ |
| `test_patch` | 判分测试补丁 | ❌ |
| `FAIL_TO_PASS` | 修复后应从失败变通过的测试 | ❌ |
| `PASS_TO_PASS` | 原本通过且不能回归的测试 | ❌ |
| `hints_text` | 上游提示 | 待确认是否使用；默认不暴露 |
| `version` / `created_at` | 元数据 | 页面按需展示 |
| `environment_setup_commit` | 环境准备信息 | 只供环境 Adapter |

`FAIL_TO_PASS`/`PASS_TO_PASS` 在该固定代码的 `TypedDict` 中声明为字符串，而 `make_test_spec` 会把 JSON 字符串或对象解析成列表。项目内部要规范化为列表，不能假定加载后天然同一类型。

当前 M0 只加载已固定、已校验的 Parquet 单题；`swe_gym.py` 的 `_string_tuple()` 仅接受列表。该固定快照可正常读取，但目标契约所述 JSON 字符串输入兼容尚未实现。扩展任务来源前需要补齐或明确其输入边界；这不是当前固定单题已知失败，也不授权本轮扩展题库。

### 4.2 候选 Adapter 映射

| Task Catalog 输入 | 上游调用 | Task Catalog 输出 |
|---|---|---|
| `dataset_id`、固定 `dataset_revision`、`split`、`instance_id` | 固定 revision 的数据加载 + `load_swebench_dataset` 兼容层 | 内部 `EvaluationTask` |

映射规则：

1. 导入/登记时校验必需字段和内容哈希，不在每次运行时盲目下载会漂移的数据。
2. 标准化字段写 PostgreSQL，同时把完整原始任务 JSON 以内容 SHA-256 寻址写入 MinIO；两者在同一同步动作中冻结。
3. 内部对象分成 Agent 可见视图和 Evaluator 受限视图；原始快照中的隐藏字段不能因为存入 MinIO 就暴露给 Agent/API。
4. 普通 HTTP API 和 Runner 永远不返回 gold patch 与判分测试答案。
5. 首个原型数据集 ID 已确认为 `SWE-Gym/SWE-Gym-Lite`；revision、split 和具体实例必须在实际读取数据元信息后记录，本文不凭 README 猜 split 名称。

## 5. SWE-Bench-Fork Patch Evaluator

### 5.1 已核验入口

官方 fork 文档把主入口定义为：

```text
python -m swebench.harness.run_evaluation
```

来源：[固定提交的 Docker Harness 文档](https://github.com/SWE-Gym/SWE-Bench-Fork/blob/242429c188fcfd06aad13fce9a54d450470bf0ac/docs/20240627_docker/README.md)和[`run_evaluation.py`](https://github.com/SWE-Gym/SWE-Bench-Fork/blob/242429c188fcfd06aad13fce9a54d450470bf0ac/swebench/harness/run_evaluation.py)。

固定提交的 CLI：

| 参数 | 必需/默认 | 含义 |
|---|---|---|
| `--dataset_name` | 默认 `princeton-nlp/SWE-bench_Lite` | HF 数据集名或本地 JSON/JSONL；本项目必须显式传 SWE-Gym 数据源 |
| `--split` | 默认 `test` | 本项目必须显式传实际 split，不借用默认值猜测 |
| `--instance_ids` | 可选，多值 | 限制本次任务；单次运行传一个 ID |
| `--predictions_path` | 必需 | `gold`、`.json` 或 `.jsonl` prediction |
| `--max_workers` | 默认 4 | Harness 并行度；单机首版候选显式传 1 |
| `--timeout` | 默认 1800 秒 | 每个实例测试超时 |
| `--run_id` | 必需 | Harness 日志和容器的运行标识 |
| `--force_rebuild` | 默认 false | 是否重建镜像 |
| `--cache_level` | 默认 `env` | `none/base/env/instance` 缓存清理层级 |
| `--clean` | 默认 false | 是否清理高于缓存层级的镜像 |
| `--open_file_limit` | 默认 4096 | 进程文件描述符上限；Linux 环境约束 |

不要直接依赖所有默认值。项目 Adapter 要显式记录 dataset、split、instance、worker 数、timeout、cache 策略、run ID 和 fork commit。

### 5.2 prediction 输入

每条 prediction 的已核验最小 schema：

```json
{
  "instance_id": "upstream-instance-id",
  "model_patch": "git unified diff",
  "model_name_or_path": "stable-agent-configuration-identity"
}
```

字段常量分别为 `instance_id`、`model_patch`、`model_name_or_path`；来源：[固定提交的 `constants.py`](https://github.com/SWE-Gym/SWE-Bench-Fork/blob/242429c188fcfd06aad13fce9a54d450470bf0ac/swebench/harness/constants.py)。

项目映射：

| 本项目字段 | prediction 字段 | 规则 |
|---|---|---|
| `EvaluationTask.instance_id` | `instance_id` | 原样使用上游 ID |
| Runner patch 制品正文 | `model_patch` | 必须与保存的 patch SHA-256 一致 |
| `AgentConfiguration` 稳定标识 | `model_name_or_path` | 使用安全、稳定、可追溯字符串；上游会把 `/` 替换为 `__` 作为日志路径 |

### 5.3 已核验输出

单实例路径：

```text
logs/run_evaluation/{run_id}/{model_name_or_path}/{instance_id}/
├─ patch.diff
├─ eval.sh
├─ test_output.txt
├─ run_instance.log
└─ report.json
```

成功形成的实例 `report.json` 至少包含：

- `patch_exists`；
- `patch_successfully_applied`；
- `resolved`；
- `tests_status`（启用详细状态时）。

Harness 还在当前工作目录生成 `<model_name_or_path>.<run_id>.json` 汇总，固定 schema version 为 2，包含 completed/resolved/unresolved/empty patch/error 等计数和 ID 列表。

重要边界：

- 空 patch 会进入 `empty_patch_ids`，可能不会产生单实例 `report.json`。
- 某实例没有产生 report 时，汇总会放入 `error_ids`；Adapter 必须把它当 Harness/基础设施失败调查，不能自动写 `resolved=false`。
- `resolved=false` 且 report 完整表示测试正常执行但补丁没有完全解决任务；这是正常评测结果，不是平台崩溃。
- Patch Evaluator Adapter 需要复制这些原始文件到 MinIO，再规范化为内部 `DeterministicResult`。

### 5.4 项目实际调用方式

`SWEbenchEvaluator` 生成不可覆盖的单条 JSONL prediction 和固定原始任务 JSONL，以隔离 Linux 子进程运行固定模块 CLI；应用仍只调用 `EvaluationRequest → DeterministicResult`。这样：

- 仍然是直接执行真实 SWE-Bench-Fork Harness；
- 上游进程、Linux `resource`、Docker 日志目录和退出状态被隔离在一个小 Adapter 内；
- 业务层只接收 `EvaluationRequest → DeterministicResult`；
- CLI 变化只需改 Adapter 与契约测试。

当前 Ubuntu WSL2 + Docker Desktop 已通过 gold、空、错误、不可应用和测试超时五类真实验证。必要的基础设施适配位于同一 Evaluator 的 `fork_entry.py`：只替换上游镜像准备和 `build_container` 函数，再以 `runpy` 执行原 `swebench.harness.run_evaluation` 模块。原因是固定 Fork 会预检查 base/env/instance 并按创建时间触发重建，且 `build_container` 硬编码 16 GiB；原生 CLI 没有固定远端 digest、内存、PID 或禁网参数。

项目适配直接使用登记的实例 digest，独立创建 `network=none`、无宿主挂载、显式 CPU/内存/PID、禁止提权的验证容器。没有伪造 base/env 标签；原 `run_instance`、模型补丁及测试补丁应用、测试脚本生成、`grading` 和汇总均未改动。每次保存 `profile.json`、`runtime.json`、`container.json`、原始命令/进程/清理证据。清理同时匹配运行 ID 和证据目录身份，不能删除其他尝试。

`result_mapper.py` 检查汇总 schema 2、唯一任务、互斥结果类别、布尔类型、冻结测试集合、报告与汇总一致性及原始 patch 字节。空补丁只由真实 `empty_patch_ids` 支持；`error_ids` 或报告缺失抛出带证据引用的 `EvaluationError`，不能写成正常 unresolved。依赖恢复只在 [`DEPENDENCIES.md`](../dependencies/DEPENDENCIES.md) 维护，真实测试证据只在 [M0 行动记录](../actions/2026-09-05-m0-codex-harbor-implementation.md) 维护。

Windows 导入 WSL 生成的报告时，完整配置指纹和嵌套目录可能使路径超过 260 字符。Evaluator 内部使用扩展本机路径读取并继续输出原有相对 object key；不改系统全局设置、不缩短指纹。该问题已经过超长路径单测、原失败报告重放和真实无模型串联回归验证。

M0 入口 `prototype_codex_harbor_e2e.py` 通过既有 `ExecutionBackend`/`PatchEvaluator` 串联，支持显式内部测试/NOP 和经可信本机构造器绑定的固定 Codex；真实入口要求见[认证接口](./CODEX_AUTHENTICATION.md)。`--check` 只验证本地固定任务，不运行容器或模型；互斥的 `--check-network` 委托执行适配层运行固定摘要、禁网的内核探针，只验证内核前提。两者都不是完整就绪或运行许可；旧 `pending` 提示的代码差距见 [Harbor 验收对账](./HARBOR_EXECUTION.md#暂停后的验收对账2026-09-08)。本机内核证据仍由 [Docker 事实第 3.4 节](../operations/LOCAL_DOCKER_ENVIRONMENT.md#34-harbor-网络前置条件)维护。

## 6. Harbor Execution Backend

[`DEPENDENCIES.md`](../dependencies/DEPENDENCIES.md) 固定的 Harbor 提交已通过官方源码静态核验：

- `JobConfig` 接受 `agents`、`datasets`/`tasks`、`n_attempts`、`n_concurrent_trials`、`environment`、`verifier` 与 `artifacts`；
- `JobPlan.build_trial_configs()` 按 attempts×tasks×agents 展开 `TrialConfig`；
- `VerifierConfig.disable` 可关闭 Harbor Verifier；
- `SingleStepTrial` 在运行 Agent 后、Verifier 前同步 Agent 输出并收集 artifacts；
- 内存 `JobResult` 聚合 `trial_results`，但真实落盘 Job `result.json` 会排除该列表；完整结果位于各 Trial 子目录；`TrialResult` 没有标准 `model_patch` 字段。
- `Trial.run()` 在发出 `START` 前先建立 Trial 目录并写 `config.json`；最终化先写完整 `result.json`，再发出 `END`。`Job` 自身为 START/END 注册内部 hook，并把实时汇总写入 Job `result.json`。
- `Job` 把已解析配置写入 Job 根 `config.json` 时使用 `exclude_defaults=True`，所以默认的 `n_attempts=1` 与 `retry.max_retries=0` 可以不出现；Trial 子目录的 `config.json` 使用 `TrialConfig`，按定义不含这些 Job 级字段。验收必须对照 Adapter 保留的源 Job 配置、Job 根配置和 Trial 配置三层读取，不能把字段缺省或配置层级差异误判为重试失控。

架构决定是：平台 Job→Harbor Job，评测运行→Harbor Trial，`n_attempts=1`、`n_concurrent_trials=1`、`verifier.disable=true`；每个 Trial 的 patch 由 Adapter 强校验后交给固定 SWE-Bench-Fork。完整输入、输出、错误和验收门槛只在 [`HARBOR_EXECUTION.md`](./HARBOR_EXECUTION.md) 维护。

任务 07 的生产接入仍通过阻塞 Harbor CLI 子进程，不能直接注入上述进程内 hook。Adapter 因此只轮询固定 Job 根下的逐 Trial `config.json`/`result.json`：前者按受信 task+agent 键映射冻结 `run_id` 并表示开始，后者在身份一致且含 Trial ID 时表示结束。日志文本、目录名和 Job 聚合计数都不作为权威业务状态；Repository 仍用租约、行版本和状态机决定能否持久化。

固定 Harbor 类型/公开 Task、NOP、四类非空补丁收集及外层超时清理的既有测试记录见 [M0 行动记录](../actions/2026-09-05-m0-codex-harbor-implementation.md)。当前已经取得[第四场真实 Codex → 固定 Fork 的单题证据](./HARBOR_EXECUTION.md#第四次授权运行真实补丁与独立判卷通过2026-09-08)；不能继续把当前整体状态写成“仅无模型路径通过”，也不能据此宣称所有契约与生命周期完成。

## 7. Codex CLI Adapter

项目已确认首个真实原型使用 Harbor 内置 Codex Agent，认证采用评测机所有者本人通过 ChatGPT Pro 登录产生的 `auth.json`；首轮 CLI 版本、模型与推理强度已由 [依赖总表](../dependencies/DEPENDENCIES.md#2-当前依赖总表) 固定。第四场已证明该固定配置的容器执行和账号/模型路径可用；Token 刷新、输出保护及剩余生命周期边界仍以[认证接口](./CODEX_AUTHENTICATION.md#63-其他尚待实测项)为准。

### 7.1 已核验官方接口

OpenAI 官方将 `codex exec` 标为稳定的非交互/脚本运行入口：

- `PROMPT` 可直接传字符串；使用 `-` 时从 stdin 读取完整 prompt；
- `--cd/-C` 设定工作区根目录；
- `--sandbox` 支持 `read-only`、`workspace-write`、`danger-full-access`；
- `--ephemeral` 不把 session rollout 持久化到默认目录；
- `--json` 使 stdout 成为 JSONL 事件流；
- 官方列出的事件包括 `thread.started`、`turn.*`、`item.*` 和 `error`；item 可包括命令执行、文件修改、MCP 调用、Web 搜索和计划更新；
- `--output-last-message/-o` 可另存最终回答，但它不是最终 Git patch。

来源：[Codex Non-interactive mode](https://developers.openai.com/codex/noninteractive)、[Codex CLI reference](https://developers.openai.com/codex/cli/reference)，复核日期 2026-09-04。官方页面当前仍把 `codex exec` 列为稳定的非交互入口；本项目认证选择及秘密边界只在 [`CODEX_AUTHENTICATION.md`](./CODEX_AUTHENTICATION.md) 维护。

### 7.2 直接 CLI 后备映射

正式主路径优先使用 Harbor 已有 Codex Agent。以下映射保留为 Harbor Adapter 调试参考和 `ProcessExecutionAdapter` 后备方案，不代表首版同时维护两套 Codex 执行实现。

```text
Runner RunEnvelope
    → Adapter 生成只含 Issue 和约束的 prompt
    → codex exec --json --ephemeral --sandbox workspace-write --cd <repo> -
    → 捕获 JSONL/stdout、stderr、退出码和超时
    → 规范化公开事件
    → 从受控 Git 工作区提取 patch
    → Runner stdout 输出 patch
```

| 统一信息 | Codex 映射 |
|---|---|
| Issue 输入 | `codex exec -` 的 stdin |
| 仓库根 | `--cd` + 外层容器工作目录 |
| 可观察轨迹 | `--json` JSONL；保留原始事件并规范化 |
| 工具调用数 | 只统计官方输出中可识别的 item，保留事件类型 |
| patch | 从最终 Git 工作区提取，不取最终回答文本 |
| 超时/CPU/内存/网络 | Execution Backend 的环境策略；Codex 自身 sandbox 是第二层，不替代 Docker |
| 版本/模型/配置 | Agent Configuration 冻结并写入 `result.json` |

历史记录：2026-09-01 从旧工作区尝试 `codex --version` / `codex exec --help` 时，WindowsApps 中打包的 `codex.exe` 被操作系统拒绝启动。该结果不再作为当前宿主 CLI 状态。

当前宿主探针：2026-09-07 `codex --version` 与用户已确认的首轮版本一致；唯一版本值见 [依赖总表](../dependencies/DEPENDENCIES.md#2-当前依赖总表)。早期探针只代表当时环境，不再把项目版本列为待确认；宿主可启动仍不代表 Harbor 容器内 Codex 可运行。

固定 Harbor `Codex.install()` 先调用 `_installed_codex_satisfies_version()`，用容器 `codex --version` 的解析值与显式 `version` 精确比较；相同则直接复用，不再执行下载。不同或命令失败时进入上游在线安装路径，涉及系统工具、Node/npm 和 Codex 下载。2026-09-07 的早期替身检查验证同版本/不同版本/命令失败为 true/false/false；后续真实无凭据安装契约也已通过，见下段。不得给未核验的安装域名开放网络或静默使用 `latest`。

2026-09-07 安装实测：按 [依赖第 2.1 节](../dependencies/DEPENDENCIES.md#21-codex-无凭据安装制品) 校验并解包固定平台包，在固定题目镜像的临时容器内离线复制工具。容器 `--network none`、无宿主挂载、去能力，CLI 以 UID 65534 执行版本与 `exec --help` 成功。测试 Environment 仅允许上游固定版本检查命令，并将其转交真实 Docker exec；调用真实 `Codex.install()` 后恰好只有该版本检查，未进入在线安装、认证 setup 或 run。这不是完整 Harbor Trial，不能据此推断模型/资源/认证兼容性。正常删除临时容器并验证无残留；命令、测试结果及边界见 M0 行动记录。

历史限制：早期窗口的默认沙箱命令启动器在命令执行前返回 `setup refresh had errors`，而提升权限后探针成功；因此该故障应归入 Codex Windows 沙箱/宿主运行环境，不应误写为 CLI 命令失败。当时的探针没有验证真实账号、发起模型请求或证明 Harbor 容器内 Codex 可用；项目版本后来由用户明确确认，见依赖事实源。

## 8. Aider CLI Adapter

### 8.1 已核验官方接口

- `aider --message "..."` / `--message-file <file>` 会处理单条任务后退出；
- Aider 直接修改当前 Git 仓库，不原生输出纯 patch；
- 当前没有官方 JSON/JSONL/NDJSON 工具事件协议；人类终端输出不能硬解析成稳定工具调用流；
- Git 集成默认开启，`--auto-commits` 和 `--dirty-commits` 默认 true，可能让普通 `git diff` 为空或污染基线；
- `--no-auto-commits --no-dirty-commits --no-gitignore` 可关闭相关行为；
- `--chat-history-file`、`--llm-history-file`、`--input-history-file` 可把历史写到指定位置；
- CLI/config 有真实版本漂移，必须固定精确版本；不依赖官方明确不保证兼容的 Python scripting API。

完整来源和源码行号见 [`2026-09-01-aider-cli-interface.md`](../research/2026-09-01-aider-cli-interface.md)。

### 8.2 直接 CLI 后备映射

正式主路径优先使用 Harbor 已有 Aider Agent。以下映射只作为能力差异事实和后备实现参考。

```text
Runner stdin JSON
    → Adapter 把 Issue 写到仓库外 UTF-8 文件
    → 固定 cwd，调用 aider --message-file ...
    → 禁止自动提交/dirty commit/.gitignore 修改
    → 捕获终端文本、历史、退出码
    → 从 base commit 和最终工作区生成包含新文件的 patch
    → Runner stdout 输出 patch
```

| 统一信息 | Aider 映射/限制 |
|---|---|
| Issue 输入 | `--message-file`；Aider 本身不是 stdin 任务协议 |
| 仓库根 | 子进程 `cwd`；需隔离 HOME 和仓库内 Aider/.env 配置污染 |
| 可观察轨迹 | 原始终端/聊天/LLM history；没有官方结构化 tool-call 流 |
| 工具调用数 | 当前不能提供与 Codex/Claude 同口径的可靠统计；显示“不支持/未知” |
| patch | 关闭自动提交后，从一次性 Git 工作区统一提取 |
| 认证 | provider key 通过 secret 环境注入；不放命令行/历史 |

当前状态：只证明理论可接入；Aider 未在本机安装或运行。

## 9. Claude Code CLI Adapter

### 9.1 已核验官方接口

- `claude -p` 是非交互模式，支持 stdin；
- `--output-format stream-json --verbose` 可输出逐行结构化会话和工具事件；
- `--max-turns`、`--max-budget-usd`、`--tools` 提供轮数、预算和工具约束；
- 较新版本的 `--restricted` 明确面向 evaluation harness 共享机器场景，但仍需固定满足最低版本的 CLI 实测；
- 运行成功/失败、结果 subtype、usage、session、成本估算可观察；最终 patch 仍需从 Git 工作区提取；
- Claude Code 是受 Anthropic 条款约束的专有 CLI；平台不能收集或中转用户 Claude.ai session token，自动化认证与费用边界要按官方政策复核。

完整来源和许可/认证边界见 [`2026-09-01-claude-code-adapter.md`](../research/2026-09-01-claude-code-adapter.md)。

### 9.2 直接 CLI 后备映射

正式主路径优先使用 Harbor 已有 Claude Code Agent。以下映射只作为能力差异事实和后备实现参考。

```text
Runner RunEnvelope
    → 生成安全 prompt 并通过 stdin 交给 claude -p
    → stream-json + verbose 捕获公开消息/工具/usage
    → 外层 Docker + 候选 --restricted/工具 allowlist
    → 从 Git 工作区提取 patch
    → Runner stdout 输出 patch
```

| 统一信息 | Claude Code 映射 |
|---|---|
| Issue 输入 | `claude -p` stdin |
| 轨迹 | `stream-json + verbose`，保留原始 event/type/id |
| 工具调用数 | 由公开 `tool_use`/`tool_result` 事件统计；子 Agent 口径需实测 |
| 预算 | `--max-turns`、`--max-budget-usd` + 外层资源限制 |
| patch | Git 工作区提取，不取 `result` 自述 |
| 认证 | API key/官方支持凭据通过 secret 注入；不得保存用户 session token |

当前状态：官方接口证明理论可接入；本机没有检测到可运行 `claude`，尚未通过 Adapter 或真实账号测试。

## 10. P2 本地自研 Agent 接口

自研 Agent 已降为 P2，不是 MVP 完成条件；当前只保留扩展接缝。P2 首版只支持 Python，并直接实现 [`RUNNER_PROTOCOL.md`](./RUNNER_PROTOCOL.md) 的 stdin JSON → stdout patch 进程 Interface。平台拥有的包装负责把审核后的 Python 模块接入 Harbor；提交者不直接实现 Harbor `BaseAgent`，也不提交 shell 命令。完整 manifest 字段、Python 版本、依赖锁格式和 Harbor 包装 extension point 留待 P2 确认/实测。

P2 自研 Agent 必须固定 Git commit、登记模型提供方/模型和关键配置、在 Agent 沙箱运行、保存轨迹/日志、生成 patch，并由同一个 SWE-Bench-Fork Evaluator 判分。提供方只允许 DeepSeek/Kimi，二者形成独立 Agent Configuration；真实 Key 由评测机可信配置持有，不进入被测进程。它不能因为是“自己写的”就绕过沙箱、取得提供方 Key 或看到隐藏答案。

## 11. 统一能力差异

| 能力 | 自研进程 | Codex | Aider | Claude Code |
|---|---:|---:|---:|---:|
| 非交互单任务 | 由我们实现 | ✅ 官方 | ✅ 官方 | ✅ 官方 |
| 任务可从 stdin 直接读 | ✅ | ✅ | ❌，用 message file | ✅ |
| 官方结构化事件流 | 由我们定义 | ✅ JSONL | ❌ | ✅ stream-json |
| 可可靠统计公开工具调用 | 取决于自研实现 | 已有单题事件证据，统一计数口径待验收 | ❌ 当前无统一口径 | ✅/待子 Agent 口径实测 |
| 原生 stdout 是 patch | 可实现 | ❌ | ❌ | ❌ |
| 统一 Git patch 提取 | ✅ | Adapter | Adapter | Adapter |
| 真实账号/模型已测试 | 待自研 | ✅，限第四场固定配置 | ❌ | ❌ |
| SWE-Gym E2E 已通过 | ❌ | ✅，限 M0 固定单题核心链路 | ❌ | ❌ |

Codex 运行能力依据[第四场记录](./HARBOR_EXECUTION.md#第四次授权运行真实补丁与独立判卷通过2026-09-08)，不是全量题库、全部网络/安全验收或 MVP 通过。

因此页面不能把“工具调用数”当成所有 Agent 天然等价的指标。过程指标只展示、不参与排序；缺失值必须显示为“不支持/未知”，不能记成 0。

## 12. Adapter 错误映射

Harbor/Adapter 的状态和错误映射唯一维护在 [Harbor 第 9 节](./HARBOR_EXECUTION.md#9-状态与错误映射)，包括 `sandbox_failed` / `policy_failed` 等当前执行结果。此前本表沿用的 `sandbox_violation` 不能作为 Harbor 领域枚举使用；它属于 [后备/P2 Runner 协议](./RUNNER_PROTOCOL.md) 的独立边界，不能因为名称相近就视为同一个字段。本次只纠正文档指针，不修改 Runner 协议或代码。

不能只看上游 exit 0：Aider/Codex/Claude 都可能正常结束但没有修好；也不能因为测试失败就把 Adapter 运行标成平台失败。

## 13. 接入验证顺序

每类 Agent 按同样四层推进，但进入开发的先后固定：

1. **官方接口/源码核验**：读取固定版本的真实入口、参数与输出定义。
2. **Adapter 契约测试**：用 Fake executable 验证参数、事件、退出、超时、patch 和脱敏，不消耗模型额度。
3. **真实 CLI 小仓库测试**：固定版本和真实凭据，在极小仓库完成一次修改。
4. **SWE-Gym E2E**：一条固定任务，保存 Runner 证据并由固定 SWE-Bench-Fork 判卷。

实现顺序为：Mock 只验证内部状态/错误分支 → M0 本机脚本用 Harbor 固定提交 + 真实 Codex 跑通单题 → M1 加入 Web/数据库/所有者批准形成 Codex 平台 MVP → Aider → Claude Code → P2 自研 Agent。Mock 和 M0 都不产生正式排行证据；P2 未定不阻塞 MVP。

## 14. 升级维护清单

升级任一框架/CLI 时必须在同一个行动文档中：

1. 记录旧/新精确版本和升级理由；
2. 查阅官方 changelog、CLI help 或源码；
3. 更新本文件的真实参数/事件/限制；
4. 保存新版 `--version` 和 `--help` 证据（秘密脱敏）；
5. 运行 Adapter 契约测试；
6. 至少运行小仓库冒烟测试，影响 Harness 时再跑 gold patch 与 E2E；
7. 只有证据通过后，才启用新的 Agent Configuration；历史成绩保留旧版本身份。

## 15. 当前未解决接口问题

当前固定单题、补丁出口和真实 Codex → 固定 Fork 核心链路已通过；未解决项不再包括“真实入口尚未接通”。完整验收对账统一见 [Harbor 执行接口](./HARBOR_EXECUTION.md#暂停后的验收对账2026-09-08)，`--check-network` 仍只代表内核前提。

1. 扩展任务来源时补齐第 4.1 节的输入类型兼容；当前固定 Parquet 单题可用不代表全题库适配完成。
2. M0 完整制品限制、网络及异常路径的覆盖差距，见 Harbor 验收对账；不自动把所有未验收项判作 M0 阻塞。
3. 当前诊断的旧 `pending` 提示仍待代码同步；诊断不授予真实运行许可，具体位置见 Harbor 验收对账。
4. Token 刷新与完整凭据生命周期仍有缺口；既有私有输出阶段例外和待验证部分见[认证接口](./CODEX_AUTHENTICATION.md#62-2026-09-07-假凭据安全收尾)，不自动新增清洗工程。
5. Aider 仓库内 `.aider.conf.yml`/`.env` 的彻底隔离方式。
6. Claude Code `--restricted` 与评测所需工具组合、账号/费用/网络策略。
7. P2 `agent-exam.yaml` 的完整 schema、Python 版本、依赖锁格式，以及平台怎样把已确认进程 Interface 包装进 Harbor；不再待选 Harbor `BaseAgent` 或进程协议，且不阻塞 MVP。
8. P2 DeepSeek/Kimi 的精确模型/外部接口、受控访问部署和 Docker 网络防绕过；不得把“架构已确认”写成真实调用已通过。

## 16. 变更记录

- 2026-09-02：把依赖来源、固定版本、获取与入库策略迁移到 `DEPENDENCIES.md` 唯一维护；公开证据改用固定提交的 GitHub permalink，避免 `framework/` 不入库后链接失效。
- 2026-09-01：创建；核验固定 SWE-Gym/SWE-Bench-Fork 源码、Codex 官方非交互接口，并汇总 Aider/Claude Code 官方研究；定义四类 Adapter 映射、能力差异、错误映射和分层验证。
- 2026-09-03：加入固定 Harbor 的真实 Job/Trial/Verifier/Artifact 接口入口；确认 Harbor 为主 Execution Backend，直接 CLI 映射降为后备，运行状态仍保持待原型。
- 2026-09-04：确认首个真实原型使用 `SWE-Gym/SWE-Gym-Lite` 的 1～3 道任务；其 revision、split 和具体实例仍待真实元数据核验。
- 2026-09-04：确认首个真实原型 Agent 为 Harbor 内置 Codex；认证政策采用评测机所有者的 ChatGPT Pro `auth.json`，容器 CLI、模型、Token 生命周期和网络能力仍待实测。
- 2026-09-04：在新路径复测宿主 `codex --version` 与 `codex exec --help` 均成功；记录本机 `codex-cli 0.142.0`，但不将其自动固定为项目版本，也不据此宣称 Harbor 容器 E2E 通过。
- 2026-09-05：确认首版自研 Agent 只支持 Python stdin JSON → stdout patch 进程 Interface，由平台包装进 Harbor；模型提供方限 DeepSeek/Kimi，真实 Key 不进入被测进程，具体外部接口和隔离待实测。
- 2026-09-05：固定 M0 Codex 本机脚本→M1 Codex 平台 MVP→Aider/Claude Code→P2 自研 Agent 的验证顺序；过程指标改为只展示，并补充任务原始快照与无效 patch 映射。
- 2026-09-06：记录真实 Harbor NOP Docker Trial、项目结果映射和生产有界执行器通过，以及 Job 根结果不落盘 `trial_results`、UTF-8 CLI、单目录 artifact、显式日志截断和宿主进程树清理的实际接口事实。
