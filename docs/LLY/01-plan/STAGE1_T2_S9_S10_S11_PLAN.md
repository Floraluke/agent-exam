# 阶段 1（05）跨机执行计划：T2 → S9 → S10 → S11

> **状态：计划（未开工）。** 本文把**负责人 A 的电脑**当作**同一人的第二台开发机**（下称 **A 机**），本机（`D:\agent-exam`）负责核对与收口。本文不构成真实模型调用授权。
>
> 权威边界：拓扑与断言的判定标准见[组长机器预案附三/附四](../../actions/2026-09-21-task05-owner-machine-runbook.md)；安全合同数值见[设计冻结底稿](STAGE1_PROXY_DESIGN_FREEZE.md)；分片与历史状态见[阶段 1 实施方案](STAGE1_IMPLEMENTATION_PLAN.md)；步骤与验收见[执行计划第 7 节](../../../.scratch/ui-catalog-providers/plan.md)。本文只编排顺序、分工与回传物，不复制其正文。
>
> 维护人：LLY（成员 E）　日期：2026-09-22

## 1. 两台机器与现状

| 项 | 本机 | 负责人机器（负责人 A 的电脑） |
|---|---|---|
| 仓库根 | `D:\agent-exam`（分支 `lly/dev`） | 记录为 `E:\9.1agent_exam`；**已有 worktree 在 `runtime\lly-dev-verify`，对应 `lly/dev`**——先用 `git worktree list` 确认，实际路径以那台机器的输出为准 |
| `framework/harbor`、`framework/swe-bench-fork` | ❌ 无（`.gitignore` 排除） | ✅ 有（固定 revision `6af8d6e3…`，**不重建**） |
| Docker 守护进程 | ❌ 未运行（仅装了 Desktop） | ✅ 可响应 |
| 能跑的事 | 策略/契约/生命周期层的替身测试、静态检查、文档与计划、核对 | 固定 Harbor 集成、真实容器与网络、含 `framework/harbor` 的全量回归（ISSUE-04 那两项在那里才会通过） |
| 不能做的事 | 不能跑 T2、S11 | 不能读真 Key、不能发起真实供应商请求、不充值 |

**两机共享的分支与推送口径**：两边都提交到 `lly/dev`，推送到 `origin/lly/dev`；片级验收后开 PR 合入 `main`，本机再拉下来核对。提交只含本片明确涉及的文件，不 `git add .`。

**全程硬边界（越界即停，不要继续）**：不重建/拉取 `framework/harbor`；不停止或删除既有持久化服务；只按**名称 + 任务标签 + 本轮 scope 标签**三重匹配删除资源，**禁止全局 prune**；不删其他项目/其他成员的卷与拉取的固定镜像（`down --rmi local` 只清本轮构建的侧车镜像）；不读真 Key、不发起真实供应商请求、不充值、不放宽到公网、不把真 Key 放进做题容器；不改共享 Docker/WSL/全局代理/防火墙。

## 2. 分片总表

顺序固定 **T2 → S9 → S10 → S11**。T2 未测得（或测得"不成立"）之前，S10/S11 不开工；S9 的**绑定接法**由 T2 的结论决定。

| 片 | 一句话目标 | 实施 | 验证 | 关键停止条件 |
|---|---|---|---|---|
| **T2** | 在固定 Harbor 上把七条拓扑断言真正测到 | A 机（探针） | A 机 | 侧车仍起不来 / 断言不成立 → 停在本任务，不带真 Key |
| **S9** | worker 按 Run 选绑定，不再无条件要求 ChatGPT 认证 | 任一台（建议 A 机，便于直接跑全量） | 本机单测 + A 机全量 | 未知身份对必须失败关闭；ChatGPT 旧路径不得退化 |
| **S10** | 把 T2 的最小形态产品化：run 级拓扑合成与网络接线 | A 机为主 | 本机替身单测 + A 机合成链 | 代理形态无法落实 → 停在 S10，不进入真实 Key |
| **S11** | 集成层五组对照与收口（含两条挂账项） | A 机 | A 机 | 任一对照不成立 → 如实回报，不调低断言 |

## 3. T2：固定 Harbor 上的双网络最小实证

**目标**：回答"整套双网络拓扑在固定 Harbor 上是否成立"，并把七条断言**测到**（首轮停在工具链失败：侧车入口 ENOENT、退出 127、七条断言一条未测）。

