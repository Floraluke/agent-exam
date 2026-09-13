# M1 基础排行榜行动记录

## 状态

In progress。用户已于 2026-09-13 明确批准本记录的最小统计口径、只读 Repository Interface 与必要子目录；当前进入 TDD 实施，不再重复询问同一授权。

## 情况说明

- 任务 11 要让用户按完整 Agent 配置查看确定性基础排行榜，并明确比较条件、未知结果与基础设施错误；不引入模型主观评分、Judge/Review 或人为破同分。
- 现有 Job/Run、冻结快照、确定性结果和过程指标已经是可信事实源，不需要新增排行榜表。排行榜应从这些记录即时聚合，并在生产查询层无条件排除 `internal_test`。
- 既有 `JobRepository` 同时承载提交、生命周期与恢复，PostgreSQL Adapter 已接近 200 行；排行榜是跨 Job 的只读投影，不能把聚合 SQL 塞进生命周期仓库。因此新增小型 `LeaderboardRepository` Interface，由 Reporting 应用能力使用，PostgreSQL Adapter 隐藏选择与聚合细节。
- 已批准的比较范围是完全相同的数据集 ID、revision、split、可选 repo、闭卷赛道、冻结网络/工具/限制策略以及 Harbor、SWE-Gym、SWE-Bench Fork 和执行契约版本。不可比范围绝不混榜，页面必须显示这些条件。
- 已批准按不可变配置 ID、Agent 类型/版本、模型提供方/模型、reasoning effort 与配置 fingerprint 组成完整身份；不返回凭据配置或秘密。
- 对同一“比较范围 + 题目 + 完整 Agent 配置”，选择最早出现的可信确定性结果。后来的重复 Job 或关联重试不能覆盖已知结果，只能填补原来没有确定性结果的题目；仍无确定性结果时，仅用最新终态尝试分类，并沿用任务 07 的既有口径把 `FAILED` Run 归为基础设施错误，取消或没有尝试归为未知。响应保留来源 Job/Run 以便追溯。
- 分母是所选数据集 revision/split/repo 范围内的全部不同题目，不只计算已完成题目。展示总题数、确定性题数、已解决、未解决、基础设施错误和未知；通过率为已解决数除以总题数。只有至少有一次合规正式尝试的配置进入榜单。
- 排名只看确定性 `resolved_count`/同分母通过率；成绩相同保持并列。稳定分页可以使用配置 ID 排序，但不得把它当作破同分成绩。
- token、成本、墙钟时间、CPU 与峰值内存只展示，不参与排名。选中运行任一项缺失时，该项聚合为 `null`，同时返回覆盖数，绝不把缺失当作 0。
- 本任务不运行真实模型、Harbor 或 Judge，不创建 Judge/Review 表、路由或依赖，不部署、不推送、不改机器设置。

## 实施措施

1. 先写领域选择/统计红灯，固定重复尝试、手动重试填空、全题分母、并列、未知/基础设施错误和指标缺失语义。
2. 增加只读 `LeaderboardRepository` 与 `LeaderboardReporting`；应用层验证闭卷筛选和分页，Repository 只返回已验证的排行榜投影。
3. 在必要的 `adapters/persistence/jobs/reporting/` 子目录实现 PostgreSQL 查询：先筛选正式范围和冻结比较条件，再按题目/完整配置选择可信结果或最新终态分类；无新表、无写事务。
4. 增加 `GET /api/v1/leaderboard`，返回比较范围、完整配置身份、统计、过程指标覆盖和来源引用；过滤、游标、空结果和错误沿用既有 HTTP 约定。
5. 在现有首页增加基础排行榜区域，显示可比条件、并列排名、未知/基础设施错误、unknown 指标，并允许来源跳转到既有 Job/Run 详情。
6. 用固定内存数据做快速 HTTP 测试，用专属临时 PostgreSQL/MinIO 验证真实查询，用少量浏览器测试验证展示、过滤、空/错误与来源跳转；同步权威架构、数据模型、HTTP 和任务单。
7. 运行相关/完整回归、Ruff、mypy、Web typecheck/build、规模检查；以任务 10 关闭提交 `6ccbd18` 为固定基准分别执行 Standards/Spec 评审，修复后复验并记录。

## 需要修改的文件树

