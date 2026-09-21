# 核心代码诊断报告（2026-09-21）

## 1. 审查结论

- 审查基线：`main` / `c71d342041e45c63dad91883b6d4bb33289b0ec3`。
- 结论：**有条件通过，建议在扩大 Agent 能力前先修复 P1 项**。本轮没有发现已经由现有测试复现的阻断级故障，也没有发现明显的跨层反向依赖、前端危险 HTML 注入或 `shell=True` 命令执行；但比较页面存在可由请求乱序触发的陈旧结果回写，HTTP 500 路径会吞掉内部异常证据，当前权威文档与实现多处不一致。
- 本轮只审查并测量，没有修改业务代码或测试代码。唯一项目规则变更是按用户授权在 `AGENTS.md` 写入历史档案边界；本报告及对应行动文档是审查产物。
- 工作量均为一名熟悉项目的工程师在现有测试基础上的净工时估算，不包含需求等待、外部服务申请、真实模型额度或部署窗口。

### 优先级

| 等级 | 含义 |
|---|---|
| P1 | 会产生误导性结果、丢失关键诊断证据，或让权威事实源失真；建议下一轮优先处理 |
| P2 | 当前可运行，但会显著增加回归、扩展或维护风险 |
| P3 | 硬化与体验改进；可排入后续维护窗口 |

## 2. 范围与方法

审查覆盖 Python 后端、Next.js/TypeScript 前端、PowerShell/Docker 本地基础设施、自动化测试，以及应随代码保持齐平的架构、数据模型、接口、依赖和运维文档。代码库存快照如下：

| 类型 | 文件数 | 行数 |
|---|---:|---:|
| Python | 168 | 12,554 |
| TypeScript | 17 | 1,492 |
| TSX | 26 | 1,849 |
| PowerShell 脚本 | 4 | 186 |
| PowerShell 模块 | 3 | 438 |
| Shell | 1 | 26 |

检查维度包括模块边界、正确性、异步竞态、异常处理、安全、性能、可维护性、测试充分性，以及代码—权威文档一致性。`docs/actions/` 已结束行动文档和 `docs/research/` 已完成研究文档仅作为历史证据读取，不按当前实现反向改写。

审查期间另一个任务持续修改 `HANDOFF.md`、部分规划/架构/行动/进度文档和 `.scratch/ui-catalog-providers/`。这些文件不是稳定快照，本报告冻结它们，不对其当前内容作最终一致性判断；核心代码的 `HEAD` 在审查期间未变化。

## 3. 问题总览

| 编号 | 优先级 | 模块定位 | 问题 | 修复方向 | 预计工时 |
|---|---|---|---|---|---:|
| CR-01 | P1 | Web / Job 比较报告 | 清空选择后，较早发出的比较请求仍可回写陈旧矩阵 | 为比较链路增加请求代次或取消机制，并补延迟响应回归测试 | 2–4 小时 |
| CR-02 | P1 | HTTP 交付层 / 异常处理 | 未预期异常被转换为 500，但没有内部日志或关联 ID | 记录脱敏结构化异常，保留通用客户端响应并测试两侧行为 | 2–4 小时 |
| CR-03 | P1 | 当前权威文档 | 架构、数据模型、接口、依赖文档与已实现代码相互矛盾 | 以代码和实测为依据修订当前文档；历史档案保持只读 | 3–6 小时 |
| CR-04 | P2 | 后端类型检查配置 | 文档化的无参数 `mypy` 入口失败，显式传源码路径才通过 | 修正 Mypy 文件/包目标或补齐包标记，让默认命令可复现 | 0.5–1.5 小时 |
| CR-05 | P2 | 测试与质量门禁 | 根目录 Pytest 会误收集虚拟环境；基础设施 mark 未注册；缺少统一 CI、Web lint、覆盖率和 Python 依赖审计 | 建立根级测试边界及最小 CI 质量矩阵 | 4–10 小时 |
| CR-06 | P2 | 外部集成验证 | PostgreSQL、MinIO、Docker、Harbor、Fork、真实提供方等本轮被环境门控跳过 | 在隔离环境运行明确的集成档位并保存本轮证据 | 2–6 小时起 |
| CR-07 | P2 | Agent 配置与执行链 | 当前模型从数据库到 Worker 都固定为 Codex/OpenAI；扩展 Agent 不是仅加一个预设 | 先确定提供方契约，再成套迁移 schema、领域快照、API、执行映射和测试 | 16–32 小时起 |
| CR-08 | P2 | 任务适配器及复杂度热点 | 一个动态语言源文件超过 200 行，数个安全/状态函数复杂度偏高 | 用测试锁定行为后提取策略、验证器或状态表，不改变外部接口 | 8–16 小时（热点） |
| CR-09 | P3 | 测试依赖兼容性 | FastAPI/Starlette TestClient 与 AnyIO 出现弃用警告 | 核对官方兼容范围后固定兼容版本或升级调用方式 | 1–3 小时 |
| CR-10 | P3 | Web/HTTP 安全响应头 | Web 仅关闭 `X-Powered-By`，统一安全响应头策略尚未形成 | 结合实际 HTTPS 反代补 CSP、frame、referrer、permissions 等策略及浏览器测试 | 2–4 小时 |

