# 组员 PostgreSQL 管理员直连教程行动

## 状态与情况

- 状态：已完成。
- 来源请求：用户明确这是五人课设，取消此前“组员只经 Web、数据库不直连”的限制，要求五人共用现有管理员账号，并需要一份从零到一的组员连接教程。
- 当前事实：正式 PostgreSQL 容器通过宿主回环 `127.0.0.1:55432` 提供服务；2026-09-18 已由 owner 执行 `tailscale serve --bg --tcp=15432 tcp://127.0.0.1:55432`，`tailscale serve status` 显示 `sss.tail03c757.ts.net:15432` 仅在 tailnet 内转发到该回环端口，主机经 Tailscale 地址的 `Test-NetConnection` 返回 `TcpTestSucceeded : True`。
- 已确认决定：五人共用 PostgreSQL 管理员 `agentexam_admin`，组员不是只读；教程不保存真实密码，由 owner 另行交付。
- 未知与限制：尚未取得组员 Windows 电脑的 DBeaver 实际连接证据；MinIO 管理入口不属于本教程；不改数据库角色、表、数据、Compose、Tailscale 配置或机器设置。

## 实施措施

1. 核对现有远程接入、所有者运行架构和已部署端口，识别与最新决定冲突的旧边界。
2. 新增面向初学者的 PostgreSQL 从零到一连接教程，覆盖 Tailscale、DBeaver、连接字段、管理员身份验证、表数据查看/编辑、退出和常见故障；不落盘真实密码。
3. 最小同步远程接入、所有者运行架构和行动指南中的旧边界，并链接教程作为操作唯一事实源。
4. 检查链接、端口、主机名、账号、敏感信息和旧冲突文本；记录实际结果。

完成标准：组员可以只凭教程和 owner 私下提供的密码，从 Windows 新电脑接入 tailnet、验证 `15432`、用 DBeaver 登录 `agentexam`，并知道管理员权限和无备份风险；权威文档不再声称 PostgreSQL 禁止向组员开放。

## 受影响文件树

```text
docs/
  actions/
    2026-09-18-team-database-connection-guide.md       # 本次文档变更、验证和限制的执行记录
  operations/
    TEAM_POSTGRESQL_CONNECTION.md                      # 新增：组员从零到一管理员直连教程，操作唯一事实源
    REMOTE_TEAM_ACCESS.md                              # 修改：远程暴露面、Tailscale 端口和教程入口
  architecture/modules/owner-host-runtime/
    ARCHITECTURE.md                                    # 修改：同步五人数据库直连的已确认课设边界和拓扑
    ACTION_GUIDE.md                                    # 修改：同步已部署的 PostgreSQL tailnet 管理入口
HANDOFF.md                                             # 修改：记录用户最新共享管理员决定、实际入口和未验证项
```

本次不新增业务 Module、Interface、数据库表或设计模式。`TEAM_POSTGRESQL_CONNECTION.md` 负责人员操作步骤；`REMOTE_TEAM_ACCESS.md` 负责网络边界；`ARCHITECTURE.md` 负责运行拓扑；`ACTION_GUIDE.md` 只给出运行入口并指向教程，避免复制维护整套步骤。

## 自验证方式

1. `rg` 检查教程包含主机、端口、数据库、用户名、连通性命令、DBeaver 流程、管理员身份查询、退出和故障处理。
2. `rg` 检查受影响权威文档中不再保留“PostgreSQL 禁止 Serve／组员不能连接数据库／Tailscale 只暴露 Web”等与最新决定直接冲突的表述。
3. 检查教程和 diff 不包含 `D:\AgentExamData\private` 中的真实密码、密码正文或要求把密码提交 Git 的步骤。
4. 检查 Markdown 相对链接可解析，查看限定文件 diff，确认未覆盖工作区既有无关改动。
5. 运行适合纯文档变更的文本与链接检查；不把尚未进行的组员双机 DBeaver 登录描述为通过。

## 自验证结果

- 已核对 Tailscale 官方 Windows 安装、Serve TCP/`--bg` 行为，以及 DBeaver 官方稳定版下载、创建连接、Data Editor 和 SQL 执行说明；教程只引用官方入口。
- 关键内容检查通过：教程包含 `sss.tail03c757.ts.net`、`15432`、`agentexam`、`agentexam_admin`、`Test-NetConnection`、DBeaver、`rolsuper`、断开连接、关闭共享和故障排查；26 个代码围栏成对。
- 相对链接检查通过：本次六份文档中的相对文件目标全部存在。第一次通用检查因根目录 `HANDOFF.md` 的父路径被脚本处理为空字符串而误报；修正检查器后重跑为 `RELATIVE_LINKS=PASS`，该失败属于检查方法，不是文档链接失败。
- 旧边界冲突检查通过：限定模块和远程接入文档中未再检出“组员只通过 Web”“不能连接数据库”“PostgreSQL 禁止 Serve”“Tailscale 只暴露 Web”等目标旧表述。
- 空白检查通过：新教程与本行动文档未检出行尾空格；限定跟踪文件的 `git diff --check` 没有空白错误，只提示既有 Windows 工作区的 LF/CRLF 转换警告。
- 敏感信息检查：教程只写密码文件路径和“由 owner 私下提供”的占位说明，没有读取或写入密码正文，没有改数据库、Tailscale、Compose 或运行服务。
- 运行证据沿用本轮用户实际输出：两项容器为 `Up`；Tailscale Serve 显示 `sss.tail03c757.ts.net:15432 → 127.0.0.1:55432` 且 `tailnet only`；owner 主机 `Test-NetConnection 100.101.148.2 -Port 15432` 返回 `True`。这不算组员电脑登录通过。
- 未运行：组员 Windows 电脑的 Tailscale 连通、DBeaver Driver 下载、账号认证、超级管理员查询，以及未授权设备负向；教程和权威状态均明确标为待实测。MinIO 不在本行动范围。