```text
apps/backend/src/eval_platform/
├─ domain/leaderboard/                                    # 为满足 200 行指标拆分的领域小模块
│  ├─ models.py                                           # 比较范围、完整身份、尝试、行与来源值对象
│  ├─ policy.py                                           # 重复选择、分母、分类、指标和并列规则
│  └─ query.py                                            # 查询、分页及不参与排名的稳定游标
├─ application/
│  ├─ reporting/leaderboard.py                            # 认证、筛选与只读应用用例
│  └─ ports/leaderboard.py                                # 新增最小只读 Repository Interface
├─ adapters/persistence/jobs/reporting/
│  ├─ __init__.py                                         # Adapter 导出
│  └─ leaderboard.py                                      # PostgreSQL 选择、聚合与稳定分页
├─ delivery/
│  ├─ jobs.py                                             # 在既有运行时装配只读能力
│  └─ http/
│     ├─ app.py                                           # 挂载既有 Reporting 路由
│     └─ routes/leaderboard/{routes,schemas}.py           # GET 参数、响应 Schema 与错误映射
apps/backend/tests/leaderboard/
├─ conftest.py                                            # 内存 HTTP 装配与固定比较范围
├─ memory.py                                              # 只读 Repository 测试替身
├─ test_policy.py                                         # 选择、分母、并列与指标语义
├─ test_leaderboard_http.py                               # 过滤、分页、空结果、错误与隔离
└─ test_leaderboard_postgres.py                           # 真实 PG 查询与生产隔离
apps/web/src/
├─ features/leaderboard/view.tsx                          # 排行榜、比较条件与来源入口
└─ lib/leaderboard/{client,shapes}.ts                     # HTTP 调用、类型与运行时校验
apps/web/tests/leaderboard/base.spec.ts                   # 少量完整浏览器动线
docs/architecture/{ARCHITECTURE,DATA_MODEL,MODULE_CONTRACTS}.md
docs/interfaces/HTTP_API.md                               # 已批准口径与当前接口事实
.scratch/m1-platform/issues/11-base-leaderboard.md        # 验收勾选和证据
```

采用 Repository、Application Service 和 Read Model（只读投影）模式。HTTP 与页面只依赖应用服务；应用服务只依赖 `LeaderboardRepository`；PostgreSQL Adapter 依赖现有持久化表，执行方向不反转。新增 `reporting/`、`leaderboard/` 子目录是因为相应现有目录已达到 8 个直属文件，且它们分别隔离跨 Job 报告查询、后端排行榜测试与 Web 类型，不形成新顶层业务服务。

## 自验证方式与成功标准

- 固定合成数据证明：最早可信结果不被重复/重试覆盖；重试只填空；没有确定性结果时最新终态准确区分基础设施错误和未知。
- 分母等于范围内全部不同题目；`resolved + unresolved + infrastructure_error + unknown = total_tasks`，确定性数等于已解决加未解决。
- 完整配置和全部冻结比较条件参与隔离；成绩相同并列，稳定顺序不改变名次；指标缺失保持 `null` 且覆盖数准确。
- `internal_test` 在生产 SQL 中无条件排除；正式 HTTP 不能用参数打开内部范围，测试替身只在隔离装配中存在。
- HTTP 验证合法/非法筛选、游标/limit、空结果、依赖错误；页面验证条件、统计、unknown、并列和来源跳转。
- 专属临时 PostgreSQL/MinIO、完整后端回归、Ruff/mypy、Web typecheck/build、少量浏览器和文件规模均实际运行；失败、跳过和未授权项如实记录并精确清理专属资源。

## 自验证情况

