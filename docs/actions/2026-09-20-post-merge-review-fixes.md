# 2026-09-20 合并后审查问题修复

## 状态与情况说明

状态：Completed（2026-09-20）。

来源请求：owner 要求确认共享 PostgreSQL 是否已经升级，并修复对 D 合并内容审查发现的问题。

已确认事实：

- 本地 `main` 与 `origin/main` 均为 `beed93f`。开始核对时已知两项既有未跟踪缓存；执行期间又出现另一协作者的远程接入/任务 14 文档增量，本行动均按无关改动保留且不暂存。
- 共享库 `evaluation_jobs_batch_preset_check` 已包含 `demo/quick/standard/continuous`，`convalidated=true`，活动 Job 为 0；本轮不重复执行 ALTER。
- 当前代码已经提供 `continuous` 与跨批次比较端点，但缺少可审计的旧库升级入口，公共 HTTP/数据/模块文档也未同步。
- 比较端点未拒绝未知或重复 query 参数；矩阵只用 `task_instance_id` 建索引，不能隔离不同仓库的同名题目。
- HTTP DTO、Markdown 渲染重复计算汇总，五档 outcome 类型也重复声明；`routes/jobs/` 已有 9 个直属文件。

确认范围：修复上述审查问题并同步权威文档。任务 03 的 Web 对比页仍未实现，本轮不把任务 03、04 或 08 标记为整体完成。

明确排除：不运行真实 Worker/模型，不新增数据库表，不改历史 Job，不重复升级已经满足约束的共享库，不实现 Web 对比页，不推送远端。

## 实施措施

1. 先补回归测试：未知/重复 query、UUID 规范化去重、跨仓库同名题隔离、汇总派生值，以及旧约束升级/新约束幂等/异常约束拒绝。
2. 在既有 Job persistence adapter 内新增显式、幂等、失败关闭的 `continuous` 约束升级；在现有 Job CLI 增加明确子命令，HTTP 启动仍不自动迁移。
3. 对比路由移入 `routes/jobs/reporting/` 内部子目录，复用矩阵领域类型与派生汇总，严格校验 query 参数并规范化 UUID。
4. 矩阵键改为 `(repo, task_instance_id)`，保持排序、缺失语义和已有响应形状。
5. 同步 HTTP API、数据模型、相关模块架构、扩展计划/实现地图、HANDOFF 和 D 的专题行动；记录 cancel/claim 快照修复及本轮验证事实。

完成标准：新增回归先能暴露旧行为；实现后定向测试、真实隔离 PostgreSQL 升级测试、全量默认门禁、Ruff、mypy、Web 类型检查和文档/文件树检查全部有实际结论；本轮文件边界与既有缓存/协作者增量可区分。

## 受影响文件树

```text
apps/backend/src/eval_platform/
├─ adapters/persistence/jobs/__init__.py              # 修改：显式、幂等、失败关闭的 continuous 约束升级
├─ application/reporting/
│  ├─ matrix.py                                       # 修改：复合题目键、统一 outcome 与 totals 派生值
│  └─ matrix_markdown.py                              # 修改：复用 totals 派生值
├─ delivery/jobs.py                                   # 修改：现有维护 CLI 增加显式升级命令
└─ delivery/http/
   ├─ app.py                                          # 修改：从 reporting 子目录装配比较路由
   └─ routes/jobs/
      ├─ report_comparisons.py                        # 删除：职责迁移，恢复直属文件上限
      └─ reporting/                                   # 新增：现有 Web/HTTP 模块内部子目录，不是新业务 Module
         ├─ __init__.py                               # 导出 comparison_router
         └─ comparisons.py                            # HTTP Adapter：严格 query 与稳定 DTO 翻译
apps/backend/tests/jobs/
├─ reporting/test_comparison_http.py                  # 修改：未知/重复参数与 UUID 去重
├─ reporting/test_matrix.py                           # 修改：跨仓库同名题和 totals 派生值
└─ scale/test_continuous_upgrade.py                   # 新增：真实 PG 迁移与 CLI 行为
docs/
├─ actions/2026-09-20-post-merge-review-fixes.md      # 本行动记录
├─ actions/2026-09-20-d-comparison-api-proposal.md    # 修改：消除 coverage/total 冲突并记录修复
├─ actions/2026-09-20-d-continuous-scale-and-rehearsal.md # 修改：共享库已升级与正式入口指针
├─ architecture/DATA_MODEL.md                         # 修改：当前约束与显式升级事实
├─ architecture/modules/job-control/ARCHITECTURE.md   # 修改：continuous、升级入口与快照修复
├─ architecture/modules/evidence-and-reporting/ARCHITECTURE.md # 修改：矩阵/比较文件树与语义
├─ architecture/modules/web-and-http/ARCHITECTURE.md  # 修改：比较 GET 契约
├─ architecture/modules/README.md                     # 修改：模块索引的部署与比较现实状态
└─ interfaces/HTTP_API.md                             # 修改：continuous 与 §10.4
.scratch/ui-catalog-providers/
├─ plan.md                                            # 修改：区分已落地后端切片与未完成产品阶段
└─ implementation-map.md                              # 修改：记录现有比较后端，Web reporting 仍候选
HANDOFF.md                                            # 修改：当前代码、数据库和未完成边界
```

