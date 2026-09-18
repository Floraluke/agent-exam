# 简化五人共享数据库协作与连接流程

## 状态与情况

- 状态：已完成；PostgreSQL 共享方案、五人代码分工和 Navicat 三步连接教程已同步并通过文档检查。
- 来源请求：用户确认五人课设只使用 owner 电脑上的一套 PostgreSQL，五人共用 `agentexam_admin` 管理员账号直接连接；模块分工只表示代码主责，不用于数据库分权。用户指出现有连接教程过于繁琐，并最终明确组员使用 Navicat，要求按该决定重新编写教程。
- 当前事实：PostgreSQL 容器映射为 owner 回环 `127.0.0.1:55432`，Tailscale Serve 已提供 `sss.tail03c757.ts.net:15432`；组员使用 Navicat，不使用 DBeaver。教程只需覆盖正常连接、查看表和最小故障排查。
- 已确认决定：不建立只读库、不建立分角色数据库账号、不要求组员各自部署数据库；owner 维护唯一共享库，五人共享管理员权限。
- 已关闭的分支：用户曾询问“使用 SQL Server”，随后明确“那不是”，因此不迁移数据库引擎。当前项目继续复用 PostgreSQL Compose、`psycopg` Repository、PostgreSQL schema、生命周期脚本和既有真实持久化验证。
- 明确排除：不修改数据库账号、密码、容器、Tailscale 配置、产品代码、业务表或现有 Module Interface；不运行模型；不提交或推送 Git。

## 实施措施

1. 将组员连接主流程缩为：加入同一 Tailscale、在 Navicat 新建 PostgreSQL 连接并填写五项连接信息、测试并保存。
2. 将 owner 日常操作缩为保证电脑、Docker Desktop、PostgreSQL 容器在线；现有后台 Serve 正常时不重复配置。
3. 把网络测试、Serve 命令和常见错误移到失败排查，不作为每次连接的必做步骤。
4. 在分工文档中明确：一套共享数据库、一个管理员账号；Module DRI 仅表示代码主责，不限制人工直连数据库。
5. 保留最少课设规则：密码不进 Git；执行 `DROP/TRUNCATE` 前在群里说明；数据库结构变化同时落到项目 schema/迁移文件，避免只改现场库。
6. 同步 HANDOFF 中的团队协作决定，并验证文档链接、连接字段和旧冲突表述。

完成标准：Navicat 首次连接正文可以在三步内完成；连接卡片只要求 Host、Port、Initial Database、Username、Password；正常连接不要求执行 PowerShell 或 SQL；分工文档不再把共享管理员解释成数据库角色或表权限分工。

## 受影响文件树

```text
docs/
  actions/
    2026-09-14-m1-private-remote-acceptance.md             # 同步任务 14 未完成的 Navicat 实机验收名称
    2026-09-18-simplify-shared-database-collaboration.md  # 本次简化决定、范围和验证证据
  architecture/modules/
    TEAM_WORK_ALLOCATION.md                               # 明确模块分工只管代码主责，共用一套管理员数据库
  operations/
    TEAM_POSTGRESQL_CONNECTION.md                         # 重写为 Navicat 三步连接卡片和最小故障排查
    REMOTE_TEAM_ACCESS.md                                 # 把任务 14 的组员数据库客户端从 DBeaver 同步为 Navicat
.scratch/
  m1-platform/issues/
    14-private-remote-acceptance.md                       # 同步已发布任务的 Navicat 验收工具
HANDOFF.md                                                # 同步唯一共享库和简化连接入口
```

设计关系：PostgreSQL Adapter 和各业务 Module 的 Interface 均不改变；本轮只简化人的协作与运维说明。owner 运行 Module 提供唯一数据库实例，A–E 通过同一管理员连接进行课设开发；产品代码仍通过既有 Interface 访问数据库。

## 自验证方式

1. 检查 Navicat 连接教程主流程只有三步，正常路径不要求组员执行 PowerShell、SQL、Docker 或安装 PostgreSQL。
2. 检查 Host=`sss.tail03c757.ts.net`、Port=`15432`、Initial Database=`agentexam`、Username=`agentexam_admin` 与当前入口一致。
3. 检索“只读库”“每人部署”“数据库角色分工”等冲突表述，确认目标文档不再引导复杂方案。
4. 检查分工文档仍保持 5 人、7 个 Module、M1-14 与 01–08 任务归属和现有工时不变。
5. 检查 Markdown 相对链接、代码围栏和尾随空格；本轮不运行产品测试，因为不改变代码或运行配置。

## 自验证结果

- Navicat 教程主流程检查通过：恰有“第一步、第二步、第三步”三个标题；正常路径只要求 Tailscale 登录、打开 Navicat、新建 PostgreSQL 连接并测试，不要求 PowerShell、SQL、Docker 或本机 PostgreSQL。
- 连接卡片检查通过：Host=`sss.tail03c757.ts.net`、Port=`15432`、Initial Database=`agentexam`、Username=`agentexam_admin` 和私下提供的 Password 五项正文一致；明确不选择 SQL Server 连接类型，也不启用 SSH/SSL。
- 当前入口只读核对通过：`agentexam-local-postgres-1` 为 `Up`，仍映射 `127.0.0.1:55432 → 5432`；`tailscale serve status` 仍显示 tailnet `15432 → 127.0.0.1:55432`。本轮没有修改容器、Serve、账号、密码或数据库内容。
- 官方资料核对通过：Navicat Premium 当前明确支持 PostgreSQL；Navicat 官方连接排查同样以 hostname、TCP/IP port、username/password 和 Initial Database 为核心字段。教程只引用这两个事实，不复制无关远程权限配置。
- 工具名称同步通过：连接教程、团队分工、远程接入、任务 14 行动/任务单和 HANDOFF 的当前验收描述均使用 Navicat；限定当前文档范围未检出残留 DBeaver。
- 分工完整性检查通过：成员 A–E 仍为 5 人，七个 Module 均保留；M1-14 与 01–08 共 9 个任务映射未改变；工时仍为 52/55/54/55/56 小时，最大差 4 小时。
- 文档结构检查通过：目标教程有 12 条成对代码围栏；六份同步文档的相对链接均存在；目标文件未检出尾随空格。教程已从原 12 节长流程压缩为 7 个短节，其中正常连接只有 3 步。
- 未运行产品测试，因为本轮不改产品代码、数据库 schema 或运行配置；未进行组员电脑上的真实 Navicat 登录，因此任务 14 的该项仍是待实测，而不是已通过。
