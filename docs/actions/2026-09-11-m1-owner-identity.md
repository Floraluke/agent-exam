# M1 任务 01：所有者登录与本机恢复

## 状态与情况说明

- 状态：In progress（实现与当前测试已完成，正式双轴评审待固定对照点确认）。对应[任务 01](../../.scratch/m1-platform/issues/01-owner-login-recovery.md)，本次新行动独立于已完成并本地提交为 `2290973` 的任务发布行动。
- 用户已确认：在既有后端分层内新增 accounts、sessions 两张 PostgreSQL 表，登录/退出/当前身份接口，本机唯一所有者引导/恢复命令，最小 Web/HTTP 入口及身份和测试子目录；不拆服务、不改 Harbor、不复用 Codex 凭据。
- 必要性：现有源码只有任务、Agent 配置、执行/判卷和本机原型，没有应用账号/会话。评测数据与登录秘密生命周期不同，已有 ExecutionBackend/PatchEvaluator 不能承担身份存储和认证；遵循既有领域→应用/ports→Adapter 依赖方向补齐身份用例。
- 完成目标：可信登录、退出、过期拒绝和本机恢复，真实持久化 Adapter 与最小页面。协作者邀请、Job、Worker 等仍属后续任务，不在本行动提前实现。
- 真实模型、其他 Docker/网络探针、用户凭据、现有服务迁移、机器配置和推送均不自动执行。用户已单独授权官方 PostgreSQL 镜像及专属回环临时容器，用合成数据验证后精确删除本测试容器/数据，不触碰已有数据库。
- 环境变化：早先提升权限的 Docker 查询返回引擎管道不存在；后续只读复查已可用（Engine 27.5.1）。本助手未启动或重启 Docker。已有官方 PostgreSQL 15 Alpine 镜像可复用，无需拉取；只建立专属临时容器，不连接正在运行的 Dify 数据库。

## 实施措施

1. 按 `implement`/`tdd` 在已确认 HTTP 主入口逐个红→绿：建立身份后登录可查询当前用户，再加入退出、过期、错误输入/凭据、提权与跨站请求拒绝、恢复撤销旧会话和依赖失败；少量浏览器验证登录/退出，数据库 Adapter 单独真实集成。
2. 新增纯领域身份对象和小型身份存储/密码处理 ports，应用用例通过真实 Argon2 密码 Adapter 与 PostgreSQL Adapter 工作；内存存储仅位于测试目录，生产不得回退到内存账号。
3. 使用有界随机会话，数据库只存会话 token 的 SHA-256 摘要，Cookie 保存原始 token；密码使用 Argon2id。恢复保留 owner ID，原子修改密码与认证版本并撤销旧会话，阻止恢复前验证的并发登录重新签发有效会话。
4. HTTP 固定三条身份端点，未知字段拒绝，错误不回显输入/连接串；写请求检查固定公开 Origin 与自定义请求头，不开启 CORS。HTTPS Cookie 使用 Secure/HttpOnly/SameSite，仅明确回环开发配置允许非 Secure Cookie。会话默认 8 小时；单进程登录限流作为本机保护，不声称具备分布式防滥用能力。
5. 本机 CLI 显式初始化专用数据库结构、引导或恢复 owner；密码仅从受保护终端交互读取，无密码命令行参数，不自动连接/迁移用户现有服务。Web 只经同源 HTTP 调用后端，不直连数据库。
6. 按官方资料核对兼容版本并在包清单/锁文件固定，只更新项目环境；新增直接依赖、恢复入口和验证限制同步到各自权威文档。
7. 按任务风险运行单测、静态检查、整套默认回归及可用集成；完成实现后使用 `code-review` 检查标准与任务符合性，关键节点限定范围本地提交，不推送。

## 实际修改的文件树

