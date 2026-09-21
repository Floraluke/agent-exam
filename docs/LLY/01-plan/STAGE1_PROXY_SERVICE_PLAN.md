# 阶段 1（05）`service.py` 与接线：实施计划

> **状态：准备件，未开工。** 用途：让一个新会话据此直接实施。本文不构成任何授权——真实模型调用、T2 在负责人机器的操作仍各自需要单独授权。
>
> 权威边界：机制见[设计冻结](STAGE1_PROXY_DESIGN_FREEZE.md)，步骤与验收以[执行计划第 7 节](../../../.scratch/ui-catalog-providers/plan.md)为准，秘密边界见[认证接口第 4.1、5 节](../../interfaces/CODEX_AUTHENTICATION.md)。本文不复制其正文。
>
> 维护人：LLY（成员 E）　日期：2026-09-21

## 1. 这一片要做什么

让"**做题侧 → 代理 → 假上游**"第一次端到端跑通，并让每条失败路径都收束到可证的结果。它是任务 05 验收第 3–7 项的载体：受控 API 配置走全链、出站前拒绝逐条可证、假服务工具循环、故障不扩大授权、生命周期接入既有终态。

**不做**：网络拓扑形态（等 T2 结论）、真实 Key 与真实供应商、worker 的 Run 绑定选择（S9，同样依赖 T2）、S8（已完成）。

## 2. 开工前必读（新会话从这里开始）

| 文件 | 为什么读 |
|---|---|
| `docs/LLY/01-plan/STAGE1_PROXY_DESIGN_FREEZE.md` | 机制候选、令牌与账本的边界、§3.7 受控文案、§3.8 受控身份 |
| `docs/actions/2026-09-21-task05-local-implementation.md` | 已完成分片的**实测数字、踩过的坑与如实记录的缺口**；本文的每处约束都来自它的验证结果 |
| `apps/backend/tests/providers/runtime/README.md` | 探针怎么跑、MSYS 假阴性陷阱、监听端为何必须非 root |
| `apps/backend/tests/providers/contract/support/fake_responses.py` | 假上游的能力与记录格式（"出站计数为 0"的取证来源） |
| `docs/interfaces/HTTP_API.md` 第 10.2 节 | 受控文案的权威约束（B 维护，不复制） |

**当前基线（2026-09-21，用于对比）**：`pytest tests/providers` = **109 passed / 1 skipped**；默认回归 **531 passed / 105 skipped / 2 failed**（2 项固定为缺 `framework/harbor` 的 ISSUE-04）；`ruff format --check` 326 文件；`mypy` 176 源文件。开工前先复跑一次确认没有漂移。

```bash
cd apps/backend
.venv/Scripts/python.exe -m pytest tests/providers -q
.venv/Scripts/python.exe -m pytest -q                      # 默认回归
AGENTEXAM_RUN_IDENTITY_POSTGRES=1 AGENTEXAM_TEST_DATABASE_URL="postgresql://agentexam_identity_test@127.0.0.1:55432/agentexam_identity_test" .venv/Scripts/python.exe -m pytest -q
```

## 3. 目标形状：一次请求的失败关闭顺序

顺序本身就是安全属性，**不得重排**。每一步失败都给固定错误码，**都不出站**。

```text
做题侧 Codex CLI ──POST /responses（Bearer＝本 Run 令牌）──▶ 代理入口
   1 形状：只接受 POST /responses，正文有大小上限
   2 鉴权：binding.resolve(令牌) → run 身份；未知/过期/跨 Run/已撤销 → 拒（PROVIDER_TOKEN_*）
   3 策略：check_request(模型＝绑定值, 工具白名单, 上限＝本 Run 剩余输出额度) → 拒（REQUEST_*）
   4 剥离客户端认证头（strip_client_auth），凭据只在可信侧加入
   5 预留：budget.reserve(输入保守上界, 本次最大输出) 原子完成 → 拒（BUDGET_*）
   6 出站：transport 构造（max_attempts=1、不跟随重定向、https 上游）→ 由**注入的发送器**发出
   7 流：把上游 SSE 原样透传给客户端；只解析终止事件取 usage
   8 收束：结算 → 撤销令牌 → 释放本 Run 资源 → 把结构化结果交回调用方（不在本片写库）
```

四条不可让步的语义：**不重试、不切换模型、不追加授权**；**未知 usage 按整笔预留全额计费**（不退款为零）并关闭该 Run；**客户端没收到不等于没计费**（断开也结算）；**内部码一律映射为受控文案**，不回显。

