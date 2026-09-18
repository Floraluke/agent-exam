# 项目依赖唯一事实源

> 文档状态：持续维护；固定依赖已支持第四场真实 Codex 单题与独立 Fork 判卷通过；完整 M0 安全/生命周期验收引用执行与认证接口
>
> 最后更新：2026-09-17（扩展规划与假配置探针）；网络镜像核验：2026-09-07；固定CLI配置探针：2026-09-17
> 权威范围：依赖身份、来源、固定版本、是否进入主仓库、获取/恢复方式和验证状态

## 1. 文档边界

“固定版本”是指团队明确使用一个不可变的版本标识，例如完整 Git 提交哈希（commit SHA）或容器镜像摘要（digest），从而避免上游更新后结果悄悄变化。

本文件是以下事实的唯一维护位置：

- 项目直接依赖什么；
- 依赖来自哪里、固定到哪个版本；
- 依赖是否进入 AgentExam 主仓库；
- 新成员如何恢复相同依赖并核验；
- 哪些依赖已经验证，哪些仍待确认。

字段、命令行参数、输入输出结构和 Adapter（把不同外部工具转换成项目统一接口的适配层）映射由 [`FRAMEWORK_INTERFACES.md`](../interfaces/FRAMEWORK_INTERFACES.md) 维护。本文件不重复维护接口细节。

## 2. 当前依赖总表