### 3.1 开工前（A 机，只读，不创建任何资源）

```bash
# 0) 先确认 worktree 与分支
git worktree list
git -C <worktree> status -sb && git -C <worktree> log --oneline -1

# 1) 诊断：侧车入口的行尾（决定 127 的机制是否成立）
git -C framework/harbor ls-files --eol src/harbor/environments/docker/harbor-docker-egress-control-sidecar/
#    entrypoint.sh 或 bin/network-policy 显示 w/crlf ⇒ 构建上下文带 CRLF，shebang 失效 ⇒ 符合 127
```

两条都照实抄进回报；若显示 `w/lf`，说明 127 另有原因（此时**先停**，把 `docker save` 解层后的入口原文取回来再定，不要盲跑）。

### 3.2 实施：探针必须显式携带侧车适配

**不要走产品入口**：`harbor_entry.validate_network_config` 把 `extra_docker_compose`（及 `kwargs`/`import_path`/`env`/`mounts`）判为非法（`harbor_entry.py:136-143` → `HARBOR_NETWORK_CONFIG_INVALID`），而最小形态必须用它声明网络与两个服务；该门禁有测试钉住（`tests/contract/test_execution_network.py:190-198`），是生产安全约束，**不为试验放宽**。

在探针里加两行（照抄 `tests/codex_trial_probe.py:36-38`）：

```python
context = <trial 目录> / "sidecar-source"
export_sidecar(<仓库>/framework/harbor, context, "6af8d6e31eced13b93849cdf80feeadf24603d15")
DockerEnvironment._EGRESS_CONTROL_SIDECAR_CONTEXT_PATH = context
```

**拓扑**（附三的最小形态，不变）：`extra_docker_compose` 给 `services.main` 声明 `internal`（`internal: true`）与 `egress` 两条网络；另起受控的 `proxy`（接 `internal`+`egress`）与 `fake-upstream`（接 `egress`）；做题侧（`main`）只接 `internal`。不接 Codex CLI、不接真实模型。

**断言作为该次 Trial 的命令**（脚本随仓库走，新增于 `apps/backend/tests/providers/runtime/t2-assertions.sh`）：

```bash
T05_PROXY_HOST=proxy T05_PROXY_PORT=8080 \
T05_UPSTREAM_HOST=fake-upstream T05_UPSTREAM_PORT=8080 \
bash apps/backend/tests/providers/runtime/t2-assertions.sh    # 期望 status=verified
```

**宿主侧另取的读数**（需要 Docker API，做题容器内取不到）：发布端口、宿主挂载、私有文件可见性、镜像/卷清单前后差异、清理复核。

**预期差异**：携带适配后侧车镜像内容哈希会变、重建一次，拆除时 `--rmi local` 清掉——前后清单出现"一处新增 + 一处移除"属**预期**，照实记录。

### 3.3 必须回传的验收文件（T2）

| 文件 | 内容要求 |
|---|---|
| `docs/actions/<日期>-task05-t2-verified.md` | ① worktree 与提交号；② 两条只读诊断命令的**原始输出**；③ 探针与 compose 的完整命令/清单；④ Trial 的命令与其**原始 stdout**（含 `status=` 行；若失败，含逐条 `FAIL`）；⑤ 宿主侧 inspect 摘录（网络 `Internal`、发布端口、挂载、标签）；⑥ 镜像/卷清单差异与清理复核（残留应为 0）；⑦ 未验证项与失败项如实列出 |
| `.tmp/.../manifest.json`（A 机本地，**不进 Git**） | 原始证据文件的路径清单 + **每个文件的 SHA-256**，供本机抽检；正文摘录抄进上面那份行动文档 |
| 进度日志与任务单更新 | `docs/LLY/03-progress/PROGRESS_LOG.md` 追加当日事实；任务 05 任务单 `## Comments` 追加一条（含结论与提交号） |

### 3.4 停止条件

- 侧车仍起不来（无论何种原因）→ 先把原始日志与入口原文取回，**不为让它起来而改侧车/放宽策略**；T2 维持"未测得"。
- 七条断言任一不成立 → 按[执行计划第 7 节](../../../.scratch/ui-catalog-providers/plan.md)停在本任务，**不进入 06/07**；如实回报，不改判定标准。

## 4. S9：worker 按 Run 选绑定

