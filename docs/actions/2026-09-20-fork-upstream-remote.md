# 行动文档：关联 fork 上游仓库并记录 Git 远程布局

## 状态与情况说明

- 状态：已完成
- 来源请求：用户声明团队采用“fork 提 PR”的协作方式，`https://github.com/anphuchoang5-sys/agent-exam` 是上游仓库，要求把用户 fork 的仓库与上游仓库关联。
- 当前事实（本次实测）：
  - 改动前仓库只有一个远程 `origin`，指向用户 fork `git@github.com:HeYuting1-alt/agent-exam.git`（SSH）；不存在 `upstream` 远程。
  - 上游仓库 `anphuchoang5-sys/agent-exam` 可匿名经 HTTPS 读取，也可用本机已有 SSH 凭据读取；两种协议的 `ls-remote` 均返回同一组引用。
  - 上游 `main`、本地 `main`、`origin/main` 三者改动前同为 `beed93f`，左右差异均为 0/0。
  - 用户 fork 当前只有 `main` 一个分支；上游另有 `fengyy-fixweb`、`lly/dev`、`xinyue-modules` 三个分支。
  - 本机未安装 GitHub CLI（`gh`），无法用 `gh` 核对仓库归属；本次只用 `git` 与只读查询，未读取 Git 凭据。（**已过期**：`gh` 已于其后安装但仍未登录，见文末“后续”）
  - 三份历史行动文档把 `origin` 记为 `https://github.com/anphuchoang5-sys/agent-exam.git`（[首次发布](2026-09-02-initial-git-publish.md)、[工作区迁移](2026-09-04-workspace-path-migration.md)、[M0 实现](2026-09-05-m0-codex-harbor-implementation.md)）。这些记录在各自日期是真实的。
- 已确认决定：
  - `upstream` 使用 SSH 协议，与现有 `origin` 保持一致，避免同一仓库混用两种认证方式。
  - 历史行动文档保持原样：它们是带日期的历史证据，改写会伪造历史；当前远程布局改由交接文档第 5 节单点维护。
  - 不做超出请求的远程配置改动：不设置 `remote.pushDefault`，不改 `push.default`，不新建分支，不推送任何提交。
- 明确排除：不安装 `gh` 或其他工具；不读取或导出凭据；不推送、不拉取合并、不改写历史；不修改业务源码、Web、测试、Docker 或模型配置。

## 实施措施

1. 只读探测上游可达性与既有远程配置，确认协议选择有依据。
2. 执行 `git remote add upstream`，加入上游仓库地址。
3. 执行 `git fetch upstream --prune`，取得上游全部分支引用。
4. 核验 `upstream/main`、`origin/main` 与本地 `main` 的哈希和差异，确认关联后没有引入偏差。
5. 在交接文档第 5 节追加本次 Git 远程布局事实，并说明“推送 `origin` 只更新个人 fork”，避免恢复会话误判发布目标。
6. 把实际执行结果与限制写回本行动文档。

完成标准：`git remote -v` 同时列出 `origin`（个人 fork）与 `upstream`（团队仓库）；上游四个分支可在本地 `git branch -r` 中看到；三个 `main` 的哈希与差异数字可复现；交接文档能单一说明推送与 PR 目标。

## 实际修改的文件树

```text
D:\agent-exam\
├─ .git\config
│  # 本次新增 remote.upstream.url 与 remote.upstream.fetch；Git 元数据，不入库
├─ HANDOFF.md
│  # 修改：第 5 节追加 2026-09-20 远程布局事实（origin=个人 fork，upstream=团队仓库）
└─ docs\actions\2026-09-20-fork-upstream-remote.md
   # 新增：本次远程关联的请求、依据、执行与验证记录
```

本次不引入代码设计模式。两个远程的分工是“个人 fork 推送、团队仓库拉取与 PR”，与既有 `.gitignore` 保护的发布边界无关，未影响源码结构。

## 修改后自验证方式

1. `git remote -v`：预期同时出现 `origin` 与 `upstream`，且各自 fetch/push 地址正确。
2. `git ls-remote --heads <上游地址>`：预期列出 `fengyy-fixweb`、`lly/dev`、`main`、`xinyue-modules` 四个上游分支。
3. `git branch -r`：预期包含 `upstream/HEAD -> upstream/main` 与四个 `upstream/*` 引用。
4. `git rev-parse main origin/main upstream/main`：预期三者同为 `beed93f`。
5. `git rev-list --left-right --count main...upstream/main` 与 `origin/main...upstream/main`：预期均为 `0	0`。
6. `git status --short --branch`：预期工作树不因本次远程配置出现源码改动，只保留本次文档增量。
7. `git config --get-regexp '^remote\.'`：预期只有 `origin`、`upstream` 两组 URL 与 fetch 规则，没有额外推送默认值。

