# 五人模块分工与排队任务分配行动

## 状态与情况

- 状态：已完成；七个 Module 的输入、成功输出、失败语义和下游消费已按当前实现补成 JSON 示例并通过结构检查。
- 来源请求：用户要求形成正式分工文档，按五人尽量均衡分配现有 Module；明确每个 Module 的上游输入、本组职责、输出和下游接收方；把此前排队任务对应到 Module 和负责人。
- 当前事实：项目有身份与成员、目录与配置、Job 控制、执行与判卷、证据与报告、Web 与 HTTP、所有者单机运行 7 个当前 Module；用户此前认可“一个 Module 一个主负责人，允许一人负责多个 Module”的方向。
- 当前队列：M1 任务 14 已发布且仍 `in-progress`；扩展计划 01–08 已形成规划但尚无独立 issue 文件；P 持久化阶段已经完成，不再列为排队开发任务。
- 已确认决定：五人课设采用共享 PostgreSQL 管理员直连；该决定改变任务 14 原有“PostgreSQL 不向组员开放”的一项边界，必须在本次同步。
- 人员信息限制：除用户是 owner/部署负责人外，尚无其余四人的姓名和技术偏好；本次使用成员 A–E 稳定占位，职责和交接先固定，姓名可后填而不改变模块 seam。
- 明确排除：本次不实现 01–08、不启动服务/容器/模型、不新建业务 Module/Interface/表、不替用户发布 01–08 issue、不执行 Git 提交或推送。

## 实施措施

1. 从七个 Module 的现有 Interface、依赖方向和现实代码地图提取上游输入、内部职责、稳定输出及下游消费者。
2. 以一个 Module 只有一个 DRI（直接负责人）为原则，将 7 个 Module 分给 5 人；跨模块任务通过 Interface、测试证据和交接清单协作，不共享同一 Module 内部实现所有权。
3. 把 M1-14 与扩展 01–08 逐项映射到任务 DRI、参与 Module、各 Module 交付和前置条件；标清 P 已完成以及 01–08 尚未发布独立 issue。
4. 给出不含等待/下载/真实调用耗时的相对工时基线，使五人计划负载接近，并记录估算假设。
5. 同步模块索引、排队计划、任务 14 当前边界和 HANDOFF；运行链接、覆盖、唯一 DRI、工时和旧冲突文本检查。
6. 对照当前 Module Interface、HTTP DTO、领域 dataclass 和 owner 生命周期状态，为七个 Module 增加输入、成功输出与失败输出 JSON；标明 HTTP 实际载荷、内部交接表示和运维状态三种不同性质，不把示例发明成新接口。

完成标准：五名成员都有明确 Module 所有权；七个 Module 无重复 DRI、无遗漏；每个排队任务有且仅有一个任务 DRI和明确的模块交付；上游/输出/下游可据此完成交接；每个 Module 至少有一组可据当前代码核对的 JSON 输入/输出/失败示例，并明确示例性质；文档不把规划任务写成已实现或已授权真实调用。

## 受影响文件树

```text
docs/
  actions/
    2026-09-18-team-module-work-allocation.md          # 本次分工设计、同步范围和验证结果
    2026-09-14-m1-private-remote-acceptance.md         # 同步任务 14 新增 PostgreSQL tailnet 例外及剩余验收
  architecture/modules/
    TEAM_WORK_ALLOCATION.md                            # 新增：五人 Module 所有权、上下游交接和排队任务总表
    README.md                                          # 修改：增加分工文档导航，不复制职责正文
.scratch/
  ui-catalog-providers/plan.md                         # 修改：指向已确认分工，保持 01–08 仍为规划任务
  m1-platform/issues/14-private-remote-acceptance.md   # 修改：用当前 PostgreSQL 共享管理员边界替代旧禁止项
HANDOFF.md                                             # 修改：记录分工入口、占位成员和“分工不等于开工”边界
```

设计关系：业务 Module 的 Interface 仍由各架构/契约文档定义；本分工文档只定义人员 DRI、交接责任和任务映射。它不创建新的代码 seam，也不复制字段、路由或数据库结构。

## 自验证方式

1. 检查 7 个现有 Module 在分工表中各出现一次且只有一个 DRI；成员 A–E 均有职责和计划工时。
2. 检查 M1-14 与 01–08 各有且只有一个任务 DRI，并链接到现有任务/计划来源；P 明确为已完成而非排队。
3. 检查每个 Module 都包含上游输入、负责内容、输出、下游接收方和交接验收。
4. 检查五人工时估算差距处于文档声明的均衡范围，且标明不含外部等待/下载/模型运行。
5. 检查任务 14、远程接入与分工文档不再冲突地声称 PostgreSQL 禁止向组员开放；MinIO、Docker、原始 FastAPI 和模型秘密仍不开放。
6. 检查 Markdown 相对链接、代码围栏、尾随空格和限定 diff；不运行产品测试，因为本轮只改规划/协作文档。
7. 逐个对照 Python dataclass/Pydantic DTO、HTTP 契约和 PowerShell 生命周期返回字段，验证 JSON 字段名称；检查每个示例能被标准 JSON 解析，且不含注释、真实密码、真实 token/Key、真实对象内部键或私有绝对路径。