## 4. 文件树与指标

`provider_access/` 现 **7 个源文件**（上限 8），`tests/providers/policy/` 也已 **8 个**。因此本片**必须建子目录**（这是指标要求的解法，不是新架构）：

```text
src/eval_platform/adapters/execution/provider_access/
└─ server/                       # 新增子目录：代理进程侧；顶层保持 7 文件
   ├─ __init__.py                # 内部导出
   ├─ service.py                 # 入口与流水线编排：按第 3 节顺序串 policy/budget/binding/transport
   ├─ http.py                    # stdlib HTTP 表面：解析请求、调用 service、把流写回客户端
   └─ stream.py                  # SSE 分帧与透传、终止事件 usage 提取（有界缓冲）
   （T2 后再加 net/ 子目录容纳原计划的 network.py）
apps/backend/tests/providers/lifecycle/     # 新增：替身与假上游驱动的流水线与生命周期
   ├─ __init__.py
   ├─ test_request_pipeline.py   # 顺序、拒绝时出站计数为 0、并发预留
   ├─ test_stream_lifecycle.py   # 终止/未知/断流/超时/客户端断开 → 结算与关闭
   ├─ test_run_closure.py        # 令牌撤销、崩溃恢复不续跑、不重置额度
   └─ test_secret_surface.py     # 秘密外表面与受控文案的端到端扫描
apps/backend/tests/providers/runtime/
   ├─ Dockerfile.proxy           # 新增：代理容器镜像（沿用 catalog/jobs 的固定 digest 与锁文件约定）
   └─ verify.ps1                 # 新增（S11）：集成层入口，仅负责人机器
```

**依赖方向**：`server/` 只向下依赖同包内的 policy/budget/binding/secrets/transport/failures，以及 `domain/agent.py` 的受控身份；**不反向被 domain 依赖**，也不新增应用可见端口、不读写数据库。（第 4 节若有别的做法需要新增顶层模块或表，必须先获用户确认。）

## 5. 需要开工时拍板的决策（我给的推荐与备选）

1. **HTTP 服务器**：推荐 **stdlib `http.server`**（线程化）。理由：这是安全边界上的组件，层数越少越可审；流式写出显式可控；不引入 ASGI 版本差异，负责人的机器上无需额外服务依赖。备选 FastAPI/uvicorn（已是项目依赖，但在本片只带来便利、不带来能力）。
2. **出站做成注入的可调用对象**：推荐。`service` 接受 `send(request) -> stream`，本机测试注入假上游客户端；T2 之后换成真实 `transport` 发送器。这让 90% 的逻辑与拓扑解耦（也让本片在 T2 判"不允许"时仍不白做，见第 9 节）。
3. **结算时机**：只在终止事件结算；无终止事件（断流/超时/客户端断开）按未知处理 → 全额计费 + 关闭 Run。**不要**在流中逐段结算。
4. **流透传策略**：字节原样透传（不改写事件、不注入事件），只旁路解析终止事件；缓冲有上限，超限按协议错误拒绝而不是无限增长；**不记录正文**。
5. **代理进程入口**：产品内 `python -m eval_platform.adapters.execution.provider_access.server.service`（`__main__` 守卫），容器镜像直接用它；测试侧不再另写启动脚本。

## 6. 分片（每片：失败用例优先 → 最小实现 → 通过 → 回归）

| 片 | 内容 | 失败用例优先 | 成功标准 |
|---|---|---|---|
| **S6a** | 入口、鉴权、策略接线（**无出站**） | 无令牌/错令牌/过期/跨 Run → 拒，且**假上游请求计数为 0** | 每条拒绝给固定码，出站计数 0；`POST /responses` 之外一律拒 |
| **S6b** | 额度预留与结算接线 | 预留不足 → 拒且出站 0；usage 缺失/断流/超时/客户端断开 → **全额计费 + Run 关闭**；重复结算报错 | 账本余量单调、并发下恰好放行到上限（沿用 S5 的 8 线程用例形态） |
| **S6c** | 出站与流透传 | 上游 401/429/5xx、连接重置、流干净提前收尾、按住不答 → 全部**不重试**、不改模型、按未知结算 | **正对照**：假上游记到 1 次请求、模型名与令牌来自绑定；客户端收到的字节与上游一致 |
| **S6d** | 收束与既有终态接缝 | 完成后令牌立即失效；进程崩溃后**不自动续跑**、恢复时不重置额度 | 令牌撤销有断言；崩溃用"重新起一个 service 实例 + 同一账本"模拟 |
| **S6e** | 秘密外表面与受控文案接线 | 每个失败路径的对外文案都被断言**不含哨兵**（主机名/URL/路径/profile 名/令牌片段/拓扑词） | 端到端扫描 argv/环境变量/inspect 可见配置/日志/DB/制品/UI 零命中 |
| **S10** | `net/`（原 `network.py`）与网络接线 | — **等 T2** | T2 结论落地后按双网络组合并跑 T1 探针 |
| **S11** | 集成层（负责人机器） | — **等 T2** | `Dockerfile.proxy` + `verify.ps1` 五组对照与精确清理 |

