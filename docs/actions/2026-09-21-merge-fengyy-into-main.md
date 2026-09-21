# 提交本地成果并合并 fengyy-fixweb 到 main

## 状态与情况说明

- 状态：进行中。
- 来源请求：本地提交现有代码，把 `fengyy-fixweb` 合并入 `main`，并让主仓库最终停在 `main`。
- 当前分支：主工作区已在 `main`，HEAD 为 `fd369cc`，相对 `origin/main` 落后 66 个提交；`fengyy-fixweb` 为 `d9a7759`，含本轮获取的最新 `origin/main` 与任务 05 负责人文档提交。
- 当前本地工作：主工作区包含已完成但未提交的任务 03 对比报告 UI、正式运行态交接、共享 PostgreSQL 连接文档、任务 05 首轮事实填充及相关权威文档同步。对应行动记录均已存在并记录测试结果。
- 审计边界：`.scratch/ui-catalog-providers.zip` 是压缩产物，`apps/web/%USERPROFILE%/AppData/Local/npm-cache/_update-notifier-last-checked` 是误展开的 npm 缓存；二者不属于源码或权威文档，本轮不提交、不删除。
- 工作区保护：不使用 `git add .`，只暂存审计后的源码、测试、文档与本行动记录；不推送 `main`，因为用户只要求本地提交与合并。
- 已知重叠：本地对比报告 UI 与 `fengyy-fixweb` 中已合入主线的报告 UI实现路径重叠；任务 05 首轮填充与 `fengyy-fixweb` 的后续负责人回执同路径重叠。合并时须保留双方有效事实并以最新测试/授权边界为准，不能简单整边覆盖。

## 实施措施

1. 对当前 `main` 的全部已跟踪改动和未跟踪文件做路径、大小及与 `fengyy-fixweb` 的内容比较；排除压缩包和 npm 缓存。
2. 运行预提交空白与敏感形态检查，按明确路径暂存本地源码、测试和文档，建立本地检查点提交。
3. 将 `fengyy-fixweb` 合并入 `main`；若发生冲突，先完整读取 `resolving-merge-conflicts` 技能，再逐项以代码事实和权威文档解决。
4. 报告 UI 保留本地已验证的深层组件拆分及完整语义回归，同时吸收 `fengyy-fixweb` 的最新接口、任务 04/05 与文档变化；任务 05 文档保留后续负责人回执和“不运行探针”边界。
5. 运行与合并风险相称的 Web 类型检查、生产构建、浏览器回归、后端默认回归、Markdown 链接与 Git 检查；失败如实记录并修复属于本次合并的问题。
6. 提交合并结果；安全移除仅用于浏览 `fengyy-fixweb` 的 worktree，确认主工作区仍在 `main`。不删除被排除的本地产物，不推送远端。

## 受影响文件树

本地检查点沿用各既有行动记录的实际文件树，本行动只负责提交和集成，不重新声明其业务设计。预期集成范围如下：

```text
.scratch/
├─ m1-platform/{spec.md,issues/14-private-remote-acceptance.md} # 远程验收与 LAN 文档状态
└─ ui-catalog-providers/ # 任务 03/05 计划、验收、任务单；排除同名 zip
apps/backend/tests/jobs/ # 任务 03 已记录的机械格式化
apps/web/
├─ src/features/jobs/ # 本地报告 UI 与 fengyy 主线 UI 集成
├─ src/lib/reporting/ # 对比合同解析和有限并发客户端
└─ tests/reporting/ # 对比语义、权限与竞态浏览器回归
docs/
├─ LLY/01-plan/ # 任务 05 首轮核对与后续负责人回执合并
├─ actions/ # 各既有行动记录与本合并记录
├─ architecture/ # 数据、模块、运行边界同步
├─ interfaces/HTTP_API.md # 报告接口合同
└─ operations/ # 远程与 PostgreSQL 接入事实
HANDOFF.md # 合并后的唯一恢复入口
```

不新增业务 Module、Interface 或数据库表。合并提交只整合既有分支和已完成的本地工作；若最终文件树偏离上述范围，本记录会同步实际差异。

## 修改后自验证方式与成功标准

- Git：`git diff --check`、限定暂存清单、合并后无未解决冲突；主工作区分支为 `main`。
- 安全：增量不含真实 Key、Cookie、Token、密码或私有凭据正文；压缩包和 npm 缓存不进入提交。
- Web：`npm run typecheck`、`npm run build`、`npm run test:e2e` 实际通过。
- Backend：使用项目虚拟环境运行默认 pytest；门禁跳过与实际通过分开报告。
- 文档：变更 Markdown 的本地链接、代码围栏、尾随空白检查通过，当前状态不把历史快照写成实时保证。
- 最终状态：本地 `main` 包含本地检查点与 `fengyy-fixweb` 合并提交；不推送；仅剩明确排除的本地产物时如实列出。

## 自验证情况

- 待实施后回填。