**现状（已核实）**：`delivery/worker/runtime.py:66` 无条件 `validate_auth_file(config.codex_auth_path)`；`:26` 的 `MODEL_HOSTS = ("auth.openai.com", "chatgpt.com")` 写死；`:80-87` 只构造**一个** `HarborExecutionAdapter` 并把 `codex_archive`/`codex_auth_path` 一起传进去。即"跑任何 Run 都要求 ChatGPT 认证"。

**目标**：绑定按**该 Run 的 `AgentConfiguration`** 选择——`model_provider` + `authentication_type` + `credential_configuration_id`（`domain/agent.py` 的 `CONTROLLED_IDENTITIES` 是唯一权威清单）。受控假提供方那条走代理绑定（不读 ChatGPT auth），ChatGPT 那条**行为逐字不变**。未知身份对、缺绑定、绑定与身份不符一律**失败关闭**，不得静默回落到 ChatGPT。

**实施要点**：
1. 新增选择模块（建议 `delivery/worker/bindings.py`）：把"身份对 → 绑定描述（网络主机集合、是否需要 codex archive/auth、代理入口与令牌来源）"集中一处；`runtime.py` 只调用它。
2. `create_runtime_worker` 不再无条件 `validate_auth_file`；改为按**即将执行的那条 Run** 取绑定（worker 的 claim 已经带 `AgentConfiguration`，不需要新接口）。
3. 指标约束：`delivery/worker/runtime.py` 现 161 行，改后仍须 ≤200；`delivery/worker/` 现 3 个 `.py`，新增 1 个后 4 个（上限 8）。
4. 测试放 `apps/backend/tests/jobs/runtime/`（现 4 个文件，有余量）：至少覆盖——受控身份不需要 ChatGPT auth；ChatGPT 身份行为不变；未知身份对失败关闭；绑定与身份不符失败关闭。**每条都要做区分力实测**（改实现→失败→还原→通过），并把结果写进行动文档。

**验证**：本机可跑（`pytest tests/jobs/runtime`、默认回归、`ruff`/`mypy`）；A 机跑**含 `framework/harbor` 的全量**（那里 ISSUE-04 那两项应通过）与 PG 开关全量。

**回传文件**：`docs/actions/<日期>-task05-s9-run-bindings.md`（含改动文件树、逐条区分力实测、本机与 A 机两套实测数字、未验证项）+ 代码与测试提交 + 进度日志/任务单更新。

**停止条件**：无法在不退化 ChatGPT 路径的前提下完成选择 → 停并汇报，不允许"临时特例"。

## 5. S10：`net/` 与网络接线（按 T2 结论）

**目标**：把 T2 验证过的形态**产品化**——run 级网络拓扑合成、代理进程随 Run 起停、把 `config.toml` 与短期令牌注入做题侧。T2 的结论决定这里的具体形态（是否需要 `net/`、代理是容器还是进程、网络如何附加）。

**实施要点**：
1. 新增 `adapters/execution/provider_access/net/` 子目录（**顶层已经 8 个 `.py`，达每层上限**，禁止新增顶层文件；`server/` 也已 8 个）。`net/` 内建议 2–3 个文件：拓扑合成、预检（复用 `network.validate_hosts`/`compose_profile`）、启动与收束。
2. 接线：`HarborExecutionAdapter`/worker 侧在启用代理绑定的 Run 上——渲染 `config.toml`（`codex/provider_config.py`，S2 已实现且**当前零调用方**）→ 写入 `CodexUploads.TARGETS` 里既有的 `/tmp/codex-home/config.toml` 目标位 → 注入短期令牌（只进代理私有内存与做题侧的短命令牌来源，**不进 argv/env/日志/制品**）。
3. 失败关闭：拓扑无法合成、代理未就绪、令牌缺失一律**拒绝出站**，给受控失败码（`provider_access/failures.py` 的映射表，含 `PROVIDER_UPSTREAM_FAILED`）。
4. 收口：Run 结束回收代理、令牌与专属网络资源；崩溃后只按已持久化证据收束，不自动续跑。

**验证**：本机跑替身单测（拓扑合成、失败关闭、令牌生命周期、`config.toml` 内容不含凭据）；A 机跑**一 Run 的合成链**：正式 Registry → 提交 → 批准 → Worker → Harbor，用受控假提供方（**不是**真 Key），证据取"假上游自己的请求记录 + 该 Run 的终态"。