```text
E:/9.1agent_exam/                             # 既有根目录
├─ apps/backend/                             # 既有后端项目
│  ├─ pyproject.toml / uv.lock                # 固定 HTTP、身份、数据库依赖及 CLI 命令
│  ├─ src/eval_platform/                     # 既有分层架构
│  │  ├─ domain/identity.py                  # 纯身份/账号/会话对象与错误
│  │  ├─ application/identity.py             # 登录、退出、查询、引导与恢复用例
│  │  ├─ application/ports/identity.py       # 身份存储与密码处理的外部依赖 Interface
│  │  ├─ adapters/identity/                 # 密码库 Adapter，不承担 HTTP 或持久化
│  │  │  ├─ __init__.py                     # 包入口
│  │  │  └─ passwords.py                    # Argon2id 哈希/验证实现
│  │  ├─ adapters/persistence/              # 已规划 PostgreSQL Adapter 目录
│  │  │  ├─ __init__.py                     # 包入口
│  │  │  ├─ identity.py                     # 账号/会话短事务与异常转换
│  │  │  └─ identity.sql                    # 两张表、唯一 owner 与会话约束
│  │  └─ delivery/                          # 已规划的外部交付入口
│  │     ├─ __init__.py                     # 包入口
│  │     ├─ owner.py                        # 本机数据库初始化/owner 引导恢复命令
│  │     └─ http/                          # FastAPI HTTP Delivery
│  │        ├─ __init__.py                  # 包入口
│  │        ├─ app.py                       # 组装真实 ports/Adapters 与路由
│  │        ├─ config.py                    # 有界公开源、Cookie 和环境配置
│  │        ├─ errors.py                    # 不泄漏请求输入的统一错误
│  │        ├─ security.py                  # 写请求同源检查和单进程登录限流
│  │        ├─ schemas.py                   # 公开身份请求/响应结构
│  │        └─ routes/                     # HTTP 到用例翻译
│  │           ├─ __init__.py               # 包入口
│  │           └─ identity.py               # 登录、退出、当前身份
│  └─ tests/identity/                       # HTTP 与存储行为测试及外部替身
│     ├─ __init__.py                        # 测试包入口
│     ├─ memory.py                          # 只在测试使用的身份存储 Adapter
│     ├─ conftest.py                        # 合成账号、时间与 HTTP 客户端夹具
│     ├─ test_http_identity.py              # 登录/会话基本流程
│     ├─ test_http_security.py              # 非法/越权/跨站与错误保护
│     ├─ test_owner_recovery.py             # 恢复后 HTTP 登录与旧会话拒绝
│     ├─ test_postgres_identity.py          # 显式环境门禁的真实 PostgreSQL 验证
│     └─ browser_server.py                  # 合成账号的浏览器测试后端，不是生产入口
├─ apps/web/                                # 已批准的最小 Next.js 15 / React 19 Web
│  ├─ package.json / package-lock.json       # 精确前端依赖、命令及完整锁
│  ├─ next.config.ts / tsconfig.json         # 同源回环转发与 TypeScript 校验
│  ├─ next-env.d.ts / playwright.config.ts   # 框架声明及小型浏览器测试配置
│  ├─ src/app/layout.tsx / page.tsx          # 中文布局和当前身份/登录页面入口
│  ├─ src/app/globals.css                    # 最小可读表单样式
│  ├─ src/features/identity/session.tsx      # 登录、当前身份与退出交互
│  ├─ src/lib/api-client.ts / contracts.ts   # 唯一 HTTP 客户端与公开类型
│  └─ tests/identity.spec.ts                 # 浏览器接线，不模拟后端 HTTP
├─ .scratch/m1-platform/issues/01-owner-login-recovery.md # 实际验收及行动指针
├─ HANDOFF.md                               # 当前能力、检查点和下一步
└─ docs/                                    # 各自权威事实同步，不另造重复专题
   ├─ actions/2026-09-11-m1-owner-identity.md # 本次实施/验证记录
   ├─ architecture/ARCHITECTURE.md           # 新增身份职责、文件树与依赖关系
   ├─ architecture/MODULE_CONTRACTS.md       # 身份用例和 ports 契约
   ├─ architecture/DATA_MODEL.md             # 两张身份表与事务不变量
   ├─ interfaces/HTTP_API.md                 # 精确端点、Cookie、同源和错误契约
   └─ dependencies/DEPENDENCIES.md           # 查证版本和本机启动/恢复命令
```

使用 Adapter 模式：PostgreSQLIdentityRepository 与测试内存存储满足同一 IdentityRepository Interface；Argon2 Adapter 实现密码处理 Interface，外部库不进入 domain/application。HTTP app 是 Composition Root（组装入口），只负责依赖连接。所有新增源码每文件不超过 200 行、每层不超过 8 个文件；超过前另行评估确认，不借任务文档例外豁免源码。

## 修改后自验证方式

