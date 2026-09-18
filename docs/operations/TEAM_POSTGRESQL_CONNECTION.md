# 组员使用 Navicat 连接共享 PostgreSQL（极简版）

> 课设方案：owner 电脑只运行一套 PostgreSQL，五个人共用 `agentexam_admin` 管理员账号。
>
> 正常连接只需要：登录 Tailscale、在 Navicat 填写五项信息、点击测试连接。
>
> 当前入口：`sss.tail03c757.ts.net:15432`。密码由 owner 私下发送，不写进本文档或 Git。

## 1. owner 发给组员的连接卡片

| 字段 | 填写内容 |
|---|---|
| Host | `sss.tail03c757.ts.net` |
| Port | `15432` |
| Initial Database（初始数据库） | `agentexam` |
| Username | `agentexam_admin` |
| Password | owner 私下发送 |

`agentexam_admin` 就是本课设所说的“数据库 root 账号”。五个人使用同一账号，可以查看、增加、修改和删除数据库内容。

## 2. 组员用 Navicat 三步连接

### 第一步：登录 Tailscale

1. 接受 owner 发来的 Tailscale 邀请。
2. 安装并打开 Tailscale。
3. 使用收到邀请的账号登录，看到 **Connected** 即可。

不用设置端口转发，不用使用 Funnel，也不用修改路由器。

### 第二步：打开 Navicat

已经安装 Navicat Premium 或 Navicat for PostgreSQL 的组员直接打开即可；尚未安装时，从 Navicat 官方下载并按普通 Windows 软件完成安装。

### 第三步：新建 PostgreSQL 连接

1. 点击 Navicat 左上角 **连接（Connection）→ PostgreSQL**。
2. 在“常规（General）”页面填写：

   ```text
   连接名：AgentExam共享库
   主机：sss.tail03c757.ts.net
   端口：15432
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
- Tailscale 保持登录。

已经保存的 Tailscale Serve 配置不需要每天重建。只有组员连不上时，owner 才需要检查：

```powershell
docker ps --filter "name=agentexam-local-postgres"
tailscale serve status
```

正常 Serve 状态应包含：

```text
tcp://sss.tail03c757.ts.net:15432
--> tcp://127.0.0.1:55432
```

如果 `15432` 转发丢失，owner 再执行一次：

```powershell
tailscale serve --bg --tcp=15432 tcp://127.0.0.1:55432
```

## 5. 只有连接失败时才排查

| Navicat 提示 | 最简单处理 |
|---|---|
| 连接超时、找不到主机 | 组员确认 Tailscale 显示 Connected；确认 owner 电脑在线 |
| Connection refused | owner 检查 PostgreSQL 容器是不是 `Up` |
| password authentication failed | 重新复制 owner 发来的密码，检查有没有多余空格 |
| PostgreSQL 连接类型不存在 | 确认使用 Navicat Premium 或 Navicat for PostgreSQL，不要选择 SQL Server 连接类型 |

仍然无法判断时，组员再打开 PowerShell 执行：

```powershell
Test-NetConnection sss.tail03c757.ts.net -Port 15432
```

`TcpTestSucceeded : True` 说明网络已经通，继续检查用户名、密码和 Database；`False` 才让 owner 检查电脑、容器和 Tailscale Serve。

## 6. 课设只保留三条共用规则

1. 密码不要发到 Git、代码、截图或公开群。
2. 执行 `DROP`、`TRUNCATE`、删库或大批量删除前，先在组内说一声。
3. 数据库结构有变化时，同时修改项目里的 schema／迁移文件，不能只改现场数据库。

除此之外不做数据库角色划分。Module 分工只表示代码由谁主责，不限制谁连接或修改共享数据库。

## 7. 下载入口

- [Tailscale Windows 安装](https://tailscale.com/docs/install/windows)
- [Navicat Premium 下载](https://www.navicat.com/en/download/navicat-premium)
- [Navicat 官方 PostgreSQL 连接排查](https://help.navicat.com/hc/en-us/articles/217791058-Why-I-cannot-connect-to-my-server)
