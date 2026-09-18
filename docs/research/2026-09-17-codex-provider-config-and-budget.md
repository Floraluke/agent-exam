# 固定 Codex 的第三方 API 配置与首轮预算核对

核对日期：2026-09-17。范围：用户已选 DeepSeek-V4.1-Flash 与 Kimi K3 开放平台按量 API，以及已批准的凭据隔离 B 方案；不是 Kimi Code 订阅。执行记录与授权以[规划行动](../actions/2026-09-17-ui-catalog-provider-planning.md)为准，秘密边界以[认证约定](../interfaces/CODEX_AUTHENTICATION.md#41-codex-第三方-api-扩展规划2026-09-17)为准。

本轮查询官方公开资料、计算预算，并以固定 CLI 执行禁外网、假令牌配置探针。没有读取 Key、登录账户、充值、调用真实 API 或执行官方安装脚本。以下官方事实与第 6 节配置探针均不等于固定 Codex CLI 0.153.0 与两家真实服务已通过集成。

## 1. Codex 能接 API，配置文件是接入方式

OpenAI 官方提供自定义 `model_providers`：`model_provider` 选择供应商，`base_url` 指定请求根地址，`env_key` 指定认证值的环境变量名，`wire_api = "responses"` 指定协议。因此“修改容器内配置文件”与“Codex 接 API”不是互斥的两种方式。配置不是新执行链，仍由现有 Codex 发起请求。[OpenAI 配置参考](https://developers.openai.com/codex/config-reference)、[自定义供应商配置](https://developers.openai.com/codex/config-advanced#custom-model-providers)

官方配置还提供 `request_max_retries`、`stream_max_retries`，默认值并非零；验收计划需显式关闭它们并由代理验证没有重发。当前公开文档随版本更新，不能据此断言所有字段在固定 0.153.0 均有效。[OpenAI 配置参考](https://developers.openai.com/codex/config-reference)

计划中容器只接私有代理：配置中的 `base_url` 指向本次隔离入口，`env_key` 指向本次临时令牌，不是供应商真 Key。固定供应商 HTTPS 地址仅在可信代理一侧绑定。容器里的用户级配置不等于题目仓库里的项目配置；后者可不受信任、受覆盖优先级影响，不能承载此安全边界。是否能被运行时覆盖必须由固定 CLI 探针与网络拒绝对照验证。

## 2. 型号、协议、端点

| 项目 | DeepSeek | Kimi |
| --- | --- | --- |
| 用户选择 | DeepSeek-V4.1-Flash | Kimi K3，开放平台按量 API |
| 官方 API 模型 ID | `deepseek-flash` | `kimi-k3` |
| 可信代理上游基址 | `https://api.deepseek.com` | 中国区 `https://api.moonshot.cn/v1` |
| 模型请求 | `POST /responses` | `POST /v1/responses`（相对基址为 `/responses`） |
| 协议 | 原生 Responses | 原生 Responses |
| 本轮默认区域 | 按中文人民币计费资料规划；实际账户币种待绑定核对 | 中国开放平台；实际 Key 必须属于该平台 |

DeepSeek 官方价格表将 `deepseek-flash` 映射到 V4.1-Flash；官方 Codex 教程包含 `config.toml` 与独立模型目录。模型元数据、工具定义与指令也可能影响实际行为，不能只冻结一个别名；集成时需记录配置/目录哈希和运行返回的模型身份，不保证该别名未来仍指向同一模型。教程里直接写 bearer token 的示例不适用于本项目 B 方案。[DeepSeek 模型表](https://api-docs.deepseek.com/zh-cn/quick_start/pricing/)、[DeepSeek Codex 教程](https://api-docs.deepseek.com/quick_start/agent_integrations/codex/)

Kimi 官方 Codex 教程明确支持 `kimi-k3`、`env_key` 和原生 Responses；中国平台创建的 Key 必须匹配 `api.moonshot.cn`，不能拿国际端点试错。无需为这两个已选模型增加 Chat/Responses 转换。凭据代理仍保留，它的目的为秘密隔离和限额，不是修补协议。[Kimi 中国区 Codex 教程](https://platform.kimi.com/docs/guide/codex-kimi)

两家 Responses 文档均提供 `max_output_tokens` 与 `usage`。DeepSeek 说明输出上限含推理 Token，流以完成/截断/失败事件结束；Kimi K3 默认为较大的输出上限，代理必须显式限制而不能依赖默认。兼容验证至少覆盖文本流、工具调用、工具结果回传、补丁和 usage，不以一次问候成功替代。[DeepSeek Responses](https://api-docs.deepseek.com/api/create-response/)、[Kimi Responses](https://platform.kimi.com/docs/api/responses)

## 3. 人民币价格和账户控制

单位均为人民币／百万 Token（MTok），不使用缓存优惠来压低预算：

| 模型 | 未缓存输入 | 输出 | 缓存命中输入 | 上下文价格阶梯 |
| --- | ---: | ---: | ---: | --- |
| DeepSeek-V4.1-Flash | 峰时 ¥2；闲时 ¥1 | 峰时 ¥8；闲时 ¥4 | 峰时 ¥0.04；闲时 ¥0.02 | 当前中文表列统一单价，预算采用峰时价 |
| Kimi K3 | ¥20 | ¥100 | ¥2 | 官方明确不按上下文长度分段 |

DeepSeek 峰时为北京时间工作日 09:00–12:00、14:00–18:00，其他时间按闲时价；其公开模型表支持 1M 上下文。以上价格是今日资料快照，执行前需复核。[DeepSeek 价格](https://api-docs.deepseek.com/zh-cn/quick_start/pricing/)

Kimi 中国平台首页列上述人民币价格，K3 文档明确 1M 上下文不实行长度阶梯计价。新用户认证赠送的 ¥15 券不能用于 K3，需充值解锁；不能把赠送额度当成本轮可用资金。直接定价页本轮多次抓取超时，价格采用已打开的官方首页并以 K3 FAQ 交叉核验，不用旧 K2 定价替代。[Kimi 官方首页](https://platform.kimi.com/)、[K3 FAQ 与定价说明](https://platform.kimi.com/docs/guide/kimi-k3-quickstart)

DeepSeek 并发是账户级而非 Key 级，公开 Flash 上限为 2500；这不是本项目应该使用的并发量，也不是花费上限。已查页面没有证明存在可用于本计划的即时日支出硬上限，不能承诺在后台填一个金额就绝不超支。[DeepSeek 限速与隔离](https://api-docs.deepseek.com/zh-cn/quick_start/rate_limit/)

Kimi 支持项目日/月消费预算，达到后拒绝后续请求，但官方说明计费限制约有 10 分钟延迟；项目仍共享组织余额与限速，所以不能把项目预算当作即时硬断路器。公开限速页按充值等级分配 RPM/TPM/TPD；本轮打开的当前页面没有返回完整等级表，不将搜索摘要中的旧表写成当前账号配额。[Kimi 项目消费管理](https://platform.kimi.com/docs/guide/org-best-practice)、[Kimi 充值与限速](https://platform.kimi.com/docs/pricing/limits)

## 4. 委托设定的首轮验收预算建议

本节是工程初值与估算，不是供应商承诺，也不是已执行的账户配置。以 2 次冒烟（每家 1 次）通过后再做 6 道已合格题 × 2 配置为目标，共 14 个 API Run，每家 7 个；旧 ChatGPT 配置不计入本次 API 费用估算，也不因此自动重跑。

| 约束 | 建议初值 | 语义 |
| --- | --- | --- |
| 实际并发 | 全部验收同时仅 1 个 Run、1 个上游请求 | 工具调用可以多次，但模型请求不并发 |
| 每 Run 输入 | 累计 300,000 Token | 多轮历史、工具输出反复发送均计入，不是单次上下文大小 |
| 每 Run 输出 | 累计 32,000 Token | 包含供应商计入输出的推理 Token，不仅最终回答 |
| 每 Run 模型期限 | 900 秒 | 与环境构建/独立判卷耗时区分；超时不可自动续跑 |
| 自动重试 | 0 | CLI 请求、流式重连、代理、Worker 均不可偷偷追加；失败保留证据 |
| 请求频率 | 起始最多 3 次/分钟，并服从更低实际账户限额 | 保守初值；若账号不支持完整矩阵，停止并记录，不自动充值或放大配额 |
| 首轮支出目标 | 合计不超过 ¥100 | 代理保守记账与预留控制；不是已验证的精确硬上限 |

按未缓存、DeepSeek 全峰时计算，且每个 Run 都用满累计额度：

```text
DeepSeek 每 Run = 0.300 × 2  + 0.032 × 8   = ¥0.856
Kimi 每 Run     = 0.300 × 20 + 0.032 × 100 = ¥9.200
14 Run 合计     = 7 × (0.856 + 9.200)     = ¥70.392
¥100 目标余量   = 100 - 70.392            = ¥29.608
```

这是“限额均准确执行时”的计算，不是预测一定花 ¥70，也不能保证该限额足够完成每道题。缓存与提前完成可能减少费用；反复工具交互、计数偏差、中断后的未知 usage 则影响精确控制。预算不足、额度耗尽或超时要按事实记录，不能为凑验收通过静默扩额。参考补丁/空补丁的独立判卷无需调用模型，不计 API Run。

建议在后续实际账户准备时，将专属 Kimi 项目日/月预算均设置为 ¥80（作为延迟生效的第二层保护），本地整批目标仍为 ¥100。DeepSeek 不假定有同等项目预算能力。账户余额、最低充值额、已有用量和其他程序使用情况本轮均未知；不自动充值，不修改组织全局规则，不承诺账户总消费只来自 AgentExam。

## 5. 要让预算具有约束力，尚需实现和验证

以下是依据 B 方案提出的实现约束，不是外部产品事实：

1. 代理接收请求前检查 Run 身份、指定模型、截止时间、剩余额度，按非缓存价保守预留输入与本次最大输出；客户端不能修改价格表、模型或扩大限制。必须定义并验证供应商相符的输入计数/保守上界；普通字符串长度不是准确 Token 数。
2. `max_output_tokens` 不超过该 Run 剩余输出额度。完整 usage 到达后结算；usage 缺失、流断开或异常时，不退回未知部分，不以“客户端没收到”推断没计费，停止该 Run 的后续请求。
3. 每 Run 累计用量与整批金额需要共同约束；某个 Run 的剩余额度不能因代理重启被重置。记录不得含 Key 或临时令牌。失去已花费证据时失败关闭，不能重新发放全部预算。
4. 禁用模型内置付费联网搜索、文件上传和其他额外计费能力；只有做题所需受控工具留在协议中。所有请求必须经过凭据代理，不允许直连、其他端点、额外认证头或任意跳转。
5. 合成验收覆盖临界剩余额度、用量缺失、异常重启、低配额 429、超时、重复请求、撤销、模型覆盖与越权；真实冒烟再核对供应商 usage 与账单差异。HTTP 错误不自动重试。
6. 供应商账户硬控制与本地估算不是同一层。未验证 tokenizer、输出上限和预留机制前，¥100 只能称计划目标；要承诺精确硬上限，必须证明每个已放行请求的最大收费及中断结算边界，否则停在冒烟门禁。

## 6. 本轮验证与未完成项

- 已完成：打开官方 Codex、DeepSeek、Kimi 页面，核对原生协议、端点、型号映射、人民币价格、K3 无上下文阶梯、项目预算延迟和预算公式。未引用第三方测评作为接口依据。
- 抓取限制：Kimi 独立定价页与部分 DeepSeek Responses 页面直接打开曾超时；已用官方其他已打开页面及官方检索文本交叉核对，并明确来源与局限。检索未找到 DeepSeek 支出硬上限，不能将“未找到”写成“产品绝对不支持”。
- 本地固定 0.153.0 无秘密配置探针：主代理实际执行，5/5 检查通过；范围和失败演进见下表。研究代理没有运行容器或服务。
- 未执行：真实 API、账号区域/配额/余额检查、充值、密钥读取、代理实现、安全验收、新题模型矩阵和产品回归。本文件不是这些项的通过证据。

### 6.1 固定 CLI 配置探针

运行日为 2026-09-17，作用域 `provider-config-20260917-01`。复用本地固定 Linux CLI 0.153.0，二进制 SHA-256 为 `fce635028842bfe9257140e8b7d53162732945e2f356fc35225be0702b4974be`；不是升级到最新 CLI 后得出的结论。Git 忽略的[探针](../../runtime/prototype/codex-provider-config-20260917-01/probe.py)、[无秘密配置](../../runtime/prototype/codex-provider-config-20260917-01/config.toml)和[实际输出摘要](../../runtime/prototype/codex-provider-config-20260917-01/summary.json)保留供本机复核；摘要由工具实际输出整理，换机器不能假定这些文件随 Git 存在。

| 检查 | 实际结果 | 可得结论 |
| --- | --- | --- |
| TOML 指定 `deepseek-flash` | 本地假服务收到 1 次 `POST /v1/responses`，模型名/假 Bearer 匹配，`stream=true` | 固定 CLI 支持文件方式的自定义 Responses 入口 |
| TOML 指定 `kimi-k3` | 同上，模型为 `kimi-k3` | 配置模型名实际进入请求，不是只解析配置无网络请求 |
| TOML 为 DeepSeek，`-c model="kimi-k3"` | 收到 Kimi 模型名的 1 次请求 | CLI 也支持命令行覆盖；产品入口仍须拒绝未经批准的覆盖 |
| `wire_api="chat"` | 非零退出，未请求假服务，错误指向 `chat` | 该固定版本不接受此协议值 |
| 缺配置指定的令牌环境变量 | 非零退出，未请求假服务，错误包含变量名 | 缺令牌在模型请求前拒绝 |

前三项服务器故意返回带合成标记的 HTTP 401；CLI 各自退出 1 为预期拒绝，探针总体退出 0。这里的通过只表示请求路由/配置正确，不能说模型回答成功、真实账号可用、全部重连/重试已关闭或 B 方案安全已验收。

实际运行命令（PowerShell，专属容器；再次执行仍须符合当轮授权）：

```powershell
docker run --rm --pull never --name agentexam-provider-config-20260917-01 `
  --label agentexam.scope=provider-config-20260917-01 --network none `
  --read-only --cap-drop ALL --security-opt no-new-privileges --user 65534:65534 `
  --pids-limit 64 --memory 1g --cpus 1 --tmpfs '/tmp:rw,exec,nosuid,size=128m,mode=1777' `
  --mount 'type=bind,source=E:/9.1agent_exam/runtime/prototype/m0-codex-install-harbor-repro-20260907-03/input/package/vendor/x86_64-unknown-linux-musl,target=/codex-bundle,readonly' `
  --mount 'type=bind,source=E:/9.1agent_exam/runtime/prototype/codex-provider-config-20260917-01,target=/probe,readonly' `
  sha256:64d91f7b885eed272bba87909446b12ff408d4aaa5f1a0e9ca787bbea1a020b9 python -u /probe/probe.py
```

仅两个只读挂载：固定无秘密安装包和本次假值输入；新临时 HOME/CODEX_HOME 位于容器 tmpfs，模型子进程使用最小显式环境。无认证目录、宿主端口、Docker socket、共享数据库或外部网络。服务器只监听该禁网容器内 loopback。命令完成后专属标签的容器、网络、卷三项查询均为空；保留共享镜像和 runtime 证据，没有执行全局清理。Docker Desktop 保持启动，未为还原状态停止其他用户容器。

失败演进保留：普通权限的 Docker 检查曾被访问控制拒绝；修正工具权限后可读引擎。初次二进制路径猜测错误，随后查明实际 `bin/codex` 并核对哈希。用户报告客户端白屏暂停后，首次探针启动因 Docker 引擎 named pipe 不存在而失败，未创建容器；自动启动 Desktop 曾被安全审查拒绝，没有绕过。用户随后明确授权本次启动，执行官方已安装程序后 Engine 27.5.1 就绪，上述探针才实际完成。这些是环境/调用准备失败，不是供应商或题目失败。