- 第一片领域 TDD 红灯已出现：`tests/leaderboard/test_policy.py` 在收集时因 `eval_platform.domain.leaderboard` 尚不存在而报 `ModuleNotFoundError`。红灯覆盖最早可信结果、重试只填空、全题分母、基础设施错误/未知、并列与指标缺失语义；尚未接触 HTTP 或数据库。
- 第一片领域绿灯为 `2 passed`。初版单文件达到 255 行并触发规模门禁，已立即拆为 `domain/leaderboard/{models,policy,query}.py` 与公开 `__init__.py`；核心文件分别不超过 191 行，并修正了多比较范围下排名位置必须各自重置的问题。
- 第二片 HTTP TDD 红灯为 `3 errors`：测试装配向 `create_app` 注入排行榜用例时明确报 `unexpected keyword argument 'leaderboard'`。三项分别覆盖登录门禁、公开响应/unknown/来源和额外、重复、未启用赛道参数；当时尚无排行榜路由。
- 第二片 HTTP 绿灯为 `5 passed, 2 warnings`（含领域组）：已增加认证只读 GET、严格参数集合、安全公开响应、unknown 指标覆盖、来源 ID 与 `quality_tiebreak=null`。同片定向 Ruff 首次发现一个测试 import 顺序问题，机械修正后通过。
- 第三片 PostgreSQL TDD 红灯已出现：`tests/leaderboard/test_postgres.py` 收集时因 `eval_platform.adapters.persistence.jobs.reporting` 尚不存在而报 `ModuleNotFoundError`。该用例使用生产建表、Job 状态机和结果事务生成正式合成结果，并故意损坏内部测试快照，以验证生产 SQL 必须在解析前排除 `internal_test`。
- PostgreSQL Adapter 已接线并通过定向静态检查；未启用外部门禁的本机组当前为 `5 passed, 1 skipped, 2 warnings`，其中跳过项正是待专属 PostgreSQL 环境执行的用例，不记为通过。首次专属脚本在进入测试前暴露清理设施问题：Windows PowerShell 把 `docker inspect` 一个尚未创建的名称当成终止错误，掩盖了原始失败；随机标签下只读复核无残留。已把清理改为先按精确名称查询 ID、再核验标签后删除，待重跑。
- 清理设施修正后用 Windows PowerShell 5.1 重跑，原始问题确认为脚本使用 PowerShell 7 的随机字节 API；仍未创建测试容器，清理检查成功。改用仓库环境可用的 PowerShell 7 后，三个隔离容器均通过无宿主端口/挂载检查，但 pytest 收集发现 `test_http.py`、`test_postgres.py` 与既有 Job 测试同名而 import mismatch，产品断言仍未执行；三个容器和 tmpfs 已精确清理。现将任务 11 测试改为全仓唯一文件名后重跑。
- 唯一文件名修正后的专属 PostgreSQL/MinIO 套件为 `111 passed, 2 warnings in 42.77s`。任务 11 的真实 PG 用例实际验证两题全分母、正式来源、过程指标和 SQL 解析前排除损坏 `internal_test`；三个容器无宿主端口/挂载，最终均按标签精确删除，tmpfs 数据移除，镜像/构建缓存保留。
- 页面 TDD 首次运行因结果目录 Windows `EPERM` 未进入测试；沙箱外两次启动又分别发现先前异常留下的 8875 Python 与 3100 Node 合成服务，均先按端口解析 PID、核验命令行为本仓库测试服务后精确终止。服务最终正常启动时发现 Playwright 1243 浏览器缓存不存在；本机已有 Chrome，测试配置改为显式 `channel=chrome`，不下载浏览器或修改机器设置，待取得真正产品红灯。
- 改用已安装 Chrome 后，浏览器测试先发现测试误以为页面有“登记第二道题”按钮；改为通过同源受保护测试请求登记现有第二个 preset。随后完整合成流程创建并完成一个 Job，在 `基础排行榜` 区域不存在处得到真实产品红灯 `1 failed`。页面测试 Adapter 将只在既有 `AGENTEXAM_IDENTITY_BROWSER_TEST=1` 门控进程内读取 `internal_test` 内存 Job；生产 PostgreSQL 仍固定 official，二者不共享数据。
- 页面接线后 Web typecheck、后端门控 Adapter Ruff 与 5 项定向测试通过。浏览器首次产品复验已实际显示 1/2、50%、未知 1、完整冻结条件和真实 Run 来源；失败仅因 JSX 中点后空格与断言不一致，且当时的合成执行真实持久化缓存 token 为 2。先按真实值修正空格和断言；随后为补齐缺失指标页面验收，门控 BrowserBackend 改为在执行结果中实际持久化该字段为 `null`，再由同一投影展示 unknown。
- 单个主流程页面在空格修正并展开来源后为 `1 passed (13.2s)`。随后补充 HTTP 游标分页、空结果、未知游标和依赖错误，补充不同冻结范围独立分母/排名；浏览器合成 Backend 实际把 cache token 持久化为缺失值，页面据此显示 `unknown（覆盖 0/1）`，不是前端伪造。当前排行榜后端组为 `8 passed, 1 skipped, 2 warnings`；跳过的唯一 PG 用例已由专属套件实际通过。
- 补强后的浏览器规格共 `2 passed (11.5s)`：第一项验证完成 Job 的两题分母、50%、unknown、全部版本条件和实际 Run 链接；第二项验证空结果及拦截的安全 503 页面状态。Web typecheck 同步通过。
- 评审前完整后端回归为 `358 passed, 76 skipped, 2 warnings in 37.50s`；76 项均为显式外部环境门禁，其中任务 11 的真实 PG 已由专属 111 项套件通过。全仓 Ruff check 通过，256 个文件 format-check 通过，mypy 为 `Success: no issues found in 148 source files`。
- Web 生产构建第一次在沙箱内因用户配置写入 `EPERM` 未进入编译，沙箱外又因虚拟文件系统原子重命名 `EXDEV` 未进入编译；仅为本次进程设置 `NEXT_TELEMETRY_DISABLED=1` 后构建成功，4 个静态页面生成完成。没有改 APPDATA、机器设置或下载依赖。
- 规模检查发现 application 根目录因新增用例达到 9 个直属文件；已将其移入既有 `application/reporting/leaderboard.py` 并由包导出。最终新增/受影响动态源码均不超过 200 行，受影响目录均不超过 8 个直属文件。
