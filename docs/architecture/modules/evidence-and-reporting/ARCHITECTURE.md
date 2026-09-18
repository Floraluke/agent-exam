# 证据与报告 Module

> 当前状态：安全证据发布、单 Run/批次报告、轨迹、原始制品保留清理和基础排行榜已实现；PostgreSQL/MinIO 仅在隔离环境中完成正式链验证，长期存储未部署。
> 权威范围：证据正文与索引怎样产生、校验、读取、保留和呈现。

## 1. 职责与非职责

本 Module 把执行和判卷返回的文件转成与 `run_id` 绑定、内容哈希固定的证据；将对象正文放入 MinIO，将索引、结果、指标和删除审计放入 PostgreSQL；再按 actor 权限提供 Run、Job、制品、轨迹和基础排行榜读取。

它不运行 Agent、不重新判卷、不根据页面需要伪造缺失用量，也不把原始私有输出直接当作公开证据。排行榜只使用正式确定性结果，不引入 Judge 分。

## 2. Interface 与不变量

- `ArtifactStore` / `ArtifactReader`：不可变写入、按摘要验证读取、限长验证读取和受控删除的 seam。
- `EvidencePublication`：把 patch、判卷摘要、公开轨迹和 raw 证据归一化并发布。
- `JobReporting`：检查结果—制品引用完整性及 owner/创建者访问后，提供报告、正文和轨迹。
- `LeaderboardReporting` / `LeaderboardRepository`：只读、按完整配置身份与可比条件聚合。
- 长期核心证据与 `raw_30d` 原始证据分开；原始正文删除后保留摘要、大小、时间和删除审计。
- `unknown` 与数值 0 不同；存储不可验证时失败关闭，不能返回“可能正确”的报告。

精确制品类型、对象键、表和保留规则见[数据模型](../../DATA_MODEL.md)，HTTP 下载/分页见[HTTP Interface](../../../interfaces/HTTP_API.md)。

## 3. 当前 Implementation 文件树

```text
apps/backend/src/eval_platform/
  domain/
    result.py                             # Trial、确定性结果、用量、资源和 ArtifactRef
    artifacts.py                          # 制品类型枚举
    leaderboard/                          # 比较范围、行、指标与确定性排序策略
    jobs/execution.py                     # RunReport、JobReport、制品索引和完成值
  application/
    execution/evidence.py                 # patch、判卷、公开轨迹和摘要发布
    execution/public_evidence.py          # 公开文本/轨迹规范化
    execution/raw_evidence.py             # raw_30d 限额与发布
    execution/completion.py               # 结果、指标和制品索引组装
    reporting/service.py                  # 报告授权、完整性复核和正文读取
    reporting/evidence.py                 # 制品/轨迹分页与响应值
    reporting/leaderboard.py              # 基础排行榜用例
    ports/artifacts.py                    # ArtifactReader / ArtifactStore Interface
    ports/leaderboard.py                  # LeaderboardRepository Interface
  adapters/artifacts/
    config.py                             # 私有 MinIO 端点/凭据配置和 S3 客户端
    minio.py                              # MinIO ArtifactStore Adapter
    local.py                              # owner 本机执行目录读取 Adapter
    bounded.py / policy.py                # 限长读取与对象引用策略
  adapters/persistence/jobs/
    execution/results.py                  # 结果、指标、制品索引原子写入
    execution/reports.py                  # Run/Job/制品报告读取
    reporting/                            # 列表、排行榜行和冻结值校验
    retention/                            # 原始正文删除意图、确认与审计
  delivery/http/routes/
    artifacts.py / artifact_schemas.py    # 制品正文与轨迹 HTTP 翻译
    jobs/report_routes.py                 # Run/Job 报告 HTTP 翻译
    leaderboard/                          # 排行榜 HTTP 翻译与 DTO
apps/web/src/
  features/jobs/report.tsx                # 单 Run 报告
  features/jobs/batch-report.tsx          # Job 批次报告
  features/jobs/evidence.tsx              # 制品与轨迹查看
  features/leaderboard/view.tsx           # 基础排行榜
  lib/reporting/                          # 制品响应校验
  lib/leaderboard/                        # 排行榜客户端与形状校验
```

## 4. 关键数据流与双存储一致性

```text
执行目录/判卷输出
  → 读取并验证原始摘要
  → 生成公开安全派生物
  → MinIO 不可变写入并回读验证
  → PostgreSQL 在 Run 完成事务中登记对象引用和确定性结果
  → 报告读取时再次核对 run_id、类型、摘要和权限
```

PostgreSQL 与 MinIO 没有跨产品原子事务。当前应用通过“先完成对象写入并验证，再提交索引；读取再校验”的顺序防止发布不完整结果。长期备份仍必须形成一致的备份集，不能只复制其中一边。

## 5. 模式、依赖和深度

ArtifactStore 是对象存储 seam；MinIO 是正式 Adapter，本地 reader 只承接 owner 本机执行证据输入。`JobReporting` 把授权和引用完整性隐藏在小读取 Interface 后，Web 不直接访问 bucket，也不自己拼对象键。

本 Module 依赖 Job Control 的 Run/结果身份和 Identity 的 actor；Execution/Evaluation 向它交付受控输出。它不反向依赖 Web 或 Harbor 配置。

## 6. 当前验证与缺口

历史验证见[安全证据行动](../../../actions/2026-09-12-m1-safe-evidence.md)、[单 Run 报告](../../../actions/2026-09-12-m1-single-run-report.md)、[制品保留](../../../actions/2026-09-13-m1-artifact-retention.md)和[基础排行榜](../../../actions/2026-09-13-m1-base-leaderboard.md)。本轮没有连接 PostgreSQL/MinIO 或重跑测试。

待补的是长期 MinIO/PG 版本、数据目录、容量、备份恢复、升级和运营监测；见[所有者单机运行](../owner-host-runtime/ARCHITECTURE.md)。MinIO 当前固定的归档 CE 测试来源存在维护/安全风险，不能直接由合成测试身份推导为长期部署选型已完成。
