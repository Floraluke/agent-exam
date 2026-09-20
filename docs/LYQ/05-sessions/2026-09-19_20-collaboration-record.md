# 协作记录：接手 C 模块到任务 04 任务单草案

> 记录期间：2026-09-19 ~ 2026-09-20
> 记录人：LYQ（成员 C）
> 记录内容：与 AI 助手协作的全过程——问了什么、查到什么事实、做了什么改动、结论是什么
> 用途：让过程可追溯，便于向组长或评审说明；也便于自己回看
> 权威边界：本文件是**过程记录**，业务规则、接口、字段与表结构仍以 `docs/architecture/`、`docs/interfaces/` 的权威文档为准

## 1. 起点

最初收到的材料有两份：一份是方向 21 的立项条目（多角色 Agent 协作平台），另一份是「AI coding Agent 评测平台架构讨论」的录音总结。与本仓库对应的是后者——仓库里的 `.scratch/ui-catalog-providers/` 计划、SWE-Gym 题库、固定 Fork 判卷、Harbor 执行链都能和录音内容对上。

接手时的身份与范围：

| 项目 | 内容 |
|---|---|
| 角色 | 五人分工中的成员 C |
| 长期负责 Module | 目录与配置（Task Catalog 题目目录 + Agent Registry 配置目录） |
| 当前任务 DRI | 任务 04 五道新题入库与 1–20 连续规模 |
| 参与任务 | 03 目录动线、05–07 提供方受控配置、08 冻结目录回归 |
| 工时基线 | 54 h |

接手时我手上的材料是组长发的三份：团队分工文档、扩展计划目录、Navicat 连接教程。

## 2. 时间线

### 2.1 2026-09-19 读材料、弄清范围

**问的问题**：我是 C，我要做什么。

**查到的事实**（都是读代码和权威文档得到的，不是推测）：

- 模块职责：把服务端写死的可信预设，变成数据库里可审计的目录记录；不接受用户给的数据 URL、镜像、模型地址、命令或 Key；不执行 Agent、不判卷、不创建 Job。
- 两个 Interface：`TaskCatalog.register/get/list`、`AgentRegistry.register/get/list/disable`；三个可替换接缝：`TaskSource`、`TaskRepository`、`ArtifactStore`。
- 任务 04 的两半：**题库**（五道 mypy 候选逐题过参考/空/错误三种补丁的门禁，通过才进白名单）与**规模**（新增连续 1–20 题、最多 3 配置、上限 60 次 Run）。
- 机制现状：`TASK_PRESETS` 只有一道题 `swe-gym-lite-mypy-15413`；`AGENT_PRESETS` 只有一个配置 `codex-0153-terra-medium`；`SubmissionPolicy` 已有 `maximum_agent_configurations=3` 与 `maximum_runs=60`，缺的是"连续 1–20"这一档 `BatchPreset`（当时只有 `demo` 1–3、`quick` 恰好 5、`standard` 10–20，所以 4 道或 6 道题的请求会被拒）。
- 本机不具备任务 04 的真实运行条件：无 `framework/`、`runtime/`、`infra/data/`、`infra/volumes/`，无固定 Parquet 数据快照，Docker Desktop 未运行。

**产出**：任务 04 的行动文档（含目录层、规模层、判卷层、浏览器层四组测试设计）。

### 2.2 2026-09-20 发现仓库对象搞错，改为 fork 工作流

**发现的问题**：我最初工作的 `Floraluke/agent-exam` 是**个人 fork**，团队上游仓库是 `anphuchoang5-sys/agent-exam`；fork 的 `main` 落后上游 **21 个提交**，是纯快照。队友的分支（`fengyy-fixweb`、`lly/dev`、`xinyue-modules`）都建在上游。

**做的改动**：

1. 接入 `upstream` remote 并 fetch，把工作 rebase 到上游 `main`。
2. 参照成员 E 已建立的 `docs/LLY/` 约定，建立个人文档目录 `docs/LYQ/`（README + 01-plan + 02-module + 03-progress + 04-issues）。
3. **按组长要求改为 fork 工作流**：代码推个人 fork、PR 从 fork 提到上游、不直接操作上游仓库。据此收回了最初直接推到上游的 `lyq` 分支（关闭上游侧 PR、删除上游侧分支），本地分支跟踪目标改回 `origin/lyq`。

