# AgentExam 项目阅读路线

> 整理日期：2026-09-17。
> 用途：帮助项目所有者把现有代码放回架构地图，理解进度、修改原因和阻塞位置。
> 本文是阅读导航，不是新的架构决定、实现计划或验收清单。当前状态看 [HANDOFF](../../HANDOFF.md)，模块职责看 [MODULE_CONTRACTS](./MODULE_CONTRACTS.md)。

## 1. 怎样使用这份指南

按第 3 节顺序阅读，每一步能用自己的话回答“完成标志”，就可以停下来或继续下一步，不必先读懂所有代码。勾选表示理解进度，不表示程序测试或 M0/MVP 验收通过；初始均未勾选，不推断你已经读懂哪些部分。

先建立三种区别：

- 架构规划不等于当前已实现清单。目标文件树里有路径，不代表文件已经存在。
- 程序中的对象不等于数据库表；本地保存 JSON 也不等于已接入 PostgreSQL/MinIO。
- 新增几个代码文件不等于新增几个业务模块；安装、网络、进程和清理可能都属于同一执行模块内部。

当前七个职责的现实代码地图、依赖方向和缺口先查[模块架构索引](./modules/README.md)；字段与错误仍查模块契约。下方第 2–4 节保留为 M0 执行链入门路线，不是完整 M1 代码清单。本指南不另外维护运行成绩、测试数量或验收进度。

## 2. 先拿到“模块—代码”地图