参与关系：`matrix.py` 是应用层领域值与聚合实现；`reporting/comparisons.py` 是 HTTP Adapter，只负责 query/DTO 翻译；Job persistence adapter 管理显式数据库升级；`delivery/jobs.py` 仅暴露本机运维命令。依赖方向保持 delivery → application/domain、adapter → domain，不新增跨层反向依赖。

## 自验证方式

1. 新增测试先在旧实现上定向运行，记录预期失败。
2. 定向运行比较 HTTP、矩阵、continuous 规模和升级测试。
3. 使用专属随机测试库运行 PostgreSQL 升级测试，确认旧约束升级、新约束幂等、未知约束失败关闭并精确清理。
4. 运行后端默认门禁全量测试、Ruff、mypy、Web `npm run typecheck`。
5. 运行 `git diff --check`、目录文件数、OpenAPI/文档关键词及最终 `git status` 检查。
6. 只读复核共享库约束仍为已验证的四值约束；不调用升级命令改写共享库。

## 自验证结果

### 先红后绿

- 比较 HTTP/矩阵回归先暴露旧行为：未知与重复 query 未拒绝、大小写不同但等价的 UUID 未规范化去重、不同仓库的同名 `task_instance_id` 被合并。
- continuous 升级测试在旧实现上因没有 `upgrade_continuous_preset` 而无法收集，证明缺少可执行迁移入口。
- 修复后定向比较/矩阵测试为 **15 passed**；最终把迁移单元用例并入定向门禁后为 **10 passed / 2 skipped**，两个 skip 是未开启真实 PostgreSQL 门禁，不是失败。

### 隔离真实 PostgreSQL

- 创建专属临时角色/数据库运行升级用例，结果 **4 passed**：旧三值约束原子升级、新四值约束重复执行无操作、未知约束拒绝覆盖、CLI 两种结果文案正确。
- 验证结束后删除该临时数据库和角色；复核 `leftover_databases=0`、`test_role_exists=false`。
- 全程没有把迁移测试指向共享业务库。

### 最终门禁

- 后端默认全量：**415 passed / 81 skipped / 0 failed**，2 个第三方弃用 warning；skip 均为显式 PostgreSQL/MinIO/Docker/真实集成门禁。首次沙箱运行因 Windows ACL 令 pytest 临时目录不可访问，不能作为业务结论；改用相同命令在本机权限下重跑后得到上述有效结果。
- 改动 Python 的 Ruff lint 与 format check：通过；mypy（5 个改动源文件）：通过。
- Web `npm run typecheck`：通过；本轮没有新增 Web 对比页或按钮。
- 实时 OpenAPI 与 `HTTP_API.md` 当前清单：**32 对 32，差异 0**；比较 GET 存在。
- `routes/jobs/` 直属文件 **8**，内部 `reporting/` **2**；改动 Python 源文件均不超过 200 行。
- `git diff --check`：通过，仅显示仓库既有 LF→CRLF 提示；本轮 pytest 临时目录清理后残留为 0。

### 共享库只读复核

最终只读查询仍返回：

```text
evaluation_jobs_batch_preset_check|CHECK ((batch_preset = ANY (ARRAY['demo'::text, 'quick'::text, 'standard'::text, 'continuous'::text])))|validated=true
active_jobs=0
```

因此数据库升级已经由他人完成且真实生效；本轮没有重复 ALTER，也没有写入共享业务数据。

### 实际偏差与边界

- 为消除模块索引里的过期部署状态，实际同步范围增加 `docs/architecture/modules/README.md`。
- 工作树同时存在其他协作者的远程接入文档、任务 14 文档和未跟踪缓存；本轮没有编辑、删除、暂存或提交这些无关增量。
- cancel/claim 的 `REPEATABLE READ` 快照修复来自合入提交；本行动补齐其模块说明和审查追踪，没有重写该既有修复。
- 任务 03 Web 对比页、任务 04 五道新题和任务 08 真实冻结矩阵仍未完成，本轮不更改这些产品阶段状态。

### 发布记录

- 2026-09-21，owner 明确要求把本行动修复提交并推送至 `origin/main`。
- 推送前发现 `origin/main` 已由其他成员新增 LLY 规划文档；这些远端提交必须保留，本轮禁止强推，并采用正常合并后再推送。
- 提交只包含本行动文件树；远程接入、任务 14、owner-host-runtime、团队分工、共享数据库接入文档及缓存等其他工作树增量不纳入。