### 2.3 2026-09-20 发现任务 04 的"规模"半已由 D 完成

**核实过程**：同步上游时看到 `docs/actions/2026-09-20-d-continuous-scale-and-rehearsal.md`，逐项核对代码后确认：

- `apps/backend/src/eval_platform/delivery/job_presets.py` 已有 `BatchPreset("continuous", 1, 20)`，既有 `demo`/`quick`/`standard` 区间未改。
- 配套测试 `apps/backend/tests/jobs/scale/test_continuous_preset.py`、`tests/jobs/reporting/test_matrix_rehearsal.py` 已存在。
- 以上**已合入上游 `main`**。

**结论**：我按分工本应负责的"规模版本"部分已由 D 按其 04/08 的 D 侧交付完成。我的任务 04 范围收窄为**题库那一半**。记为 [ISSUE-05](../04-issues/KNOWN_ISSUES.md)。

### 2.4 2026-09-20 数据库连接排查（结论：不在我这边，暂搁置）

现象是 Navicat 连不上共享库，报错从"连接超时"变成"找不到主机名"。逐项排除后定位到问题不在本机。详细过程见第 4 节。

### 2.5 2026-09-20 看最新仓库，起草任务 04 任务单

**查到的最新状态**：

- 任务 **01、02 已完成**：计划文档已更新，`issues/01`、`issues/02` 已发布，B 的 Web 工作台（`ff46cec feat(web): add API-backed role workbench`）已合并进 `main`。
- 任务 **03、04 仍未发布任务单**；有人在推进 03 方向的部分工作（对比报告、报告语义设计）。
- **没有任何人给 C 留活**；个人 PR 尚无评论与审阅。
- 按项目规则「任务未发布、未安排时不提前修改后续任务代码」，我当时没有可开工的正式任务。

**产出**：起草 `.scratch/ui-catalog-providers/issues/04-five-new-tasks-and-continuous-scale.md`，按已发布的 01、02 任务单格式（What to build / Blocked by / Spec stories / 验收清单 / Comments），状态 `needs-info`，Comments 里写明由 C 起草、等待发布与授权，并如实记录 D 已完成规模部分。

## 3. 关键结论汇总

| 问题 | 结论 |
|---|---|
| 我是谁、负责什么 | 成员 C；目录与配置 Module；任务 04 任务 DRI；工时 54 h |
| 任务 04 现在要做什么 | **题库那半**（五道 mypy 候选过门禁后进白名单）；规模那半已由 D 完成 |
| 任务 04 能不能开工 | 不能。任务单未发布，且缺固定数据/镜像下载授权与 Fork 判卷安排 |
| 代码往哪推 | 个人 fork `Floraluke/agent-exam` 的 `lyq` 分支；PR 从 fork 提到上游 `main` |
| 文档放哪 | 个人目录 `docs/LYQ/`；权威事实仍在 `docs/architecture/`、`docs/interfaces/` |
| 数据库为什么连不上 | 不在本机侧：本机 Tailscale 在正确的 tailnet 内且设备在线，但看不到其他设备（见第 4 节） |
| 仓库文档是否与组长版本一致 | 现已一致：01、02 标注完成、issues/01、02 已发布（此前的差异已消除） |

## 4. 数据库连接排查记录

现象与逐项证据：

| 检查项 | 结果 | 含义 |
|---|---|---|
| Navicat 第一次：`10.62.158.77:55432` | 连接超时 | 主机与端口都不在教程要求内 |
| 教程要求 | `sss.tail03c757.ts.net:15432`，初始库 `agentexam`，用户 `agentexam_admin` | 端口 `55432` 是 owner 本机回环端口，外部不可达 |
| Navicat 第二次：主机与端口修正后 | 找不到主机名 | 变成名字解析问题 |
| 本机 Tailscale 连接状态 | `Running`、设备在线、密钥有效期 2027-03-18 | 本机客户端本身正常 |
| 本机 Tailscale 可见设备数 | **0**（`tailscale status` peer 为 0，网络地图里的用户只有自己） | 看不到 owner 的设备 |
| `tailscale ping 100.101.148.2`（owner 的 Tailscale 地址） | `no matching peer` | 该设备不在本机网络视图内 |
| 用 Tailscale 自带解析器查两个名字 | 自己的设备名解析成功；`sss.tail03c757.ts.net` 查不到 | MagicDNS 正常，是对方设备不在视图内 |
| 本机虚拟网卡 | Tailscale 网卡 `Up` | 不是队友 E 遇到的"虚拟网卡装不上"问题 |

