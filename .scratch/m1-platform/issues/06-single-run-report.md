# 06: 单题执行与最小报告

**What to build:** 一个已批准的单题 Job 被本机 Worker 领取，通过既有执行与独立判卷边界处理，保存结果和证据；用户从页面查看最小可信报告。首轮以可控替身验证平台链路。

**Blocked by:** 05 所有者批准或拒绝

**Status:** ready-for-agent

**Spec stories:** 23, 24, 26, 27, 28, 35, 36, 37, 38, 41, 47, 51

- [x] Worker 原子领取已批准队列项；待批准、拒绝和已领取项不可重复领取，双 Worker 竞争仍最多一个重型 Job 活跃。
- [x] 深化既有应用编排、Execution Backend 和 Patch Evaluator；一个平台 Job 对应一个 Harbor Job，当前切片完整验证一个 Run，不另造平行执行系统。
- [x] 多组合 Job 在任务 07 接通前不被部分领取或伪装为全部完成；这一开发期限制明确可见，不改写最终 M1 批量范围。
- [x] 最终文本 patch 经身份、哈希、大小和格式检查；超过 256 KiB 警告、超过 1 MiB 或二进制拒绝，不截断后判卷；空补丁按现有契约处理。
- [x] 确定性结论只来自固定 Fork 的独立判卷；Harbor reward、模型自述、缺失或无可信报告不能冒充成绩；基础设施错误与题目未解决分别保存和展示。
- [x] 领取、状态事件与结果短事务持久化，运行期间不长期持有数据库锁；租约/身份校验和资源限制的精确方案查证后确定，越权 Worker 不能推进状态。
- [x] 结果元数据存 PostgreSQL，证据存不可变 MinIO 并关联哈希/大小；重启后报告可查询，单侧存储失败和缺失正文不能伪装成完整结果。
- [x] 页面从 Job 进入 Run 报告，只暴露受保护摘要与允许发布的证据；原始私有输出不能因接入存储而自动公开。
- [x] 报告保留 M1 兼容空值：judge_analyses 为空、human_review 和 quality_tiebreak 为 null、review_status 为 NOT_REQUIRED；不调用或预建 Judge/Review 能力。
- [x] HTTP 主流程保留真实用例，只在执行/判卷外部边界用替身；浏览器验证报告接线，真实 PostgreSQL/MinIO 集成验证领取并发与存储失败；替身记录不进入正式报告或排行。
- [x] 独立行动记录注明实际测试、跳过项和本地提交；真实 Codex、Docker 探针或真实凭据实验须另行授权，本任务模拟闭环不记为 M1 真实验收通过。

## Comments

2026-09-11：任务已发布，尚未实施。任务 07 扩展逐题进度与批量收束；任务 08 扩展安全证据浏览，不延后本任务已暴露内容的安全要求。

2026-09-12：任务 05 已验收并完成双轴评审，阻塞解除。任务 06 以 `4944ce6` 为固定基准开工；首轮仅接通一个 `internal_test` Run，多组合在任务 07 前保持不可领取，不运行真实 Codex/Harbor，也不创建或调用 Judge/Review。

2026-09-12：11 项验收全部完成。固定基准双轴初评发现真实 Harbor 契约、本地制品归档、缺失正文失败关闭、空 patch 不变量及若干项目规范问题；全部修复后，Spec 与 Standards targeted 复评均为无 findings。真实隔离 PG+MinIO+HTTP 为 46 passed，默认后端 306 passed/61 gated skipped，浏览器 14 passed；替身仅限 `internal_test`，未运行真实模型或改动 Judge/Review。
