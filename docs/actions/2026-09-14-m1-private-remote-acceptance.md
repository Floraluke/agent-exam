# M1 任务 14：私有双机协作验收

> 状态：In Progress；2026-09-15 用户已批准官方 Windows Tailscale、人工账号登录、私有 HTTPS Serve、最小 `tcp:443` grants、VPN 双态/双机/离线恢复测试与结束后关闭 Serve。任务 13 已在 `f3870f6` 关闭，任务顺序门槛已解除。

## 情况说明

任务 14 对应 Spec stories 48–52，要求另一台获准设备通过私有 HTTPS 使用 AgentExam，同时以未获准设备、原始端口、VPN 开关和评测机离线/恢复形成正反证据。它是实际双机验收，不是新增业务模块；网络准入不能替代应用账号和 owner 权限。

2026-09-14 只读现状核对显示：评测机没有 Tailscale CLI、Windows 服务或匹配网卡，也没有 Serve 配置；FlClash/Mihomo 类进程存在，但未读取其配置；`443/3000/8000/5432/9000` 当前均无监听。2026-09-05 的远程行动只完成设计文档和官方资料对账，明确没有安装或双机实测，不能作为本任务通过证据。

2026-09-15 用户明确批准任务 14 推荐方案：可安装官方 Windows Tailscale，由用户完成人工登录；配置仅限私有 HTTPS Web 的 Serve 与最小 `tcp:443` grants，禁止 Funnel、exit node 和 subnet router；可执行 FlClash/VPN 开关、获准/未获准设备、离线恢复测试，结束后关闭 Serve。用户可配合操作两类外部设备。该授权不包含公开发布、读取或记录账号秘密、扩大 tailnet 权限、修改 Docker/WSL/代理/防火墙长期设置或调用 Judge。

## 已确认边界、未知与建议

- 已确认：只采用 Tailscale Serve 私有 HTTPS，不启用 Funnel、exit node、subnet router 或校园网端口映射；只转发回环 Web，同源 API 由 Web 代理，PostgreSQL/MinIO/Docker/Worker 不对 tailnet 直接开放。
- 已确认：应用中的 `owner` / `collaborator` 继续来自 AgentExam 会话；tailnet 用户或设备身份不授予 owner 权限。
- 已确认：不需要再次调用真实模型。双机流程可用受控合成执行结果验证提交、决定、刷新、报告和安全证据；任务 13 已单独证明真实执行链。
- 已确认：允许安装官方 Windows Tailscale；用户在场完成人工登录和获准/未获准两类外部设备操作；Codex 负责本机核验、回环平台、最小 Serve/策略指导、HTTP/浏览器/端口检查、证据汇总和精确回退。
- 已确认：只允许私有 HTTPS Web 和最小 `tcp:443` grant；禁止 Funnel、exit node、subnet router，结束后必须执行 `tailscale serve off`。VPN 开启、关闭和评测机离线/恢复均在本任务授权内。
- 当前待现场冻结：tailnet 管理者、评测机和两类外部设备的测试代号及参与状态。真实账号、设备名、tailnet 域名和 IP 只在本次临时会话中使用，不写入 Git、行动或对话输出。
- 当前待验证：官方安装渠道在本机可用性、登录/HTTPS 证书同意、既有 tailnet 是否有更宽规则、两类设备能否完成 VPN 双态实测，以及 Tailscale 与 FlClash 的实际共存路径。

## 实施措施

1. **授权与设备冻结**：已取得安装、登录、Serve/grant、VPN 双态、双机、离线恢复和关闭 Serve 的范围授权；现场只冻结 `HOST`、`ALLOWED`、`DENIED` 三个非秘密代号，不持久化真实身份。
2. **人工向导**：按 `wizard` 的阶段、暂停确认和断点续做规则生成一次性人工向导。由于本机只有不可用的 WSL `bash.exe` 且没有 Git Bash，不额外安装 shell 或修改 WSL；采用同等边界的临时 PowerShell 向导，并记录该平台偏差。向导不保存密码、登录 URL、域名、IP 或策略正文。
3. **本机回环门禁**：启动受控临时 PostgreSQL/MinIO、FastAPI 和 Next.js；确认 Web/API 只监听回环，存储与 Docker 无 tailnet/公网监听，创建只进入 `AWAITING_OWNER_APPROVAL`。
4. **私有入口配置**：安装并登录官方 Tailscale 后，仅把 Web 回环端口通过 Serve 暴露为私有 HTTPS；在 tailnet policy 中用 grants 只允许获准主体访问评测机 `tcp:443`，并确认没有 Funnel/更宽旧规则抵消限制。
5. **双机正反例**：分别在 FlClash/VPN 关闭和开启时，从获准设备验证登录、提交、状态刷新、报告/安全证据；从未获准设备验证 HTTPS 拒绝；同时验证协作者批准/管理/越权读取失败及原始端口不可达。
6. **离线与恢复**：停止 Web 或评测机入口，验证远端明确不可用；在同一临时持久化数据上恢复后确认历史 Job、结果和证据仍可查，不触发旧 Job 自动续跑。
7. **回退与收尾**：关闭 Serve，停止临时服务并精确清理专属存储；按用户确认的终态保留或卸载 Tailscale，不更改 FlClash、Docker、WSL、代理或防火墙的长期设置。
8. **回归与评审**：记录每项实际结果；运行任务 14 定向验证和全量回归，以任务 13 关闭提交 `f3870f6` 为固定基准做 Standards/Spec 双轴评审，修复后同步任务单、运维文档和 HANDOFF。

## 需要修改的文件树

