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
├─ evidence/
│  ├─ tailscale-install.log                    # 首次未提升安装的真实 1603 日志
│  ├─ tailscale-install-elevated.log           # UAC 提升后返回 0 的安装日志
│  └─ platform/                                # 脱敏 Web 启动日志；每次预检覆盖
└─ platform/
   ├─ host_runtime.py                          # 登录后长驻平台、Serve 开关与精确退出控制器
   ├─ host_app.py                              # internal_test 应用组合、临时身份和目录初始化
   ├─ real_worker.py                           # 真实模式的一次性正式 Worker CLI Adapter
   ├─ tailscale_control.py                     # Tailscale 状态、Serve 与有界错误转换
   ├─ synthetic.py                             # 不读 auth/模型的受控 Backend/Evaluator
   ├─ preflight.py                             # 真实回环 HTTP、权限、合成结果与清理预检
   ├─ runtime_support.py                       # 随机端口/秘密、API/Web 生命周期与浏览器门禁
   ├─ tests/
   │  └─ test_real_worker.py                   # 显式触发、固定输入、零重试与超时脱敏测试
   └─ runtime_parts/
      ├─ config.py                             # Task14 专属 scope 与 Docker 标签
      ├─ storage.py                            # 固定 PG/MinIO 镜像、回环发布与就绪门禁
      └─ cleanup.py                            # 专属进程/容器/网络/四端口尽力清理和终态核对
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
- 已完成官方人工登录。安全复核只记录非秘密事实：CLI 状态正常、后端为 `Running`、本机在线且已有 Tailscale 网卡；当前没有 Serve 配置，没有使用 exit node，没有发布 subnet route，也没有启用 Tailscale SSH。复核没有读取或输出登录 URL、账号、设备名、tailnet 域名或 IP；登录门禁通过，但不替代后续 grants 与双机验收。
- 用户在 Tailscale 管理后台确认新的最小 policy 保存成功；策略使用临时代号区分 `HOST`、`ALLOWED`、`DENIED`，仅授予获准设备到主机 `tcp:443`，并对主机 `80/3000/5432/8000/9000` 及未获准设备 `443` 设置否定测试。保存成功是控制面语法与策略测试证据；设备标签、规则预览和真实网络正反例尚未完成，因此不能据此宣称远程验收通过。
- 用户把当前评测机绑定为 `HOST` 后，首次只读核对脚本误用了 PowerShell 只读自动变量 `$Host`，该项输出无效且未计为通过；改用任务专属变量重新执行后确认本机在线、仅含 `tag:agentexam-host`，不含 `tag:agentexam-allowed` 或 `tag:agentexam-denied`。获准与未获准设备仍待加入和分别绑定。
- 一台独立 Android 手机通过官方客户端加入同一 tailnet，手机端观察为已连接且 exit node 为 `None`；真实账号、设备名和 Tailscale 地址未写入仓库。用户将该手机绑定为 `ALLOWED` 后，主机侧只读复核确认其他设备共 1 台且在线 1 台、`tag:agentexam-allowed` 恰为 1、`tag:agentexam-denied` 为 0、没有其他设备误绑 `HOST`。这只证明设备角色同步，不替代 HTTPS 和应用动线实测。
- 用户原先要求先走 `ALLOWED`，随后进一步明确要求开启完整真实评测条件。本轮因此不以合成 Worker 代替最终正向证据：临时合成控制器仅到达 `ready/serve=off`，随后立即收到 `stop` 并以 `cleanup=verified` 退出，未开启 Serve、未创建远程 Job、未读取 auth 或调用模型。后续正向流复用此前已授权三次中的剩余一次私有 auth 真实运行，固定题目、Codex/模型、两个出站主机、单尝试和零重试保持不变；不调用或修改 Judge。模型次数只在真实 Worker 开始后计入。
- 为真实交互流深化 Git 忽略的 Task14 验收器：新增一次性 `RealWorker` Adapter，复用正式 Worker CLI；真实模式启动后必须显式 `run`，不会在提交或批准前自动读取 auth/调用模型。TDD 依次得到“模块缺失”“控制器不接受 real mode”“缺少固定 Codex 输入”三个红灯，最小实现后 3 项测试通过；Ruff check 通过，格式化后 10 个文件一致。既有私有 auth 只做元数据检查：普通非链接、非空、从关闭继承且仅有两条允许规则的受保护目录继承权限；未读取或输出正文。
- 真实模式首次启动达到 `ready/serve=off`、Worker `idle`；本机回环 Web 登录与目录均为 HTTP 200。第一次目录读取为 401 是安全 Cookie 带 `Secure`、回环 HTTP 客户端按规范不回送；仅在内存中原样回送该 Cookie 后 Task/Agent 目录均为 200，没有降低 Cookie 安全属性。
- 首次执行 Serve 命令超过验收器 30 秒等待上限并抛出 `TimeoutExpired`；没有收到 `serve=on`，不计为通过。控制器退出后独立确认 Serve 未配置、Task14 容器/网络均为 0、私有 operator 文件不存在，Worker 始终 idle，因此未读取 auth、未调用模型、未消费真实运行次数。官方当前文档确认首次 Serve 若 tailnet 未启用 HTTPS，会要求通过网页同意启用证书；下一步先由用户在管理后台完成 HTTPS 条件，再修正控制器的有界错误处理并重试一次。
- 用户已在 Tailscale DNS 管理页阅读公开证书日志提示并启用 HTTPS。随后按 TDD 先增加缺失 `tailscale_control` 的红灯，再把状态/Serve 调用拆入 120 秒有界 Adapter：超时只返回 `TAILSCALE_SERVE_COMMAND_TIMEOUT`，不输出命令正文、登录 URL、域名或堆栈。定向测试从 collection error 转为 4 项通过，Ruff check 通过；`host_runtime.py` 从 201 行降至 171 行，恢复到项目单文件指标内。尚未因此宣称 Serve 已成功，需下一次实际开启验证。
- HTTPS 条件完成后的第二次 Serve 在约 30 秒内返回 `serve=on`。提升权限的独立脱敏核验确认 TCP 条目恰为 1、唯一端口为 443 且启用 HTTPS，Web/Handler 各 1 并只代理随机回环 Web，Funnel 条目为 0，固定原始端口监听为 0；此时真实 Worker 仍为 idle。
- 首次手机页面操作实际误用了 owner 身份：持久化证据显示唯一 Job 的创建和批准事件均属 owner，状态为 `QUEUED`；collaborator 可见 Job 为 0。该 Job 没有被 Worker 领取、没有读取 auth 或调用模型。为避免它抢占剩余真实运行，按完整双角色验收范围只取消该唯一排队 Job，终态 `CANCELED` 且历史记录保留；下一次必须由 collaborator 新建并等待 owner 单独批准。
- 手机改用 collaborator 后，接口交叉核验确认活动 Job 恰为 1、创建事件属于 collaborator、状态 `AWAITING_OWNER_APPROVAL`、1 个 trial/Run 且 owner 决定为空；Worker 继续 idle。评测机随后通过自身 Tailscale HTTPS 名称访问得到浏览器 `ERR_CONNECTION_CLOSED`，而 Serve/Handler 仍在线；根因是 deny-by-default policy 只授予 `ALLOWED -> HOST:443`，没有 `HOST -> HOST:443`。这是一条有效拒绝证据，不是 Web 或 Serve 崩溃。为完成评测机上的 owner 浏览器动线，临时策略文件增加仅限 `HOST -> HOST tcp:443` 的自访问 grant 及对应正反测试，不扩大到其他设备或原始端口，待管理后台保存后实测。
- 用户保存自访问规则后，首次 PowerShell 默认网络探测仍失败，但无代理直连复核为 DNS 可解析、TCP 443 可达、HTTPS 200；Chrome 继续 `ERR_CONNECTION_CLOSED`，Windows 普通系统代理关闭而 FlClash/Mihomo 相关进程仍存在。采用隔离 Edge 临时 profile，并显式 `--no-proxy-server --disable-quic` 后成功显示登录页；没有修改 Chrome、FlClash、系统代理或防火墙。该结果把 Chrome 路径差异与 Serve/应用故障区分开，FlClash 开启态的兼容性仍需单列验证。
- 评测机 Edge 以 owner 登录并批准后，最终门禁确认队列恰为 1、创建者为 collaborator、批准者为 owner、规模为 1×1。控制器只接收一次 `run`；状态依次观察到 Worker `running`、Job `EXECUTING`、Run `RUNNING_AGENT/running_agent` 且无失败码，随后 Job/Run 均 `COMPLETED`。Worker 最终 `completed/result_published=true/worker_error=false`。
- owner 与原 collaborator 均能读取完成 Job 和报告；批次 1 个 Run、未解决数 0，正确 Run 报告显示确定性结果 `resolved=true`、patch 存在且成功应用、12 个制品链接、Judge 分析 0、`review_status=NOT_REQUIRED`、human review/quality tiebreak 均空。首次 Job 级监测把不存在字段经 PowerShell `@($null)` 误计为 1，已用正确 Run 端点与过滤空值复核纠正，不作为 Judge 调用证据。本次 token 用量字段均未提供，资源 wall time 可用、peak memory 不可用；唯一规范化警告为 `TRAJECTORY_UNAVAILABLE`，不影响确定性通过，但保留为后续证据完整性限制。
- Task14 零模型预检首次在普通沙箱以 `CalledProcessError` 失败且清理无法证明；只读诊断确认 Docker Desktop 当时未运行，启动既有 Desktop 后又确认普通沙箱仍因用户级 Docker 配置和命名管道 ACL 拒绝访问。提升后的 Docker 探针显示服务版本 `27.5.1` 且 Task14 标签为空；没有修改 Docker/WSL 配置。
- 提升后的首次预检在账号就绪后以 `CatalogUnavailable` 失败并 `cleanup=verified`。分阶段复现把失败定位到固定 Task 登记；离线 Task source 可读，最终确认验收器多一层 `platform/` 却沿用 Task13 根路径算法，把项目根误算为 `runtime/`。只把 `parents[3]` 修为 `parents[4]` 后，schema、bucket、账号、Task、Agent、API、Web 全部就绪。
- 完整 HTTP 预检第一轮登录返回 403，根因是验收器漏带真实 Web 客户端必须发送的 `X-AgentExam-Request: 1`；补齐既有安全头后 owner/collaborator 登录通过。下一轮 Job/Run 收束为 `FAILED/EVIDENCE_UNAVAILABLE`，根因是合成 Evaluator 自创测试分组，产品公开证据只允许 `FAIL_TO_PASS`/`PASS_TO_PASS`；改用既有合法分组，不放宽白名单。
- 修复后的真实回环 Web→FastAPI→临时 PG/MinIO 预检通过：Job 先为 `AWAITING_OWNER_APPROVAL`，协作者批准和成员管理均被拒，owner 批准后只有 internal-test 合成 worker 领取，Job/Run 均 `COMPLETED` 且报告可读；最终 `model_called=false`、`auth_read=false`、`serve=off`、`cleanup=verified`。独立 Docker 标签复核容器/网络/卷为 `0/0/0`。
- 当前仍未完成最小 grants、Serve、获准/未获准设备、VPN 双态和离线恢复实测；这些项目保持未通过，不由登录成功或本机预检替代。
