# 核心诊断问题全量修复行动

## 状态与情况说明

- 状态：进行中。
- 来源：用户要求先本地提交当前工作区，再拉取远端新代码；对远端增量做 Spec/Standards 双轴诊断并更新诊断报告，随后修复报告中的全部问题并完成本地提交。
- 本地检查点：`859f1316a3204822f01c8f6a12a41eb7e2a7e6d4`。
- 拉取后合并基线：`3676d7412065e335e2c88ef586cc0fb3ad69af0a`；远端增量固定比较命令为 `git diff 859f131...3676d74`。
- 已确认事实：远端加入任务 05 的 provider-access 策略层、受控 `internal_test` 身份和 T1 探针；合并冲突已经按两侧事实解决。Ruff 通过、显式 Mypy 通过 176 个源文件、目标测试 80 passed / 4 skipped。
- 增量诊断：Standards 轴发现 2 组硬违规与 1 个判断项；Spec 轴发现 2 个实现错误、1 个范围扩张及 1 组计划内未完成项。诊断报告必须先更新，之后才修改业务代码。
- 顺序门禁已完成：`docs/reviews/2026-09-21-core-code-diagnostic-report.md` 已先更新到拉取后固定点，独立保留 Standards/Spec 两轴结论，并新增 CR-11 至 CR-13；截至该更新完成尚未修改业务代码。
- 明确边界：已结束 `docs/actions/` 和已完成 `docs/research/` 是只读历史档案；远端对既有行动文档的追加只作为增量审查事实记录，不在本轮反向改写。不会读取或调用真实提供方凭据，不充值，不把未获授权的真实模型运行作为修复手段。
- 用户现有未跟踪 `.scratch/ui-catalog-providers.zip` 与 `apps/web/%USERPROFILE%/` 不修改、不暂存。
- 待用户决定：完整 CI 需要新增顶层 `.github/workflows/`；已说明现有目录不能承载 GitHub Actions，并推荐允许。本行动在收到答复前先完成其他修复。

## 实施措施

1. 将拉取后的固定点、Standards/Spec 两轴结论、新增问题和已改变的 CR-07 状态写入诊断报告，不混合或重排两轴结论。
2. 为可复现缺陷建立快速、确定且能失败的回归测试：比较请求乱序、HTTP 500 内部诊断、错误 Host 剥离、provider/auth 成对约束、根级测试发现、响应安全头。
3. 修复 P1 正确性与诊断问题：比较请求代次、脱敏异常日志、当前权威文档漂移、默认 Mypy 入口。
4. 修复任务 05 增量问题：请求头白名单、领域/数据库身份对约束、任务 05 只允许受控假上游、类型化或单一来源错误码；保持真实 DeepSeek/Kimi 为后续 06/07 范围。
5. 建立可复现质量入口：根级 Pytest 边界、基础设施 mark、Web lint、覆盖率和 Python 依赖审计；若用户允许，再新增最小 GitHub Actions 工作流。
6. 用行为测试保护后拆分 `swe_gym.py` 及报告列出的复杂度热点，保持既有 port/interface、状态和安全语义。
7. 消除测试依赖弃用警告，加入 Web/HTTP 安全响应头及浏览器验证。
8. 在不调用真实供应商的前提下运行可用的 PostgreSQL、MinIO、Docker/T1、Harbor/Fork 集成档位；未获授权或缺环境的档位如实保留为限制。
9. 同步当前架构、接口、依赖、运维、交接和任务状态文档；不修改历史行动/研究档案。
10. 运行全量静态检查、单元/集成/浏览器测试、依赖审计和文档一致性检查；更新诊断报告与本行动的实际结果，完成本地提交。

完成标准：报告中的每项问题均有“已修复并验证”或不可由代码修复的明确限制；新增 Spec 问题有回归测试；当前权威文档与代码齐平；所有实际运行结果可复查；业务变更完成本地提交但不推送。

## 受影响文件树