每片结束都要跑：`pytest tests/providers -q`、默认回归、`ruff check .`、`ruff format --check .`、`mypy src`，并把**实际数字**写进行动文档（与第 2 节基线对比，失败项必须仍是那 2 项）。

## 7. 取证方式（不得用日志文本推断）

- **"出站计数为 0"**：以假上游自己的请求记录为证（`FakeUpstream.request_count`），不是扫日志。
- **"经代理发出"**：假上游记录到 1 次请求，且模型名与令牌来自该 Run 的绑定。
- **受控文案**：断言对外文案不命中哨兵集合（沿用 `tests/providers/policy/test_controlled_failures.py` 的哨兵表）。
- **秘密不外泄**：只用假值哨兵，扫描 argv、环境变量、`docker inspect` 可见配置、日志、数据库、制品与 UI。
- **每片区分力**：新用例必须先制造真实失败（改实现让它失败、还原后通过），把这一步写进行动文档——这条在 S8、受控文案两片都做过。

## 8. 阻塞与授权

- **T2（负责人机器）**：决定 `net/` 与容器网络形态，也决定 S9 的绑定接法。窗口已可用，探针命令见[组长机器预案附二](../../actions/2026-09-21-task05-owner-machine-runbook.md)。
- **固定 CLI 复核**：S2 渲染的字段名与契约层事件词表靠它在负责人机器对账（`tests/providers/contract/serve_fake_upstream.py` 就是给这一步用的）。
- **真实模型调用**：06/07 各自单独授权；本片全程只用假值与假上游。
- **需要确认才会做**：新增顶层模块、公共接口或数据库表；放宽 `--cap-drop ALL`；把假上游接到真实上游地址。

## 9. 风险与已知未知

| 风险 | 影响 | 处置 |
|---|---|---|
| T2 判"固定 Harbor 不允许替换侧车附加" | 按计划第 7 节停在本任务，本片部分代码可能不再被使用 | 出站注入让逻辑与网络解耦；policy/budget/lifecycle 在任何 provider 路径下都成立，不会白做 |
| 事件词表是候选（无"成功流"的既有依据） | 与固定 CLI 不一致时流透传可能不被接受 | 词表集中在 `responses_events.py` 一处；契约层对账即改 |
| 假上游是明文 HTTP | 代理→上游那段必须是 HTTPS，真接代理需要 TLS 包装 | 归集成层；本片用注入的发送器绕开，不假装已解决 |
| SSE 边界：跨包事件、超大 usage、注释行与心跳 | 解析错位会误判终止事件（可能漏结算） | 有界缓冲 + 只认终止事件 + 未知一律按全额计费关闭（宁可高估） |
| 客户端在流中途断开 | stdlib 写出会抛异常，若被当成"未计费"就是漏洞 | 断开路径也必须结算并关闭 Run；用例显式覆盖 |
| 代理进程在容器内的生命周期与 Harbor 试验生命周期对齐 | 泄漏进程或残留容器 | 归 S10/S11，随 T2 的拓扑一起定 |

## 10. 权威来源

| 内容 | 位置 |
|---|---|
| 机制候选与已确认数值 | `docs/LLY/01-plan/STAGE1_PROXY_DESIGN_FREEZE.md` |
| 负例矩阵与验收要求 | `.scratch/ui-catalog-providers/verification.md` 第 4 节 |
| 步骤、验收与停止条件 | `.scratch/ui-catalog-providers/plan.md` 第 7 节 |
| 受控文案 | `docs/interfaces/HTTP_API.md` 第 10.2 节 |
| 秘密边界与强制约束 | `docs/interfaces/CODEX_AUTHENTICATION.md` 第 4.1、5 节 |
| 已完成分片的实测与缺口 | `docs/actions/2026-09-21-task05-local-implementation.md` |

本文只把权威要求编排成可执行顺序，不替代上述文件，也不构成开工或执行授权。
