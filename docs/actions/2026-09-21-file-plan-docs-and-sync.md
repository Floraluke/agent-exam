# 归档扩展计划文档与同步 origin/main

## 状态与情况

- 状态：已完成。
- 来源请求：用户提供 6 份扩展计划文件（来自 `D:\ui-catalog-providers\ui-catalog-providers\`），要求归档归类，并说明 01 号任务已完成；随后要求拉取代码。
- 当前事实（均经实际核对）：
  - 4 份（`spec.md`、`plan.md`、`implementation-map.md`、`verification.md`）在仓库已有权威位置 `.scratch/ui-catalog-providers/`，但仓库版本是**旧版**（仍写"01 未开工、未发布任务单"）；2 份任务单（`issues/01-...`、`issues/02-...`）在仓库中原本**完全不存在**，`issues/` 目录也不存在。
  - 6 份文件的内部相对链接只有在 `.scratch/ui-catalog-providers/`（及其 `issues/`）下才成立；`docs/LLY/README.md` 与 `TEAM_WORK_ALLOCATION.md` 都把该目录列为扩展计划的权威位置。
  - 归档完成后拉取远端发现：`origin/main` 已从 `6dfa2be` 前进到 `beed93f`，其中包含与本次归档**内容完全相同**的 6 份文件，以及此前缺失的 `docs/actions/2026-09-18-ui-workbench-prototype.md`、`docs/actions/2026-09-18-ui-workbench-implementation.md` 和任务 02 的产品代码。
  - 逐份比对确认：本次归档的 6 份文件与 `origin/main` 中的版本差异为 **0 行**。
- 已确认决定：
  - **不把 6 份文件复制进 `docs/LLY/`**。理由：`docs/LLY/README.md` 自定规则禁止在本目录复制项目级事实（否则会出现两份各自过期的文档），且 `AGENTS.md` 要求同一事实只设一个权威来源。LLY 目录只增加指向权威位置的链接。
  - 确认远端已有同一内容后，**丢弃本地冗余改动并删除本地新增的任务单副本**，改由合并 `origin/main` 取得，避免留下内容相同却来源不同的两份文件。
- 明确排除：不修改产品代码，不新建 Module/Interface/表，不启动服务或容器，不调用模型，不下载镜像，不推送 Git。

## 实施措施

1. 用用户提供的版本更新 `.scratch/ui-catalog-providers/` 下 4 份权威文档，保持仓库工作区既有的 CRLF 约定（`core.autocrlf=true`）。
2. 新建 `.scratch/ui-catalog-providers/issues/` 并放入任务单 01、02。
3. 在 `docs/LLY/README.md` 的权威位置表中补充这 6 份文件的链接并更新当前状态；在 `PROGRESS_LOG.md` 追加记录；修正 `01-plan/PLAN.md` 中已失效的待确认事项。
4. 拉取远端，逐份比对本次归档内容与 `origin/main` 版本，确认完全一致。
5. 丢弃本地冗余改动（3 份修改文档 + 2 份新增任务单），将 `origin/main` 合并进 `lly/dev`，使这些文件统一由远端提交提供。
6. 合并后运行后端静态检查与默认回归，确认新带入的代码未破坏既有基线。

完成标准：`lly/dev` 包含 `origin/main` 全部提交；6 份计划文件以远端版本为准且内容与用户提供版本一致；`docs/LLY/` 只含链接；本地过程文档改动保留；后端检查相对合并前基线无新增失败。

## 受影响文件树

```text
.scratch/ui-catalog-providers/
├─ spec.md / plan.md / implementation-map.md / verification.md
│                            # 内容净变化为 0：先按用户版本更新，后确认与 origin/main 相同，改由合并取得
└─ issues/
   ├─ 01-clickable-html-prototype.md            # 同上：最终来源为 origin/main 的提交
   └─ 02-role-workbench-submission-approval.md  # 同上
