# M1 任务 14：私有双机协作验收

> 状态：Blocked；本机没有 Tailscale，且尚缺获准/未获准设备与 tailnet 配置授权。任务 13 已在 `f3870f6` 关闭，任务顺序门槛已解除。

## 情况说明

任务 14 对应 Spec stories 48–52，要求另一台获准设备通过私有 HTTPS 使用 AgentExam，同时以未获准设备、原始端口、VPN 开关和评测机离线/恢复形成正反证据。它是实际双机验收，不是新增业务模块；网络准入不能替代应用账号和 owner 权限。

2026-09-14 只读现状核对显示：评测机没有 Tailscale CLI、Windows 服务或匹配网卡，也没有 Serve 配置；FlClash/Mihomo 类进程存在，但未读取其配置；`443/3000/8000/5432/9000` 当前均无监听。2026-09-05 的远程行动只完成设计文档和官方资料对账，明确没有安装或双机实测，不能作为本任务通过证据。

当前用户只对任务 13 的固定验收题目、私有 auth 和指定模型端点给出具体出站授权；这不等于授权安装 Tailscale、登录第三方账号、修改 tailnet grants/Serve、切换 FlClash/VPN、控制另一台设备或公开服务。任务 14 在这些事实明确前不安装、不下载、不配置、不启动长期服务。

## 已确认边界、未知与建议

- 已确认：只采用 Tailscale Serve 私有 HTTPS，不启用 Funnel、exit node、subnet router 或校园网端口映射；只转发回环 Web，同源 API 由 Web 代理，PostgreSQL/MinIO/Docker/Worker 不对 tailnet 直接开放。
- 已确认：应用中的 `owner` / `collaborator` 继续来自 AgentExam 会话；tailnet 用户或设备身份不授予 owner 权限。
- 已确认：不需要再次调用真实模型。双机流程可用受控合成执行结果验证提交、决定、刷新、报告和安全证据；任务 13 已单独证明真实执行链。
- 当前未知：tailnet 管理账户、评测机稳定设备名、一个获准协作者账号/设备、一个未获准账号/设备，以及这些设备是否可在 VPN 开启/关闭两种状态参与。
- 当前未知：用户是否允许在评测机安装官方 Windows Tailscale、登录 tailnet、启用 HTTPS/Serve、以最小 grant 限制 `tcp:443`，以及测试后执行 `tailscale serve off` 并保留或卸载客户端。
- 推荐：由用户在场完成账号登录和两台外部设备操作；Codex 负责本机安装后的只读核验、回环平台启动、Serve/策略命令草案、HTTP/浏览器/端口检查、证据汇总和精确回退。第三方登录凭据、tailnet 域名和设备 IP 不写入 Git。

## 实施措施

1. **授权与设备冻结**：确认评测机、获准/未获准设备、tailnet 管理者、允许的安装/Serve/grant/VPN 开关动作及最终回退状态。
2. **人工向导确认**：按 `wizard` 流程向用户展示阶段和每阶段产物；用户确认后再生成一次性脚本。向导不保存密码，只记录非秘密测试代号与通过/失败摘要。
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
runtime/acceptance/m1-task14-*/          # Git 忽略的非秘密编排摘要；获准后才创建
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
- 未安装或下载 Tailscale，未登录第三方账号，未修改 Serve/grants、FlClash、路由、DNS、代理、防火墙、Docker 或 WSL；未启动任务 14 临时服务或真实模型。
- 当前结果为 `Blocked`：缺少具体机器变更授权和双机/账号参与条件。下一步先由用户确认第 2 节推荐方案与设备范围，再生成并验证人工向导。
