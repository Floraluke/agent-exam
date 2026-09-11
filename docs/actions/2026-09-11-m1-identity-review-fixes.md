# M1 任务 01：评审问题修复与浏览器安全验收

## 状态与情况说明

- 状态：Completed。用户已确认的两项 Standards P2 与一项 Spec P2 已逐项修复或补证，并完成针对性自验证及完整默认回归；本轮未另做一次独立双轴复审。本次是独立修复行动，不将其追加成旧实施行动的另一项工作。
- 基线：`b15f062` 身份实现检查点；规格为[任务 01](../../.scratch/m1-platform/issues/01-owner-login-recovery.md)。此前[身份实施](2026-09-11-m1-owner-identity.md)的真实 PostgreSQL 测试证据保留，不为本次 HTTP 修复重建数据库。
- 已证实问题：框架 HTTP 404/405 返回 detail 而非统一 error；OpenAPI 422 仍使用框架默认错误模型、遗漏实际身份错误；浏览器缺少 HTTPS Cookie、会话过期/旧会话重放和跨站防护证据。
- 不改变账号/会话表、应用用例、ports、角色、8 小时会话和原子恢复规则；不新增业务接口或服务，不部署长期数据库，不创建真实账号、不运行模型、不改机器信任/网络设置、不推送。
- 现有工作区包含此前文档增量及 `%USERPROFILE%/` 缓存目录，保留且不整批暂存。关键节点允许范围清晰的本地提交。

## 实施措施

1. 按已确认 HTTP seam，先以测试复现 404/405 错误对象缺失，再在既有 Delivery/errors 中转换 Starlette HTTPException，保留 Allow 等协议头，不回显异常 detail。
2. 在既有 schemas 中表达统一错误结构，使用 FastAPI 支持的响应声明补齐已实现身份端点；测试公开 OpenAPI 与真实错误正文，不修改框架内部方法。
3. 将已有浏览器测试入口改为专属回环 HTTPS，使用项目 runtime 中的自签测试证书，不安装受信 CA、不修改操作系统证书存储。既有合成后端保留真实身份用例/密码与内存存储，测试时间只通过已允许的 clock 依赖替换。
4. 逐项补充浏览器 Cookie 属性/脚本不可读、退出后的旧会话重放、服务器时间过期及跨站表单拒绝。外站页面由浏览器工具本地拦截提供，不访问第三方；后端 API 响应不得 mock。不新增生产调时或测试后门端点。
5. 同步 HTTP/架构/依赖指针、任务验收、旧行动和交接中的评审状态；运行默认回归、前端检查及复核，记录失败和限制后做本地检查点。

## 实际修改的文件树

```text
E:/9.1agent_exam/
├─ apps/backend/src/eval_platform/delivery/http/
│  ├─ app.py                 # 注册统一框架 HTTP 异常处理
│  ├─ errors.py              # 安全错误转换、必要响应头
│  ├─ schemas.py             # 已有 HTTP Schema 内补齐 ApiError
│  └─ routes/identity.py     # 三个既有端点的 OpenAPI 错误声明
├─ apps/backend/tests/identity/
│  ├─ test_http_identity.py  # 公开 OpenAPI 与请求/响应契约回归
│  ├─ test_http_security.py  # 404/405 安全包装与协议头回归
│  └─ browser_server.py      # 仅测试入口的 HTTPS Origin 与可控时间依赖
├─ apps/web/
│  ├─ playwright.config.ts  # 回环 HTTPS、项目内测试证书入口
│  └─ tests/identity-security.spec.ts # 新增浏览器安全边界与隔离时间夹具
├─ runtime/tests/            # 既有忽略目录：测试证书/密钥、时间文件与运行结果；不入 Git
├─ .scratch/m1-platform/issues/01-owner-login-recovery.md # 验收与评审结果指针
├─ HANDOFF.md                # 真实检查点、评审和下一步
└─ docs/
   ├─ actions/2026-09-11-m1-identity-review-fixes.md # 本行动证据
   ├─ actions/2026-09-11-m1-owner-identity.md       # 原行动状态与后续指针
   ├─ architecture/ARCHITECTURE.md                # 当前树与测试职责
   ├─ architecture/DATA_MODEL.md                  # 仅同步评审状态指针，不改变数据模型
   ├─ architecture/MODULE_CONTRACTS.md            # 评审/验证状态指针
   ├─ interfaces/HTTP_API.md                     # 统一错误与 OpenAPI 唯一契约
   └─ dependencies/DEPENDENCIES.md               # HTTPS 浏览器测试的恢复方式
```

不新增架构模式。沿用 Adapter/Composition Root：测试后端只替换外部存储和时间，业务仍调用同一 IdentityService；浏览器真实访问 Next→FastAPI。源码继续满足每文件 200 行、每目录 8 文件，测试目录不借 14 任务文档例外放宽。

原有 `apps/web/tests/identity.spec.ts` 未修改，随整套 HTTPS 测试回归。实际增加数据模型文档的状态指针修正，以消除“正式评审待完成”的过期描述；没有改表或引入额外业务设计。

## 修改后自验证方式

- 分别观察 404/405 与 OpenAPI 测试红→绿；检查 Allow 保留、details 为空、request_id 存在，不泄漏合成输入。
- 通过公开 OpenAPI 比对已实现路由/状态、错误字段和实际响应；成功和 204 语义不变。
- Playwright 真实浏览器：HTTPS 登录、刷新、退出、错误密码，Cookie 属性与脚本隔离、旧会话重放 401、时间过期 401、跨站表单 403 且身份不变。仅本机 HTTPS 接线，不代替生产证书/双机访问验收。
- Ruff check/format、mypy、默认无模型 pytest、前端 typecheck/build；检查源文件行数/目录数量、链接锚点、diff 与范围。未修改数据库 Adapter/SQL 时保留此前 PG 结果为历史证据，不描述为重跑。
- 检查测试服务结束后无专属端口监听，证书/密钥不进 Git；不停止其他服务。