docs/LLY/
├─ README.md                  # 修改：权威位置表由 1 条扩为覆盖 4 份文档 + 2 份任务单；当前状态增加扩展任务进展
├─ 01-plan/PLAN.md            # 修改：待确认事项 1 由"01–08 何时发布"改为"03–08 何时发布"
└─ 03-progress/PROGRESS_LOG.md # 修改：追加归档与同步记录，并修正归档阶段写下的两处缺口描述
docs/actions/
└─ 2026-09-21-file-plan-docs-and-sync.md       # 新增：本行动记录
（以下由 origin/main 合并带入，非本次创建）
apps/web/src/features/workbench/{shell,dashboard}.tsx           # 任务 02 正式 Web 布局
apps/web/src/features/jobs/{wizard,listing}/                    # 任务 02 向导与列表
apps/web/tests/workbench/、apps/web/tests/support/workbench.ts   # 任务 02 浏览器回归
apps/backend/.../delivery/http/routes/jobs/report_comparisons.py # 对比查询接口
docs/actions/2026-09-18-ui-workbench-{prototype,implementation}.md、2026-09-19/20-d-*.md # 此前缺失的行动文档
```

设计关系：本行动不涉及设计模式，不改变模块边界、依赖方向或任何 Interface；只做文档归位、链接、状态同步与工作区合并。权威事实归属不变——计划仍归 `.scratch/ui-catalog-providers/`，E 模块过程记录仍归 `docs/LLY/`。

## 自验证方式

1. 归档阶段：逐份比对 6 份文件与用户提供版本（忽略换行符），应无差异；检查新位置的相对链接可解析；确认 `docs/LLY/` 未复制权威正文。
2. 同步阶段：比对本次归档内容与 `origin/main` 版本，差异应为 0；合并后确认无冲突、无残留未跟踪副本。
3. 合并后运行 `ruff check`、`mypy` 与默认 `pytest`，与合并前基线（386 passed / 82 skipped / 2 failed）比较：只应出现新增用例带来的通过数增加，不得出现新的失败。
4. 检查 `git status` 只出现本次预期的文件。
5. 前端类型检查、生产构建与浏览器回归本次不运行（`apps/web/node_modules` 未安装），如实记录为未验证项。

## 自验证情况

### 归档阶段

- **内容一致性：** 6 份文件逐份与用户提供版本比对（`diff --strip-trailing-cr`），差异均为 **0 行**。
- **仓库侧实际变化：** `git diff --stat` 显示 `spec.md` +2 行、`plan.md` 25 行变化、`implementation-map.md` 95 行变化；`verification.md` 与旧版内容本就相同；2 份任务单为新增。
- **相对链接：** 6 份文件在新位置的全部仓库内相对链接共 79 条可解析，1 条缺失——`docs/actions/2026-09-18-ui-workbench-prototype.md`（任务单 01 引用）。该缺失归档前即存在，已如实登记，未伪造。
- **LLY 目录边界：** 用「逐控件契约清单」「flexible-v2」「provider_access」「无后端请求」四个权威正文特征词检索，`docs/LLY/` 命中文件数均为 0，确认未复制计划正文；LLY 内全部相对链接可解析。
- **格式：** LLY 目录 Markdown 代码围栏成对，未检出文件行尾空格。

### 同步阶段

- **与远端比对：** 本次归档的 6 份文件与 `origin/main`（`beed93f`）中的对应版本差异均为 **0 行**，确认归档内容与远端提交一致。
- **处理方式：** 丢弃 3 份本地修改（`git checkout --`）并删除本地新增的 `issues/` 目录副本，改由合并取得。因内容经比对完全相同，此操作无信息损失。
- **合并结果：** `git merge refs/remotes/origin/main` 无冲突；`lly/dev` 由 `469ba1d` 前进到合并提交 `2a55a9e`，当前相对 `origin/lly/dev` 领先 25 个提交（未推送）。远端同时新增分支 `origin/xinyue-modules`，本次未处理。
- **链接复查：** 合并后重新解析 6 份文件的全部仓库内相对链接，**全部可解析**；先前缺失的 `docs/actions/2026-09-18-ui-workbench-prototype.md` 已由 `origin/main` 带入。
- **后端静态检查：** `ruff check` → `All checks passed!`；`mypy` → `no issues found in 167 source files`（合并前为 164，新增 3 个源文件）。
- **后端默认回归：** `404 passed, 84 skipped, 2 failed, 55.89s`。合并前基线为 `386 passed, 82 skipped, 2 failed`：通过数 +18、跳过数 +2，**失败项完全相同**，仍为缺少 `framework/harbor` 的既有环境失败（ISSUE-04）。未出现新的失败，合并未破坏既有基线。
- **工作区状态：** `git status --short` 只出现本次预期文件——3 份修改的 `docs/LLY/` 文档与本行动文档，无其他改动混入，无残留未跟踪副本。

### 未运行的检查与遗留

- **前端未验证：** `apps/web/node_modules` 未安装，前端类型检查、生产构建与浏览器回归本次均未运行。合并带入的任务 02 Web 代码因此在本机**未经验证**，不得据此声称任务 02 的前端在本机通过。
- **其余未运行的检查：** 未启用 PostgreSQL 集成测试（未设 `AGENTEXAM_RUN_*` 开关）、未启动容器、未调用模型。
- **未提交、未推送：** 本地过程文档改动与合并提交均留在本机。
- **独立未关闭任务：** M1 任务 14（私有双机协作验收）仍在进行中，与本次文档归档和合并无关。