## 自验证结果

以下结果为首版分工文档验证；JSON 深化完成后在本节追加本轮实际检查，不删除历史结果。

- Module 覆盖检查通过：第 4 节检出身份与成员、目录与配置、Job 控制、执行与判卷、证据与报告、Web 与 HTTP、所有者单机运行 7 个 Module，各自恰有一个职责小节和唯一 DRI。
- 人员与工时检查通过：成员表有 A–E 五行，计划工时为 52/55/54/55/56 小时，总计 272 小时，最大差 4 小时；文档已明确不含下载、等待、真实模型运行和返工。
- 任务覆盖检查通过：任务表恰有 9 行且 ID 唯一，覆盖 M1-14 与 01–08；每行只有一个任务 DRI，并列出参与 Module、上游前置和下游停点。P 明确为已完成、非排队。
- 交接内容检查通过：每个 Module 均包含“上游提供、本 Module 负责、向下游输出、交接完成标准、对应排队任务”；另有统一 Interface 交接清单和“分工不等于全部开工”规则。
- 任务 14 当前边界已同步：任务单和行动的当前状态允许获准 tailnet 成员访问 HTTPS Web 与 PostgreSQL `15432`，同时保留 MinIO、原始 FastAPI、Docker、Worker 和模型秘密不开放；历史 2026-09-15 记录仍作为当时事实保留，并由 2026-09-18 段明确覆盖。
- 相对链接最终检查为 `RELATIVE_LINKS=PASS`。第一次检查发现新分工文档中模块契约、数据模型、HTTP 和数据库教程 4 个链接多退了一层目录；修正后重跑通过，该失败属于文档链接检查，不是产品行为失败。
- Markdown/空白检查通过：分工文档代码围栏为偶数；本次相关文件未检出行尾空格；限定跟踪文件的 `git diff --check` 无空白错误，仅有 Windows 工作区既有 LF/CRLF 转换提示。
- 首版分工阶段未运行产品测试、容器、数据库、Tailscale 或模型；当时只修改分工、规划和任务边界文档。未创建 01–08 issue，未改变其未开工状态，也未提交或推送 Git。
- JSON 深化覆盖通过：第 4.1–4.7 节各有且只有一个“当前 JSON 交接示例”小节；共 25 个 `json` 代码块，全部由标准库 `json.loads` 成功解析。
- `HANDOFF.md` 的团队分工入口已同步说明：示例区分实际 HTTP、内部 dataclass 表示和运维状态，避免下一任务把这些 JSON 全部误当成公共 API。
- 当前 Pydantic 契约校验通过：登录、actor、统一错误、两种目录登记、`TaskDetail`、`AgentDetail`、`JobRequest`、两处 `JobSummary` 和 `RunReportResponse` 共 14 个实际 HTTP 示例均由当前后端模型 `model_validate` 成功。
- 内部 Interface 已逐项回读并通过构造校验：执行输入成功构造 `ExecutionJobRequest/ExecutionRunRequest/RunLimits`，成功与失败两个示例成功构造 `ExecutionTrialResult`，判卷示例成功构造 `DeterministicResult`，共 4 个 dataclass 示例通过；文档明确这些只是内部对象的 JSON 表示，不是新增 HTTP 路由。
- owner 运行示例已做只读现状核对：部署状态文件为 `phase=complete`；`agentexam-local-postgres-1`、`agentexam-local-minio-1` 均为 `running`；查询得到 `active_jobs=0`；`tailscale serve status` 仍显示 HTTPS 代理到 `127.0.0.1:59336`、TCP `15432` 转发到 `127.0.0.1:55432`，`Test-NetConnection` 为 `True`。未读取或输出任何密码、token、Key、MinIO 对象键或私有绝对路径。
- PowerShell 限制已如实保留：当前主机命令行仍不能识别 `pwsh`，所以没有把 `Get-AgentExamStatus.ps1` 写成“本轮直接执行成功”；成功 JSON 的字段来自脚本源码，当前值由上述三个只读来源交叉核对，失败示例明确标为进程捕获表示。
- 安全与文档检查通过：7 个 Module 标题、7 个 JSON 小节均齐全；敏感值/私有路径扫描无命中；相对链接通过；52 条代码围栏成对；目标文档和行动文档无尾随空格。
- 未运行产品测试或模型；本轮只有文档修改及 Docker/PostgreSQL/Tailscale 的只读状态核对，没有启停服务、改数据库、调用模型、创建 01–08 issue、提交或推送 Git。