**回传文件**：`docs/actions/<日期>-task05-s10-network-wiring.md`（含拓扑图、实际命令行、Run 终态与假上游请求记录原文、失败关闭用例的区分力实测、清理复核）+ 代码与测试提交。

**停止条件**：拓扑无法落实，或做不到"未批准/缺令牌仍能出站"的反例证明失败关闭 → 停在 S10，不带真 Key。

## 6. S11：集成层验证与收口

**目标**：在真实隔离环境里跑五组正反对照并收口两条挂账项。

**实施要点**：
1. 入口：`apps/backend/tests/providers/runtime/verify.ps1` + `Dockerfile.proxy`（该目录现 6 个文件，加这两个正好 8，达上限；如需再加须建子目录）。
2. 五组对照（与附三一致）：拓扑（做题侧只通代理）、直连拒绝（做题侧直连上游/宿主/metadata/其他 Trial 不通）、宿主隔离（无发布端口、无 Docker 套接字、无可写宿主挂载）、假 Key 探查（私有文件在做题侧与公开输出零命中，含正对照）、**精确清理**（按三重标签复核残留为 0）。
3. 两条挂账项：
   - 用真实上游复核 `accept-encoding` 转发后的**流压缩与用量结算**（main 把 `accept-encoding` 归入转发集合；若上游压缩 SSE，终止事件扫描会按未知用量结算——失败关闭、绝不少计费但会多计费并提前关闭该 Run）；
   - 把 `codex/provider_config.py:62-72` 的裸 `ValueError("PROVIDER_CONFIG_*")` 收口为**受控失败**（当前零调用方，接线后才会暴露）。
4. 秘密外表面复扫：对外文案、进程 stdout/stderr、env 与 argv、运行目录落盘文件，全部零哨兵命中。

**回传文件**：`docs/actions/<日期>-task05-s11-integration.md`（五组对照逐条的原始输出、清理复核、两条挂账项的处理与证据、未验证项）+ 代码与测试提交。

**停止条件**：任一对照不成立 → 如实回报并按第 2 节风险行处理，**不调低断言、不改判定标准**。

## 7. 两机协作流程

### 7.1 A 机（worktree）日常

```bash
git -C <主仓库> fetch origin                      # 主仓库拉取，worktree 共享对象库
git -C <worktree> switch lly/dev && git -C <worktree> pull --ff-only
git -C <worktree> status -sb                      # 开始前必须干净
```

- 改动只落在本片涉及的文件；提交信息用仓库既有风格（`fix(...)`/`feat(...)`/`test(...)`/`docs(...)` + 英文正文说明"为什么"）。
- 每片完成即 `git push origin lly/dev`（或先本地提交、由同一侧统一推——**同一时间只由一台机器推送**，避免非快进冲突）。

### 7.2 合入主分支

1. 在 `origin/lly/dev` 上开 PR：`lly/dev → main`，标题写明片号与结论，正文附"改了哪些文件 + 实测数字 + 未验证项 + 回传的行动文档链接"。
2. PR 合并后，`main` 前进；本机拉取核对（下一节）。
3. **若 T2 结论是"不成立"**：不合并实现代码，只合并"如实回报"的那份行动文档与状态更新。

### 7.3 本机核对清单（合并后逐条做）

```bash
git fetch origin && git switch lly/dev && git merge origin/main
cd apps/backend
.venv/Scripts/python.exe -m ruff check
.venv/Scripts/python.exe -m ruff format --check
MYPYPATH=src .venv/Scripts/python.exe -m mypy src/eval_platform
.venv/Scripts/python.exe -m pytest -q -p no:cacheprovider
.venv/Scripts/python.exe -m pytest tests/providers tests/jobs/runtime -q -p no:cacheprovider
```

