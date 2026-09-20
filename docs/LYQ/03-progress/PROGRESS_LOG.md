# 开发进度日志

> 只记录事实与实际结果：做了什么、实际输出是什么、遇到什么。计划见 [`01-plan/PLAN.md`](../01-plan/PLAN.md)。
> 格式：按日期倒序追加，最新在最上面。

## 2026-09-20

### 已完成

- 确认仓库关系：`Floraluke/agent-exam` 是**个人 fork**，团队上游仓库是 `anphuchoang5-sys/agent-exam`。接入 `upstream` remote 并 fetch；上游 `main` 比我 fork 的 `main` 领先 **21 个提交**，且 fork 没有上游缺的提交（fork 是纯快照）。
- 上游现有分支：`main`、`fengyy-fixweb`（冯颖怡）、`lly/dev`（成员 E）、`xinyue-modules`。上游当前 **0 个 PR**。
- 把我个人的两个提交 rebase 到 `upstream/main`（`a49b000`）。rebase 干净，无冲突。
- 建立个人分支 `lyq`（基于 `upstream/main`）与个人文档目录 `docs/LYQ/`，结构参照成员 E 的 `docs/LLY/` 约定（README + 01-plan + 03-progress + 04-issues，另按分工文档要求加 02-module 放模块架构/契约/接口的个人视图）。
- 个人视图三份文档的实际来源：`TaskCatalog`/`AgentRegistry` 的调用形状与 7 个 HTTP 端点逐条从 `apps/backend/src/eval_platform/` 代码核对；契约内容取自[模块契约](../../architecture/MODULE_CONTRACTS.md)第 6.2、6.3 节。

### 观察到的事实

- 上游 `main` 的 [`.scratch/ui-catalog-providers/plan.md`](../../.scratch/ui-catalog-providers/plan.md) 仍是 **09-17 草案版**（表头写「计划草案，未开工」，01、02 未标完成），且没有 `issues/` 目录。而我 09-19 从组长处收到的同目录更新版（plan/spec/implementation-map 更新，任务 01、02 标注完成，含 `issues/01`、`issues/02`）**不在上游任何分支上**。详见[问题记录 ISSUE-02](../04-issues/KNOWN_ISSUES.md)。
- 上游 `main` 09-20 有 12 个新提交（作者 `noachlola`），内容包括任务 03 报告语义设计、对比报告的服务与端点、以及给 08 用的 D 侧 runbook。即：**有人在按单项授权推进 03 方向的工作**，但计划文档尚未同步这个进展。
- 成员 E 的[阶段 0 计划](../../LLY/01-plan/PLAN.md)明确：真实执行链（Harbor、SWE-Bench-Fork、固定镜像、`framework/`、`runtime/`）只在组长机器上，不进 Git；开发机只做代码、单元与契约测试、替身验证。这条同样约束我的任务 04。

### 当前停点

- `lyq` 分支已基于上游最新提交，个人文档目录已建立；**产品代码未开工，未下载镜像或数据，未运行容器或模型**。
- 任务 04 仍无开工授权；按顺序先等 `03`（B 主责）完成。

## 2026-09-19

### 已完成

- 从组长处收到更新版规划文档（`TEAM_WORK_ALLOCATION.md`、`ui-catalog-providers` 目录、Navicat 连接教程）。
- 通读我负责模块的权威文档与源码：模块架构、模块契约 6.2/6.3 节、数据模型、HTTP API 第 5/6 节，以及 `catalog_presets.py`、`swe_gym.py`、`job_presets.py`、`domain/jobs/policy.py`、`routes/catalog.py`。
- 核对出任务 04 的机制现状：`TASK_PRESETS` 只有一道题 `swe-gym-lite-mypy-15413`；`AGENT_PRESETS` 只有一个配置 `codex-0153-terra-medium`；`SubmissionPolicy` 已有 `maximum_agent_configurations=3` 与 `maximum_runs=60`，**缺的是「连续 1–20 题」的 `BatchPreset`**（现在只有 `demo` 1–3、`quick` 恰好 5、`standard` 10–20，所以 4 道或 6 道题的请求会被拒）。
- 建立任务 04 的行动文档并按验证规范补出测试设计（目录层、规模层、判卷层、浏览器层四组用例）。
- 建立 `docs/lyq/` 个人文档目录（后于 09-20 按上游约定重命名为 `docs/LYQ/`）。

### 实际结果

- 我 fork 的 `main` 停在 `6dfa2be`，当时误认为是最新；09-20 接入上游后才知道上游已领先 21 个提交。

## 2026-09-18

- 五人分工确定（[团队分工文档](../../architecture/modules/TEAM_WORK_ALLOCATION.md)）。我被分配为成员 C：长期负责「目录与配置」Module，任务 04 的任务 DRI，工时基线 54 h。
- 分工文档同时明确：01–08 仍未发布独立 issue，分工不等于开工；成员可提前阅读自己 Module 和准备测试设计，但不提前修改后续任务代码、不调用真实模型、不下载大体量镜像。
