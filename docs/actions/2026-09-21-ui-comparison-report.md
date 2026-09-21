# 03 对比报告与单次证据行动记录

## 状态

- 完成，等待用户确认 UI；不自动进入任务 04
- 基线提交：`fd369cc`
- 任务来源：用户于 2026-09-21 明确发布“03：先看对比，再看单次证据”，并要求审查代码与文档、执行全量测试回归。

## 情况说明

- 后端已有 `GET /api/v1/reports/comparisons?job_ids=...`，可返回题目 × 配置矩阵及 `resolved`、`unresolved`、`infrastructure_error`、`incomplete`、`missing` 五类结果。
- `JobDetail` 已提供冻结的模型、版本、限制、工具与网络策略；`RunReport` 已提供用量、资源、确定性判卷、制品和轨迹。
- Web 已有单次 Run 报告和证据组件，但缺少把现有接口整合成对比页的入口和页面。
- 因现有公开接口足够，本任务不新增 API、顶层模块、数据库表或约束。
- 工作区在本任务开始前已有其他未提交修改；它们不属于 03，不修改、不暂存、不删除。
- 用户允许在测试中使用现有 `auth.json`。03 的验收可由确定性测试数据完成；除非全链路缺口确实需要真实模型调用，否则不读取该文件、不产生模型用量。

## 实施措施

1. 先补浏览器验收测试并确认在旧实现上失败。
2. 在现有工作台导航中增加“对比报告”，只展示当前身份通过服务端可见的批次。
3. 复用对比端点展示矩阵和五类汇总；缺失始终单列，不折算为未通过或零。
4. 复用 Job 详情展示冻结配置差异；不在 UI 重算排行榜，也不引入 Judge 分。
5. 复用 Run 报告按用户触发、有限并发加载用量；只有所有组成值都有来源时称“总量”，否则显示“部分”或“未知”，并将数字 0 与未知区分。
6. 单元格进入既有 Run 报告/证据视图，保留下载、轨迹、过期提示和确定性结果；技术错误字段折叠展示并附通俗说明。
7. 同步接口、架构、交接、任务和验证文档，确保代码与唯一事实源一致。
8. 完成定向测试、全量回归、静态检查、构建和相对基线 `fd369cc` 的规格/规范双轴审查。

## 实际修改的文件树

```text
.scratch/ui-catalog-providers/
├── issues/03-comparison-report-and-evidence.md # 03 任务状态、范围和验收证据
├── implementation-map.md                      # 03 实现落点和复用边界
├── plan.md                                    # 阶段状态和停点
├── spec.md                                    # 已发布范围与后续未授权边界
└── verification.md                            # 03 实际验证证据
apps/backend/tests/jobs/
├── cancellation/test_cancel_races.py          # 仅按现行 Ruff 规则机械格式化
└── reporting/test_matrix_rehearsal.py         # 仅按现行 Ruff 规则机械格式化
apps/web/
├── src/
│   ├── app/globals.css                        # 桌面/手机矩阵布局
│   ├── features/
│   │   ├── jobs/reporting/                    # 对比页的深层实现目录
│   │   │   ├── comparison.tsx                 # 页面编排、选择与请求状态
│   │   │   ├── configuration.tsx              # 冻结配置差异
│   │   │   ├── matrix.tsx                     # 题目 × 配置矩阵及单次钻取
│   │   │   └── metrics.tsx                    # 有来源语义的用量/资源汇总
│   │   ├── jobs/report.tsx                    # 单次失败通俗说明与折叠技术详情
│   │   └── workbench/shell.tsx                # 既有工作台导航入口
│   └── lib/
│       ├── api-client.ts                      # 对比请求的统一客户端错误语义
│       ├── contracts.ts                       # Web 侧既有接口类型
│       └── reporting/
│           ├── comparison-client.ts           # 对比接口与有限并发 Run 报告加载
│           └── comparison-shape.ts            # 运行时响应校验和类型
└── tests/reporting/
    ├── comparison.spec.ts                     # 真实接口与混合状态浏览器验收
    ├── comparison-permissions.spec.ts         # owner/协作者可见范围回归
    └── comparison-semantics.spec.ts           # 分配置、未知和异步竞态回归
docs/
├── actions/2026-09-21-ui-comparison-report.md # 本行动记录
├── architecture/DATA_MODEL.md                 # 说明 03 不改变持久化模型
├── architecture/modules/web-and-http/ARCHITECTURE.md
├── architecture/modules/evidence-and-reporting/ARCHITECTURE.md
└── interfaces/HTTP_API.md                     # 对比页复用的 HTTP 合同
HANDOFF.md                                     # 当前恢复入口与验证状态
```

所有动态源文件保持不超过 200 行；未新增顶层模块、API 或数据库表。

## 设计关系

