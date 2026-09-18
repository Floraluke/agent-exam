# 本机 Docker / WSL 运行环境

> 状态：Docker/WSL 历史动态验证保留；2026-09-17 补充容量盘点和持久化准备的限定只读核对
>
> 最后核验：文件系统元数据、Docker Client/Server 与 Compose 版本 2026-09-17；其他 Docker/WSL 动态值沿用下文注明的历史日期
> 文档同步：2026-09-17；只读检查不代表服务健康或持久化验收。任务 13 的 `-04` 历史验收不变
> 权威范围：本机 Docker/WSL 的实际版本、数据位置、资源上限、磁盘余量和验证状态

## 1. 这份文档解决什么问题

本文件是“这台笔电当前能怎样运行 Docker”的唯一事实源。架构、研究和依赖文档只引用这里，不各自复制一套容易过期的内存与磁盘数值。

这里记录的是**本机事实**，不是全组电脑必须一致的项目版本基线。项目依赖是否正式固定，仍由 [`DEPENDENCIES.md`](../dependencies/DEPENDENCIES.md) 决定。

## 2. 当前环境

| 项目 | 已验证值 | 通俗解释 |
|---|---:|---|
| 物理内存 | 约 15.636 GiB | 整台 Windows 笔电的内存 |
| Docker Desktop | `4.38.0.181591` | Windows 上管理 Docker 的桌面程序 |
| Docker Engine | `27.5.1` | 真正创建和运行容器的后台引擎 |
| WSL | `2.7.13.0`，WSL2 后端 | 2026-09-06 经用户授权及系统 UAC 确认，官方更新成功 |
| Docker 容器所见内核 | `6.18.33.2-microsoft-standard-WSL2` | 重启 Docker 后实际生效；Harbor 内核配置前提已通过，非网络隔离验收 |
| Windows 系统代理 | 已关闭；FlClash 进程仍监听 `127.0.0.1:7890` | 2026-09-06 `ProxyEnable=0`；需要联网的本轮命令仅使用进程级代理，不改变系统设置 |
| Docker Desktop 代理 | `ProxyHTTPMode=system` | Desktop 读取 Windows 系统代理；Engine 内部显示 `http.docker.internal:3128` |
| Docker CLI 容器代理 | `http://http.docker.internal:3128` | 新的 CLI 创建容器/构建自动注入 HTTP(S) 代理；Harbor 动态 Trial 仍须显式映射 |
| WSL 内存上限 | `10GB` | 所有 WSL2 虚拟机可动态使用的上限，不会启动时立刻占满 |
| Docker 实际可见内存 | `10,425,643,008` bytes，约 `9.710 GiB` | 2026-09-06 更新/重启后 Engine 动态值；WSL 配置仍为 10 GB |
| Docker 数据目录 | `E:\dockerdata\DockerDesktopWSL\DockerDesktopWSL` | 历史 Docker 设置中的位置；2026-09-17 只核对该路径下文件元数据，未读取当前引擎配置 |
| 主数据盘文件 | `...\disk\docker_data.vhdx`，当前逻辑长度见第 2.1 节 | 一个虚拟 Linux 磁盘文件；不得在 Docker 运行时手工剪切 |
| 各盘可用空间 | 最新文件系统查询见第 2.1 节 | 旧迁移/探针数字保留在相应历史段落，不再作为当前余量 |

Docker Desktop 会在用户选择的 `E:\dockerdata\DockerDesktopWSL` 下再创建自己的 `DockerDesktopWSL` 子目录，所以实际路径多一层。这是 Docker Desktop 保存的真实设置，不是重复迁移。

### 2.1 课设容量只读盘点（2026-09-17）

**持久化恢复时的更新快照（21:05 左右，新加坡时间）：** 只运行 `Get-PSDrive -Name D,E` 与目标目录存在性检查，未枚举私人目录或读取正文。D 可用 `37,905,600,512` bytes（约 35.30 GiB），E 可用 `8,254,152,704` bytes（约 7.69 GiB）；`D:\AgentExamData` 不存在。余量变化原因未调查，不推断是谁清理了什么，也不把余量当作增长预算已通过。下表与目录统计为当天较早快照，不作为最新余量。