```text
.scratch/m1-platform/issues/
└─ 14-private-remote-acceptance.md       # 九项验收、授权和双机实际结果
docs/actions/
└─ 2026-09-14-m1-private-remote-acceptance.md # 本行动、设备代号、措施与证据
docs/operations/
└─ REMOTE_TEAM_ACCESS.md                 # 当前 Tailscale/Serve/VPN 实测状态与回退
HANDOFF.md                               # 当前阻塞、授权边界和恢复入口
runtime/acceptance/m1-task14-20260915-01/
├─ operator-wizard.ps1                         # Git 忽略的分阶段人工登录/双机操作向导
├─ tailscale-setup-1.102.4-amd64.msi           # 官方稳定 Windows 安装包；仅本机临时使用
├─ tailscale-setup-1.102.4-amd64.msi.sha256    # 官方校验文件；供应链门禁
├─ state/                                      # Git 忽略的断点标记；只含阶段号与非秘密测试代号
└─ evidence/
   ├─ tailscale-install.log                    # 首次未提升安装的真实 1603 日志
   └─ tailscale-install-elevated.log           # UAC 提升后返回 0 的安装日志
```

本任务不新增产品 Module、Interface、数据库表或顶层源码目录。Tailscale Serve 是 Web 回环入口的网络 Adapter；AgentExam HTTP 会话仍是应用授权边界，两者串联但不互相替代。

## 修改后自验证方式与成功标准

- **本机状态**：`tailscale version/status/serve status` 可读，评测机在线但不作为 exit/subnet 节点；Serve 仅有一个 HTTPS→回环 Web 映射，Funnel 关闭。
- **策略正反例**：tailnet policy 保存并通过测试；获准设备可访问 443，未获准设备拒绝，同一主体不能直达 API/PG/MinIO/Docker/Worker。
- **应用权限**：真实协作者会话能提交/查看本人内容，批准、成员/配置管理、制品清理和他人资源均拒绝；owner 在评测机决定后状态刷新。
- **VPN 双态**：FlClash/VPN 开启和关闭都记录 Tailscale `direct` 或 `relay`、可用性与延迟；任一状态失败均如实记录，不改写为通过。
- **离线恢复**：入口停止时远端失败，恢复同一数据后历史状态可查，旧 Job 不自动执行。
- **输出保护**：远程页面、下载、错误和摘要不含 auth、完整私有日志、内部对象键或秘密路径；敏感设备/账号信息不入 Git。
- **清理**：Serve、临时 Web/API/PG/MinIO 和专属容器/网络/卷按确认范围关闭；实际终态逐项核对。
- **最终门禁**：九项任务验收、任务 14 定向测试、任务 14 后全量回归和相对 `f3870f6` 的 Standards/Spec 均通过，才关闭任务 14 并宣布 M1/MVP 完成。

## 自验证情况

- 2026-09-14 只读现状：`TAILSCALE_CLI_PRESENT=False`、服务 absent、匹配网卡 0；FlClash/Mihomo 类进程 3 个。没有读取其配置、账号、设备名或网络地址。
- `443/3000/8000/5432/9000` 当前监听数均为 0，非回环监听也均为 0；这只证明检查时没有服务，不证明双机隔离已经通过。
- 当前 Tailscale Windows 安装文档、Serve CLI、Serve 功能、grants 与其他 VPN 共存说明已从官方站点核对。官方当前说明 Serve 只在 tailnet 内分享并受 access controls 约束；grants 权限是累加的；与其他 VPN 并存可能需要分流，不能只凭配置存在宣称成功。
- 2026-09-14 的授权前基线没有安装或下载 Tailscale，也没有登录或修改 Serve/grants、FlClash、路由、DNS、代理、防火墙、Docker 或 WSL；2026-09-15 的安装事实由下列新增记录覆盖。任务 14 临时平台与真实模型仍未启动。
- 2026-09-15 授权门禁已解除，状态恢复为 `In Progress`。本机复核仍为 `tailscale` 与 `winget` 命令缺失；`C:\Windows\System32\bash.exe` 是不可用的 WSL 启动器并返回访问拒绝，常见 Git Bash 路径也不存在。该失败属于向导运行环境限制，不是 Tailscale 或 AgentExam 验收失败。
- 已生成 Git 忽略的 `operator-wizard.ps1`，PowerShell 解析结果为 109 行、0 错误，阶段只记录下一阶段数字，不收集身份或网络地址。标准 Bash 向导因上述环境限制未生成或冒称通过。
- 官方稳定包页当前提供 Windows `1.102.4`；已下载 AMD64 MSI 与官方 `.sha256` 到专属 Git 忽略目录。本地 SHA-256 `80eb007e39dfebe17299fa1a09c79a8e1d934f76e0246c0817ebe3af675b7ef6` 与官方值一致，Authenticode 状态为 `Valid`、签名者为 Tailscale Inc.，安装前供应链门禁通过。
- 首次静默安装进程表面返回 0，但日志的真实 MSI 结果为 1603，原因是缺少提升权限；程序、服务和网卡均未留下。随后通过可见 UAC 由用户批准管理员安装，`MainEngineThread` 与安装结果均为 0；客户端 `1.102.4`、Tailscale 服务 `Running`、CLI 签名 `Valid`。失败与修复均保留，未把首次进程返回值误记为成功。
- 已启动官方人工登录流程；安全轮询只读布尔状态，当前仍为 `NeedsLogin`，未读取或输出登录 URL、账号、设备名、tailnet 域名或 IP。网卡数为 0 与未登录状态一致。登录和外部设备步骤等待用户实际操作；尚未把任何双机检查记为通过。