## 自验证情况

- 远程列表：`git remote -v` 返回 `origin`（`git@github.com:HeYuting1-alt/agent-exam.git`）与 `upstream`（`git@github.com:anphuchoang5-sys/agent-exam.git`）各一组 fetch/push，符合预期。
- 可达性：改动前分别用匿名 HTTPS 和 `BatchMode` SSH 对上游执行 `ls-remote --heads`，两次退出码均为 0、返回同一组引用，证明上游公开可读且本机 SSH 凭据可用。
- 抓取：`git fetch upstream --prune` 返回 `fengyy-fixweb`、`lly/dev`、`main`、`xinyue-modules` 四个新分支引用，退出码 0。
- 引用一致性：`main`、`origin/main`、`upstream/main` 均为 `beed93f`；`main...upstream/main` 与 `origin/main...upstream/main` 的左右差异均为 `0	0`，关联后未引入任何提交偏差。Git 在抓取时自动建立了 `upstream/HEAD -> upstream/main`。
- 配置范围：仓库配置中只新增 `remote.upstream.url` 与 `remote.upstream.fetch` 两项；未新增 `remote.pushDefault`、未修改 `push.default`、未改动 `branch.main.*`。
- 工作树与配置：`git status --short --branch` 显示 ` M HANDOFF.md` 与未跟踪的新行动文档，没有业务源码改动；`git config --get-regexp '^remote\.'` 只有 `origin`、`upstream` 两组 URL 与 fetch 规则；`remote.pushDefault` 与 `push.default` 在仓库和全局均未设置。
- 顺带发现（早于本次变更，本轮未修改）：交接文档头部把工作区记为 `E:\9.1agent_exam`，而本机实际工作区根为 `D:/agent-exam`；同一处把“当前状态”记为分支 `fengyy-fixweb`，而实际签出为 `main`。这两处与本次远程配置无关，需用户确认真实机器情况后再同步，本次不为它们扩大范围。
- 未被本次验证覆盖的限制：
  - 未安装 `gh`，所以无法用 GitHub CLI 的账号身份复核两个仓库的归属与可见性，只能依据 `ls-remote` 结果和用户的明确说明判断哪个是 fork、哪个是上游。（**已过期**：`gh` 已安装、未登录，见文末“后续”）
  - 用户 fork 当前只有 `main`，因此“从上游分支拉取到本地、推送个人分支、开 PR”这条完整链路本次没有实际跑过；本次只验证到远程关联与引用一致。（**已过期**：该链路其后已实际跑通，见文末“后续”）
  - 未向任何远程推送，两个远程的 `push` 地址虽被列出但未实测；向 `upstream` 推送预期会被 GitHub 以无写权限拒绝，该预期未验证。
  - 历史行动文档中的旧 `origin` 地址按“历史证据不改写”原则保留，因此全库搜索 `anphuchoang5` 仍会命中三份带日期的行动文档；当前布局以交接文档第 5 节为准。

## 2026-09-21 后续：工具链安装与 fork→PR 链路的实际运行

本文件“明确排除”里写的“不安装 `gh` 或其他工具”是**当时**的范围边界；其后用户另行授权安装了工具。事实如下（唯一权威记在 [HANDOFF](../../HANDOFF.md) 第 5 节“环境与证据”）：

- **`gh` 已安装**（2.101.0，用户级，Authenticode 签名与官方 SHA-256 均已核对），但**尚未登录**——浏览器授权在换取 token 时因直连 `github.com` 超时失败。因此本节开头“本机未安装 GitHub CLI（`gh`）”那条**已过期**。
- **`uv` 与 uv 管理的 Python 3.13.15 已安装**，`apps/backend/.venv` 已按项目命令 `uv sync --locked --no-python-downloads` 建立；`argon2`/`pytest`/`ruff`/`mypy` 可用。
- **fork→分支→PR 的完整链路已实际跑通**（本文件当时记为“没有实际跑过”）：`task03/comparison-api-spec` 与 `docs/web-http-module-scaffold` 两个分支已推送，对应的 PR #3、#4 已在上游创建；其中 #3 因 `main` 上已有 §10.4 而**关闭不合并**，#4 并入新 `main` 后重做。
- **`origin/main` 已同步**到上游当时的 `fd369cc`。
- 上一节“顺带发现”里关于交接文档工作区路径的疑问**仍未定论**：`E:\9.1agent_exam` 很可能是 **owner 主机**的路径，而本机工作区是 `D:\agent-exam`——也就是两条记录可能各自描述一台机器，并不构成“过时”。需 owner 确认后才好在交接文档里改，本次**未改**。
