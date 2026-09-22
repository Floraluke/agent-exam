Status: ready-for-agent

# 05：假提供方安全执行链

**What to build:** 让**假提供方**走完正式执行链，把秘密隔离、请求边界、额度计量与生命周期收束固定在可证的事实上，为真实 Key 放行建立门禁。不接真实 Key、不发起真实供应商请求、不充值。

**Blocked by:** 无实施授权阻塞（2026-09-21 用户转述已直接向负责人确认同意授权）。剩余待办：**T2 在负责人机器执行**（窗口已可用，只差在那台机器上运行探针与本任务授权范围的操作）；**B 的契约确认**（受控提供方的响应呈现方式，见 Comments）。

安全合同三项：额度上界与账本计数方式已由负责人 2026-09-21 拍板（A 保守上界）并已实现；**请求字段白名单**仍须用固定 CLI 复核后才定稿。已有的 5/5 禁外网假令牌配置探针只作历史输入，不重复计为本项通过。

（2026-09-21 事实修正：本机**已安装 Docker**，T1 已在纯 Docker 层证成——原句"本机不安装 Docker"已失效。本任务单**已进入 `main`**（起草提交 `6ccf001` 是 `origin/main` 的祖先），此前"待发布"的说法作废。）

**Spec stories:** 19、21、22、23。

- [ ] 冻结安全合同：代理拓扑、私有文件格式与权限拒绝条件、可允许请求字段白名单、计量与令牌上界策略。三项尚未验证的未知（Token 上界、请求字段白名单、账本具体格式）显式标注为待冻结，不写成已确认。
- [ ] 最小拓扑实证（**T1 本机已证成 / T2 负责人机器**；原写"组长机器"，拆分经负责人 2026-09-21 同意）：做题容器仅可达专属代理；真实上游网络仅在代理侧；做题侧与代理隔离 PID、文件系统与秘密；无主机发布端口、无 Docker 套接字、无可写宿主挂载。直连拒绝、宿主隔离与正常模型请求三组正反对照齐全。
- [ ] 以 `internal_test` 的受控 API 配置走正式 Registry → 提交 → 批准 → Worker → Harbor 全链；假 Key 只进代理私有内存；做题侧固定 `config.toml` 只含代理地址、模型与短命令牌来源；生产目录不得登记假服务。
- [ ] 出站前拒绝逐条可证：未批准、错误 profile、缺密钥、宽权限或链接形式的私有文件、任意 URL、重定向、其他模型、路径越界、远程工具、跨 Run 令牌、过期重放、未知字段、超限请求。代理剥离客户端认证头后由可信侧添加凭据；"出站计数为 0"以假上游服务的请求记录为证，不以日志文本推断。
- [ ] 假服务返回 Responses 流与本地工具调用，完成一次完整工具循环、补丁收集、固定 Fork 独立判卷与报告，使**正式链路的合成 Run 可完成**、可端到端跑通。
- [ ] 故障与中断不扩大授权：401/429/5xx、断流、超时、未知 usage、超限均不自动重试、不切换模型；并发额度预留原子；流中断不退款为零；未知用量保守占用而非记零。
- [ ] 生命周期接入既有终态、协作取消、强制超时与崩溃恢复：回收代理、令牌与任务专属资源；崩溃后只按已持久化证据收束、不自动续跑；新 Job 重试需重新批准；计量状态遗失时拒绝再用旧额度、不重置为满额。
- [ ] 秘密外表面零命中：真值与假值均不进入 argv、共享环境变量、inspect 可见配置、日志、数据库、制品或 UI；做题侧能取得的 Run 令牌仍受限且会过期，不宣称完全不可窃取。
- [ ] 回归与收口：隔离 PostgreSQL/MinIO、假网络/浏览器及旧 ChatGPT 合成链回归通过；记录网络图、威胁与限制、配置摘要、失败与精确清理；无新增数据库表、无第二执行接口；全程未读取真实 Key、未发起真实供应商调用、未充值。

**停止（阻断真实 Key）：** 拓扑无法落实、固定 CLI 无法闭卷执行、预算缺失时仍可出站——任一项不通过即停在本任务，不得进入 06/07 真实调用。不降级为真 Key 进做题容器、不放宽到公网、不静默更换 CLI、不实现协议桥接。

## Comments

2026-09-21 由成员 E（LLY）起草，等待项目负责人发布与开工授权。起草依据：[执行计划第 7 节](../plan.md)、[分层验收规范](../verification.md) 的需求覆盖表 Q10/Q13/Q14 与第 4 节"代理与限额"、[团队分工](../../../docs/architecture/modules/TEAM_WORK_ALLOCATION.md) 第 5 节。

起草时已核对的事实：