以上估算彼此可能重叠，不能简单相加。CR-07 是后续扩展目标的独立规模，不属于本轮修复工时。

## 4. 详细诊断

### CR-01：比较结果存在异步竞态

- 问题定位：`apps/web/src/features/jobs/reporting/comparison.tsx:32` 只为打开详情和指标请求维护代次；`resetResult()`（52–55 行）没有使比较请求失效；`compare()`（66–79 行）在两个 `await` 后无条件执行 `setMatrix` / `setDetails`；“清空选择”（115 行）在请求进行时仍可点击。
- 模块定位：Web → Job reporting → comparison。
- 影响：用户发起比较后立即清空或更换选择，旧响应到达时仍会恢复已过期矩阵和详情。页面展示的数据可能与当前选择不一致，属于结果可信度问题。
- 修复方向：增加 `compareRequest` 代次、`AbortController` 或二者组合；在重置及新请求时使旧请求失效，并在每个异步阶段后核对代次。用延迟路由的 Playwright 用例覆盖“开始比较 → 清空/重选 → 旧响应返回”。
- 预计工时：2–4 小时。

### CR-02：安全的 500 响应缺少服务端诊断

- 问题定位：`apps/backend/src/eval_platform/delivery/http/app.py:102-106` 捕获广义 `Exception` 后直接返回通用 500，没有记录异常、请求方法/路径或关联 ID。
- 模块定位：后端 → HTTP 交付层 → 全局错误边界。
- 影响：客户端没有泄露内部细节是正确的，但数据库、驱动或适配器异常会失去可追踪证据，运维只能看到 500，难以区分故障来源。
- 修复方向：在异常边界使用 `logger.exception` 写入脱敏的结构化字段（方法、规范化路径、请求/关联 ID），客户端继续只收到稳定错误码和通用消息；不得记录凭据、Cookie、请求秘密或堆栈到客户端。测试同时断言“客户端不泄密”和“内部诊断存在”。
- 预计工时：2–4 小时。

### CR-03：当前权威文档与代码漂移

- 问题定位：
  - `docs/architecture/ARCHITECTURE.md:76,314` 仍把已实现的 `continuous` 规模称为待实现；同文档 764–768 行的设计模式表引用不存在的 `ports/execution.py`、`adapters/execution/process.py`、`application/submit_job.py` 等路径。
  - `docs/architecture/modules/catalog-and-configuration/ARCHITECTURE.md:3,77` 对任务数量分别描述为 1 和 6；代码目录当前登记 6 项。
  - `docs/architecture/DATA_MODEL.md:10` 仍称五道新题未完成，但代码和预设已有 6 项。
  - `docs/interfaces/HTTP_API.md:365,427` 对 `continuous` 的预设列表前后不一致。
  - `docs/dependencies/DEPENDENCIES.md:49,213-218` 对当前任务镜像范围存在旧状态与新清单并存。
  - 历史记录曾把 `apps/backend/src/eval_platform/adapters/tasks/swe_gym.py` 记为 198 行，当前文件为 202 行。历史记录应保持原样，当前架构/质量状态需另行反映真实值。