| 依赖 | 项目用途 | 固定版本 | 是否进入主仓库 | 当前状态 |
|---|---|---|---:|---|
| SWE-Gym | 任务数据、模型与复现实验材料的上游来源 | `b681068ca20628c6987b7416cc4cf03f06b77ba5` | 否 | 源码身份、许可证和上游制品入口已核验；M0 固定 Lite revision/split/单题已下载并通过内容校验 |
| SWE-Bench-Fork | SWE-Gym 环境常量、Docker 环境构建和评测 Harness（自动执行测试并判定补丁是否解决任务的程序） | `242429c188fcfd06aad13fce9a54d450470bf0ac` | 否 | 已在隔离 Linux 环境运行原 CLI；项目仅适配镜像准备/容器创建，gold、空、错误、不可应用、超时五类真实判卷通过 |
| Harbor | Execution Backend（执行后端）：把一个平台 Job 展开并运行成多个 Agent Trial，管理 Agent、环境、资源/网络策略和轨迹 | `6af8d6e31eced13b93849cdf80feeadf24603d15` | 否 | 固定源码和隔离环境已恢复，CLI `0.22.0` 可用；真实 Codex Trial 与独立判卷已通过，范围见[第四场记录](../interfaces/HARBOR_EXECUTION.md#第四次授权运行真实补丁与独立判卷通过2026-09-08) |
| Python 运行时 | 后端及 SWE-Bench-Fork 运行时 | 后端 `>=3.13,<3.14`；Fork 当前 Ubuntu Python `3.12.3` | 不适用 | 后端使用 `pyproject.toml`/`uv.lock`；Fork 使用 `swebench-requirements.txt` 的 Linux Python 3.12 带哈希锁，63 项运行依赖已安装且启动时核对版本 |
| FastAPI | 后端 HTTP 交付层 | `0.141.1` | 清单与 uv.lock | 身份 HTTP 已接通；见第 2.2 节 |
| Node.js 运行时 | Web 前端构建/运行 | 正式部署版本待固定；本机测试 `20.19.0` / npm `10.8.2` | 不适用 | 未升级机器；本机测试版本不作为当前受维护的部署基线 |
| Next.js | Web 框架 | `15.5.25` | package.json 与 package-lock.json | 延续已批准 15 主版本，身份页面/构建已验证 |
| React | Web 视图框架 | `19.3.0`（react 与 react-dom） | 前端清单与锁 | 与 Next.js peer 范围核对，身份页面已验证 |
| Docker Engine / Docker Desktop / Compose | 隔离并运行评测环境 | 项目基线待确认；本机 Desktop `4.38.0.181591`、Engine `27.5.1` | 不适用 | Harbor NOP/超时与固定 Fork 五类真实补丁集成已验证；环境细节见 [`LOCAL_DOCKER_ENVIRONMENT.md`](../operations/LOCAL_DOCKER_ENVIRONMENT.md) |
| PostgreSQL | 结构化业务数据存储与 MVP 平台 Evaluation Job 队列 | 正式部署待确认；本次集成 15.18 | 测试复用既有官方摘要镜像 | 身份集成已验证，镜像见第 2.2 节；不代表队列已实现 |
| MinIO | 对象存储，即保存 patch、日志等文件制品 | 隔离测试固定源码及构建身份见第 2.3 节；正式部署未定 | 不适用 | 保留 MinIO；已完成专属合成集成，不关闭已知维护/安全风险 |
| Codex CLI | M0 本机真实原型与 M1 平台 MVP Agent | 首轮 `0.153.0`，用户于 2026-09-07 确认 | 否 | 使用 Harbor 内置 Codex Adapter，认证沿用评测机所有者的 ChatGPT Pro（见 [`CODEX_AUTHENTICATION.md`](../interfaces/CODEX_AUTHENTICATION.md)）；固定包校验、禁网容器启动和 Harbor 预装复用已通过，见第 2.1 节；第四场真实单题已通过，剩余网络/凭据生命周期验收引用执行与认证接口 |
| Aider CLI | Codex MVP 之后的已知 Agent | 待确认 | 否 | 已确认在 Codex 平台闭环后接入；尚未安装或固定版本，不阻塞 MVP |
| Claude Code CLI | Codex MVP 之后的已知 Agent | 待确认 | 否 | 已确认在 Codex 平台闭环后接入；尚未安装或固定版本，不阻塞 MVP |
| 本地自研 Agent | P2 扩展 Agent | 待实现 | 是，由提交者固定 Git commit 提交，审核后登记 | 只保留扩展接缝；P2 首版只支持 Python 和固定进程 Interface，完整 manifest、Python 版本、依赖锁格式与 Harbor 包装不阻塞 MVP |
| DeepSeek / Kimi 模型接口 | 新增Codex API规划；P2自研Agent仍另行延期 | DeepSeek-V4.1-Flash（`deepseek-flash`）与 `kimi-k3`；服务alias非不可变版本 | 否 | 官方原生Responses与固定CLI假配置探针已核对；真实工具循环、Key代理、计量和账号资格未验收，见[研究](../research/2026-09-17-codex-provider-config-and-budget.md) |

“待确认”不等于推荐使用最新版；在版本被确认并写入本文件前，不得把本机偶然安装的版本当成团队基线。

原M0/M1恢复顺序保持；用户新增的Codex多提供方规划按[扩展计划](../../.scratch/ui-catalog-providers/plan.md)分阶段推进，不受旧“DeepSeek/Kimi仅P2”排期限制。Aider/Claude Code与P2自研仍未进入本次范围，不升级固定Harbor/Fork/CLI或因此重建环境。

### 扩展依赖规划（未安装/未运行）

新增五题优先固定Lite的mypy候选，名单与替换门槛见计划04；每题镜像digest、base commit、参考/负例判卷证据在资格检查通过后才写入本表对应记录。当前只有旧题已登记，不把同项目视为同镜像或已通过。代理固定运行镜像/依赖尚待05技术核验，不凭空指定最新版；实际需要下载时先列来源、大小、权限及隔离范围。

提供方精确端点、地区、官方配置资料及价格快照唯一见[研究](../research/2026-09-17-codex-provider-config-and-budget.md)；Key管理和禁止订阅端点替代见[认证4.1](../interfaces/CODEX_AUTHENTICATION.md#41-codex-第三方-api-扩展规划2026-09-17)。长期暂停后重新核对会变化的型号alias/价格/账户资格，不把今日报价当永久承诺。5/5假配置探针不等于两家真实API验收通过。

Codex 的版本选择已完成，不再根据宿主升级或 `latest` 自动变化。[官方安装文档](https://learn.chatgpt.com/docs/cli) 提供独立安装器和 npm `@openai/codex`；本项目采用该包发布的 Linux 平台制品完成无凭据离线安装探针，身份见第 2.1 节。Harbor 复用同版本预装 CLI 的条件见 [框架接口第 7 节](../interfaces/FRAMEWORK_INTERFACES.md#7-codex-cli-adapter)。

2026-09-07 用户确认首轮模型 ID 为 `gpt-5.6-terra`，随后确认 reasoning effort（推理强度）为 `medium`；提供方仍为 OpenAI，认证仍用既定 ChatGPT 登录政策。首轮 CLI、模型与推理强度选择已完成，实际配置沿用现有 `critical_config.reasoning_effort` 显式传入。该选择不等于已经证明本账号或固定容器 CLI 能实际调用；不自动换模型或强度，不把测试占位符当真实配置，也不因本次确认打开尚未验收的真实入口。

### 2.1 Codex 无凭据安装制品

2026-09-07 已从官方 npm registry 的主包元数据核对 Linux x64 optional dependency，并下载对应平台包。仅核验 registry 公布的完整性值与实际包字节，未验证签名/来源证明链，不将校验和称为完整供应链审计。

| 输入 | 固定值或事实 |
|---|---|
| 平台包 | `@openai/codex@0.153.0-linux-x64`；目标 `x86_64-unknown-linux-musl` |
| 下载地址 | `https://registry.npmjs.org/@openai/codex/-/codex-0.153.0-linux-x64.tgz` |
| 大小 | `129210185` bytes |
| SHA-512 | `b0517e83ba75a3ab1954be8f1ddf494d8acfda3df16a8dd07aee409e072b0f96eb5ab09cfb0f627c124226e45233bdbc59f8235cc2fd3d03dd1cf69949e1c010` |
| 包布局 | 8 个普通文件；包含 Codex、code-mode host、rg、bwrap、zsh 和平台布局元数据 |
| 本机证据 | 忽略目录 `runtime/prototype/m0-codex-install-20260907-01/`；归档保留，解包逐文件 SHA-256 写入 `installation-input.json` |
| 实现 | [`codex/install.py`](../../apps/backend/src/eval_platform/adapters/execution/codex/install.py)；先核验大小/整包 hash/严格成员列表/平台身份，再创建独占解包目录；不执行 npm 脚本或下载最新版 |

使用既有固定任务摘要镜像创建临时禁网容器，离线复制已校验工具包；以非 root 用户执行版本/帮助，通过固定 Harbor 真实 `Codex.install()` 的版本检查复用已安装工具。随后正式接线把同一校验加入生产 `GuardedCodex.install()`：每次运行重新验证归档与解包文件，固定 `/opt/agentexam-codex` 和 PATH，版本不符即失败而不进入 curl/npm 在线安装；假认证、`network none` 的 Docker 契约已通过。首次真实 Trial 暴露的版本首行误判已修复，现严格要求最后一条非空行等于 `codex-cli 0.153.0`；第二次启动误传不存在的 Windows `.zip` 后，正确固定 Linux `.tgz` 的大小与 SHA-512 再次复核一致。第三次授权运行共用同一预检/启动构造，已通过生产离线安装、真实认证上传和 UID 65534 的 CLI 会话启动，但因 DNS 转发受阻而超时，无模型回复或有效补丁。未重建基础镜像、安装 Node/npm 或升级宿主；本轮无生产代码变更。上述为第三场历史结果；后续 DNS 修正已获授权并接入，第四场真实模型/工具、补丁和独立判卷已通过，剩余 Token 刷新等验收见[当前执行状态](../interfaces/HARBOR_EXECUTION.md#第四次授权运行真实补丁与独立判卷通过2026-09-08)及[M0 行动记录](../actions/2026-09-05-m0-codex-harbor-implementation.md)。

### 2.2 M1 身份切片的依赖与本机入口

2026-09-11 查询官方 [PyPI](https://pypi.org/) 与 [npm registry](https://registry.npmjs.org/next/15.5.25) 元数据并核对兼容要求；精确直接依赖由[后端清单](../../apps/backend/pyproject.toml)和[前端清单](../../apps/web/package.json)固定，传递依赖及完整性由同目录锁文件维护，不在多份文档复制全量锁内容。

| 新增直接依赖 | 固定版本 | 作用 |
|---|---|---|
| FastAPI / Uvicorn | 0.141.1 / 0.52.4 | HTTP 交付与回环 ASGI 服务 |
| psycopg[binary] | 3.3.5 | PostgreSQL 客户端，不代表已部署数据库服务 |
| argon2-cffi | 25.1.0 | Argon2id 密码哈希，time_cost=3、memory_cost=65536 KiB、parallelism=4 |
| httpx（开发依赖） | 0.28.1 | HTTP 契约测试；当前上游有弃用提示但测试可执行 |
| Next.js / React、React DOM | 15.5.25 / 19.3.0 | 已确认主版本内的最小 Web |
| TypeScript / @types/react / @types/node | 5.9.3 / 19.3.0 / 22.20.2 | 构建时类型检查；类型包版本不是 Node 运行时版本 |
| @playwright/test | 1.63.0 | 少量真实浏览器接线测试；专属浏览器缓存留在 runtime |

Next.js 官方 [2026-08 安全更新](https://nextjs.org/blog/august-2026-security-release)要求 15.5 修复线至少 15.5.24；本次采用 registry 的 backport 15.5.25，而不切换到 16。以上核对不等于完整供应链审计。正式远程部署前仍须锁定受维护的 Node/PostgreSQL 运行版本，不把本机 Node 偶然版本或只存在 SQL 的状态当作已完成平台基线。

恢复依赖（项目环境，非机器升级）：后端运行既有 `uv sync --locked --no-python-downloads`；前端运行 `npm ci --ignore-scripts`。缓存可放在项目 runtime；不要将模型登录或现有服务连接配置拷入测试。

生产后端要求私有进程配置 `AGENTEXAM_DATABASE_URL` 和 `AGENTEXAM_PUBLIC_ORIGIN`；命令不包含连接字符串或密码。以下为入口说明，不授权现在连接现有服务：

```powershell
# apps/backend；仅对明确的空白专属应用数据库执行一次，不在 HTTP 启动时迁移
.venv/Scripts/python.exe -m eval_platform.delivery.owner init-db
# 已有任务 01 身份库升级才执行，不能重复 init-db；先确认专属目标与备份
.venv/Scripts/python.exe -m eval_platform.delivery.owner upgrade-members
# 本机交互终端读取两次密码，不回显；不能通过参数或管道传密码
.venv/Scripts/python.exe -m eval_platform.delivery.owner bootstrap owner
.venv/Scripts/python.exe -m eval_platform.delivery.owner recover owner
# 不自动建表、不自动创建账号；无配置拒绝启动
.venv/Scripts/python.exe -m uvicorn eval_platform.delivery.http.app:create_runtime_app --factory --host 127.0.0.1 --port 8000 --no-access-log
# 每次只领取一次；运行成败从 Job/Run 报告读取，命令成功不等于模型解决任务
.venv/Scripts/python.exe -m eval_platform.delivery.worker.runtime local-worker-01
# apps/web；AGENTEXAM_API_ORIGIN 只允许本机回环 HTTP，默认 127.0.0.1:8000
npm run dev
```

HTTP 回环开发需要显式 `AGENTEXAM_ALLOW_INSECURE_LOOPBACK=1`，精确 Cookie/Origin 语义只在 [HTTP 契约](../interfaces/HTTP_API.md#32-任务-01-身份-http-切片)维护。未配置专属数据库时不启动正式应用；浏览器测试使用独立且显式门禁的合成后端，不是生产回退模式。

正式 Worker 另外要求 `AGENTEXAM_PROJECT_ROOT`、`AGENTEXAM_WORKER_EVIDENCE_ROOT`、`AGENTEXAM_CODEX_ARCHIVE` 和 `AGENTEXAM_CODEX_AUTH_PATH` 都是显式绝对路径；证据根必须是项目 `runtime/` 的专属子目录。任务数据继续使用下文的 `AGENTEXAM_TASK_PARQUET`，PostgreSQL/MinIO 配置与 HTTP 共用既有专属环境变量。Composition Root 只核验认证文件类型和大小，不解析或打印正文；固定 Codex 归档、Harbor/Fork revision 和任务快照错配会在领取前失败。Harbor 的绝对对象引用和 Fork 以项目根生成的相对对象引用都由 `LocalArtifactReader` 解释，但解析后的文件仍必须位于专属证据根内并通过类型、大小和哈希核对；MinIO 只接收规范化后的长期对象。首次真实 Run 曾因漏配该 source reader 在判卷前失败，`10f0c53` 与评审修复 `3d66230` 已完成无模型接线验证。真实模型网络和授权结果只在执行/认证专题与任务 13 行动维护。

任务 02 未增加第三方依赖。新空库 init-db 同事务建立账号/会话/邀请；已有身份库才使用 upgrade-members 补邀请结构，重复执行明确失败、不清表。二者是择一情境，不按上方命令顺序全部执行；本轮没有操作任何长期应用库。后端打包清单同时包含 identity.sql 与 membership.sql。原子性与字段只在[数据契约](../architecture/DATA_MODEL.md#401-邀请表invitations)维护。

浏览器安全验收改用回环 HTTPS。首次恢复或证书到期时，在仓库根目录用已有 Git OpenSSL 生成专属 2 天自签测试证书（本机核验为 3.5.4；其他机器先确认自己的可执行文件和配置路径）：

```powershell
New-Item -ItemType Directory -Force -Path 'E:/9.1agent_exam/runtime/tests' | Out-Null
& 'D:/download/git/Git/usr/bin/openssl.exe' req -x509 -newkey rsa:2048 -noenc -keyout 'E:/9.1agent_exam/runtime/tests/identity-https-key.pem' -out 'E:/9.1agent_exam/runtime/tests/identity-https-cert.pem' -days 2 -subj '/CN=127.0.0.1' -addext 'subjectAltName=IP:127.0.0.1,DNS:localhost' -config 'D:/download/git/Git/usr/ssl/openssl.cnf'
# 随后在 apps/web 执行；复用已安装的专属浏览器，不自动下载或升级
$env:PLAYWRIGHT_BROWSERS_PATH='E:/9.1agent_exam/runtime/tools/playwright'
$env:NEXT_TELEMETRY_DISABLED='1'
npm run test:e2e
```

`playwright.config.ts` 显式传入上述密钥/证书，不走 Next 的自动 mkcert 安装或系统信任流程；`ignoreHTTPSErrors` 仅限测试浏览器及就绪检查。此验证覆盖 HTTPS Cookie 行为，不验证证书受信任或生产 TLS 部署。证书/密钥和结果均在忽略的 runtime，不能用于正式服务或进入 Git。依据见 [Next CLI](https://nextjs.org/docs/app/api-reference/cli/next)，本机固定 Next 15.5.25 源码已核对显式证书分支。

测试后端仅在 `AGENTEXAM_IDENTITY_BROWSER_TEST=1` 启用，使用合成账号、内存存储和可注入时间。过期用例只写专属 `runtime/tests/identity-browser-clock.txt` 并在结束时删除，不修改系统时间或生产 API；异常强停后若该文件遗留，先核对其确为本测试文件再清理。合成外站页面由浏览器本地拦截提供，平台请求仍实际到达后端，不访问第三方。最新验证及限制见[评审修复行动](../actions/2026-09-11-m1-identity-review-fixes.md)。

真实 PostgreSQL 测试只接受显式启用及专属测试连接：回环、非默认端口、维护库名/用户均为 `agentexam_identity_test`；每个用例仅在该专属服务中新建随机数据库并精确删除。测试代码不扫描已有服务，也不自动启动 Docker。2026-09-11 复用本机已有官方 `postgres:15-alpine`，实际服务 15.18，镜像 `postgres@sha256:df7bca0066e6f60cc3dd32faa70caddec20e2c22b58932f79498e5704b23854a`，本地 image ID `sha256:5cce759a2777634ff1edd0d56b9241a2961deb7f72e125d4af6ae2928163a6b6`；没有拉取或改变原有标签。它是本次集成环境证据，不自动固定未来生产部署版本。临时容器授权、验证与清理结果见[身份行动](../actions/2026-09-11-m1-owner-identity.md)。本轮未接入 MinIO、模型或 Worker。

2026-09-12 任务 02 复用上方同一固定镜像完成新增成员事务与身份回归，临时 PG 授权已覆盖任务 02–04；准确运行结果、两次编排及精确清理只在[成员行动末节](../actions/2026-09-11-m1-collaborator-invitations.md#2026-09-12-获准的真实数据库验收)维护。未部署长期数据库。

### 2.3 任务 03 对象存储依赖复核

本节保留任务 03 的历史 CE 合成测试输入；2026-09-17 用户已确认正式持久化采用 AIStor Free 修复版方向，见第 2.4 节。下文当时的“不自动转用 AIStor”不再表示发行方向待选，但有效许可和实际部署尚未完成。

2026-09-12 只读核对 [MinIO 官方社区仓库](https://github.com/minio/minio)：仓库显示于 2026-04-25 归档，README 明确停止维护；社区版仅源码分发，历史预编译制品不再更新。停止维护不等于旧版本无法运行，但不能把它记为受维护的部署依赖。

该 README 列出 AIStor Free / Enterprise 后续入口；实际 Free 链接跳转至[官方下载页](https://www.min.io/download)，页面提供许可证申请/获取入口及试用说明。尚未确认适用的免费许可条件或部署版本，不把 README 的 Free 名称视为已获可用许可证；未注册、获取许可证、下载、构建或安装。本文不是许可证法律意见。

本次开工时本机镜像过滤 `reference=*minio*` 没有结果。用户后续决定保留 MinIO，产品与分层选择以[总架构第 3.1 节](../architecture/ARCHITECTURE.md#31-m1-交付边界2026-09-09-已确认)为准，不再等待更换产品的决定。精确发行版本、来源与部署风险仍须核对；不自动采用 AIStor、不固定 latest，也不把产品确认记为所有旧版本风险均获接受。当时任务 03 尚未安装或进行真实对象存储验证；后续已获批准并实测完成，执行状态见[任务 03 行动](../actions/2026-09-12-m1-task-agent-catalog.md)。

本次后续官方调研已形成[MinIO M1 基线调研](../research/2026-09-12-minio-m1-baseline.md)：最后正式 CE release 之后另有条件写修复，因此提出归档源码 commit `7aac2a2c5b7c882e68c1ce017d8256be2feea27f` 作为**仅限隔离合成测试的候选**，不是新的 release 或已批准固定基线。最后 release、完整提交、条件写源码和后续安全通告的原始来源由调研记录保留。候选源码仍有已知签名校验风险，正式/远程部署风险未关闭；不自动转用 AIStor。

任务 03 用户随后已批准该固定 CE 源码的隔离合成验证，Adapter 和测试镜像已构建并完成真实集成；不是批准正式部署或关闭维护/安全风险。使用 AWS 官方 Boto3 的公开 put_object 条件写和 get_object 流式读取，不手写签名或调用私有 SDK 方法；S3 客户端不代表更换 MinIO 产品。方案、实测及清理只在[同一行动](../actions/2026-09-12-m1-task-agent-catalog.md#任务-03-最小接入方案)维护，本机端口发布限制见[Docker 环境文档](../operations/LOCAL_DOCKER_ENVIRONMENT.md)。上文“尚未安装”是开工快照，以下为当前固定输入。

| 任务 03 输入 | 已核验身份 / 适用范围 |
|---|---|
| S3 客户端 | [PyPI boto3 1.43.93](https://pypi.org/project/boto3/1.43.93/)，Python >=3.10；botocore 1.43.93，完整传递依赖由 apps/backend/uv.lock 锁定，未升级既有直接依赖 |
| MinIO 源码 | 上述固定提交的官方 codeload 归档，SHA-256 `71794c2df26aad0cc99e8421c58b7aa2dd55969f979b0e7d1e931042e9fabcd6`；构建前检查通过 |
| Go 构建镜像 | 官方 golang 1.26.8-bookworm，linux/amd64 digest `sha256:bc6beb46032d45f421cf400036bf031cdc64f683ba9cdc124e31d063e71670bd` |
| Linux 测试镜像基础 | 官方 python 3.13.15-slim-bookworm，linux/amd64 digest `sha256:2f2e5a876c71a6757f55ec57f2add0225ddaf01c802a33fcc29073943f94d907`；不升级本机 Python |
| 镜像分发 | [Docker 官方镜像的 ECR 分发](https://aws.amazon.com/blogs/containers/docker-official-images-now-available-on-amazon-elastic-container-registry-public/)；通过 public.ecr.aws/docker/library 固定摘要拉取，不改机器级镜像源 |
| Linux 构建工具 | uv 0.12.10 官方 PyPI manylinux x86_64 wheel，SHA-256 `f7d6248ad9f2d282fea795f248da8fa666ab382df50d8385bd98e01049440a0c`；只在测试构建镜像安装 |
| 自建 MinIO 测试镜像 | `sha256:922042a62be66dc71bd1b23de25c7c232a6084033f3bcc2337ab49611cc3aba8`，111,899,710 bytes；标签 agentexam-minio-test:7aac2a2c-go1.26.8。版本输出 DEVELOPMENT.GOGET，不能冒称官方 release；源码/归档和最终 image ID 联合固定身份 |

本机命令：在 apps/backend 用 `.venv/Scripts/python.exe -m eval_platform.delivery.catalog init-db` 显式补三张目录表；仅对已确认目标使用，不在启动时迁移，也不自动建立 bucket 或登记任务。MinIO bucket 必须预先存在且私有；本次仅在专属测试容器建立合成 bucket，没有部署长期服务。

目录首次使用所需私有进程配置：AGENTEXAM_TASK_PARQUET（已有固定本地快照的绝对路径），AGENTEXAM_MINIO_ENDPOINT/BUCKET/ACCESS_KEY/SECRET_KEY。MinIO 仅支持 HTTPS，或同机明确 127.0.0.1 的 HTTP；凭据须显式提供，不能回退 AWS 默认账号；客户端禁用代理并使用单次有界请求、签名及校验。缺少目录配置在调用目录时安全失败，不阻断已配置的账号登录；数据集读取继续复用既有完整大小/哈希校验，不下载新题目镜像。公开 preset ID 和字段只在 HTTP 契约维护。

### 2.4 最小本地持久化的部署候选（2026-09-17）

用户已确认 PostgreSQL/MinIO 本机持久化，并明确采用 **MinIO AIStor Free 修复版**；继续复用现有 S3 Adapter。CE 仍仅作历史隔离测试输入，不用于本次正式部署。AIStor 的当前版本/许可调查由[原 MinIO 调研新增章节](../research/2026-09-12-minio-m1-baseline.md)维护；选择发行方向不表示接受条款、取得许可证或部署验收通过。

PostgreSQL 保留 15 大版本，新部署采用 [15.19 修补版](https://www.postgresql.org/docs/release/15.19/)，不连接或升级既有 15.18 测试库。2026-09-17 经批准只读查询 [Docker Hub 官方标签元数据](https://hub.docker.com/v2/repositories/library/postgres/tags/15.19-alpine3.24)，随后按固定摘要实际拉取并运行无网络、只读版本检查：

| 项目 | 候选值 / 验证范围 |
|---|---|
| 标签与平台 | `15.19-alpine3.24`，`linux/amd64` |
| 平台镜像摘要 | `docker.io/library/postgres@sha256:a2c20749c564b4eb73a77bfda626f8a3cde1bbfae020fb97c616a00cdc1a2181`；是标签 API 返回的平台 digest，不是本机 image ID |
| API 报告的压缩大小 | `115,228,114` bytes；不等于 Docker 展开后占用或部署空间预算 |
| 已验证 | RepoDigest 与候选一致；本机 image ID `sha256:aad6289ca337b3ce76896f2e7e61480490152886c7828120371fb28e6b779e1d`；版本输出 PostgreSQL `15.19` |
| 未验证 | 正式进程 UID、Windows/D 盘挂载、初始化/重建与应用兼容性 |

AIStor 标准版固定为 `quay.io/minio/aistor/minio@sha256:dfa8e241413464755a9cd90574b15030d6a5703c74ec73928abb6d9c5f4f42ce`（linux/amd64）；实际 RepoDigest 一致，本机 image ID 为 `sha256:2cacca14bad4502feddcbf99cd1a927d8002c6d1ba874a81def1c37b2986b580`，无网络、只读版本检查报告 `RELEASE.2026-09-07T08-39-31Z`、commit `021f251729c44aa71377b5a740e8b7e753bd35ba`。两镜像 `Config.User` 均为空；正式进程 UID、许可证加载和 D 盘兼容性仍须实际运行核对。

`infra/.env.example` 已固定上述两个摘要，不使用 `latest` 或仅 tag，不覆盖原有标签或旧数据库。实际许可证与部署验收进度见[持久化实施行动](../actions/2026-09-17-minimal-local-persistence.md)；首次并发拉取的网络 EOF 及后续逐镜像成功记录也由该行动维护。

## 3. 第三方框架源码策略

`framework/` 是本机用于阅读和运行第三方上游源码的工作区，不是 AgentExam 自有源码的一部分。团队已确认：

1. `framework/swe-gym/`、`framework/swe-bench-fork/` 和计划恢复的 `framework/harbor/` 不上传到 AgentExam 主仓库；
2. 不把它们作为普通目录、复制代码或 Git Submodule（主仓库只记录另一个仓库提交的机制）纳入主仓库；
3. 主仓库只提交本文件记录的来源、固定提交与恢复方法；
4. 后续可以提供恢复脚本，但本次仅提供人工命令，没有创建脚本；
5. 在主仓库批量暂存文件前，应人工确认 `framework/` 未被纳入；当前 `.gitignore` 已忽略整个 `framework/`，后续还应增加自动检查。

## 4. SWE-Gym

### 4.1 身份与来源

| 项目 | 已核验值 |
|---|---|
| 官方仓库 | <https://github.com/SWE-Gym/SWE-Gym.git> |
| 本地恢复路径 | `framework/swe-gym` |
| 固定提交 | `b681068ca20628c6987b7416cc4cf03f06b77ba5` |
| 核验时分支 | `main`，跟踪 `origin/main` |
| 核验时工作树 | 干净；无已修改或已暂存文件 |
| 许可证 | Apache License 2.0 |
| 固定提交入口 | <https://github.com/SWE-Gym/SWE-Gym/tree/b681068ca20628c6987b7416cc4cf03f06b77ba5> |

许可证结论来自固定提交中的 [`LICENSE`](https://github.com/SWE-Gym/SWE-Gym/blob/b681068ca20628c6987b7416cc4cf03f06b77ba5/LICENSE)。

### 4.2 安装、数据与镜像入口

- 该固定提交的仓库根目录没有 `pyproject.toml`、`setup.py`、`setup.cfg`、`requirements.txt`、`environment.yml`、`Pipfile`、`poetry.lock` 或 `package.json`，因此不能把 SWE-Gym 本身描述成一个具有统一安装入口的软件包。
- 官方 [`README.md`](https://github.com/SWE-Gym/SWE-Gym/blob/b681068ca20628c6987b7416cc4cf03f06b77ba5/README.md) 将数据与模型入口指向 Hugging Face 的 [`SWE-Gym`](https://huggingface.co/SWE-Gym) 组织页，并把环境常量指向 SWE-Bench-Fork。
- 同一 README 声明实例预构建镜像位于 Docker Hub 的 `xingyaoww/sweb.eval.x86_64` 前缀下。
- 团队已确认首个真实原型使用 `SWE-Gym/SWE-Gym-Lite` 的 1～3 道任务。M0 当前固定 revision `61231f2c90b18985b42a1419738a240085a15107`、`train` split 和候选 `python__mypy-15413`；固定 Parquet 大小为 `931,193` bytes，SHA-256 为 `f3a7cd934e8cc523b6053298d0abb2c82fd7db2b83f9f2ccba5944545aaa4eb1`。
- 当前候选镜像固定为 `xingyaoww/sweb.eval.x86_64.python_s_mypy-15413@sha256:f069dfc74592d438ad870bbc6dfb369bff1b125d21237ead49190b414f5f3456`，已拉取并确认 `/testbed` HEAD 为任务 base commit `e7b917ec7532206b996542570f4b68a33c3ff771`。这只证明镜像身份，不证明 Harness 或 Codex Trial 通过。
- OpenHands 和 MoatlessTools 出现在上游复现实验说明中；它们当前不是 AgentExam 已固定的直接依赖，不能仅凭上游示例自动纳入项目。

当前验证状态：Task Adapter 的公开/隐藏隔离、固定 Parquet、摘要镜像与 Harbor NOP 已核验；同一固定镜像又用于通过的 Fork 五类真实补丁验证。第四场真实 Codex 与独立 Fork 已通过，具体结果见第 2.1 节执行状态指针。

## 5. SWE-Bench-Fork

### 5.1 身份与来源

| 项目 | 已核验值 |
|---|---|
| 官方仓库 | <https://github.com/SWE-Gym/SWE-Bench-Fork.git> |
| 本地恢复路径 | `framework/swe-bench-fork` |
| 固定提交 | `242429c188fcfd06aad13fce9a54d450470bf0ac` |
| 包内版本 | `2.0.13` |
| 核验时分支 | `main`，跟踪 `origin/main` |
| 核验时工作树 | 干净；无已修改或已暂存文件 |
| 许可证 | MIT License |
| 固定提交入口 | <https://github.com/SWE-Gym/SWE-Bench-Fork/tree/242429c188fcfd06aad13fce9a54d450470bf0ac> |

完整提交哈希是项目的权威固定版本；包内版本 `2.0.13` 只作为辅助身份。许可证结论来自固定提交中的 [`LICENSE`](https://github.com/SWE-Gym/SWE-Bench-Fork/blob/242429c188fcfd06aad13fce9a54d450470bf0ac/LICENSE)。

两个上游仓库的许可证只约束各自上游内容，不会自动替 AgentExam 选择许可证；AgentExam 主仓库是否开源、采用哪种许可证仍需团队另行确认。

### 5.2 安装入口与直接 Python 依赖

固定提交提供 `pyproject.toml`、`setup.py` 和 `setup.cfg`，源码安装入口为：

```powershell
python -m pip install -e .
```

该命令是上游入口；项目实际使用固定源码的 `PYTHONPATH` 加隔离依赖环境，没有对上游执行 editable 安装。上游 [`setup.py`](https://github.com/SWE-Gym/SWE-Bench-Fork/blob/242429c188fcfd06aad13fce9a54d450470bf0ac/setup.py) 声明：

- Python 要求：`>=3.8`；
- 核心直接依赖：`beautifulsoup4`、`chardet`、`datasets`、`docker`、`ghapi`、`GitPython`、`pre-commit`、`python-dotenv`、`requests`、`rich`、`unidiff`、`tqdm`；
- `inference` 可选依赖：`tiktoken`、`openai`、`anthropic`、`transformers`、`peft`、`sentencepiece`、`protobuf`、`torch`、`flash_attn`、`triton`、`jedi`、`tenacity`。

上游没有锁文件；项目现以 [`swebench-requirements.in`](../../apps/backend/swebench-requirements.in) 记录这 12 项运行依赖，以 [`swebench-requirements.txt`](../../apps/backend/swebench-requirements.txt) 锁定 Linux Python 3.12 的 63 项传递依赖及分发文件 SHA-256，不安装 inference extra。当前载体为已有 Ubuntu WSL2 的 Python `3.12.3`，隔离环境位于 `framework/swe-bench-fork/.venv`。每次 Fork 启动核对锁文件哈希与全部已装版本，并保存 `runtime.json`。

本机恢复流程（先确认目标不存在，复用已有缓存；不修改系统 Python）：

```text
Windows：uv pip install --target runtime/tools/uv-linux --python-version 3.12 --python-platform x86_64-unknown-linux-gnu --no-python-downloads --only-binary :all: uv==0.12.10
WSL：runtime/tools/uv-linux/bin/uv venv framework/swe-bench-fork/.venv --python /usr/bin/python3 --no-python-downloads
Windows：uv pip install --target framework/swe-bench-fork/.venv/lib/python3.12/site-packages --python-version 3.12 --python-platform x86_64-unknown-linux-gnu --no-python-downloads --only-binary :all: --require-hashes -r apps/backend/swebench-requirements.txt
```

这里 Windows 的 `uv` 为本项目 `runtime/tools/uv-bootstrap/Scripts/uv.exe`（`0.12.10`）。需要下载时仅给对应进程配置既有代理和 `UV_CACHE_DIR`；Linux 实际执行使用清空后重建的环境变量，不继承个人凭据或 `.env`。原生 `--help` 已在该隔离环境通过；接口适配范围见 [`FRAMEWORK_INTERFACES.md` 第 5.4 节](../interfaces/FRAMEWORK_INTERFACES.md#54-项目实际调用方式)。

### 5.3 数据与镜像来源

- Harness 支持 Hugging Face 数据集名称以及本地 JSON/JSONL；具体字段和 CLI 规则见 [`FRAMEWORK_INTERFACES.md`](../interfaces/FRAMEWORK_INTERFACES.md)。
- 上游 CLI 默认数据集是 `princeton-nlp/SWE-bench_Lite`、默认 split 是 `test`。这是上游默认值，不是 AgentExam 已确认的 SWE-Gym 数据选择；项目调用时必须显式指定后续确认的数据集与 split。
- 固定源码把本地镜像命名为 `sweb.base.<arch>:latest`、`sweb.env.<arch>.<hash>:latest` 和 `sweb.eval.<arch>.<instance_id>:latest`。
- 基础 Dockerfile 从 `ubuntu:22.04` 构建并下载 Miniconda 安装器；两者都未按镜像 digest 或文件校验和固定。
- 对固定提交执行源码搜索，没有发现 `docker pull` 或 Docker SDK `images.pull` 调用。也就是说，SWE-Gym README 提到的 `xingyaoww/...` 预构建镜像不是当前 Harness 自动恢复流程；默认行为是在本机缺少镜像时按源码构建。

当前验证状态：固定 Fork CLI 与五类真实判卷已经通过。原 CLI 的 base/env 预检查与 16 GiB 默认限制由 Evaluator 内部基础设施适配处理，直接使用已固定的实例镜像 digest，不伪造 base/env 标签、不重建上游镜像、不修改上游源码或 grading。原始报告与失败证据见 [M0 行动记录](../actions/2026-09-05-m0-codex-harbor-implementation.md)；第四场 Codex 端到端已通过，完整验收边界引用执行接口。

## 6. Harbor

### 6.1 身份与来源

| 项目 | 已核验值 |
|---|---|
| 官方仓库 | <https://github.com/harbor-framework/harbor.git> |
| 本地恢复路径 | `framework/harbor` |
| 固定提交 | `6af8d6e31eced13b93849cdf80feeadf24603d15` |
| 包内版本 | `0.22.0` |
| Python 要求 | `>=3.12` |
| 许可证 | Apache License 2.0 |
| 固定提交入口 | <https://github.com/harbor-framework/harbor/tree/6af8d6e31eced13b93849cdf80feeadf24603d15> |

完整提交哈希是项目的权威固定版本；包内版本 `0.22.0` 只作为辅助身份。固定源码和按上游 `uv.lock` 的隔离环境已在本机恢复，CLI 可启动；NOP 是已有基础验证，当前真实 Codex 单题核心链路及完整 M0 的区别见[执行接口](../interfaces/HARBOR_EXECUTION.md#暂停后的验收对账2026-09-08)。

### 6.2 在项目中的边界

- Harbor 是已确认采用、但仍须通过原型验收的 Execution Backend，不是平台数据库、课程管理后端或最终判卷器。
- PostgreSQL 继续管理平台 Evaluation Job 队列；一个平台 Job 映射为一个 Harbor Job。
- Harbor 按 Agent × Task × Attempt 展开 Trial；首版 `n_attempts=1`、`n_concurrent_trials=1`。
- 固定 SWE-Bench-Fork 的 `swebench.harness.run_evaluation` 仍是唯一确定性最终判卷入口，Harbor Reward 不能覆盖其结论。
- Harbor 的精确接口、转换与退出门槛由 [`HARBOR_EXECUTION.md`](../interfaces/HARBOR_EXECUTION.md) 维护；采用决定见 [`ADR-0001`](../adr/0001-use-harbor-as-execution-backend.md)。

当前验证状态：固定源码/环境已恢复；配置模型、Job/Trial 展开、结果模型、制品顺序和 Verifier 关闭能力已做源码核验，真实 `JobConfig`/`Task` 契约测试通过。NOP Docker Trial 已实际启动并完成，collect hook 生成的空 `model.patch`/元数据、单目录 artifact、结果映射和正常 Compose 清理均通过；固定摘要、禁网容器又覆盖了修改、新建、删除和 Agent commit 四类非空 patch，并经宿主生产校验器验证。阻塞 collect 探针复现外层强杀残留并验证生产 Adapter 的精确 Compose project 清理和日志有界收束。固定 Fork 已完成第 5 节的五类验证；真实 Codex 最新单题结果及剩余网络/凭据验收引用第 2.1 节执行状态指针。

### 6.3 网络探针的固定镜像与构建输入

2026-09-07 为 M0 无凭据网络探针拉取固定 Harbor 源码已引用的两个镜像，并核对摘要：

| 输入 | 固定身份 | 用途 |
|---|---|---|
| Alpine | `alpine:3.23.4@sha256:5b10f432ef3da1b8d4c7eb6c487f2f5a8f096bc91145e68878dd4a5019afde11` | Harbor 原生内核探针；该镜像没有 httpd applet，不作测试 HTTP 服务 |
| GOST | `gogost/gost:3.2.7-nightly.20260602@sha256:afc0137758ab4ce399d47a299f9abbacbf522b52a17e59cbb4b4e7a1a66e9196` | 原生透明网络侧车的基础镜像；版本来自固定源码，不是选择 nightly 最新值 |

侧车由固定提交的 `src/harbor/environments/docker/harbor-docker-egress-control-sidecar/` 五个文件构建，复用 Harbor 原生内容哈希命名及构建缓存。Windows 检出中的 CRLF 会使脚本解释器无效；既有 Execution Backend 内部 `network.py` 使用 `git show <固定提交>:<路径>` 获取原始 blob，拒绝覆盖或非固定/跟踪文件有修改的上游工作树。2026-09-08 已授权限定 DNS 修正只作用于导出的 network-policy 运行副本；`network-source.json` 同时保存 revision、五项 `upstream_sha256`、五项生效 `sha256` 和 adaptation 标识。生产 `harbor_entry.py` 与网络测试共用该导出，按生效内容构建；固定上游工作树、其他四个 blob、旧缓存与全局 Git 配置不变。允许/禁止 HTTP 对照服务复用第 4.2 节任务摘要镜像中的 Python 标准库，无额外 Python 依赖。具体适配边界、失败关闭与验证状态唯一维护在 [Harbor 执行接口](../interfaces/HARBOR_EXECUTION.md#限定-dns-适配2026-09-08)。

## 7. 恢复固定源码

在 AgentExam 仓库根目录执行以下命令。目标目录必须不存在；如果已经存在，应先核验，不要直接覆盖。

```powershell
git clone https://github.com/SWE-Gym/SWE-Gym.git framework/swe-gym
git -C framework/swe-gym checkout --detach b681068ca20628c6987b7416cc4cf03f06b77ba5

git clone https://github.com/SWE-Gym/SWE-Bench-Fork.git framework/swe-bench-fork
git -C framework/swe-bench-fork checkout --detach 242429c188fcfd06aad13fce9a54d450470bf0ac

git clone https://github.com/harbor-framework/harbor.git framework/harbor
git -C framework/harbor checkout --detach 6af8d6e31eced13b93849cdf80feeadf24603d15
```

`--detach` 表示不跟随某个可继续移动的分支，而是直接停在指定提交。恢复源码不等于安装依赖，也不会自动下载数据集或镜像。

## 8. 核验本地源码

分别执行：

```powershell
git -C framework/swe-gym remote get-url origin
git -C framework/swe-gym rev-parse HEAD
git -C framework/swe-gym status --porcelain

git -C framework/swe-bench-fork remote get-url origin
git -C framework/swe-bench-fork rev-parse HEAD
git -C framework/swe-bench-fork status --porcelain

git -C framework/harbor remote get-url origin
git -C framework/harbor rev-parse HEAD
git -C framework/harbor status --porcelain
```

成功标准：

- 三个远程地址分别与第 4、5、6 节完全一致；
- 三个 `HEAD` 分别等于表中的 40 位完整提交哈希；
- 三个 `status --porcelain` 均无输出，表示没有本地改动；
- SWE-Bench-Fork 的 `swebench/__init__.py` 仍声明 `2.0.13`；若任一结果不同，不得把该环境标记为已复现。

Harbor 已恢复到本机固定提交且工作树干净；若上述核验失败，应先查明本机后续变化，不得覆盖或重建现有环境。

## 9. 尚待确认的锁定项

以下事项必须通过后续架构确认或真实运行完成，当前不得补猜：

1. 首个原型已经固定 Lite revision、`train` split、单题和内容校验值，并取得真实核心闭环证据；正式榜最终数据范围另行确认，不因原型单题通过自动扩大；
2. M0 预构建实例镜像的固定 digest 和 `/testbed` base commit 已核验，该固定环境已支持第 2 节记录的真实单题；扩题或改变环境时仍须重新验证兼容性；
3. 后端 Python 与身份切片应用依赖已有精确基线（见第 2 节），Node.js、Docker/Compose、PostgreSQL、MinIO 的正式部署版本/形态仍需确认；不能用本机测试版本代替部署决定；
4. SWE-Bench-Fork 已有 Linux Python 3.12 哈希锁与单题实测；新增题目/升级依赖时重新验证，不默认把当前单题扩展成全题库通过；
5. Codex 首轮 CLI 版本、模型 ID、推理强度与认证政策已确认；制品身份及无凭据容器安装见第 2.1 节，第四场账号/模型路径和实际工具执行已通过，完整生命周期与网络边界仍按专题接口收尾。Aider、Claude Code 的精确 CLI 版本、安装来源和校验方式仍待确认；
6. P2 自研 Agent 的精确 Python 版本、依赖锁格式、DeepSeek/Kimi 模型 ID、外部接口和受控访问运行依赖；不阻塞 M0/M1；
7. Windows + Docker Desktop、WSL2 或 Linux 中哪一种环境作为官方运行基线；
8. Harbor Job/Trial 目录、空 patch collect 和结果映射已由 NOP 固定；修改/新建/删除/Agent commit 四类非空 patch 已由固定摘要、禁网容器验证；CLI 进程 Adapter 的正常 NOP、外层超时精确 Compose 清理和日志有界收束均已验证，第四场真实 Codex 核心闭环已通过，完整原型验收继续按专题接口收尾；
9. 恢复脚本、依赖缓存和供应链校验流程。

## 10. 本次核验证据摘要

本节汇总此前记录的环境核验和后续运行证据；2026-09-08 的文档同步未重新运行版本、环境或模型检查。较早的宿主 CLI 探针不能替代后续独立记录的容器结果。

| 检查 | 结果 |
|---|---|
| 本机三仓库 `remote.origin.url` | SWE-Gym、SWE-Bench-Fork 与 Harbor 均与第 4～6 节官方地址一致 |
| 本机三仓库 `HEAD` | SWE-Gym、SWE-Bench-Fork 与 Harbor 均与固定提交一致 |
| 本机三仓库 tracked worktree / index | 均干净 |
| 三项上游许可证 | SWE-Gym、Harbor 为 Apache-2.0；SWE-Bench-Fork 为 MIT |
| Harbor 固定源码与环境 | 本机固定提交、`uv.lock` 环境和 CLI `0.22.0` 已核验；最新运行能力引用第 2 节与执行接口，不再止于 NOP |
| SWE-Gym 根目录安装清单 | 未发现统一包清单或锁文件 |
| SWE-Bench-Fork 安装入口 | `setup.py` / `pyproject.toml` 存在；Python `>=3.8`，依赖未锁版本 |
| 数据集来源 | 固定 Lite revision、`train` split、230 条记录、候选单题和 Parquet 内容哈希已核验 |
| 镜像来源 | 候选 Docker Hub 镜像的 linux/amd64 digest、拉取结果与 `/testbed` base commit 已核验 |
| Codex 宿主 CLI 探针 | 2026-09-07 `codex --version` 返回值与第 2 节已确认首轮版本一致；该宿主探针本身不验证容器 |
| 动态验证 | NOP/超时、collect-patch 四场景及固定 Fork 五类验证已有记录；后续真实 Codex 单题与独立判卷见[执行接口](../interfaces/HARBOR_EXECUTION.md#第四次授权运行真实补丁与独立判卷通过2026-09-08)，完整阶段验收未完成 |