## 自验证情况

- 404/405：新增公开 HTTP 回归先得到 2 failed（实际为 detail），注册框架异常转换后，同文件 17 passed；Allow=POST 保留、统一字段和 no-store 均通过。
- OpenAPI：三个端点的声明检查先得到 3 failed；补齐 ApiError/ErrorDetails、响应声明并用同一模型生成实际错误后，两份 HTTP 测试为 29 passed，mypy 52 源文件通过。当前生产身份用例和数据库 Adapter 未改变。
- HTTPS 浏览器：默认沙箱先因既有结果文件 EPERM 未能开始测试；提升权限后，旧 HTTP 测试环境实际失败于开发 Cookie（secure=false），不是生产 HTTPS Cookie 漏洞。改为显式回环 HTTPS 后，该测试 1 passed；退出重放补充回归 1 passed。
- 过期浏览器：先写检查但尚未接测试 clock 时得到 200 而非 401；只为合成测试入口注入可控时间后为 1 passed。时间文件仅在既有 runtime/tests 中，测试结束精确删除；未增加生产调时端点、不改系统时间或 8 小时策略。
- 自签证书由已有 Git OpenSSL 3.5.4 生成，仅项目 runtime/tests 内保存，2 天有效；未下载工具或写系统证书库。首次传 NUL 作为配置文件被 MSYS OpenSSL 拒绝，随后核对并使用已有 openssl.cnf 成功，不把证书准备失败算业务错误。
- 跨站浏览器首次批次为 2 failed / 1 passed：合成外站 HTML 缺少 UTF-8 声明，按钮中文乱码导致选择器超时，非平台 API 错误或真实外网失败。修正合成页面 MIME/meta 编码后两项跨站检查为 2 passed。浏览器确认 Origin 为合成外站、SameSite 阻止携带会话 Cookie、平台返回安全 403，回到本站后原身份不变；同源请求缺少自定义头也被拒绝。
- 最终后端：`ruff check src tests prototype_codex_harbor_e2e.py` 通过，`ruff format --check` 为 93 文件已格式化，`mypy src prototype_codex_harbor_e2e.py` 为 53 源文件通过。在子进程移除全部 `AGENTEXAM_RUN_*` 后执行 `pytest -q -p no:cacheprovider --tb=short`，实际 227 passed / 26 skipped / 2 warnings（16.59 秒）。26 项为受门禁的重型/数据库检查，本轮未运行；7 项真实 PostgreSQL 沿用前次独立批次证据，不描述为重跑。两项上游 Starlette/httpx/AnyIO 弃用警告仍存在。
- 最终前端：在项目浏览器缓存和遥测关闭的进程配置下，`npm run test:e2e` 为 8 passed（17.4 秒）；`npm run typecheck` 与 `npm run build` 均通过。专属测试服务器已退出，3100/8875 无监听，时间文件不存在；两份证书/密钥经 `git check-ignore` 确认不入 Git。仅测试进程忽略自签证书错误，不证明生产证书受信任或远程部署已完成。
- 针对性自查确认框架错误走已有 Delivery、实际错误与 OpenAPI 使用同一模型、生产身份用例/SQL/存储 Adapter 不变、测试调时只在显式门禁的合成入口。9 个变更源文件最长 156 行，涉及的 5 个目录各不超过 8 文件；未扩大分层、接口、表或目录。基线 166 个已跟踪 app/HANDOFF/docs 文件中，151 个内容 SHA-256 未变；15 个变化均在本行动树内，既有 M0 和数据库实现保持不变。
- 文档与范围检查：9 份本行动相关文档的本地链接/锚点、围栏、行尾空白均通过；`git diff --check` 通过。任务 01 已按实际证据勾选，旧行动与交接不再把已执行评审写成待授权。原有两个 npm extraneous 包问题沿用旧行动的限制，本轮未清理依赖缓存或声称完成供应链审计。

## 本地检查点与恢复边界

检查点范围限定为上树的 9 个源码/测试文件、任务 01 和本行动记录，共 11 文件；精确提交号和提交后检查在 [HANDOFF 第 5 节](../../HANDOFF.md#5-git环境与测试快照)记录。架构、HTTP、数据、依赖、旧行动及交接已经在工作区同步，但混合此前增量，不整批加入此次提交。恢复或评审须同时读取当前权威文档，不能将单个代码检查点当作完整最新文档快照。

没有运行模型、创建用户真实账号或重新启动数据库，没有改机器信任/网络配置、触碰其他服务数据或推送。保留两天有效的忽略测试证书；下次过期按依赖入口重新生成。任务 01 的此轮修复已结束，任务 02 与长期数据库部署尚未开始，M1/MVP 未完成。

## 技术依据

- [FastAPI 异常处理](https://fastapi.tiangolo.com/tutorial/handling-errors/)：注册 Starlette HTTPException 才覆盖框架路由错误。
- [FastAPI 额外响应声明](https://fastapi.tiangolo.com/advanced/additional-responses/)：统一模型与 responses 声明协作，不手改生成器。
- [Next CLI HTTPS](https://nextjs.org/docs/app/api-reference/cli/next)：固定本地 15.5.25 源码亦确认可传显式证书/密钥，避免自动 mkcert/系统信任变更。
- [Playwright 请求拦截](https://playwright.dev/docs/network)：仅提供合成外站页面，真实身份 API 不替换。