- [ ] 两套实测数字与 A 机的回报**逐项对上**（本机的 2 项 ISSUE-04 失败仍是那两项——本机没有 `framework/harbor`，这是预期）。
- [ ] 抽检 A 机的证据：按其 `manifest.json` 的 SHA-256 校验 1–2 个原始文件；正文摘录与原始输出一致。
- [ ] 抽检合并进代码的**区分力实测**：随手挑一条断言，把实现改回旧行为确认用例真的失败，再还原。
- [ ] 无新增数据库表、无第二执行接口、无新增顶层目录/模块（`provider_access/net/`、`delivery/worker/bindings.py` 之外）。
- [ ] 指标：单文件 ≤200 行、每层 ≤8 文件（`provider_access/` 顶层已 8、`server/` 已 8、`tests/providers/runtime/` 将达 8——越界需在行动文档说明理由并取得确认）。
- [ ] 文档齐平：进度日志、任务单 Comments、受影响的权威文档（若 S10 改变运行要求，需给 A 的部署输入）；`docs/LLY/` 不出现与代码矛盾的状态。
- [ ] 秘密零命中复扫（对外文案、日志、制品）。

### 7.4 冲突与回退

- 同一文件被两台机器同时改：**由后到者 rebase/merge 并手工合并**，保留双方条目（文档类）；代码类以 A 机（有新证据的一侧）为准并在行动文档说明。
- 回退：每片是一个或多个独立提交，`git revert <片的首末提交>` 即可回退，不动其他片。
- 推送冲突（非快进）：先 `fetch` 再 `rebase`，**不要** `push -f`。

## 8. 汇总：每片必须交回的验收文件

| 片 | 行动文档（进 Git） | 原始证据（不进 Git） | 代码/测试 | 其他 |
|---|---|---|---|---|
| T2 | `docs/actions/<日期>-task05-t2-verified.md` | `.tmp/...` + SHA-256 清单 | 探针改动（如需） | 进度日志、任务单 Comments |
| S9 | `docs/actions/<日期>-task05-s9-run-bindings.md` | — | `delivery/worker/bindings.py` + 用例 | 同上 |
| S10 | `docs/actions/<日期>-task05-s10-network-wiring.md` | 假上游请求记录原文 | `provider_access/net/` + 接线 + 用例 | 必要时给 A 的部署输入 |
| S11 | `docs/actions/<日期>-task05-s11-integration.md` | 五组对照原始输出 | `verify.ps1` + `Dockerfile.proxy` + 用例 | 同上 |

**每份行动文档的最低要求**（沿用 `action-document` 技能）：情况说明、实施措施、**实际**改动文件树、自验证方式、自验证情况（**命令 + 实际输出**）、未验证项与限制、失败如实记录。**"未运行"不得写成"通过"**。

## 9. 风险与已知未知

| 风险 | 影响 | 处理 |
|---|---|---|
| T2 侧车仍起不来 | 拓扑无法在固定 Harbor 上成立 | 先取原始日志与入口原文；不为让它起来而改侧车或放宽策略；维持"未测得"并停下汇报 |
| 携带适配后镜像重建 | 前后清单出现增删 | 已在 附四 说明属预期，照实记录 |
| S9 改动触及 worker 组合 | 可能影响真实运行 | ChatGPT 路径行为必须逐字不变，并用回归与全量证明 |
| S10 与 A 机现有 Harbor 组合的耦合 | 形态取决于 T2 结论 | T2 出结论前不开工；先写替身单测再接线 |
| 两机同时改同一文件 | 冲突/覆盖 | 约定同一时间只由一台机器推送；提交粒度按片 |
| 本机无法复现 A 机的集成证据 | 只能抽检 | 用 SHA-256 清单 + 正文摘录抽检；必要时要求补一次最小复现命令 |

## 10. 权威来源

| 内容 | 位置 |
|---|---|
| 拓扑步骤、授权边界、回报要求 | [组长机器预案附三/附四](../../actions/2026-09-21-task05-owner-machine-runbook.md) |
| 分片、文件树、机器归属、逐片验证 | [阶段 1 实施方案](STAGE1_IMPLEMENTATION_PLAN.md) |
| 测试归属与断言 | [阶段 1 测试设计](STAGE1_PROXY_TEST_DESIGN.md) |
| 已确认数值与剩余边界 | [设计冻结底稿](STAGE1_PROXY_DESIGN_FREEZE.md) |
| 步骤、验收、停止条件 | [执行计划第 7 节](../../../.scratch/ui-catalog-providers/plan.md) |
| 失败码与受控文案 | [HTTP 接口第 10.2 节](../../interfaces/HTTP_API.md) |
| 秘密与强制安全约束 | [认证接口第 4.1、5 节](../../interfaces/CODEX_AUTHENTICATION.md) |

本文只编排顺序、分工与回传物，**不替代**上述文件，也不构成开工或执行授权。