- 模块定位：项目治理 → 架构、数据模型、HTTP 接口、依赖权威文档。
- 影响：新任务或 Agent 会基于错误路径和旧能力边界设计，代码审查也无法判定哪一份描述是当前事实。
- 修复方向：代码行为、数据库约束和本轮测试作为事实依据，只修订描述当前系统的权威文档；已结束 `docs/actions/` 和已完成 `docs/research/` 永不反写。并发任务正在改动的文档应在其稳定后重新对照，而不是在本轮覆盖。
- 预计工时：3–6 小时。

### CR-04：默认 Mypy 命令不可复现

- 问题定位：`apps/backend/pyproject.toml:57-60` 的 Mypy 配置使用 `packages = ["eval_platform"]`。从后端目录运行无参数 `mypy` 报错：`Package 'eval_platform' cannot be type checked due to missing py.typed marker`；显式运行 `mypy src prototype_codex_harbor_e2e.py` 则 169 个源文件全部通过。`docs/LYQ/06-environment/LOCAL_SETUP.md:65-69` 已记录显式路径绕行，但默认入口仍坏。
- 模块定位：后端 → 静态类型检查配置。
- 影响：开发者和 CI 按标准入口执行会得到失败，而绕行命令依赖文档记忆，容易造成“有人认为已检查、有人认为工具坏了”的分歧。
- 修复方向：在 `pyproject.toml` 使用与 `src` 布局匹配的 `files` / `mypy_path`，或在确实要按已安装包检查时补齐正确包标记；修复后删除绕行语义并确保无参数命令覆盖相同 169 个源文件。
- 预计工时：0.5–1.5 小时。

### CR-05：测试和质量门禁碎片化

- 问题定位：从仓库根目录运行 Pytest 会收集 `.venv` 和第三方测试，出现 690 个收集错误；从 `apps/backend` 正确运行则通过。基础设施套件报告两个未知 `integration` mark 警告。仓库没有统一 CI 配置，Web 没有 ESLint/lint 脚本，Python 没有可用的覆盖率和依赖漏洞审计工具。
- 模块定位：全项目 → 测试发现、静态检查、CI。
- 影响：质量依赖操作者知道正确工作目录和隐含命令；新增模块可能未进入任何门禁。覆盖率和 Python 依赖安全是“未知”，不能据现有结果声称达标。
- 修复方向：添加根级 Pytest 配置或明确 `testpaths` / `norecursedirs`，统一注册 mark；建立最小 CI 矩阵（Ruff、format、Mypy、后端/基础设施测试、Web type/build/E2E、npm audit），再评估 ESLint、覆盖率阈值与 Python 依赖审计。先让门禁可复现，不在同一改动中机械修完全部风格建议。
- 预计工时：根测试边界 1–2 小时；完整最小门禁 4–10 小时。

### CR-06：外部集成只有历史证据，本轮未重验

- 问题定位：后端本轮 96 项、基础设施 10 项测试因 PostgreSQL、MinIO、Docker、Harbor、Fork、进程树或真实模型等环境门槛被明确跳过。
- 模块定位：持久化、对象存储、执行后端、Worker、真实提供方。
- 影响：单元及本地浏览器链路健康不等于外部适配器当前仍可工作。既有行动文档可证明当时发生过什么，但作为历史档案不能冒充 2026-09-21 的新鲜验收。
- 修复方向：把外部测试划分为可独立授权的档位，在隔离 PostgreSQL/MinIO、Docker/Harbor/Fork、真实提供方环境分别运行并保存新证据；涉及个人登录、额度或机器服务改变时先取得对应授权。
- 预计工时：已有环境下 2–6 小时；真实提供方额度、授权或环境修复另计。

### CR-07：扩展 Agent 会跨越多个硬编码契约

