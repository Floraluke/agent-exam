# 共享 PostgreSQL 端口统一与物理局域网接入文档同步

## 状态与情况

- 状态：已完成。
- 来源请求：用户要求只修改文档，把当前 PostgreSQL 的 Tailscale 入口从 `15432` 更正为实际运行的 `55432`；同时确认因部分组员无法下载 Tailscale，决定允许同一物理局域网内的组员直连 owner 主机数据库。
- 当前事实：`infra/compose.yaml` 仍把 PostgreSQL 宿主端口绑定为 `127.0.0.1:55432`；2026-09-20 只读检查显示 Tailscale Serve 当前实际为 `sss.tail03c757.ts.net:55432 -> 127.0.0.1:55432`，`15432` 不可达而 `55432` 可达。
- 已确认决定：当前 Tailscale 文档端口统一为 `55432`；保留 Tailscale 作为可用组员的私有远程路径；新增同一物理局域网直连路径，供不能安装 Tailscale 的组员使用；不做路由器端口转发或公网发布。
- 未知与限制：本轮仅改文档，不修改 Compose、PostgreSQL、Windows 防火墙、Tailscale 或运行中容器；物理局域网入口尚未实施和双机验证，owner 的局域网 IPv4 可能随网络变化，不写死在 Git 中。
- 明确排除：不读取或记录数据库密码；不改账号、表、数据、业务代码、Module Interface、Docker/WSL 设置；不提交或推送 Git。

## 实施措施

1. 将当前权威文档和进行中的任务里 Tailscale PostgreSQL 端口从 `15432` 同步为实际运行的 `55432`，保留已完成历史行动记录中的当时事实。
2. 把物理局域网直连补入组员教程和远程接入文档，明确两种连接路径、使用条件、相同数据库字段及故障检查。
3. 同步 owner 运行架构、行动指南、团队分工、M1 规格、任务 14、交接文档的网络边界和验收项；把局域网路径标为“已决定、未实施、未验证”。
4. 记录未来实施边界：PostgreSQL 只向物理局域网的 TCP `55432` 开放，Windows 防火墙应限制为专用网络和本地子网；不得做路由器转发或公网开放。
5. 检查当前文档不再把 `15432` 当作现行入口，也不把尚未实施的物理局域网入口写成已可用。

完成标准：组员教程能区分 Tailscale 与物理局域网两条路径；所有当前权威文档对 Tailscale `55432`、局域网目标边界和未实施状态表述一致；历史行动记录未被改写。

## 受影响文件树

```text
.scratch/m1-platform/
  spec.md                                                   # 同步 M1 私有协作与数据库直连范围
  issues/14-private-remote-acceptance.md                    # 同步仍在进行的双机验收入口与正反例
docs/
  actions/
    2026-09-20-shared-database-lan-access-docs.md           # 本次决定、文档变化和验证证据
    2026-09-14-m1-private-remote-acceptance.md              # 同步进行中的任务 14 行动边界与验收方式
  operations/
    TEAM_POSTGRESQL_CONNECTION.md                           # 两种组员连接路径的操作唯一事实源
    REMOTE_TEAM_ACCESS.md                                   # 网络暴露面、配置边界和诊断唯一事实源
  architecture/modules/
    TEAM_WORK_ALLOCATION.md                                 # 同步团队使用的入口与任务 14 交接
    owner-host-runtime/
      ARCHITECTURE.md                                       # 同步 owner 主机当前/目标网络拓扑与风险
      ACTION_GUIDE.md                                       # 同步 owner 运维入口和待实施步骤指针
HANDOFF.md                                                   # 同步当前决定、实际状态和未验证项
```

本次不新增顶层 Module、Interface、数据库表、目录层级或设计模式。`TEAM_POSTGRESQL_CONNECTION.md` 维护组员操作步骤，`REMOTE_TEAM_ACCESS.md` 维护网络边界，owner-host-runtime 架构只引用并解释职责，不复制维护完整教程。

## 自验证方式

1. 使用 `rg` 检查非历史当前文档中的 `15432`，预期没有仍表示现行入口的命中。
2. 使用 `rg` 检查 `55432`、Tailscale、物理局域网、未实施/未验证、禁止公网或路由器转发等关键语义。
3. 检查教程中的两条连接路径均包含 Host、Port、Initial Database、Username、Password，并明确 LAN IPv4 不写死。
4. 检查 Markdown 相对链接目标、代码围栏、尾随空格和限定文件 `git diff --check`。
5. 查看限定 diff，确认没有修改 Compose、机器配置、历史已完成行动记录或用户已有无关改动。

## 自验证结果

- 当前端口检查通过：限定 `HANDOFF.md`、M1 规格、两份运维文档、团队分工和 owner-host-runtime 两份文档执行 `rg "15432"` 无命中，输出 `CURRENT_PORT_REFERENCES=PASS`；当前入口统一为 `55432`。2026-09-18 已完成行动和任务评论中的 `15432` 保留为带日期的历史事实，不代表现行入口。
- 关键语义检查通过：当前文档均能检出 `55432`；Tailscale 主机 `sss.tail03c757.ts.net:55432`、物理局域网、尚未实施／未验证以及禁止路由器转发或公网发布已同步到对应权威范围。
- 链接检查通过：十份目标文档的 Markdown 相对路径和本地绝对路径目标均存在。第一次检查器把 Windows `C:/...` 绝对路径错误拼到相对目录后误报两个 HANDOFF 链接；修正绝对路径判断后重跑为 `RELATIVE_AND_ABSOLUTE_LINKS=PASS`，该失败属于检查方法，不是文档链接失败。
- 文本结构检查通过：十份目标文档的代码围栏均成对，未检出行尾空格；限定文件 `git diff --check` 通过，只出现现有 Windows 工作区的 LF/CRLF 转换警告。
- 范围检查通过：`infra/compose.yaml` 的限定 diff 为空，未修改 Compose、PostgreSQL、Windows 防火墙、Tailscale、容器、账号、表、数据或业务代码；已完成的 2026-09-18 行动记录未改写。工作区原有后端代码和其他未跟踪文件保持不动。
- 未运行产品测试或局域网双机测试，因为本轮仅修改文档且用户未授权机器配置。物理局域网入口仍为“已决定、未实施、未验证”；当前可用入口仍是 Tailscale `sss.tail03c757.ts.net:55432`。
