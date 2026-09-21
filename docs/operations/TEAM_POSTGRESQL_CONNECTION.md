# 组员使用 Navicat 连接共享 PostgreSQL（极简版）

> 课设方案：owner 电脑只运行一套 PostgreSQL，五个人共用 `agentexam_admin` 管理员账号。
>
> 已运行入口：通过 Tailscale 连接 `sss.tail03c757.ts.net:55432`。
>
> 已确认但尚未实施：同一物理局域网内可通过 owner 当前局域网 IPv4 的 `55432` 直连，供无法安装 Tailscale 的组员使用。密码由 owner 私下发送，不写进本文档或 Git。

## 1. owner 发给组员的连接卡片

| 字段 | 填写内容 |
|---|---|
| Host | Tailscale：`sss.tail03c757.ts.net`；物理局域网：owner 当天私下提供的局域网 IPv4 |
| Port | `55432` |
| Initial Database（初始数据库） | `agentexam` |
| Username | `agentexam_admin` |
| Password | owner 私下发送 |

`agentexam_admin` 就是本课设所说的“数据库 root 账号”。五个人使用同一账号，可以查看、增加、修改和删除数据库内容。

先选择一种路径：

- **Tailscale 路径（当前可用）**：适合已经能安装并登录 Tailscale 的组员，Host 使用 `sss.tail03c757.ts.net`。
- **物理局域网路径（已决定，尚未实施）**：适合和 owner 电脑连接同一个可信 Wi-Fi／路由器、但无法安装 Tailscale 的组员，Host 使用 owner 当天提供的局域网 IPv4。owner 完成 Compose 与防火墙配置并实测前，不要把这条路径当作已可用。

两条路径的 Port、Database、Username 和 Password 相同。局域网 IPv4 可能变化，因此不写死在 Git 或本文档里。

## 2. 组员用 Navicat 三步连接

### 第一步：确认连接路径

- 使用 Tailscale：接受 owner 邀请，安装并登录，看到 **Connected**；Host 使用 `sss.tail03c757.ts.net`。
- 使用物理局域网：确认两台电脑连接同一个可信 Wi-Fi／路由器；从 owner 私下取得其当前局域网 IPv4。此路径不需要 Tailscale，但必须等 owner 明确通知“局域网入口已实施并通过测试”。

两种路径都不用设置路由器端口转发，不使用 Funnel，也不向公网开放数据库。

### 第二步：打开 Navicat

已经安装 Navicat Premium 或 Navicat for PostgreSQL 的组员直接打开即可；尚未安装时，从 Navicat 官方下载并按普通 Windows 软件完成安装。

### 第三步：新建 PostgreSQL 连接

1. 点击 Navicat 左上角 **连接（Connection）→ PostgreSQL**。
2. 在“常规（General）”页面填写。下面先给出当前可用的 Tailscale 示例；物理局域网连接只替换“主机”一项：

   ```text
   连接名：AgentExam共享库
   主机：sss.tail03c757.ts.net
   端口：55432
   初始数据库：agentexam
   用户名：agentexam_admin
   密码：owner 私下发送的密码
   ```

3. 不启用 SSH 或 SSL，点击 **连接测试（Test Connection）**；显示成功后点击 **确定（OK）**。

到这里就连接完成了。正常情况下，组员不需要执行 PowerShell、Docker 命令或验证 SQL。

## 3. 连接后怎么看表

在 Navicat 左侧双击 `AgentExam共享库`，然后依次展开：

```text
AgentExam共享库 → agentexam → public → 表（Tables）
```

双击目标表即可查看；需要改数据时打开表并编辑、保存。五个人使用的都是管理员账号。

## 4. owner 平时只需要做什么

owner 只需保证：

- 电脑没有关机或休眠；
- Docker Desktop 正在运行；
- `agentexam-local-postgres-1` 容器状态为 `Up`；
- 使用 Tailscale 的组员连接时，Tailscale 保持登录；
- 使用物理局域网的组员连接时，owner 与组员仍在同一个可信局域网，且局域网入口已经另行实施并验证。

已经保存的 Tailscale Serve 配置不需要每天重建。只有组员连不上时，owner 才需要检查：

```powershell
docker ps --filter "name=agentexam-local-postgres"
tailscale serve status
```

正常 Serve 状态应包含：

```text
tcp://sss.tail03c757.ts.net:55432
--> tcp://127.0.0.1:55432
```

如果 Tailscale 的 `55432` 转发丢失，owner 再执行一次：

```powershell
tailscale serve --bg --tcp=55432 tcp://127.0.0.1:55432
```

物理局域网路径当前只是已确认目标，本轮没有实施。后续实施任务至少需要：把 PostgreSQL 的 Docker 宿主发布从回环地址改为局域网可达、只允许 Windows“专用网络／本地子网”的 TCP `55432`、重建容器，并从组员电脑做一次成功连接和一次非局域网拒绝测试。不要仅因“同一 Wi-Fi”就跳过防火墙限制，也不要设置路由器端口转发。

## 5. 只有连接失败时才排查

| Navicat 提示 | 最简单处理 |
|---|---|
| Tailscale 连接超时、找不到主机 | 组员确认 Tailscale 显示 Connected；确认 Host 为 `sss.tail03c757.ts.net`、Port 为 `55432`，并确认 owner 电脑在线 |
| 物理局域网连接超时 | 确认两台电脑在同一可信局域网、Host 是 owner 当前局域网 IPv4，并确认 owner 已实际完成局域网入口和防火墙配置；校园网／访客 Wi-Fi 可能启用设备隔离 |
| Connection refused | owner 检查 PostgreSQL 容器是不是 `Up` |
| password authentication failed | 重新复制 owner 发来的密码，检查有没有多余空格 |
| PostgreSQL 连接类型不存在 | 确认使用 Navicat Premium 或 Navicat for PostgreSQL，不要选择 SQL Server 连接类型 |

仍然无法判断时，组员再打开 PowerShell 执行：

Tailscale 路径使用：

```powershell
Test-NetConnection sss.tail03c757.ts.net -Port 55432
```

物理局域网路径把主机替换为 owner 提供的 IPv4：

```powershell
Test-NetConnection <owner局域网IPv4> -Port 55432
```

`TcpTestSucceeded : True` 说明网络已经通，继续检查用户名、密码和 Database；`False` 才根据所选路径检查 Tailscale Serve，或检查局域网绑定、Windows 防火墙和 Wi-Fi 设备隔离。

## 6. 课设只保留三条共用规则

1. 密码不要发到 Git、代码、截图或公开群。
2. 执行 `DROP`、`TRUNCATE`、删库或大批量删除前，先在组内说一声。
3. 数据库结构有变化时，同时修改项目里的 schema／迁移文件，不能只改现场数据库。

除此之外不做数据库角色划分。Module 分工只表示代码由谁主责，不限制谁连接或修改共享数据库。

## 7. 下载入口

- [Tailscale Windows 安装](https://tailscale.com/docs/install/windows)
- [Navicat Premium 下载](https://www.navicat.com/en/download/navicat-premium)
- [Navicat 官方 PostgreSQL 连接排查](https://help.navicat.com/hc/en-us/articles/217791058-Why-I-cannot-connect-to-my-server)