- 问题定位：
  - `apps/backend/src/eval_platform/application/agent_registry.py:33-40`：只接受 Codex、OpenAI ChatGPT、`chatgpt_auth_json` 和 `reasoning_effort`。
  - `apps/backend/src/eval_platform/adapters/persistence/catalog/schema.sql:111-123`：数据库 CHECK 固定同一集合。
  - `apps/backend/src/eval_platform/delivery/http/catalog_schemas.py:50-76`：HTTP schema 使用 Codex/OpenAI 的 `Literal`。
  - `apps/backend/src/eval_platform/domain/jobs/snapshots.py:88-104`：Job 冻结快照固定凭据引用与推理强度形状。
  - `apps/backend/src/eval_platform/adapters/execution/harbor/config_mapper.py:102-120`：Harbor 映射拒绝非 Codex Agent。
  - `apps/backend/src/eval_platform/delivery/worker/runtime.py:13-86`：Worker 启动配置要求 Codex archive 和认证文件。
- 模块定位：目录注册 → PostgreSQL → 领域快照 → HTTP → Harbor 执行 → Worker。
- 影响：后续“扩展 Agent 配置”若只增加 UI/预设，会在持久化约束、运行快照或 Worker 启动阶段失败；服务启动也不会自动迁移旧数据库。
- 修复方向：先明确新 Agent 是仅展示目录、经现有代理协议执行，还是拥有独立运行时。端到端方案必须一次定义提供方/认证公共契约、秘密边界、显式数据库迁移、旧 Job 兼容、执行适配器、报告字段及验证矩阵。
- 预计工时：仅目录展示的假配置约 4–8 小时；具备凭据隔离和显式迁移的端到端提供方约 16–32 小时起。
- 与本次目标的关系：不发生天然冲突；建议以本报告作为扩展目标的输入。若两个任务同时修改上述文件或当前权威文档，则会使审查基线失效，应串行执行或由扩展任务在合并后重新运行受影响检查。

### CR-08：文件上限和复杂度热点

- 问题定位：`apps/backend/src/eval_platform/adapters/tasks/swe_gym.py` 为 202 行，超过项目对动态语言源文件默认 200 行限制，未找到当前例外。补充 Ruff 复杂度扫描还定位到：
  - `adapters/execution/codex/agent.py` 的 `guarded_codex_class`，圈复杂度 26；
  - `adapters/persistence/jobs/state_validation.py` 的 `stored_job_valid`，复杂度 18、18 个返回；
  - `adapters/execution/harbor/lifecycle/monitor.py` 的 `scan`，复杂度 14；
  - `delivery/http/app.py` 的 `create_app`，复杂度 13；
  - `adapters/evaluation/result_mapper.py` 的 `map_evaluation`，复杂度 15。
- 模块定位：任务适配器、Codex 安全守卫、Job 状态验证、Harbor 生命周期、HTTP 装配、结果映射。
- 影响：这些函数集中控制安全边界或状态转换，新增 Agent/状态时更容易遗漏分支。补充扫描得到 85 个复杂度/参数/安全规则提示；它不是当前配置门禁，因此不等同于 85 个确定缺陷。
- 修复方向：先为现有行为补字符化测试，再提取不可变验证策略、状态转换表或窄职责辅助函数；保持现有 port/interface，不以压缩行数替代设计。202 行文件可移动稳定常量或纯映射，不应仅合并代码行。
- 预计工时：202 行越限 0.5–1 小时；优先处理上述热点 8–16 小时。是否纳入下一轮重构应由用户确认。

### CR-09：依赖弃用警告未清零

- 问题定位：后端和浏览器服务测试重复出现 FastAPI/Starlette TestClient 对 HTTPX 接口的弃用警告，以及 AnyIO `BlockingPortal` 别名警告。
- 模块定位：测试基础设施及 Python 依赖锁。
- 影响：当前不导致失败，但依赖升级后可能变成不兼容；重复警告也会掩盖新的告警。
- 修复方向：依据实际锁定版本核对上游兼容矩阵，选择兼容升级或调整测试调用；修复后将已知告警收紧为不可新增，而不是盲目整体升级。
- 预计工时：1–3 小时。

### CR-10：统一安全响应头仍是空白