完整当前地图先按[七个模块文档](./modules/README.md#2-七个当前模块)选择职责；下表只是一条适合初学者理解“执行与判卷”的 M0 阅读入口，不是模块全部完成的声明。模块契约以[模块总表](./MODULE_CONTRACTS.md#5-模块总表)为准。

| 架构模块 | 先从哪里读 | 带着什么问题读 |
|---|---|---|
| Task Catalog：任务目录 | [swe_gym.py](../../apps/backend/src/eval_platform/adapters/tasks/swe_gym.py) 中的 `SWEGymTaskSource.load()` | 固定题目怎样读取？公开题目与判卷专用数据在哪里分开？ |
| Execution Backend：执行后端 | [Harbor Adapter](../../apps/backend/src/eval_platform/adapters/execution/harbor/adapter.py) 的 `execute()` | 项目请求怎样转成 Harbor 运行？如何拿回补丁、过程记录和执行状态？ |
| Patch Evaluator：补丁判卷 | [swe_bench.py](../../apps/backend/src/eval_platform/adapters/evaluation/swe_bench.py) 的 `evaluate()` | 为什么要独立判卷？如何保证使用同一份补丁和固定框架？ |
| Job Orchestrator：流程编排 | [原型入口](../../apps/backend/prototype_codex_harbor_e2e.py) 的 `run_prototype()` | 当前单题流程怎样串联执行和判卷？哪些完整平台职责不在这里？ |
| Trajectory Recorder / Artifact Store：过程记录与证据存储 | [输出映射](../../apps/backend/src/eval_platform/adapters/execution/harbor/result_values.py)与[结果对象](../../apps/backend/src/eval_platform/domain/result.py) | 当前怎样引用轨迹与文件？这与完整统一记录服务、MinIO 存储还有什么区别？ |

另外两类是共同基础，不是单独的产品页面或业务流程：

- [domain](../../apps/backend/src/eval_platform/domain/)：题目、Agent 配置、结果等对象及其规则。
- [application/ports](../../apps/backend/src/eval_platform/application/ports/)：模块之间的调用约定，约定交入什么、交回什么；不是浏览器 HTTP 接口。Adapter 是把外部工具转换成这些约定的适配实现。

[Codex 安装/权限/上传](../../apps/backend/src/eval_platform/adapters/execution/codex/)、[网络适配](../../apps/backend/src/eval_platform/adapters/execution/network.py)、[进程执行](../../apps/backend/src/eval_platform/adapters/execution/harbor/process_runner.py)都先放回 Execution Backend 理解，不把每个内部文件当成一个新的顶层模块。

## 3. 按这个顺序阅读

### 第一步：先知道项目现在在哪

- [ ] 我能说明最近新增了什么能力、当前在做什么或为什么暂停、下一步是否已经确定。

**阅读范围：** [HANDOFF 第 1 节](../../HANDOFF.md#1-目标与当前阶段)、[第 2 节](../../HANDOFF.md#2-当前阻塞与授权边界)、[第 6 节](../../HANDOFF.md#6-下一窗口的工作顺序与验收)。

这次只需要回答三个问题：

1. 最近完成的是哪项真实能力，而不只是改了哪些文件？
2. 当前是正常开发、技术卡住、等待决定，还是主动暂停？
3. 下一步准备改变什么，是否已经获准？

可先跳过完整历史命令和全部源码阅读清单。Handoff 的开发者必读要求仍然有效，但不是要求你掌握全局前先完成的作业。

完成标志：能用三句话复述当前阶段、正在做的事和下一步边界。

### 第二步：把能力放回架构图

- [ ] 我能把当前主流程对应到模块，并说明每个模块不负责什么。

**阅读范围：** [总架构第 4 节](./ARCHITECTURE.md#4-总体架构)、[第 5 节](./ARCHITECTURE.md#5-一次运行的输入输出)、[第 7 节](./ARCHITECTURE.md#7-为什么选择这个架构)，以及[模块总表](./MODULE_CONTRACTS.md#5-模块总表)。

结合第 2 节的代码地图，关注：题目从哪里来、执行由谁负责、补丁由谁判、证据由谁保存。尤其弄清为什么 Harbor 不直接决定最终 `resolved`（题目是否被修好）。

可先跳过完整规划文件树的逐路径记忆、所有字段和 P2 扩展细节。不熟悉项目词语时按需查 [CONTEXT](../../CONTEXT.md)。

完成标志：面对“模型连不上”和“补丁没修好”，能说明它们为什么不是同一种问题，也不由同一个模块给结论。

### 第三步：沿一条成功流程读代码

- [ ] 我能复述 `run_prototype()` 的成功路径，并指出执行和判卷的交接位置。

**阅读范围：** [原型入口](../../apps/backend/prototype_codex_harbor_e2e.py)中的 `run_prototype()`，先不读底部 `main()` 的命令行处理。

按函数内的顺序找：

1. 收到什么请求和题目，以及单题、身份一致等检查。
2. 哪里调用 `execution.execute(request)`，拿回什么结果。
3. 为什么还要调用 `_read_patch()` 检查补丁的身份、大小和哈希。
4. 哪里把补丁交给 `evaluator.evaluate(...)`，判卷专用题目数据从哪里来。
5. 哪里保存执行、判卷和最终结果。

再读[执行接口](../../apps/backend/src/eval_platform/application/ports/execution.py)中的 `ExecutionBackend` 和[判卷接口](../../apps/backend/src/eval_platform/application/ports/evaluator.py)中的 `PatchEvaluator`。先理解输入输出，再按需要读请求类型；对象不懂时返回[题目对象](../../apps/backend/src/eval_platform/domain/task.py)或[结果对象](../../apps/backend/src/eval_platform/domain/result.py)。

第一遍可跳过异常分支、安装细节、底层网络规则和资源清理。想了解某一步内部怎样完成，再进入第 2 节对应 Adapter，不一次追完所有调用。

完成标志：能指出“执行完成不等于补丁正确”，并找到代码中分别检查这两件事的位置。

只阅读，不直接运行该脚本、历史启动脚本或测试；阅读计划不授予模型/Docker 调用许可。

### 第四步：用测试理解规则，用行动记录理解曲折

- [ ] 我能从测试说出至少一个失败边界，并从历史记录区分现象、原因和修复证据。

**先读测试：** [编排契约测试](../../apps/backend/tests/contract/test_m0_pipeline.py)。契约测试就是检查模块是否遵守约定的测试；先看 `scenario` 场景名称和 `assert` 断言，不必先学会整个测试框架。

优先跟踪三个问题：

- 执行失败时，为什么不能继续把部分补丁当作成功产物判卷？
- 补丁内容或哈希改变时，怎样阻止证据串错？
- 补丁没有修好，与判卷程序没能形成可信结果，有什么区别？

再回到 `run_prototype()` 看对应的判断和异常分支。测试使用替身还是实际外部工具，要看其实现和开关，不能仅凭“通过”二字认定真实模型通过。

**再查历史：** 先用 [Handoff 开发历程索引](../../HANDOFF.md#11-上一窗口的开发历程索引)定位事件，再读 [M0 行动记录](../actions/2026-09-05-m0-codex-harbor-implementation.md)中的对应段落。只跟一件事的“情况 → 措施 → 实际结果”，不从头追整本记录。

完成标志：能说明某次失败发生在哪一步、当时原因是否已经证实、改了哪里、怎样证明修复；不会把历史失败自动当成当前阻塞。

### 第五步：再把主流程对应到数据模型

- [ ] 我能解释主要数据之间的关系，并区分规划中的持久化与当前程序对象。

**阅读范围：** [数据模型第 1、2 节](./DATA_MODEL.md#1-给初学者的解释)、[第 3 节实体关系](./DATA_MODEL.md#3-实体关系)、[第 5 节状态流转](./DATA_MODEL.md#5-job-与运行状态机)。

先看任务、Agent 配置、一批评测任务（Job）、其中一次逐题运行（Run）、判卷结果和文件证据怎样关联；准确词义以 [CONTEXT](../../CONTEXT.md)为准。然后把第三步的执行/判卷过程，对应到规划中的运行状态变化。

可先跳过字段长度、索引、SQL 锁和事务细节。进入数据库开发或审查相应修改时，再深入第 4 节表级契约、第 6 节队列领取及第 7 节 MinIO 布局。

完成标志：能说明“为什么结构化记录与大文件证据分开保存”，以及“已有 Python 对象为什么不等于数据库模块已经实现”。

## 4. 遇到具体问题时，再沿对应分支深入

| 想弄清的问题 | 优先阅读入口 |
|---|---|
| 到底采用哪个版本、模型或固定镜像？ | [依赖总表](../dependencies/DEPENDENCIES.md) |
| 模型为什么不能启动、执行结果怎样返回？ | [Harbor 执行接口](../interfaces/HARBOR_EXECUTION.md) → 对应执行 Adapter |
| 凭据、权限或上传问题为什么需要谨慎处理？ | [认证接口](../interfaces/CODEX_AUTHENTICATION.md) → 对应 Codex 内部实现 |
| Docker、WSL、网络或资源问题发生在哪层？ | [本机环境事实](../operations/LOCAL_DOCKER_ENVIRONMENT.md) → Harbor 对应实验段落 → 行动记录 |
| 还有哪些实现或验收差距？ | [现有验收对账](../interfaces/HARBOR_EXECUTION.md#暂停后的验收对账2026-09-08)，不要从历史测试总数推导 |
| 为什么当时这样选择或修改？ | [总架构设计理由](./ARCHITECTURE.md#7-为什么选择这个架构)；Harbor 选择另见 [ADR](../adr/0001-use-harbor-as-execution-backend.md)，具体改动看对应行动记录 |

这些是查阅入口，不是要求执行其中的命令。不要为了理解项目去读取真实凭据、完整私有轨迹或重新运行历史实验。

## 5. 怎样判断进度和“阻塞”

不要把所有未完成事项都叫阻塞：

- **未实现**：计划中尚未开发的能力。
- **待验证**：实现或路径已有，但还缺足够证据。
- **技术阻塞**：当前目标确实走不通，需要定位和处理原因。
- **主动暂停／待决定**：在控制节奏或等待范围选择，不是代码坏了。

“在研究一个问题”也不等于“已经证明问题的原因”。看进度时，追问它属于哪个模块、卡在调用链哪一步、原因是证据还是假设、下一步是在缩小未知还是改变实现。

这项提问模板已由用户确认提升为所有开发项目的个人主动汇报规则，不再依赖用户记得追问。调用要求在[个人 AGENTS](C:/Users/YINGYI/.codex/AGENTS.md)，固定输出格式唯一维护在 [project-control-report 技能](C:/Users/YINGYI/.codex/skills/project-control-report/SKILL.md)；本指南不复制第二套格式。它与项目 [AGENTS](../../AGENTS.md) 的已有授权、暂停和验证规则共同适用。

这是评测机所有者的个人配置，未打包进项目 Git；换机器或重装时须另行核对个人技能与规则，不能仅凭克隆项目认定已生效。既有 `action-document` 继续负责行动记录，新技能负责面向人的主动说明；普通闲聊不套项目汇报模板。

不需要靠追读每一条日志获得可控性。先要求每轮工作能放回模块地图，再针对真正影响判断的地方深入。

## 6. 最小的下一次共读

第一、二步可以先略读建立位置感。下一次一起读第三步的 `run_prototype()` 成功路径，只讲输入、执行、补丁交接、判卷和结果保存，暂不展开底层实现。

目标是能用自己的话复述一条链路，不是新增功能。一次只读到能够解释为止；不自动运行模型、测试或修改代码。