**结论**：本机侧没有可修的东西。需要 owner 侧确认设备是否在线、加入方式（邀请成员还是分享设备），以及本机登录身份（`Floraluke@github`）是否与邀请对象一致。已按此整理成给 owner 的排查请求。

**处理**：暂搁置，不阻塞任务 04 的准备工作（任务 04 的验证不在本机做）。

## 5. 本次产生的仓库改动

分支 `lyq`（fork → 上游 PR #2），提交：

| 提交 | 内容 |
|---|---|
| `docs: add task 04 action document for catalog candidates and scale` | 任务 04 行动文档：范围、上游门禁、计划文件树、验证方式 |
| `docs: add task 04 test design to the action document` | 四组测试设计（目录层、规模层、判卷层、浏览器层） |
| `docs: add LYQ personal module folder for catalog and configuration` | 个人文档目录 `docs/LYQ/`（按 `docs/LLY/` 约定） |
| `docs(lyq): add daily git workflow notes to the personal folder readme` | 日常 git 操作说明 |
| `docs(lyq): switch documented workflow to fork-based pull requests` | 协作方式改为 fork 工作流 |
| `docs(lyq): record that member D already implemented the continuous scale preset` | 记录 D 已完成规模部分，改正过期结论 |
| `docs: draft task 04 issue for five new tasks and continuous scale` | 任务 04 任务单草案 |

文件结构：

```text
docs/LYQ/
├─ README.md                       # 目录说明 + 权威边界表 + 当前状态 + 日常 git 操作
├─ 01-plan/PLAN.md                 # 我负责范围的计划书：范围、硬约束、分工边界
├─ 02-module/                      # 我负责模块的个人视图（正文仍在权威文档）
│  ├─ MODULE_ARCHITECTURE.md       #   职责、两个 Interface、三个接缝、数据流
│  ├─ CONTRACTS.md                 #   输入输出契约：收什么、返什么、什么情况报错
│  └─ INTERFACES.md                #   7 个 HTTP 端点 + 模块内部 Interface 调用形状
├─ 03-progress/PROGRESS_LOG.md     # 进度日志，按日期倒序
├─ 04-issues/KNOWN_ISSUES.md       # 5 条问题记录（含 Tailscale、文档差异、范围边界）
└─ 05-sessions/                    # 本文件所在的协作记录目录
docs/actions/2026-09-19-task-04-catalog-candidates-and-scale.md   # 任务 04 行动文档
.scratch/ui-catalog-providers/issues/04-five-new-tasks-and-continuous-scale.md  # 04 任务单草案
```

## 6. 当前阻塞与下一步

| 阻塞项 | 归属 | 状态 |
|---|---|---|
| 任务 04 任务单未发布 | 项目负责人 | 已提交草案，等待发布 |
| 固定数据集获取方式未定 | 项目负责人 | 待确认 |
| 五道候选题的镜像下载授权与磁盘配额 | 项目负责人 | 待授权 |
| Fork 判卷的执行安排 | E 主责，我组织交接 | 待约时间 |
| 共享库连接 | owner 侧 | 暂搁置，不阻塞任务 04 准备工作 |

**下一步动作**：

1. 把任务 04 任务单草案提交给项目负责人审阅发布，并说明申请现在开工的三条理由（01、02 已完成；计划第 6 节写明 04 技术上不依赖 03 的 UI；04 是唯一不调用模型、不需要真实 Key 的任务）。
2. 与 E 约定参考/空/错误补丁的 Fork 资格验证时间。
3. 等待授权期间：读 D 的行动文档，学习真实 PostgreSQL 回归与矩阵演练的执行方式；细化任务 04 的实现方案与测试分层，但不提前修改产品代码。
4. 拿到授权后开工，第一步锁定当时的 HEAD 基线并更新行动文档。