同一持久化行动此前经批准只读核对 Docker Client/Server 均为 `27.5.1`、Compose 为 `v2.32.4-desktop.1`；旧任务 14 两个专属存储容器处于 Exited，未启动、删除或连接。未复核全机资源/网络健康、未改 Docker/WSL 设置；实际命令权限与结果见[实施行动](../actions/2026-09-17-minimal-local-persistence.md)。

背景：用户确认课设最小方案，先查本机占用和数据位置，云存储暂列可选。本次使用 `Get-PSDrive`、`.NET DriveInfo`、目录枚举及 `Get-Item` 等文件系统元数据；未启动或查询 Docker/WSL、未读取容器内数据、文件正文或秘密，未创建/删除/迁移文件。

| 盘符 | 已用 GiB | 可用 GiB | 文件系统 / 类型 |
|---|---:|---:|---|
| C | 258.83 | 60.54 | NTFS / Fixed |
| D | 52.76 | 27.24 | NTFS / Fixed |
| E | 44.64 | 5.36 | NTFS / Fixed；项目与历史 Docker 数据路径所在盘 |
| F | 3.73 | 25.56 | FAT32 / Removable；用途和能否保存本项目数据未获确认 |

`Get-Partition` 和 `Get-Disk` 均返回“拒绝访问”，本轮未提权重试。因此没有确认 C/D/E 对应哪些物理磁盘，不能把另一盘符直接视为防整盘故障的独立备份。F 的可移动类型也不表示已获使用该设备的授权。

对 `E:\9.1agent_exam` 跳过重解析点，只累计可读取文件的逻辑长度；不是磁盘分配量，也不是可清理量：

| 范围 | 逻辑大小 GiB | 说明 |
|---|---:|---|
| 项目可读取文件合计 | 7.335 | 7,876,056,986 bytes；包含源码、依赖、缓存和历史证据，不能等同于业务数据库大小 |
| `runtime/` | 5.797 | 下方子项包含在本行，不能再加到总计 |
| `runtime/tools/` | 2.671 | 仅路径/长度汇总，未读取正文或判断可删 |
| `runtime/cache/` | 1.611 | 缓存不等于已授权清理 |
| `runtime/prototype/` | 1.056 | 历史原型目录，不改变证据保留约束 |
| `runtime/acceptance/` | 0.459 | 历史验收目录，未读取私有结果内容 |
| `framework/` | 0.790 | Harbor 0.466、固定 Fork 0.320、SWE-Gym 0.004；都保留 |
| `apps/` | 0.709 | Web 0.461、backend 0.248；包含依赖，不仅是源码 |

扫描耗时 18.39 秒，读取 156,535 个文件、遍历 17,502 个目录；56 个路径读取失败、8 个重解析点跳过。因此项目总计仅为可读取部分；没有按硬链接去重或计算稀疏文件实际分配量，不承诺扫描原子性。

指定文件 `E:\dockerdata\DockerDesktopWSL\DockerDesktopWSL\disk\docker_data.vhdx` 存在，逻辑长度为 26,996,637,696 bytes（25.143 GiB）。本轮没有打开 VHDX 内部、确认容器运行状态或核算镜像/卷/可回收空间；该长度不能解释为“可删除 25 GiB”，也不能全归属于 AgentExam，历史环境中还有其他应用。