- 每个切片先执行对应 HTTP 测试并观察失败，再实现并确认通过，定期运行 Ruff/mypy；禁止一次写完所有未来测试后再补整层实现。
- HTTP 测试经过真实路由、应用用例和密码处理，仅数据库/时间等外部依赖用替身；测试通过公开响应与会话行为观察，不查询私有属性或统计内部调用次数。
- 浏览器用真实 Next.js→FastAPI 同源链，合成账号、测试内存存储；验证首次未登录、错误密码、登录刷新、退出和错误状态。不能计为真实数据库通过。
- PostgreSQL 集成必须使用明确的专属测试数据库，覆盖唯一 owner、并发引导/恢复/签发、事务回滚、重启持久化与过期/撤销；无环境时明确跳过，不自动连接现有服务或启动 Docker。
- 执行默认无模型回归、前端类型/构建检查；检查源码行数、目录文件数、依赖方向、文档链接、Git diff 和暂存范围；保留未运行/失败/跳过的事实。
- 通过 `code-review` 对照任务与项目标准；实际代码、文件树、接口、数据、依赖、任务验收和本记录保持一致。

数据库执行补充：测试容器使用明确名称/标签、127.0.0.1 随机端口、合成密码，数据仅在容器 tmpfs 中，不挂载宿主或现有卷；限制为 1 CPU / 512 MiB / PID 128。记录执行前资源身份，结束按本次容器 ID 及标签核对后删除，保留原有镜像。测试在该容器内新建随机命名数据库隔离各用例，finally 只删除本用例刚创建的确切数据库；恢复失败使用专属库中的临时失败触发器注入，断言仍经公开身份接口，不查询业务表来冒充用例结果。新增并发登录/恢复、独立进程读取会话和真实过期/撤销验证；已有实现若直接通过则标为补充回归，不伪造红绿失败。

## 自验证情况