- 问题定位：`apps/web/next.config.ts:14` 仅设置 `poweredByHeader: false`；后端统一添加 `Cache-Control: no-store` 和 `X-Content-Type-Options: nosniff`，但没有一份覆盖浏览器入口/反向代理的 CSP、frame、referrer、permissions 策略。
- 模块定位：Web 部署边界、HTTP 中间件、HTTPS 反向代理。
- 影响：React 默认转义和现有 CSRF/HTTPS Cookie 测试已经降低主要风险，但部署层缺乏纵深防护和可审计的统一策略。
- 修复方向：先确认生产域名、代理终止点及资源来源，再在唯一边界配置 `Content-Security-Policy`、`frame-ancestors`、`Referrer-Policy`、`Permissions-Policy`；HSTS 只在确认全域 HTTPS 后启用。增加响应头和关键页面浏览器测试。
- 预计工时：2–4 小时。

## 5. 实测结果

| 检查 | 结果 | 说明 |
|---|---|---|
| Ruff lint | 通过 | `src`、`tests`、原型脚本均通过当前配置 |
| Ruff format check | 通过 | 300 个文件保持格式 |
| Mypy 默认入口 | 失败 | 缺少 `py.typed`；见 CR-04 |
| Mypy 显式源码入口 | 通过 | 169 个源文件无错误 |
| 后端 Pytest | 通过 | 424 passed、96 skipped、3 warnings，44.72 秒 |
| 基础设施 Pytest | 通过但有门控 | 11 passed、10 skipped、5 warnings，2.21 秒 |
| 根目录 Pytest | 失败 | 误收集虚拟环境/第三方测试，690 个收集错误；见 CR-05 |
| Web TypeScript | 通过 | `npm run typecheck` |
| Web production build | 通过 | 首页 first-load JS 127 kB；构建成功 |
| Web Playwright | 通过 | 使用项目支持的系统 Chrome：43 passed |
| npm 生产依赖审计 | 通过 | `npm audit --omit=dev`：0 vulnerabilities |
| Python 依赖审计 | 未运行 | 环境无 `pip-audit`，不能声称安全通过 |
| 覆盖率 | 未测量 | 环境无 coverage 工具且项目无阈值 |

补充静态核对结果：

- 领域/应用/适配器之间未发现禁止的反向 import。
- 实际注册的 32 个 HTTP 端点与接口文档的 32 项清单数量一致。
- Web 生产代码未发现 `dangerouslySetInnerHTML`、`innerHTML`、`eval`、`new Function`、`any` 或 `@ts-ignore`；生产 `fetch` 集中在 `src/lib/api-client.ts`。
- Python 未发现 `shell=True`。`adapters/persistence/jobs/execution/common.py:66-80` 的 SQL 字符串插值只接受固定 `{job, run}` 映射，审阅后判定不是可控输入注入。
- 浏览器测试覆盖 HTTPS Cookie、登出重放、过期、写请求/CSRF 头和角色权限；这些是当前安全基线的正向证据。
- Web 构建的 127 kB 首页首载体积低于审查清单采用的 200 kB 提醒线；这只是当前构建测量，不代表所有运行时性能已验收。

## 6. 建议修复顺序

1. 先处理 CR-01、CR-02、CR-03、CR-04，预计约 8–14 小时；完成后重跑当前全套检查。
2. 再处理 CR-05，并为 CR-06 选择需要授权的集成档位；不要把历史行动结果当本轮运行证据。
3. 扩展 Agent 前，以 CR-07 的跨模块清单建立独立规格和迁移行动；避免与上述文件的修复并行落地。
4. CR-08 作为单独的可维护性任务征得范围确认后执行；CR-09、CR-10 可进入后续硬化窗口。

## 7. 并发任务与报告有效性

本报告对固定提交 `c71d342041e45c63dad91883b6d4bb33289b0ec3` 有效。审查期间观测到的并发任务仅修改文档和草稿，没有改动核心代码，所以没有阻止本轮完成。以下任一情况发生后，应重审受影响模块而不是继续沿用本结论：

- Agent 注册、catalog schema、Job snapshot、Harbor mapper、Worker runtime 或比较页面发生修改；
- 当前架构/接口文档完成并发合并；
- 数据库迁移或真实提供方契约改变；
- 依赖锁、测试发现配置或执行环境改变。