- 模式：现有 HTTP 适配器 + 展示组件分层。
- `comparison-client.ts` 是服务端合同的浏览器适配器；它只请求既有端点并限制并发。
- `comparison.tsx` 负责页面状态，不重算后端业务结论。
- `matrix.tsx`、`configuration.tsx`、`metrics.tsx` 是展示组件，分别消费后端矩阵、冻结 Job 快照和 Run 报告。
- 单次详情直接复用现有 `RunReportView`/`EvidenceView`，不复制证据规则。

## 验证方式与成功标准

- TDD 红灯：新增 03 浏览器用例在基线实现上因缺少对比入口/页面而失败。
- 定向绿灯：03 浏览器测试覆盖混合成功、未通过、基础设施故障、取消/未完成、缺失报告；缺失不计入未通过，0 与未知不同。
- 请求约束：用量仅由用户触发，Run 报告加载并发上限可由测试观察，不出现一屏 60 个无界请求。
- 钻取：桌面和手机均可从有报告的单元格进入详情、查看确定性结果与轨迹并下载制品；缺失单元格没有伪造交互。
- 权限：owner/collaborator 的可见性仍由后端决定，不新增 Key 页面。
- Web：`npm run typecheck`、`npm run build`、`npm run test:e2e` 全部通过。
- 后端：报告相关定向测试、默认全量测试、静态检查通过；需要持久化门禁时仅使用随机命名的隔离数据库/桶，不写共享业务库。
- 仓库：`git diff --check`、源文件行数/目录文件数检查、文档链接与状态检查通过。
- 代码评审：相对 `fd369cc` 的 Standards 与 Spec 两轴没有未处置的高优先级问题。

## 自验证情况

- TDD：基线页面因没有“对比报告”导航而形成真实红灯；新增语义回归又复现“较旧单次报告覆盖最后点击”的红灯，修复后转绿。
- 03 浏览器定向：`comparison.spec.ts` 3 项、`comparison-permissions.spec.ts` 1 项、`comparison-semantics.spec.ts` 2 项均通过。覆盖五档结果、缺失语义、按配置指标、0/未知、最多 3 并发、刷新收敛选择、最后点击优先、同一 Job 多配置、部分快照不误报差异、手机钻取、轨迹及下载。
- Web 全量：`npm run test:e2e` 按每个 spec 独立合成后端运行，38 项全部通过；`npm run typecheck` 通过；最终 `npm run build` 在默认 `.next` 配置下成功生成 4 个静态页面。
- 后端定向：报告相关测试 16 项通过、2 项按显式 PostgreSQL 门禁跳过。
- 后端默认全量：使用仓库内唯一临时 `basetemp` 运行，415 项通过、81 项按显式 PostgreSQL/MinIO/Harbor/Fork/Codex 环境门禁跳过，2 条既有警告；没有把跳过记成通过。
- 专属 PostgreSQL + MinIO Job 门禁：用项目自带 `pwsh` 运行 `tests/jobs/runtime/verify.ps1`，175 项通过、2 条既有警告；测试容器和 tmpfs 已精确删除，镜像/缓存保留。未连接或写入共享业务库。
- 静态检查：Ruff check 通过；Ruff format 在机械格式化 2 个基线测试文件后报告 295 个文件均已格式化；Mypy 检查 168 个源码文件通过。
- 仓库检查：动态源文件均不超过 200 行，相关目录直属文件不超过 8 个；未新增 API、数据库表或顶层业务 Module。`git diff --check` 无空白错误；换行转换提示不属于校验失败。
- 双轴审查相对固定基线 `fd369cc` 执行。首轮发现按配置指标、未知差异、完整限制、最后点击、刷新选择和文档状态问题，复审又发现同一 Job 多配置与指标加载竞态；均已修复并增加回归。最终 Standards PASS、Spec PASS，未留未处置发现。
- 用户虽允许测试使用 `auth.json`，本轮确定性合成/隔离门禁已覆盖 03，故未读取该文件、未调用模型、真实模型用量为 0。

## 偏差与遗留风险

- 首次浏览器红灯运行被既有 `.next/trace` 的 Windows ACL 拒绝；切换隔离构建目录和系统 Chrome 后取得真实产品红灯。最终配置已恢复默认 `.next` 并完成全量浏览器、类型和生产构建复验；`.next` 仅是 Git 忽略的标准构建输出。
- 仓库级 `ruff format --check` 发现基线中的 `test_cancel_races.py` 与 `test_matrix_rehearsal.py` 未格式化；纳入本轮机械修复，不改变测试语义。
- 直接把当时的全部报告 spec 放进同一个 Playwright 进程会共享合成后端状态，曾得到 4/5 通过；项目权威 `npm run test:e2e` 会逐 spec 重启后端，新增多配置用例后的最终隔离结果为 38/38。该中间失败不冒充产品回归。
- 默认 pytest 首次使用系统临时目录时遭 Windows ACL 拒绝，后改用仓库内唯一临时目录完成 415/415 个实际收集且未跳过的用例；专属脚本首次在 Windows PowerShell 5 因缺少所需加密 API 而未创建容器，改用项目自带 `pwsh` 后通过并完成精确清理。