- 依赖核验最初在默认沙箱读官方 registry 时遇到套接字权限拒绝，随后只读提升权限查询成功；不是模型网络或项目服务故障。项目 uv sync 成功，直接版本与完整锁已生成，未更新固定 M0 直接依赖。
- 已观察红→绿：登录/查询（缺少实现→通过）、退出重放（404→204 且旧 Cookie 401）、写请求来源（错误来源仍 200→403）、校验错误回显合成秘密（回显→安全 422）、身份响应缓存（缺少头→no-store）、本机恢复（缺少用例→旧凭证/会话 401）、存储故障（500→安全 503）、全局登录预算（第 11 次仍 200→429）、回环开发 Cookie（配置缺少→显式 HTTP 模式通过）。8 小时过期边界作为已有行为回归通过，未伪造新的失败记录。
- 截至首轮后端切片：12 passed、1 PostgreSQL 集成 skipped；mypy 52 源文件通过，Ruff check 通过。早期 Ruff 发现导入顺序和行长问题，经格式化及拆分长 SQL 字符串修正；未将失败检查称为通过。
- PostgreSQL 测试先写时，入口导入最初确认 Adapter 不存在，实际数据库行为因环境不可用未进入红绿运行。环境恢复后首个真实集成为 1 passed；补充唯一 owner/失败触发器回滚后为 2 passed；最终两个文件合跑为 11 passed（其中 7 项真实 PostgreSQL，4 项本机/内存回归）。数据库新增场景直接通过，属于补充验证，不虚构生产实现的红绿修复。
- 测试输出含上游 Starlette 对 httpx/AnyIO 别名的两项弃用警告，现有固定测试依赖仍可执行；没有为了消除提示更换测试语义或隐藏警告。
- 浏览器先观察到缺少登录表单的失败，再完成页面。随后两次失败属于测试选择器歧义：账号区域与输入框重名、Next 路由公告也使用 alert；改为精确标签和区域内定位后，`npm run test:e2e` 为 2 passed（8.0 秒）。真实 Next→FastAPI、合成测试存储覆盖错误密码、登录刷新、身份显示与退出；截图 `runtime/tests/identity-login.png` 已人工查看。测试端口 3100/8875 在收尾无监听。
- 最终默认后端回归：先在子进程移除全部 `AGENTEXAM_RUN_*` 再调用 `pytest -q -p no:cacheprovider --tb=short`，222 passed / 26 skipped / 2 warnings（14.77 秒）。26 项为 19 个既有重型门禁与 7 个本次数据库门禁；后者在前述独立真实数据库批次已运行通过，默认套件中仍如实记为跳过。
- 最终 `ruff check src tests prototype_codex_harbor_e2e.py` 通过；`ruff format --check` 为 93 文件已格式化；`mypy src prototype_codex_harbor_e2e.py` 为 53 源文件通过。前端 `npm run typecheck` 与 `npm run build` 通过。新增动态源文件 34 个/涉及目录 14 个全部满足 200 行及每层 8 文件指标，当前最长 172 行；`git diff --check` 通过。
- 依赖恢复：项目 uv sync 与前端 npm install 成功，没有升级机器级工具。Playwright Chromium/Headless 与辅助下载仅落在 `runtime/tools/playwright`。`npm ls --depth=0` 虽 exit 0，但报告两个 extraneous 包；`npm explain --offline` 确认它们是 `@img/sharp-wasm32@0.35.4` 及其 `@emnapi/runtime@1.11.3`，尚未清理/证明安装树完全等同锁文件，不把这一检查记为干净通过。
- PostgreSQL 使用[依赖总表第 2.2 节](../dependencies/DEPENDENCIES.md#22-m1-身份切片的依赖与本机入口)记录的已有官方镜像，无拉取、无镜像变更。容器 `agentexam-identity-test-20260911-a1` / ID `470bb6be0af992061a99acfe6203f62f0bbd162083eec4c55b9543a56582b69a`，实际端口为 `127.0.0.1:64752`；数据 tmpfs，Mounts 为空。验证后先核对 ID/名称/标签/无挂载，再 `docker rm --force --volumes <该完整 ID>`；标签查询为空，执行前后 18 容器、15 卷、5 网络共 38 个身份逐项一致。只删除本次合成测试数据，不可恢复；原有服务和镜像保留。没有启动/重启 Docker/WSL、改网络或连接 Dify 数据库。
- 真实数据库覆盖：并发/重复引导（含不同用户名）不能产生第二个 owner；另一应用及独立子进程经 HTTP 读取已有会话；恢复中 DELETE 失败时密码/版本/会话整体回滚；3 次并发登录/恢复后旧访问无效；8 小时过期及退出撤销；生产本机 CLI 引导/恢复和拒绝对已有结构重新初始化。CLI 仅替换终端输入设备，生产数据库/密码/用例真实执行；没有自动验证物理终端的隐藏回显，没有做穷尽并发调度、数据库服务重启或崩溃耐久性实验，不宣称这些也通过。
- 正式 `code-review` 尚未运行：其固定点须由用户指定，已建议账号源码前的 `2290973`，待答复。不把当前测试和人工核对写成双轴评审通过。当前只准备本地实现检查点；此前混合修改的权威文档保持在工作区，不整批混入本次提交，最终提交范围和文档链接检查另记收尾项。
- 文档收尾检查：首次链接检查发现本次新写入的行动文件名漏掉月份，修正后 8 份变更文档、188 个本地链接和 46 个锚点全部通过；围栏/行尾空白检查通过。写入工具曾返回上下文不匹配，但核查发现首份文件已部分写入，故逐文件确认后只补写未生效部分，没有盲目重放整批补丁。71 个既有 M0 源码/测试/配置（排除本次明确更新的包清单/锁）与行动开始前哈希一致。
- 暂存范围预检发现 `apps/web/%USERPROFILE%/` 下的 npm 通知缓存，不是源码，和根目录此前的同名未跟踪路径均不读取、不暂存或删除。构建/运行缓存不进入检查点；后续可在独立维护范围中清理，不扩大本次身份工作。

## 技术来源

- [FastAPI Cookie 响应](https://fastapi.tiangolo.com/advanced/response-cookies/)：使用框架响应设置 Cookie。
- [Psycopg 事务](https://www.psycopg.org/psycopg3/docs/basic/transactions.html)：连接/事务上下文的提交与回滚语义。
- [Argon2 官方用法](https://argon2-cffi.readthedocs.io/en/stable/howto.html)、[OWASP 密码存储](https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html)：库实现密码哈希，不自制密码算法。
- [OWASP 跨站请求防护](https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html)：同源验证、自定义头和 Cookie 防护协作，SameSite 不作为唯一控制。
- [Next.js 2026-08 安全更新](https://nextjs.org/blog/august-2026-security-release)：15.5 修复线至少 15.5.24；本次官方 registry 的 backport 为 15.5.25，继续使用已批准的 15 主版本，不静默升级到 16。
