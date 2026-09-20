# 已知问题记录

> 记录我遇到的、影响我这项工作的实际问题：现象、证据、处理过程、遗留风险。
> 项目级缺陷应提升到权威文档或对应行动记录，本文件只保留与我工作相关的记录。

## ISSUE-01 本机直连 GitHub 不通，git 操作必须走本机代理

- **现象**：`git push` 反复报 `Failed to connect to github.com port 443` 或 `Recv failure: Connection was reset`；浏览器的 GitHub 页面也可能加载出缓存旧内容。
- **证据**：2026-09-20 连续 6 次 `git push` 失败；同一时刻 `curl https://api.github.com` 直连超时（返回码 000），改走本机 `127.0.0.1:7892` 代理后返回 200。
- **处理**：在该仓库的**本地** git 配置里写入 `http.proxy=http://127.0.0.1:7892`（只影响本机，不会提交到仓库）；推送与 fetch 随即正常。
- **遗留风险**：代理端口来自本机 Clash 配置，若代理软件关闭或端口变更，git 会再次失败，届时需要更新或删除该配置：
  `git config --unset http.proxy`（在仓库目录执行）。
- **影响范围**：只影响本机联网操作，不影响代码与文档内容。

## ISSUE-02 上游计划文档落后于组长提供的最新版本

- **现象**：上游 `main` 的 `.scratch/ui-catalog-providers/plan.md` 表头仍写「2026-09-17 计划草案，未开工」，任务 01、02 未标完成；且**没有** `issues/` 目录。
- **证据**：逐分支核对 `upstream/main`、`upstream/lly/dev`、`upstream/fengyy-fixweb`、`upstream/xinyue-modules`、`origin/main`，`ui-catalog-providers/issues` 文件数均为 0。而组长 2026-09-19 提供的更新版中，计划、规格、实现地图都已更新，任务 01、02 标注完成，并含 `issues/01-clickable-html-prototype.md`、`issues/02-role-workbench-submission-approval.md`。
- **处理**：未处理。我**没有**把组长那份更新版提交到自己的分支——它不是我产出的内容，混进我的分支容易与其他人的提交冲突。
- **遗留风险**：我行动文档里引用的「前项状态」可能因此与仓库事实不一致；等文档同步后需要回读计划再继续。另需注意上游 09-20 已有人推进任务 03 方向的代码，计划文档尚未反映。
- **建议**：由组长把更新版推送到上游，或确认以哪一版为准。

## ISSUE-03 开发机不具备任务 04 的真实运行条件

- **现象**：任务 04 的资格验证需要在容器里跑参考/空/错误三种补丁，本机无法执行。
- **证据**：本机仓库下无 `framework/`、`runtime/`、`infra/data/`、`infra/volumes/`；未发现固定 Parquet 数据快照（`AGENTEXAM_TASK_PARQUET` 指向的本地文件不存在）；`docker ps` 报 `dockerDesktopLinuxEngine` 管道不存在，Docker Desktop 未运行。
- **处理**：未处理，属预期状态。参考成员 E 的[阶段 0 计划](../../LLY/01-plan/PLAN.md)：真实执行链与固定镜像只在组长机器上，开发机只做代码、单元与契约测试、替身验证。
- **遗留风险**：任务 04 的题库资格验证（三补丁门禁）必须在组长机器上或由 E 执行；本机只能验证「连续规模预设 + 合成受控目录」这半边，且同样需要先获得开工授权。

## ISSUE-04 fork 与上游仓库的关系曾被误判（已解决）

- **现象**：2026-09-19 我在 `Floraluke/agent-exam` 上建分支并开 PR，当时以为它就是团队仓库。
- **证据**：该仓库的 API 返回 `parent = anphuchoang5-sys/agent-exam`，即它是 fork；fork 的 `main` 曾是纯快照，落后上游 21 个提交。
- **处理**：2026-09-20 接入 `upstream` remote，把工作 rebase 到 `upstream/main`。协作方式经确认为 **fork 工作流**：代码推个人 fork、从 fork 向上游提 PR、不直接操作上游仓库。据此收回了最初直接推到上游的 `lyq` 分支（关闭上游侧 PR、删除上游侧分支），改由 `origin`（fork）承载分支与 PR。
- **遗留风险**：无。教训是动手前先确认 `git remote -v` 与仓库的 parent 关系。