1. **无技术硬前置**：计划第 7 节的前置是"用户安排 API 阶段；先确认候选内部树与安全实现合同"。因此本任务不被 03 的收尾阻塞；但按计划第 2 节"独立项也不并行越阶段"，实际开工仍以用户安排为准。
2. **既有探针不重复计分**：固定 CLI `0.153.0` 的禁外网假令牌配置探针 5/5 通过（[研究第 6.1 节](../../../docs/research/2026-09-17-codex-provider-config-and-budget.md#61-固定-cli-配置探针)），只证明配置加载、请求路径与模型名正确，**不证明**真实供应商兼容、代理隔离或完整工具循环。该结果只作历史输入。
3. **必须新增内部实现**：现有 Harbor 网络侧车只有网络过滤能力，不能托管 Key 或注入认证头（[认证接口第 4.1 节](../../../docs/interfaces/CODEX_AUTHENTICATION.md#41-codex-第三方-api-扩展规划2026-09-17)）。代理定向为既有 Execution Adapter 的内部实现，不新增业务 Module、公共接口或数据库表。
4. **侧车拓扑不能照搬**：认证接口第 4.1 节第 5 条明确警告——现有主容器与网络侧车共享网络命名空间，照搬后不能宣称防绕过。Compose 拓扑须重新设计，并按第 2 项验收做三组正反对照。
5. **三项未验证未知**：Token 上界、请求字段白名单、账本具体格式由[实现地图第 5 节](../implementation-map.md#5-05-开工必须冻结的安全候选)明示尚未验证，须在开工时先冻结，否则测试会把假设编码成断言。
6. **本机限制与排期影响**：E 的开发机按阶段 0 决定不安装 Docker，`framework/`、`runtime/` 与固定镜像均只在组长机器。因此第 2 项验收与集成层验证只能到组长机器执行；本机只能覆盖策略层、契约层与生命周期层的替身测试。排期上需先取得组长机器的可用窗口。
7. **Spec story 19 在本任务的范围**：只覆盖 `internal_test` 受控配置这一片。生产目录登记 DeepSeek/Kimi 真实预设属于 06/07，本任务不得在生产目录登记假服务。

E 侧已有准备产物：[阶段 1 代理测试设计](../../../docs/LLY/01-plan/STAGE1_PROXY_TEST_DESIGN.md)，把本任务验收项与负例矩阵映射为测试归属、断言与运行位置，可直接作为开工清单使用。

等待事项：负责人发布与开工授权；组长机器窗口；三项安全未知的冻结。

2026-09-21 负责人只读核对结论（填充版）：**前置总判定 STOP，拓扑实证未执行。** 负责人对本仓库作只读核对后返回[填充版记录](../../../docs/LLY/01-plan/TASK05_OWNER_DELIVERY_FILLED.md)，要点：

- **9 项拍板事项全部仍为"待负责人确认"**，因此本任务单第 1 项验收（冻结安全合同）尚不可开始。第 7 项输入 Token 计数方式负责人**推荐 A 保守上界起步**（当前仓库没有经过供应商账单对齐验证的 tokenizer），但这是建议、不是最终选择。
- **6 项运行前置只有 1 项完整满足**：`framework/harbor` revision `6af8d6e31eced13b93849cdf80feeadf24603d15` 与依赖表一致、工作树干净。Docker Engine 27.5.1 可响应但**未获创建授权**；持久化服务容器在运行；假 Key 文件未提供或核验；专属命名/标签边界与创建删除授权均未给出。
- **7 条拓扑断言全部未执行**，无探针目录、命令输出、`summary.json`、网络图、镜像 digest 或清理记录。负责人明确：不得用历史 M0 Harbor 侧车探针代替本任务的双网络证明。
- 负责人已核实的代码事实：Catalog / 目录 HTTP schema / Agent Registry / Worker 组合 / Harbor 引导**仍全部固定 `openai_chatgpt` 与 Codex**，候选 `provider_access`、短期令牌、请求字段白名单、预算账本、双网络均不存在；Harbor 层 `max_retries=0` 已存在，但**不能**替代 Codex CLI 的 `request_max_retries`/`stream_max_retries` 显式置零与代理实际转发次数的独立验证；现有认证文件校验不足以证明 Windows ACL/属主。
- 负责人指出原交付要求第 2 节第 3 项存在措辞缺陷（把"业务 Job"与"持久化服务"混为一谈），已修正并标注来源。
- 负责人另指出 `docs/LLY/01-plan/STAGE1_PROXY_DESIGN_FREEZE.md` 在仓库中不存在——**该判断正确**，原因是该文件产出后未提交。该文件已随本次归档切片提交，指针修复。

结论：本任务仍停在"未发布、未授权、前置未满足"状态。下一步需要负责人明确给出 9 项决定，以及第 3 节的机器窗口与创建/删除专属容器、网络、卷的操作授权。

2026-09-21 负责人回执（9 项决定已完成）：**9 项全部拍板**，见[负责人决定与授权回执](../../../docs/LLY/01-plan/TASK05_OWNER_ACTION_REQUIRED.md)。

- 输入 300,000 Token、输出 32,000 Token（含推理）、模型期限 900 秒（与环境构建/独立判卷分开计时）、频率最多 3 次/分钟（账户更低时从低）、首轮支出目标 ¥100（**只称计划目标，不称硬上限**）、Kimi 项目日/月预算各 ¥80（**账户侧设置本轮未执行**）。
- **第 7 项选 A 保守上界**：必须证明不低估，**不承诺精确账单**；做不到就停在假提供方门禁。
- 私有文件使用负责人已选定的仓库外私有路径、当前 Windows 用户为属主、**绝对路径不入 Git**。
- **第 9 项只确认资源范围（项目名/网络/服务/标签），未给执行窗口**：本轮负责人只授权填文档、同步分支、提交并普通推送，**不运行拓扑探针、不创建或删除 Docker 资源**。
- 前置核对由 1/6 升为 **3/6**（Harbor revision、无活动业务 Job、专属资源范围）；Docker 创建能力、假文件权限、当前执行授权仍未满足或未给出。**7 条拓扑断言仍全部未执行。**
- 已确认数值写入[设计冻结底稿](../../../docs/LLY/01-plan/STAGE1_PROXY_DESIGN_FREEZE.md)第 3.4 节与第 4 节；**仍未取得实施开工授权**，本任务单第 1–9 项验收均不得据此视为开始。

2026-09-21 与 B（Web 与 HTTP）对齐两项：

1. **接口边界纳入冻结项**：`HTTP_API.md` 第 10.2 节新增受控文案约束——`failure_code` 是受控枚举；`failure_summary` 与 `stage_message` 是**面向用户的受控短文案**，不得包含上游主机名或 URL、文件系统路径、凭据 profile 名、令牌或 Key 片段、容器与网络拓扑；**内容安全由写入方负责、Web 层不猜测**。该段点名"任务 05 的假提供方链以及任何未来的 provider 实现都必须遵守"。已纳入[设计冻结底稿第 3.7 节](../../../docs/LLY/01-plan/STAGE1_PROXY_DESIGN_FREEZE.md)作为第 1 项验收的组成部分，权威正文以 §10.2 为准。
2. **呈现验证排期**：B 需要在本任务链条落地后补两项呈现验证——受控文案的忠实呈现、未知错误码的失败关闭。后者需给浏览器夹具加"强制下一次响应出错"的控制端点，B 希望与本任务链条落地后排期一起加；该端点属 B 的测试基建，本任务不代为实现。**触发条件：本任务链条落地后通知 B。** B 的切片记录见 `docs/architecture/modules/web-and-http/actions/05-necessary-error-presentation.md`。
3. B 明确任务 05 内没有其他实现项；若错误呈现需要新的出口，E 侧提前告知，B 从契约侧配合。

2026-09-21 本机 Docker 前提变更与拆分提案（**待负责人确认；本次不修改已批准的验收项**）：

- **变更事实**：E 的开发机已安装 Docker Desktop（CLI 29.6.2，**守护进程当前未运行**），WSL 存在 Ubuntu-22.04。原方案"本机不装 Docker、容器与网络全部在负责人机器"的前提不再成立。阶段 0 当时拒绝装 Docker 的理由是"依赖虚拟网络、与本机既有网络驱动问题叠加"；该风险点**尚未验证**——本机能否创建自定义网络仍未知，正是前置核对第 1 项所指。
- **不变的事实**：`framework/harbor` 仍只在负责人机器上（被 `.gitignore` 排除），因此"固定 Harbor 是否允许替换其侧车网络附加方式"仍只能由负责人机器回答。
- **提案（未获批准前不执行）**：把拓扑实证拆成两半——**T1 纯 Docker/Compose 层在 E 本机跑**，覆盖断言 1–7 中不依赖 Harbor 的全部条目（"其他 Trial 网络"用第二个容器模拟）；**T2 固定 Harbor 集成层仍在负责人机器**。价值：本机先证拓扑概念，负责人侧只需做 Harbor 集成那一半，风险与工作量都小得多；若拓扑本身不成立，也最早发现。T1 通过**不等于**本任务拓扑验收通过——最终仍须在固定 Harbor 上成立。
- **本任务单第 2 项验收仍写作"（组长机器）"**：本次**不擅自修改负责人已批准的验收项**。若负责人同意拆分，再据其确认同步该验收项与 `Blocked by`，并同步[测试设计](../../../docs/LLY/01-plan/STAGE1_PROXY_TEST_DESIGN.md)与实施方案的运行位置。
- 实施方案（文件树、S1–S11 分片、验证方式、待授权清单）见 `docs/LLY/01-plan/STAGE1_IMPLEMENTATION_PLAN.md`。

2026-09-21 E 侧实施进展（按会话内授权执行；**状态标签与已批准验收项均未改动**）

授权口径（如实记录，避免与负责人书面回执混淆）：

- 负责人 2026-09-21 书面回执原写"未授予实施开工许可，第 2–4 步仍须等待任务状态和开工授权"。**其后用户（项目发起人）在会话中明确同意三项**：①任务 05 实施开工；②把拓扑实证拆为 T1（本机纯 Docker 层）/T2（负责人机器固定 Harbor 层）；③T1 在本机执行；并追加"其它需要开工授权的也同意"。E 据此执行，范围**只含本机实施与 T1**，不含真实模型/供应商调用，也不含负责人机器上的任何操作。
- 因此本任务单 `Status` 仍为 `needs-info`、第 2 项验收仍写"（组长机器）"，**未获负责人书面确认前不擅自改动**。建议负责人补一句书面确认，再据其同步第 2 项验收的机器归属与 `Blocked by`。

已完成（本机）：

1. **S3–S7 代理纯逻辑安全不变量全部落地并有测试**：`adapters/execution/provider_access/` 6 个源文件（均 ≤200 行，目录上限 8）；测试 `tests/providers/policy/` 5 个文件，定向 **67 passed / 1 skipped**（跳过项为 POSIX 属主位，本机 Windows 属设计如此）。同一 HEAD 实测：`ruff check` 通过、`ruff format --check` 313 文件、`mypy` 174 源文件无问题、默认回归 **484 passed / 102 skipped / 2 failed**（2 项失败仍为缺 `framework/harbor` 的 ISSUE-04，与基线一致）。
2. 测试抓出并修掉 **4 处真实缺陷**：缺 `profiles` 时结构校验被短路；上游地址校验过宽（任意主机都能通过）；请求缺 `stream` 抛裸 `KeyError`；`transport` 的 `repr` 泄漏认证头（`repr(headers)` 同样会漏）。
3. **T1 已在纯 Docker 层证成**：7 条断言全部测到并通过（**28 项判定**全 PASS，连续两次一致），含正对照（做题侧 → 代理 → 假上游，假上游自身 verbose 日志记下"连接来自代理 IP"与 `cmd=ping`）和**反向对照自检**（故意把做题侧接进出网网络时断言 2/3 如预期失败，证明负例不是空断言）。**探针已纳入仓库**：`apps/backend/tests/providers/runtime/`（含 `README.md` 与假值 fixture，可在负责人机器直接复用），运行证据写到被忽略的 `.tmp/t05-topology/`；原始记录已抄进[本机实施行动](../../../docs/actions/2026-09-21-task05-local-implementation.md)。清理按 `agentexam.task=05` 标签复核残留为 0，未执行全局 prune。
4. **run 01"未证成"的根因已定位，其 CLOSED 全部是工具链假象**：监听端容器因 `--cap-drop ALL` 去掉 `CAP_SETUID`/`CAP_SETGID`，在入口脚本降权时退出（`setpriv: setresuid failed: Operation not permitted`，退出码 127）——容器根本没起来。修法是让监听端以镜像内 redis 用户运行，`--cap-drop ALL` 与 `no-new-privileges` 全部保留。另修掉 4 处会产出假阴性的探针缺陷（监听端镜像无 bash、转发替身漏端口号、一次性监听的重生窗口、用 redis argv 做 PID 标记），并加入健康门禁：工具链不健康即中止且**不输出任何断言**。
5. 本机 Docker 能力（前置第 1 项）验证通过：阶段 0 记录的"虚拟网络风险"未出现。

**边界**：T1 与 Harbor 无关，转发用中继替身（不含 HTTP 语义），**T1 通过不等于第 2 项验收通过**——第 2 项仍须在固定 Harbor 上成立。

未做与等待：

- **未做**：S2（`provider_config.py`，字段名待固定 CLI 复核）、`service.py` 网络接线、S8（目录与身份扩展）、S9（`delivery/worker/runtime.py`）、S10、S11。
- **等负责人书面确认**：实施开工与 T1/T2 拆分（据以同步第 2 项机器归属与 `Blocked by`）。
- **等 T2 窗口**：资源范围已确认，窗口为空。
- **等本任务链条落地后通知 B**：给浏览器夹具加"强制下一次响应出错"的控制端点（属 B 的测试基建）。

2026-09-21 登记范围决定（用户确认）与给 B 的契约请求

- **用户已确认方案 A**：S8 只放开到**受控假提供方**——新增一个仅在 `internal_test` 用途下可登记的 provider/auth 身份；DeepSeek/Kimi 的真实提供方身份不在本任务放行，留给 06/07；既有 OpenAI/Codex 身份与指纹不变。已写入[设计冻结第 3.8 节](../../../docs/LLY/01-plan/STAGE1_PROXY_DESIGN_FREEZE.md)。
- **给 B 的契约请求（按任务单"E 侧提前告知、B 从契约侧配合"）**：受控 API 预设的身份要在**响应里如实呈现**，而现在的响应层做不到。2026-09-21 实测：给一条 `model_provider="deepseek"` 的记录，列表接口回的是 `"model_provider":"openai_chatgpt"`——`AgentDetail.from_record` 把 `agent_type`/`model_provider` 写死而不读记录，所以**当前不是报错，是假报告**（指纹按真实记录算，两个字段却按写死值回）。注册路径另有两道更早的拦截（注册表校验与库级 CHECK），但那是"拒绝"，与"如实呈现"是两件事。
  - 因此要请 B 确认两点：① `model_provider` 从只含 `openai_chatgpt` 的**字面量**扩为**受控集合**（含一个仅 `internal_test` 使用的受控值），并更新 `HTTP_API.md` §195 示例与 §297/§315 说明；② 受控值作为非秘密元数据在列表/详情里公开是否可接受（若不接受，需要契约明确规定隐藏方式，E 不自行决定）。
  - `agent_type` 保持 `codex`（本方案只放开提供方与认证方式），故只扩 `model_provider`。扩枚举与"改为读取记录"必须同批：先改读取会在窄枚举下直接 500。
  - 请 B 决定 `HTTP_API.md` 正文与响应示例的写法（当前 §195 示例、§297/§315 的 query 说明都只提到 `codex` / 既有提供方）。
  - 代码侧 `delivery/http/catalog_schemas.py` 在本任务 S8 的文件范围内，E 会一并改成**从记录读取**（现在 `from_record` 把 `agent_type` / `model_provider` 写死，扩枚举时若不同时改，登记第二种身份就会与记录不符）。
  - 若 B 认为该扩宽应等待更明确的契约措辞，请回复，E 会把该处留空、只交付不依赖它的部分（库级约束的显式升级脚本与注册表校验）。
- 另：本任务链条落地后仍需通知 B 排期"强制下一次响应出错"的夹具端点（B 的测试基建），触发条件不变。

2026-09-21 授权到位与状态同步

- **授权依据（如实记录）**：用户 2026-09-21 转述"负责人我直接问了，同意授权"——即负责人同意实施开工与 T1/T2 拆分。此前负责人书面回执原写"未授予实施开工许可"，本条为**经用户转述的口头确认**；建议负责人在本任务单 Comments 补一句自己的书面确认，以便与他人交接时口径一致。
- **本任务单已发布**：`6ccf001`（起草提交）已是 `origin/main` 的祖先，任务单在 `main` 中，故"待负责人发布"已不成立。据此把状态标签由 `needs-info` 更新为 `ready-for-agent`（要求已明确、已获授权、正在实施）；**发布与标签的最终口径仍以负责人为准**，若认为不宜，请直接改回。
- **第 2 项验收的机器归属已按同意口径更新**为"T1 本机 / T2 负责人机器"，原措辞"（组长机器）"在括号内保留可查。**T1 已证成**：七条断言全部测到并通过（28 项判定全 PASS，含反向对照自检），探针已纳入 `apps/backend/tests/providers/runtime/` 供负责人复用。**T2 仍未执行**——它要回答的是固定 Harbor 是否允许替换其侧车网络附加，只能在负责人机器回答。
- **T2 就绪**：窗口已可用（用户确认随时可跑）；执行命令、前置核对现状、需要的那句操作授权与回报要求已写入[组长机器预案附二](../../../docs/actions/2026-09-21-task05-owner-machine-runbook.md)。
- **本机实施进展**：S3–S7 与 T1 完成、S8 首个片段（`agent_type` 筛选接线）完成；S8 主体（受控 API 预设）已定范围（方案 A，见[设计冻结第 3.8 节](../../../docs/LLY/01-plan/STAGE1_PROXY_DESIGN_FREEZE.md)），其中"受控提供方用什么身份"这一处架构选择待用户拍板；S2 待固定 CLI 复核字段名；`service.py` 网络接线待 T2。

2026-09-21 S8 主体完成：受控 API 预设可登记（身份机制已定稿）

- **身份（E 侧机制决定，记入设计冻结第 3.8 节）**：provider `internal_test_fake` + authentication `provider_run_token`，成对校验；唯一权威清单在 `domain/agent.py` 的 `CONTROLLED_IDENTITIES`。该身份的"固定上游"登记为 `https://fake-upstream.t05.invalid`——**保留域 `.invalid` 在隔离网络之外永不解析**，故生产误配也只失败关闭，不会打到任何真实供应商；假上游需终止 TLS（测试专属证书，属集成层）。
- **顺带修掉一处真实缺陷**：`catalog_schemas.py` 原把 `agent_type`/`model_provider` 写死，导致非既有提供方的记录被**假报告**成 `openai_chatgpt`（指纹却按真实记录算）。现改为按记录如实呈现，并对超出受控集合的值失败关闭。
- **生产目录仍不含假服务**：受控预设单独放在 `INTERNAL_TEST_AGENT_PRESETS`，生产 `AGENT_PRESETS` 不变，并有专门用例钉住这一点（对应本任务第 3 项验收"生产目录不得登记假服务"）。
- **库级约束放宽且可显式升级**：`schema.sql` 的两条 CHECK 改为受控集合并命名；新增 `upgrade_api_constraints()`，复用 Job 包既有的"读定义 → 升级 → 复核"模式，未知形状直接拒绝、不静默重写。**已在本机真实旧库 `agentexam_dev` 上实测**：首次 `True`、再次 `False`。
- **验证**：默认回归 **489/104/2**、开启 PG **541/52/2**（增量正好是 5 个新用例），静态检查全绿，2 项失败仍是缺 `framework/harbor` 的 ISSUE-04。用例区分力实测两处（退回写死值即失败；升级用例先制造真实失败）。
- **仍需 B 一件事（措辞，不阻塞代码）**：`HTTP_API.md` 的响应示例与 query 说明请补上受控提供方值 `internal_test_fake`（§195 示例、§297/§315 说明目前只提 `codex`/既有提供方），并确认该非秘密元数据在列表/详情公开是否可接受。代码侧已完成，B 若要求改为隐藏，E 按新措辞调整。

2026-09-21 受控文案映射完成（B 点名要求的那一片）

- 新增 `provider_access/failures.py`：内部错误码 → 四类受控 `PROVIDER_*` 码 + 固定中文短句（凭据不可用 / 访问未授权 / 请求被策略拒绝 / 额度或期限用尽）。**未映射的内部码一律落到通用受控值，绝不回显**——内部码未经发布审查，且其中一些就在文件路径与凭据 profile 名旁边抛出。
- 两条结构性门禁已进测试：**词汇表防漂移**（扫描包内所有大写码字面量，出现未决定的新码即失败）与**文案哨兵扫描**（发布文案不得含上游主机名/URL、路径、profile 名、令牌片段、容器与网络拓扑词，长度也受限）。门禁区分力已实测（注入 `TRANSPORT_NEW_UNREVIEWED_CODE` 即失败并指名）。
- **请 B 在 `HTTP_API.md` 第 10.2 节把四个受控码列入枚举**（当前为候选）：`PROVIDER_CREDENTIAL_UNAVAILABLE`、`PROVIDER_ACCESS_DENIED`、`PROVIDER_REQUEST_REJECTED`、`PROVIDER_BUDGET_EXHAUSTED`，以及通用兜底 `PROVIDER_ACCESS_FAILED`。若 B 更倾向别的命名或粒度（例如额度与期限拆成两个码），E 按契约改映射表与用例即可。
- 边界：映射表当前**尚无调用方**——接线在 `service.py`（其网络形态待 T2 结论），因此本片只保证"映射存在且受门禁保护"，不声称任何失败链路已端到端可用。

2026-09-21 本机部分实施完毕（S6a–S6e，`service.py` 与接线）

按 [`docs/LLY/01-plan/STAGE1_PROXY_SERVICE_PLAN.md`](../../../docs/LLY/01-plan/STAGE1_PROXY_SERVICE_PLAN.md) 实施五片，实测与证据见[本机实施行动](../../../docs/actions/2026-09-21-task05-local-implementation.md)：

- **S6a 入口、鉴权、策略、凭据**：`decide()` 按六步失败关闭顺序执行（形状 → 鉴权 → 策略 → 凭据 → 预留 → 出站描述），任一步失败都给固定内部码 + 受控文案，且**不动账本、不出站**。
- **S6b 额度与结算**：`stream.py` 只解释终止事件（有界缓冲，畸形帧一律当"没有 usage"）；`runner.py` **无论流怎么结束都只结算一次**——没有终止事件、被切断、超时、客户端中途离开，一律**按整笔预留全额计费并关闭该 Run**。
- **S6c 出站与流透传**：`egress.py` 是全项目唯一开 socket 的地方（一次连接、一次尝试、不跟随重定向、上游状态映射为固定码）；`http.py` 用受控文案应答、字节原样透传，**客户端消失也会结算**。
- **S6d 收束**：`closure.py` 撤销令牌 + 关闭账本，首个原因不被改写；"新代理 + 同一账本"继承已花费额度，**重启不是重新发额度**。
- **S6e 秘密外表面**：五条错误路径的对外文案与响应头、进程 stdout/stderr、环境与 argv、运行目录落盘文件，**全部零哨兵命中**；经代理发出的凭据是代理自己的假值，做题侧令牌从未到达上游。

证据方式（不用日志文本推断）：假上游自己的请求记录证明"经代理发出"（1 次请求、模型名与凭据来自绑定）与"被拒时只有一次尝试"；客户端收到的字节与上游逐字节一致。**区分力实测七处**（改实现让它失败、还原后通过）。最终实测：**默认回归 587 passed / 105 skipped / 2 failed**（失败项仍是缺 `framework/harbor` 的 ISSUE-04）、`pytest tests/providers` **165 passed / 1 skipped**、静态检查全绿。

**仍未完成，且都等 T2**：S9（worker 按 Run 选绑定）、S10（`net/` 与网络接线）、S11（集成层：容器拓扑、直连拒绝、宿主隔离、假 Key 探查、精确清理）——这些必须在固定 Harbor 上回答，属负责人机器。S2 的 TOML 字段名与事件词表也要在那台机器上用固定 CLI 对账。

**请负责人/用户定夺一件安全取舍**：`build_outbound` 会转发除认证头以外的客户端头。`Host` / `Accept-Encoding` / `Content-Length` / `Transfer-Encoding` / `Connection` 现由传输层接管（否则会出现两个 Host、或压缩流破坏终止事件解析），但 `X-Forwarded-Host` 一类仍会到达注册上游（**目的地本身不受影响**，已断言）。是否收紧为白名单（只留 `Content-Type` 等）需明确。

2026-09-22 关闭 B 指出的缺陷：超受控集合的存量记录不再返回 500（E 侧小片已实施）

- **来源**：B 在[受控词汇对齐行动](../../../docs/architecture/modules/web-and-http/actions/05b-t05-controlled-vocabulary-alignment.md)第 6 节把一处新问题留给 E 决定——`catalog_schemas.py` 的 `_controlled()` 抛裸 `ValueError`，而 `app.py` 只注册了 6 个异常处理器、没有 `ValueError` 的，因此该路径当时表现成 500、不带受控错误码。
- **修法（E 的实现选择，零契约变更）**：改为抛既有域错误 `CatalogUnavailable`，由 `errors.py` 既有处理器映射为 **503 `DEPENDENCY_UNAVAILABLE`**——`HTTP_API.md` §5 已把"目录对象缺失/损坏"归为 503，故未新增错误码、未改契约。内部码 `UNCONTROLLED_AGENT_TYPE` / `UNCONTROLLED_PROVIDER` 只留在进程内，不回显。
- **可观察行为（给 B）**：该路径对客户端是 **503 + `DEPENDENCY_UNAVAILABLE`**，正文不含内部码，也不含记录自身的 provider / agent 取值。§4.2 现只把 `UNCONTROLLED_*` 记为失败关闭标记、未写状态码，B 可自行决定是否补一句；本片未改 B 的文档。
- **验证**：新增 `tests/catalog/agent_identity/test_uncontrolled_records.py`（4 条用例）；**区分力实测**（把实现退回 `raise ValueError(code)` 后 4 条全部失败，还原后通过）；`pytest tests/catalog` 46 passed / 29 skipped、默认回归 **591 passed / 105 skipped / 2 failed**（+4，失败项仍是缺 `framework/harbor` 的 ISSUE-04）、`ruff`/`format`/`mypy` 全绿。过程见[行动记录](../../../docs/actions/2026-09-22-t05-uncontrolled-identity-http-error.md)。
- **另记 B 对我方转述的一处修正**：HTTP 响应只含 `agent_type` 与 `model_provider`，**不含** `authentication_type` 与凭据 profile（契约本就规定不返回认证方式与凭据引用）；E 侧此前把它算作"要公开的身份"，属转述不准确，已按代码更正。
- 本片不改变本任务其余停点：**S9/S10/S11 仍等 T2**（T2 需在负责人机器执行，探针已入库、窗口可用，只差一句书面授权）。

2026-09-22 负责人机器复测 T1、Harbor 源码结论与 T2 授权增补

- **T1 已在负责人机器复测通过**：在 `lly/dev`（`ffb2c74`）上运行两条探针命令，正常 **28 PASS / 退出 0 / `status=verified`**，反向对照 **4 条预期 FAIL / `status=negative-control-ok`**；每次 4 容器 3 网络均带双标签、无卷创建，清理复核为空。探针本身也经其收紧：预检拒绝同名资源与未缓存镜像（不自动拉取）、清理改为"名称 + 任务标签 + 本轮 scope"三重匹配、UID 查询容器纳入标签，**断言与 verdict 未改**（E 已逐行核对）。记录见[负责人 T2 复测记录](../../../docs/actions/2026-09-22-task05-owner-t2.md)。
- **Harbor 侧车附加的源码结论**：**允许按服务绕过默认侧车附加**——任务 Compose 或 `extra_docker_compose` 中显式声明 `networks`/`network_mode` 的服务被排除在生成的侧车覆盖文件外（`docker.py:433-449`、`466-473`）；入口为 `JobConfig.environment` → `Trial EnvironmentConfig.extra_docker_compose` → `DockerEnvironment`。**该结论不等于 T2 已运行，也不等于防绕过成立**。
- **T2 因此仍未运行**，原因是两处授权冲突：Harbor 构造期会创建**无名称无标签**的内核探针容器；其常规拆除路径可能执行 `down --rmi local --volumes`（超出"只按名称与标签删除、不删镜像"）。**用户 2026-09-22 明确授权增补**，范围与硬边界写在[组长机器预案附三](../../../docs/actions/2026-09-21-task05-owner-machine-runbook.md)：允许那个 `--rm` 短命探针容器（但不得挂载 Docker 套接字/发布端口/写宿主路径，若包含即停并报告）；允许常规拆除但**只可删除该次 Trial 自己的 compose 项目资源**，不得删除拉取的固定镜像或其他项目的卷，且须在执行前后记录并复核镜像/卷清单。
- **建议的最小 T2 形态**（不接 Codex CLI、不接真实模型）：用 `extra_docker_compose` 给 `services.main` 声明显式网络，定义 `internal`（`internal: true`）与 `egress`，另起受控 `proxy` 与 `fake-upstream`，把**七条断言作为该次 Trial 的命令**在真实 Harbor 环境里跑，证据取 Trial stdout 与事后 `docker inspect`。
- 任务 05 的拓扑验收**仍未通过**；本轮也没有把 T1 结果外推为 T2 通过。

2026-09-22 负责人机器 T2 首次执行：**未测得**（工具链失败，非拓扑结论）

- **实际结果**：在 `runtime/lly-dev-verify` worktree 的 `lly/dev` 上跑固定 Harbor 最小环境，Harbor 创建了 `internal`/`egress` 两张网络与五个容器，但**自带侧车 `agentexam-t05-topology-harbor-docker-egress-control-sidecar-1` 在 `up --wait` 时退出（码 127）**，因此**七组 Trial 命令一条也未执行**，运行期 inspect 也未取得。负责人按停止条件停手，未调整侧车、未重试。拆除前后镜像 90/卷 16 无增删，按项目名与标签复核残留为 0；首次预检因 Alipine 摘要抄错而提前失败（已修正后重跑一次）。
- **分类（重要，避免误记）**：这是**工具链失败**，不是"拓扑无法落实"。与 T1 首次失败同一形状（当时监听端容器启动即退出 127）。**七条断言尚未在 Harbor 上被测量**，因此第 2 项验收既不能记为通过、也不能记为"拓扑不成立"；任务**停在 T2**，不得据此进入 06/07。
- **仓库内已有的强线索（供诊断，非结论）**：本仓库早就知道**固定 Harbor 自带侧车在这台机器上需要 DNS 适配**——M0 已查明上游 `bin/network-policy` 不放行 Docker Desktop 的转发解析器 `192.168.65.7:53`，导致两个批准域名解析失败；`adapters/execution/network.py` 因此有 `export_sidecar()`（加 DNS 守卫 + 一条 `192.168.65.7 udp dport 53 accept`），并**只通过 `adapters/execution/harbor_entry.py` 的 `_EGRESS_CONTROL_SIDECAR_CONTEXT_PATH` 生效**。负责人这次用的是**自写的最小探针**（`.tmp/t05-harbor-minimal/.../probe.py`），**可能没有走这条链**，于是 Harbor 用的是未适配的侧车上下文。退出码 127 通常表示**容器内命令找不到**（如入口脚本 exec 失败），而我们的 DNS 守卫失败会给退出码 1 并打印 `HARBOR_DOCKER_DNS_CONFIG_UNSUPPORTED`，与 127 不符——**具体原因仍未证实，需取侧车日志**。
- 另注：即使 `main` 用显式 `networks` 绕开侧车覆盖（源码结论），Harbor 的 compose 里**仍然含侧车服务**且 `up --wait` 会等它——所以侧车至少要能起来，这是 T2 的前置。
- **待办**：① 负责人侧加取侧车日志与镜像/入口信息（诊断，不新增资源）；② 负责人的行动文档目前只在其 worktree 中（`docs/actions/2026-09-22-task05-harbor-minimal-t2.md`），**尚未提交**，需其提交后本仓库才能引用；③ T2 判定维持"未测得"，等待下一次执行结果。

2026-09-22 回复 B 的三问（落地时间、超集合记录的 HTTP 表现、夹具控制端点）

1. **落地时间：由 T2 的结论触发，不是日期；本轮 T2 尚未测得。** 已核实：链路零件（S1–S8、S6a–S6e）已实现并在 `main`，但**未接运行主链路**——`provider_access` 包外只有一个导入方（`codex/provider_config.py:28` 引 `REGISTERED_UPSTREAMS`），`render_provider_config` **零调用方**；`delivery/worker/runtime.py:66` 仍无条件 `validate_auth_file`，`:26` 的 `MODEL_HOSTS` 仍写死 ChatGPT 两个域名并只构造一个 adapter。因此**今天没有任何真实 provider 失败能写到 Run 的 `failure_code`/`failure_summary`**。
   - 触发链（顺序固定）：① T2 侧车退出码 127 的诊断 → 七条断言在固定 Harbor 上被测到；② S9/S10/S11；③ 链路接入。另有一项会先做、与本问题无关：把 `origin/main` 的加固改造合入本分支并让 `server/` 适配新接缝（合并后全套实测数字须重测）。
   - E 的承诺：链路接入后**同一工作窗口内通知 B**（附提交哈希与"如何复现一条真实受控失败"）；若结论是"固定 Harbor 不允许替换侧车"或诊断表明不可行，**立即告知 B**，不让其空等。
   - **两项呈现验证不必等这条链**：它们验的是 Web 层对"给定码/给定文案"的行为，不是链路可用性。夹具造一条带受控 `failure_summary` 的 Run、再造一条未知码的 Run 即可；`tests/identity/browser_server.py:194` 已有 `POST /__test__/jobs/interrupt-next` 这类控制端点先例。真实链路 → 真实 DB 行 → 页面的端到端证据建议排在任务 08 的矩阵里。
2. **"超受控集合记录的 HTTP 表现"：已定并已实现，不再是待定项。** 提交 `3a5a9b8`：选 **503 `DEPENDENCY_UNAVAILABLE`**（`HTTP_API.md` §5 已把"对象缺失/损坏或依赖故障"归为 503），**零契约变更、无新错误码**；内部码 `UNCONTROLLED_*` 只留进程内。4 条新用例 + 区分力实测（退回旧实现全部失败）。
   - 留给 B 决定（可选，一句即可）：§4.2 现只把 `UNCONTROLLED_*` 记为失败关闭标记、未写状态码；是否补一句"客户端可观察为 503 `DEPENDENCY_UNAVAILABLE`"由 B 定，E 不改 B 的文档。E 建议补——B 的"未知错误码失败关闭"验证会走到这个分支。
3. **夹具"强制下一次响应出错"的控制端点不依赖 E**，B 现在即可实现。E 的唯一请求：造例覆盖两类码——链路将来会发出的（`PROVIDER_*` 五个）与永不会发出的未知码；并确认页面**不回显**原始内部码或文本（§10.2"内容安全由写入方负责、Web 层不猜测"的呈现侧对照）。
4. 顺带记一处 E 侧同类隐患（当前不在 HTTP 路径上）：`codex/provider_config.py:62-72` 也抛裸 `ValueError("PROVIDER_CONFIG_*")`，目前零调用方；S10 接线时一并收口为受控失败。

2026-09-22 T2 诊断结果：**侧车入口文件 ENOENT（工具链/环境问题，仍非拓扑结论）**

- **实测证据**（负责人只读取证，`up --detach` 返回 0 后立刻取证）：`docker logs` 原文为 `[FATAL tini (7)] exec /opt/egress-sidecar/entrypoint.sh failed: No such file or directory`；容器 `Exited (127)`；`image=harbor-prebuilt:harbor-docker-egress-control-sidecar--f57c86fb4906508e`、`entrypoint=["/opt/egress-sidecar/entrypoint.sh"]`、`error=` 空、非 OOM；该镜像 `RepoDigests=[]`（**本机构建、非拉取**）。
- **归类**：**环境/工具链失败**，不是七组断言失败。断言仍未测量，第 2 项验收既不能记通过也不能记"拓扑不成立"。
- **根因判断（强假设，且有本仓库早已记录的机制）**：`docs/dependencies/DEPENDENCIES.md:314` 明确写过——"侧车由固定提交的五个文件构建，复用 Harbor 原生内容哈希命名及构建缓存，**Windows 检出中的 CRLF 会使脚本解释器无效**"，而 `network.py` 之所以用 `git show <revision>:<path>` 取原始 blob，正是为了绕开这一点。负责人本次的 `probe.py` **没有**设置 `_EGRESS_CONTROL_SIDECAR_CONTEXT_PATH`、也未调用 `export_sidecar()`，因此 Harbor 用的是**它自己默认的侧车上下文**（即固定 Harbor 的 Windows 工作树检出），若该检出为 CRLF，`entrypoint.sh` 的 shebang 变成 `#!/bin/sh`，内核找不到解释器 → 正是 `No such file or directory` → tini 报错 → 退出 127。**该假设仍需一次只读确认**（见下），未确认前不写成已定位。
- **重要澄清（对产品路径有利）**：产品路径 **Worker → `HarborExecutionAdapter` → `harbor_command()` → `harbor_entry.py`** 一定会先 `export_sidecar()` 并把导出上下文交给 Harbor（`harbor_entry.py:177`、`:186`），因此**这个 CRLF 陷阱不影响产品路径**，只影响绕过该入口的手写探针。同一导出还携带**已在 M0 授权的 DNS 适配**（放行 Docker Desktop 转发解析器 `192.168.65.7:53`），没有它即使侧车起来，域名解析也会失败。
- **对下一轮 T2 的更正**：本仓库此前的"最小 T2 形态"建议（由 E 写）是**手写 probe**，实测证明这条建议会绕过仓库必需的侧车适配。下一轮应改为**经产品入口跑最小 job config**（同 `harbor_entry.py`），或至少在独立探针里显式设置 `_EGRESS_CONTROL_SIDECAR_CONTEXT_PATH` 指向 `export_sidecar()` 导出的上下文。已同步修正[组长机器预案附三](../../../docs/actions/2026-09-21-task05-owner-machine-runbook.md)。
- **待办**：① 负责人侧一次只读确认（工作树与镜像内 `entrypoint.sh` 的实际行尾）；② 负责人的两份行动文档（`2026-09-22-task05-harbor-minimal-t2.md`、`2026-09-22-task05-sidecar-127-diagnosis.md`）目前只在其 worktree 中、**尚未提交**，需其提交后本仓库才能引用；③ T2 维持"未测得"。