```text
docs/
├─ actions/2026-09-21-core-diagnostic-remediation.md
│  本次诊断更新、修复、偏差和验证的唯一行动记录。
├─ reviews/2026-09-21-core-code-diagnostic-report.md
│  更新固定点、双轴诊断、新增问题及最终处置状态。
├─ architecture/ARCHITECTURE.md
├─ architecture/DATA_MODEL.md
├─ architecture/MODULE_CONTRACTS.md
├─ architecture/modules/catalog-and-configuration/ARCHITECTURE.md
├─ architecture/modules/job-control/ARCHITECTURE.md
├─ interfaces/HTTP_API.md
├─ interfaces/CODEX_AUTHENTICATION.md
├─ dependencies/DEPENDENCIES.md
└─ operations/（按实际影响更新）
   当前权威架构、接口、依赖和运维事实；历史 actions/research 不修改。

.scratch/ui-catalog-providers/
├─ issues/05-fake-provider-secure-execution-chain.md
├─ plan.md
├─ implementation-map.md
└─ verification.md
   当前任务规格、状态和验收映射；历史 Comments 保留，顶部现状同步。

HANDOFF.md
  当前恢复入口，移除与新代码冲突的旧状态。

pytest.ini
  根级测试发现边界与共享 mark，避免收集虚拟环境/第三方代码。

apps/backend/
├─ pyproject.toml / uv.lock
│  默认 Mypy 目标、覆盖率、依赖审计及兼容测试依赖。
├─ src/eval_platform/delivery/http/app.py
│  HTTP 错误边界、关联 ID 与统一安全响应头。
├─ src/eval_platform/adapters/execution/provider_access/
│  请求头策略、受控错误类型、假上游范围、秘密读取与预算不变量。
├─ src/eval_platform/domain/agent.py
├─ src/eval_platform/application/agent_registry.py
├─ src/eval_platform/adapters/persistence/catalog/{schema.sql,__init__.py}
│  受控身份的单一来源、领域校验、数据库成对约束与显式迁移。
├─ src/eval_platform/adapters/tasks/swe_gym.py
├─ src/eval_platform/adapters/execution/codex/agent.py
├─ src/eval_platform/adapters/persistence/jobs/state_validation.py
├─ src/eval_platform/adapters/execution/harbor/lifecycle/monitor.py
├─ src/eval_platform/adapters/evaluation/result_mapper.py
│  报告指定的文件上限与复杂度热点；只在测试保护下提取窄职责实现。
└─ tests/
   对应回归、架构、迁移、日志、安全和复杂度行为测试。

apps/web/
├─ package.json / package-lock.json
│  可复现 lint 脚本与依赖锁。
├─ next.config.ts
│  浏览器安全响应头。
├─ src/features/jobs/reporting/comparison.tsx
│  比较请求代次与陈旧响应防护。
└─ tests/
   乱序比较与安全响应头浏览器回归。

infrastructure/
└─ tests/（仅按现有结构调整 mark/config）
   基础设施测试入口。

.github/workflows/quality.yml（待用户确认）
  GitHub Actions 最小质量矩阵；不承载业务逻辑。
```

- 不新增业务顶层 Module、应用 Interface 或数据库表。
- provider-access 继续作为 Execution Adapter 的内部实现；数据库只深化既有 `agent_configurations` 约束。
- 复杂度拆分优先使用私有辅助函数、不可变策略或状态表，不建立没有第二实现的抽象层。

## 自验证方式

- Git：固定点与提交清单复核、`git diff --check`、冲突标记扫描、只暂存本行动拥有的文件。
- 后端静态：无参数 `mypy`、Ruff lint、Ruff format check；补充复杂度扫描用于确认指定热点下降。
- 后端测试：先运行每个红—绿回归用例，再运行默认全量；集成档位按实际环境和授权分别记录。
- 前端：lint、TypeScript、生产构建、Playwright 全量、`npm audit --omit=dev`。
- 安全与依赖：Python 依赖审计、响应头断言、秘密/错误文案扫描、provider-access 负例矩阵。
- 文档：检查当前架构文件树、端点/枚举/约束和任务状态与代码一致；历史档案无本轮改动。

成功标准：所有新增回归先能捕获对应缺陷，修复后通过；全量检查无未解释失败；跳过、环境限制和未授权真实提供方检查不描述为通过。

## 自验证结果

### 后端修复节点（进行中）

- 先建立并观察到失败的回归：比较页陈旧请求回写、HTTP 500 请求关联
  ID、错误出站头、provider/auth 非法组合、预算超预留用量、私密文件替换
  竞态及安全响应头；修复后对应定向测试均转绿。
- provider access 现在只允许 `internal_test_fake`，使用最小出站头允许集合、
  类型化内部错误和竞态安全的私密文件读取；没有调用真实供应商。
- `AgentConfiguration` 与 PostgreSQL 使用同一合法身份对不变量；临时隔离的
  PostgreSQL 实例实测迁移和非法组合拒绝为 `2 passed`，实例随后删除。
- Ruff lint、Ruff format、无参数 Mypy（177 个源文件）通过；复杂度
  `C901 > 10` 从 9 个热点降为 0；生产 Python 文件均不超过 200 行。
- 后端风险定向回归在沙箱外使用独立临时目录完成：
  `207 passed, 23 skipped`。跳过项是未配置的 PostgreSQL/MinIO 档位以及
  Windows 不支持的 POSIX 权限/符号链接能力；不描述为通过。
- Windows 沙箱内运行同组测试时，Pytest 临时目录被 ACL 拒绝；该次仅作为
  环境失败记录，不计入测试通过结果。

### Web 与质量门禁节点（完成）

- 新增可复现 ESLint 9 flat config；`npm run lint` 与
  `npm run typecheck` 通过，生产源文件均不超过 200 行。
- 使用隔离的 `.next-e2e` 构建目录完成 Next.js 生产构建，避免触碰用户正在
  使用的默认 `.next` 开发目录；构建成功并生成 4 个静态页面。
- 完整 Playwright 清单为 45 项 / 24 个规格文件，使用本机 Chrome 全部通过；
  包含新增的比较请求乱序和浏览器安全响应头回归。默认 Playwright 二进制未
  安装的首次启动只作为工具限制记录，不计入失败断言。
- 浏览器启动器会在成功或失败时恢复 Next 自动改写的 `next-env.d.ts` 与
  `tsconfig.json`；删除构建产物后的类型检查和单规格复测均通过。
- `npm audit --omit=dev --audit-level=low` 与全依赖
  `npm audit --audit-level=low` 均报告 `0 vulnerabilities`。
- Python 全量测试、覆盖率、Python 依赖审计和权威文档齐平仍待后续节点完成。