规划含义：E 盘余量有限，但其他本机盘还有空间；尚无证据说明课设业务数据必须搬到云端。用户随后已确认正式根目录 `D:\AgentExamData`，准确约束见[所有者单机架构](../architecture/modules/owner-host-runtime/ARCHITECTURE.md#11-已确认的课设运行约束2026-09-17)；不删除缓存或迁移全局 Docker 磁盘。最终容量还要计入新增题目镜像、运行临时空间和备份副本；仅迁项目源码目录不能证明 Docker 所在盘的增长风险已经解决。

## 3. 生效配置

### 3.1 WSL 资源上限

用户级文件 `C:\Users\YINGYI\.wslconfig` 当前内容为：

```ini
[wsl2]
memory=10GB
```

`memory=10GB` 是上限，不是预留值。Docker、Ubuntu 等 WSL2 工作负载共同受它影响；修改后必须执行 `wsl --shutdown`，再启动 Docker 才会生效。Microsoft 将 `.wslconfig` 定义为 WSL2 的全局配置文件，参见 [WSL 高级配置官方文档](https://learn.microsoft.com/windows/wsl/wsl-config)。

### 3.2 Docker / FlClash 代理通路

2026-09-05 的本机配置采用两级本地代理：

```text
新 Docker CLI 容器
  → http.docker.internal:3128（Docker Desktop 内部代理）
  → 127.0.0.1:7890（Windows 系统代理 / FlClash）
  → 外网目标
```

- Docker Desktop 设置文件已经是系统代理模式，并指向当前 Windows 系统代理；没有修改 Docker Engine `daemon.json`。
- 用户级 Docker CLI 配置只新增 `proxies.default`，HTTP 与 HTTPS 均指向 `http://http.docker.internal:3128`；原有 `auths`、`credsStore`、context、feature 和 plugin 字段保留。
- `NO_PROXY` 当前覆盖 loopback、Docker 的宿主/内部代理名称、`.local` 和 RFC1918 私网。它是应用兼容配置，不是安全边界；不同客户端对 CIDR 的支持并不完全一致。
- FlClash 仍为 `mixed-port: 7890`、`allow-lan: false`、`tun.enable: false`，宿主监听仍是 `127.0.0.1:7890`。本次没有修改 FlClash 配置，也没有创建 7890 防火墙规则。
- Harbor 动态创建 Trial，不能假设它读取宿主 Docker CLI 代理配置。2026-09-07 的执行模板已清空 Agent 主容器代理变量，由固定 Harbor 侧车约束出站；不再沿用早期“向 AgentConfig.env 直接注入通用代理”的建议。侧车自身如何经 FlClash 到真实端点仍待验收，唯一网络边界见 [Harbor 执行接口](../interfaces/HARBOR_EXECUTION.md#无凭据网络探针2026-09-07)；公开 Job 不得提供代理值。

### 3.3 固定 Fork 验证环境

2026-09-06 固定 Fork 实测补充：现有 Ubuntu WSL2（Python `3.12.3`）可以通过 `/var/run/docker.sock` 连接同一 Docker Desktop Engine；Fork 的隔离依赖安装在项目被忽略的 `framework/swe-bench-fork/.venv`。真实 gold、空、错误、不可应用、测试超时五类判卷均通过。验证容器来自既有固定摘要镜像，实际 `NetworkMode=none`、CPU `1`、内存/内存加交换上限均 `4 GiB`、PID `256`、`CapDrop=ALL`、禁止提权、无宿主挂载；未创建新镜像。测试结束后 Docker 容器/网络/卷/唯一镜像数为 `18/5/15/21`，本轮 Evaluator label 查询为空，E 盘可用 `19,154,898,944` bytes。该结果只覆盖判卷阶段，不代表 Codex 生成阶段的网络与秘密隔离已经通过。运行命令和证据目录见 [M0 行动记录](../actions/2026-09-05-m0-codex-harbor-implementation.md)。

无模型串联最终复核（2026-09-06）：Harbor NOP＋测试专用无关改动，经生产 collect 与独立 Fork 完成真实判卷；串联路径的 Windows 长路径导入修复后通过。Docker 容器/网络/卷/唯一镜像仍为 `18/5/15/21`，Evaluator label 容器为 0；固定 Fork 源码工作区干净。先前四批独立验证与本轮两次串联的八份清理记录均通过。该证据仍不包含真实 Codex 或凭据。

### 3.4 Harbor 网络前置条件

当前状态：**内核配置前提已通过，真实白名单/防绕过尚未验收**。更新前 `5.15.167.4-microsoft-standard-WSL2` 缺少 `CONFIG_NFT_FIB_INET`，`--check-network` 为 exit 2 / UNSUPPORTED_KERNEL，历史证据保留在 `runtime/prototype/network-preflight-9f314c10d4d9/`。用户授权 WSL 更新并亲自确认 UAC 后，原 `wsl --update` 返回 0，MSI 1033/11707 事件确认 WSL 2.7.13.0 安装成功；没有重复运行安装器。

固定 Harbor 的网络策略接口和能力判断见 [执行接口](../interfaces/HARBOR_EXECUTION.md#131-m0本机-codex-技术原型)。2026-09-06 更新后的这次预检仅检查内核；后续真实网络探针见第 3.5 节。`SUPPORTED_KERNEL` 只能表示内核配置前提满足，不能代表模块已加载、白名单/防绕过通过或真实 Codex 可运行；无法确定时同样非零退出。固定 Fork 的独立禁网判卷已通过，不受这一原生白名单前提阻塞。

更新期间 Docker 报告 “WSL distro terminated abruptly”，后端日志确认 WSL proxy 退出及 `running wsl-bootstrap: exit status 1`，当时本助手尚未手动 shutdown/restart。重启前同一预检实际 Docker run=125、清理查询失败，证据 `network-preflight-b950cd08235d/` 保留。这与安装过程中的 WSL 中断相符，不据此推断数据丢失。随后按授权执行官方 `docker desktop restart --timeout 90`，exit 0、Desktop running、新内核实际生效；没有手动 `wsl --shutdown`、重启 Windows、升级 Docker、修改代理/防火墙或清空发行版。正常重启命令见 [Docker 官方说明](https://docs.docker.com/reference/cli/docker/desktop/restart/)。

重启后运行 `.venv/Scripts/python.exe prototype_codex_harbor_e2e.py --check-network`：exit 0 / SUPPORTED_KERNEL、kernel_supported=true、cleanup verified=true、remaining=[]；证据 `runtime/prototype/network-preflight-254a062ee2b4/network-preflight.json`。探针使用固定摘要、禁止拉取、禁网、只读、去能力、无挂载、低资源的一次性容器，无模型/秘密。全部网络预检标签查询无残留，包含此前因 daemon 不可用而无法确认清理的探针。

更新前后快照保存在 `runtime/prototype/wsl-update-20260906/before.json` 和 `after.json`。18 个容器、15 个卷、21 个唯一镜像身份逐项一致；5 个网络名称保留，仅默认 `bridge` 的 ID 变化，其余网络身份未变。Docker 按既有重启策略从 0 个运行容器恢复为 13 个运行容器，本助手没有新建这些服务或修改重启策略；只验证资源身份与引擎可用，未做这些其他应用的业务健康验收。后续真实白名单、宿主/公网绕过阻断和模型/凭据生命周期仍须单独验证。

更新后既有 Harbor NOP→生产 patch→固定 Fork 串联回归已通过；测试结束再次核对现有容器/网络/卷/镜像身份与更新后快照完全一致，Fork 清理验证无残留、Desktop 仍 running。命令、耗时、证据及默认跳过项详见 [M0 行动记录](../actions/2026-09-05-m0-codex-harbor-implementation.md#uac-确认后的恢复结果)。没有把这次无模型回归记为真实 Codex 验收。

### 3.5 无凭据网络探针

2026-09-07 在当前 Docker/WSL 上运行固定 Harbor 原生网络侧车和两个受控 HTTP 服务；已解析 IPv4 的允许/禁止对照、两条宿主代理 CONNECT、去能力、策略切换及正常停止侧车场景通过。其后完成生产配置接线，重新通过上述网络对照及无模型 Trial/判卷/超时回归。具体行为与未覆盖边界唯一维护在 [Harbor 执行接口](../interfaces/HARBOR_EXECUTION.md#无凭据网络探针2026-09-07)，实际命令/失败/证据见 [M0 行动记录](../actions/2026-09-05-m0-codex-harbor-implementation.md#2026-09-07-网络配置接线与本地检查点)。没有读取凭据、调用模型、重启 Docker/WSL 或修改代理/防火墙。

本次按固定摘要新增 Alpine/GOST 两个上游镜像，并保留原生哈希命名的两个侧车构建缓存（首轮 CRLF 检出构建和后续原始 Git blob 构建）；输入身份见 [依赖第 6.3 节](../dependencies/DEPENDENCIES.md#63-网络探针的固定镜像与构建输入)。测试资源精确清理，容器/网络/卷/唯一镜像数为 `18/5/15/25`，仍有 13 个原有容器运行；镜像比之前多 4 个是本次明确保留的缓存，不是残留 Trial 容器或卷。未删除其他应用资源，未对其他应用做业务验收。

生产接线后的三轮无凭据实测结束，再次只读核对 Engine `27.5.1`，上述计数仍为 `18/5/15/25`、运行容器仍为 13；本次接线复用已有镜像缓存。正常/超时 Trial 与网络夹具的专属资源清理断言通过；没有执行全局 prune 或删除共享镜像。

### 3.6 项目运行状态只读核对

2026-09-07 12:33（UTC+8）用户询问 Dify 容器是否为 AgentExam。只读查询 `desktop-linux`：Docker 共 18 个容器、0 个运行、25 个镜像；`docker ps` 为空，名称含 `agentexam` 的容器查询为空。`docker compose ls --all --format json` 显示另一套 `dify` 项目，状态为 `exited(14)`，配置文件在 `D:\rag\dify\docker-compose.yaml`，不是本项目。Windows 进程查询也未发现命令行匹配项目路径或已知评测入口的 Python/Node/Harbor/Uvicorn 进程；未检查 WSL 内所有进程，不将这一检查称为全系统审计。

查询时本项目未在跑评测，也未启动 M1 网页平台。第 3.5 节的 13 个运行容器是之前测试结束时的历史快照，不代表本次查询状态。本次没有执行启动、停止、删除、重启或代理变更。用户随后明确说明 Dify 是其为释放运行内存主动关闭；这是用户补充的原因，不是从容器退出码推断出的故障诊断。本轮文档同步没有重新查询容器状态。

### 3.7 无凭据 Codex 安装探针

2026-09-07 使用依赖总表第 2.1 节所列固定 Codex 包，在既有任务摘要镜像的临时容器内离线安装工具。探针仅执行版本/帮助和 Harbor 版本复用检查；运行命令使用 UID 65534、空白受控环境、禁网、无宿主挂载、去全部能力、禁止提权、1 CPU / 1 GiB / PID=64。这是安装探针额度，不是已验收的真实 Trial 资源模板。

前后 Docker 均为 18 个容器、0 个运行、25 个镜像；专属标签容器已删除并复查为空，原镜像和其他应用容器未改。保留约 129 MB 的下载归档及约 335 MB 的解包证据，未产生新 Docker 镜像；E 盘可用空间从约 19.12 GB 到约 18.66 GB。没有重启 Docker/WSL、修改代理或启动 Dify。入口和边界见 [依赖第 2.1 节](../dependencies/DEPENDENCIES.md#21-codex-无凭据安装制品)。

网络追加取证结束后再次核对仍为 18 个容器、0 个运行、25 个镜像；安装专属标签和最后一轮网络 Compose project 的容器/网络/卷/镜像查询均为空，E 盘可用 `18656620544` bytes。网络结果见 [追加边界取证](../interfaces/HARBOR_EXECUTION.md#无凭据追加边界取证2026-09-07)：清理成功不代表隔离通过，DNS/ICMP 缺口仍需修复。

## 4. 迁移和回退纪律

- 数据位置只通过 Docker Desktop 的 `Settings → Resources → Advanced → Disk image location` 修改。
- 不在 Docker 运行时用资源管理器移动 `docker_data.vhdx`，也不直接修改 VHDX 内部内容。
- 如需迁回其他磁盘，仍使用同一 Docker Desktop 设置入口，并在操作前记录镜像、容器和卷数量。
- Docker 官方确认该设置可移动 Linux 磁盘镜像，参见 [Docker Desktop 设置文档](https://docs.docker.com/desktop/settings-and-maintenance/settings/#resources)。

D 盘目前仍有 `D:\dockerdata\DockerDesktopWSL\oslab-ubuntu-noble.tar`，约 0.88 GiB。它不是迁移后的 Docker 主 VHDX，本次没有删除；确认其来源与用途前不得把它当作“迁移残留垃圾”清理。

## 5. 2026-09-03 验证证据

| 检查 | 迁移前 | 迁移后 | 结果 |
|---|---:|---:|---|
| Docker 镜像 | 20 | 20 | 一致 |
| Docker 容器 | 18 | 18 | 一致 |
| Docker 卷 | 15 | 15 | 一致 |
| Docker 可见内存 | 约 7.575 GiB | 约 9.713 GiB | 10 GB 上限已生效 |
| 主 VHDX | D 盘，约 21.36 GiB | E 盘，约 21.34 GiB | 迁移成功 |
| 无网络冒烟测试 | 未执行 | `busybox:latest` 输出 `docker-smoke-ok` | 通过 |

冒烟测试使用本地已有镜像，并显式设置 `--network none`，没有下载新镜像：

```powershell
docker run --rm --network none busybox:latest sh -c 'test -x /bin/sh && echo docker-smoke-ok'
```

## 6. 2026-09-05 容器代理验证证据

| 检查 | 实际结果 | 结论 |
|---|---|---|
| Docker Desktop / Engine | Desktop `running`；Client/Server 均为 `27.5.1` | Engine 恢复并可执行容器 |
| Engine 代理 | `HTTPProxy`/`HTTPSProxy` 均为 `http.docker.internal:3128` | 镜像链路使用 Desktop 内部代理 |
| 内部代理 TCP | BusyBox 连接 `http.docker.internal:3128` 成功 | 运行中容器可达 Desktop 内部代理 |
| 自动环境变量 | 新 BusyBox 自动获得大小写两套 `HTTP_PROXY`、`HTTPS_PROXY`、`NO_PROXY` | Docker CLI 用户级配置已对新容器生效 |
| OpenAI 无凭据 HTTPS | `GET https://api.openai.com/v1/models` 返回 `401 Unauthorized` | DNS、TCP、代理和 TLS 已通；不表示 Codex 已认证 |
| 固定摘要镜像拉取 | `busybox@sha256:32015e...` 返回 `Image is up to date` | Docker Hub 拉取链路可用，且没有移动 `latest` 标签 |
| Docker 代理日志 | 明确记录 OpenAI 与 Docker Registry 经 `127.0.0.1:7890` 的系统 HTTPS 代理转发 | 不是根据 `401` 猜测 FlClash 路径 |
| 校园网 WLAN 地址访问 7890 | 对实测 WLAN 地址 `10.62.158.77:7890` 连接失败 | FlClash 没有向校园网接口监听 |

有一项与原先假设不同：容器连接 `host.docker.internal:7890` 实测成功，即使宿主 `netstat` 只显示 `127.0.0.1:7890`。这是 Docker Desktop 的宿主转发能力，不表示校园网能访问该端口，但意味着不可信 Agent 容器可能绕过 `HTTP_PROXY` 直接使用宿主 FlClash。**因此代理变量只解决连通，不构成闭卷网络隔离。** 正式 Trial 仍必须通过 Docker 网络/代理策略阻断宿主入口和任意直连，只允许平台登记的受控模型访问路径及其必需端点。

本次读取具体 7890 防火墙筛选器时系统返回“拒绝访问”，因此没有把“已完整审计现有防火墙规则”记为通过；本次自身没有创建、修改或删除任何防火墙规则。

第一次更新 Docker CLI JSON 时，使用带空备份参数的 `.NET File.Replace` 被拒绝；原文件 SHA-256 和 JSON 随即复核未变，临时文件数为 0。第二次使用同目录覆盖移动成功，写入后重新解析 JSON 并核对全部原顶层字段和代理字段。

2026-09-06 的 Harbor NOP 探针使用固定任务镜像真实创建 Docker Compose Trial。映射后复测 `runtime/prototype/m0-harbor-nop-20260906-05` 为 `1 passed in 20.56s`；生产有界执行器接真实 Harbor CLI 的复测 `runtime/prototype/m0-harbor-bounded-process-20260906-01` 为 `1 passed in 19.61s`：Verifier 关闭，collect hook 生成并校验 0-byte patch，stdout 未截断，Harbor CLI 在显式 UTF-8 环境正常退出，Trial 对应的 Compose container/network/volume 均无残留。修复后的正常 NOP 回归为 `1 passed in 18.87s`，真实 Windows 父子进程回归为 `1 passed in 1.34s`。这些证据不包含模型、认证或网络白名单，不能推导真实 Codex Trial 已安全可用。

同日的固定摘要镜像 collect-patch 探针使用 `--network none`，对跟踪文件修改、新文件、删除和容器内 Git commit 四种场景得到 `4 passed in 5.91s`。测试直接运行生产 `collect_patch.sh` 并调用宿主生产校验器；运行前后均为 18 个容器、13 个运行和 21 个镜像，测试前缀容器查询无输出。该证据证明四类非空 patch 与测试容器精确清理，不证明 Harbor 外层超时后的 Compose 清理。

外层超时探针使用上游 `nop` 和测试专用阻塞 collect。修复前 `1 failed in 48.51s` 并精确观测到该 project 留下 1 个容器、1 个网络、1 个本地镜像；测试 `finally` 清理后总数恢复。生产 Adapter 随后只按本 Job 落盘 Trial 身份推导的 project label 清理并复核，`runtime/prototype/m0-harbor-timeout-green-20260906-02` 为 `1 passed in 49.47s`，运行前后容器/网络/卷/镜像总数都是 `18/5/15/21`。该证据不包含真实模型或凭据。

## 7. 对 AgentExam 的直接限制

- 单机重型评测并发继续固定为 `1`；增加 WSL 上限不会让笔电变成多机系统。
- Harbor SWE-Gym 模板中的 `8192 MB` 是**单个任务环境上限**，而 `10GB` 是整个 WSL2 的共享上限，两者不是同一个概念。
- Agent 容器、判卷容器、Docker/WSL 开销和宿主进程会竞争内存，因此不能因为 `8192 MB < 10GB` 就断言模板稳定可用。
- 首个真实任务必须实测峰值内存、耗时和磁盘增长，再决定 Harbor Trial 的正式资源模板。
- 2026-09-06 collect-patch 四场景复测后 E 盘可用 `19,594,158,080` bytes（约 18.25 GiB），不适合批量下载完整 SWE-Gym 镜像集合；M0 只能选择 1 道任务起步、必要时扩至 3 道，并控制镜像缓存。
- 固定 Harbor 与任务镜像的基础验证已完成；后续容器内真实 Codex 及独立判卷证据见[第四场记录](../interfaces/HARBOR_EXECUTION.md#第四次授权运行真实补丁与独立判卷通过2026-09-08)。Token 刷新和剩余凭据生命周期仍见[认证接口](../interfaces/CODEX_AUTHENTICATION.md#63-其他尚待实测项)，不由基础连通探针推断。
- Docker CLI 自动代理不等于 Harbor 动态 Trial 自动代理；实现时必须核对 Harbor `AgentConfig.env` 的实际容器结果。
- `host.docker.internal:7890` 可达证明环境变量可以被绕过；闭卷赛道不得把当前配置直接当作端点白名单或防绕过措施。
- Harbor 原生白名单的内核配置前提已通过（第 3.4 节），但代理可联网或禁网判卷通过均不能替代实际白名单/防绕过验收。
- 当前处于 M0 核心闭环通过后的剩余验收核对阶段；Web、PostgreSQL、MinIO、登录和所有者审批属于其后的 M1 平台集成，不应阻塞 M0。
- P2 自研 Agent 只允许 DeepSeek/Kimi，但其真实 Key 不得直接注入被测容器；当前尚未实现或验证受控模型访问路径，不能把一般容器 HTTPS 已通当成该安全要求已满足，也不因此阻塞 Codex MVP。

### 7.1 任务 03 存储测试的发布端口限制（2026-09-12 来源核对）

[Docker 官方端口发布文档](https://docs.docker.com/engine/network/port-publishing/)提示：低于 28.0.0 的引擎，同一二层网络的其他主机可能访问绑定 localhost 的已发布端口。已记录本机 Engine 为 27.5.1，但本次未做网络重现、未重新核对当前版本，不能由一般文档断言这台 Docker Desktop 已被访问或已发生数据泄漏。

此前任务 01/02 的临时 PostgreSQL 确实绑定回环且清理完成，运行与原资源一致性证据保留；这些事实不能额外证明旧引擎回环发布的完整网络隔离。历史测试均为合成账号/数据，不能把本次来源发现改写成此前数据库断言失败。

任务 03 因要验证存在已知风险的固定 MinIO 社区源码，候选采用不发布宿主端口、运行期 `network none` 的共享回环测试安排；具体方案/新增授权范围只在[任务 03 行动](../actions/2026-09-12-m1-task-agent-catalog.md#专属对象存储验证环境)维护。官方说明 [none 网络只提供内部 loopback](https://docs.docker.com/engine/network/drivers/none/)，本机可行性仍需获准后实测。本次不升级 Docker、不改代理/防火墙/WSL，不连接现有数据库。

### 7.2 任务 13 本机编排预检（2026-09-13）

任务 13 先复用不发布端口的专属测试拓扑完成 Job/排行榜/取消/恢复/制品全套 `135 passed`，三个容器均只用 tmpfs、只在专属共享 network namespace 内通信，结束后按标签清理。固定 Codex 离线安装和 Harbor 外层超时清理两个 Docker 门禁分别通过；未读取认证或调用模型。

为让宿主机正式 HTTP/Worker 同时访问一次性 PostgreSQL/MinIO，后续编排预检改用专属临时 bridge，并只把两个随机端口发布到 `127.0.0.1`。Docker Desktop 实测在 `--internal` bridge 下容器内健康但宿主回环持续 `ConnectionTimeout`，所以没有保留该标志；存储镜像和启动命令固定、去全部 capability、禁止提权、只读根、受限 CPU/内存/PID、数据只在 tmpfs，凭据为本次随机合成值。该 bridge 理论上可出站，因此它是本机一次性存储拓扑的已知限制，不可直接当作长期或远程部署模板；模型 Trial 仍使用 Harbor 的独立 allowlist 网络。

完整零模型预检最终记录 `storage=ready`、`http=ready`、`jobs_created=0`、`model_called=false`、`auth_read=false`、`cleanup=verified`。回环 Python HTTP 客户端必须 `trust_env=False`，否则本机代理偶发返回 502；这只让 `127.0.0.1` 直连，不修改机器代理。首次真实 Run 在判卷前因平台本地证据 reader 漏配失败；第二次 Run 的平台 Job/Run 与固定 Fork 完成，但后置验收器误读 Harbor 配置并在页面前退出。上述实现/验收器修复后，`m1-task13-20260914-04` 用新隔离 scope 完成一次且零重试的真实 Job/Run、固定 Fork、PostgreSQL/MinIO 和浏览器闭环；最终摘要核对四个随机回环端口关闭，随后独立按专属标签查询容器、网络和卷均为空。全过程未更改 Docker/WSL/代理/防火墙；证据见[任务 13 行动](../actions/2026-09-13-m1-local-real-acceptance.md)。

## 8. 尚未验证

- 第四场授权真实 Codex 单题已完成补丁并由固定 Fork 独立判卷通过；本环境文档不维护逐场结果，最新证据见 [执行接口](../interfaces/HARBOR_EXECUTION.md#第四次授权运行真实补丁与独立判卷通过2026-09-08)。该轮未改变 Docker/WSL/代理设置。
- 固定 SWE-Bench-Fork 的五类判卷已运行并验证（第 3.3 节），真实 Codex → Fork 核心链路亦已接通；完整阶段验收仍有[执行接口对账](../interfaces/HARBOR_EXECUTION.md#暂停后的验收对账2026-09-08)所列缺口。
- 尚未确定单个 Trial 的安全内存、CPU、磁盘和超时上限。
- 尚未确认 Codex CLI 实际所需的完整域名集合，也未完成只允许登记模型访问且阻断宿主/任意公网直连的网络策略。
- P2 尚未裁决自研 Agent 的受控 DeepSeek/Kimi 访问采用宿主进程还是可信侧车，也未验证单次运行访问能力、预算限制、撤销、清理和“真实 Key 不进入被测容器”；该项不属于 M0/M1 验收门槛。

以上事项完成真实实验前，不得在其他文档中标记为“已跑通”。
