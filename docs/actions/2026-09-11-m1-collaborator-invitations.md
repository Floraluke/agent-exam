# M1 任务 02：邀请协作者与成员管理

## 状态与情况说明

- 状态：Blocked（待本轮专属临时 PostgreSQL 执行授权及实测）。代码、合成 HTTP/浏览器、双轴评审及发现修复已完成当前检查；任务 02 未验收完成。用户已授权依次开发、评审和修复任务 02–04；本行动只承载任务 02。评审固定点为 `777f67a`，后续任务以各自开工前提交为准。
- 已确认：24 小时、一次性、可撤销邀请码；创建时仅显示一次，所有者手动交给受邀者；受邀者设账号/密码且只成为 collaborator；停用立即撤销旧访问、保留历史身份。
- 已确认最小结构：复用现有身份分层，新增 invitations 表和必要邀请/成员接口，以及成员测试子目录。accounts/sessions 不能代表尚未加入的邀请及其独立到期/兑换状态；不拆独立认证服务。
- 既有工作区文档增量及两个 `%USERPROFILE%/` 缓存保留，不整批暂存。不创建真实用户、不发邮件、不运行模型、不推送、不改变机器网络/信任或现有服务。真实数据库使用专属合成测试环境，不能连接已有数据库；执行前核对授权及环境。

## 实施措施

1. 同步已确认的邀请契约和任务 Comments，先以 HTTP 测试观察邀请→加入→登录的缺失，再逐切片实现；遵循已确认 HTTP 主验收、少量浏览器及独立真实数据库测试边界。
2. 复用密码哈希/会话能力，邀请只存随机凭据摘要；邀请码只经创建响应一次交付，不进 URL、列表或日志。应用授权和账户规则不交给页面实现。
3. 扩展既有身份 ports，新增同层 membership 用例与 PostgreSQL Adapter，短事务原子兑换/停用；邀请失效、重放、撤销、角色伪造和依赖错误均可观察。适度拆分同层实现以遵守 200 行/8 文件限制，不引入泛化权限框架。
4. 既有本机初始化入口包含邀请结构，已有身份库通过显式本机命令补表，不在 HTTP 启动迁移，不覆盖已有数据。成员/邀请列表有界分页。
5. 页面经唯一 HTTP 客户端完成手动邀请码加入、所有者邀请状态及停用；真实浏览器与 API 不 mock 业务用例。真实 PostgreSQL 验证并发兑换、失败回滚和停用/会话竞争。
6. 完成静态/回归、文档及范围检查，按 code-review 进行标准和规格并行评审；修复真实发现并复验，本地提交后再进入任务 03。实现检查点不等于评审通过。

## 实际修改的文件树

```text
E:/9.1agent_exam/
├─ apps/backend/src/eval_platform/
│  ├─ domain/membership.py                 # 邀请、成员公开值与领域错误
│  ├─ application/membership.py            # 邀请/兑换/停用的授权及业务用例
│  ├─ application/ports/identity.py        # 同一身份分层内的成员存储边界
│  ├─ adapters/persistence/
│  │  ├─ connection.py                     # 复用身份短事务和错误转换，不泄漏连接
│  │  ├─ identity.py                       # 保持账号行为，复用事务及显式初始化
│  │  ├─ membership.py                     # 原子兑换/撤销/停用与安全查询
│  │  └─ membership.sql                    # invitations 结构与约束
│  └─ delivery/
│     ├─ owner.py                          # 显式本机邀请结构升级入口
│     └─ http/
│        ├─ app.py / errors.py             # 组装与统一成员错误处理
│        ├─ membership_schemas.py          # 安全请求/公开响应与分页
│        └─ routes/membership.py           # 邀请及成员 HTTP 翻译
├─ apps/backend/tests/
│  ├─ membership/                          # 已批准的新测试目录，至多 8 文件
│  │  ├─ __init__.py / conftest.py         # 合成应用与公共测试夹具
│  │  ├─ memory.py                         # 只替代外部存储，不替代授权用例
│  │  ├─ test_membership.py                # HTTP 邀请、兑换、列表与停用
│  │  ├─ test_security.py                  # 越权、秘密、失效与 schema
│  │  ├─ test_boundaries.py                # 全入口权限、分页与依赖安全错误
│  │  ├─ test_postgres.py                  # 显式专属 PostgreSQL 兑换/撤销/停用并发
│  │  └─ test_postgres_rollback.py         # 失败回滚、恢复重试与显式补表
│  └─ identity/browser_server.py           # 合成浏览器接通成员用例
├─ apps/backend/pyproject.toml             # 打包显式包含邀请 SQL 资源
├─ apps/web/
│  ├─ src/features/identity/
│  │  ├─ session.tsx                       # 加入入口和所有者成员视图接线
│  │  ├─ join.tsx                          # 手动输入邀请并建立协作者
│  │  └─ members.tsx                       # 一次性邀请显示、列表、撤销及停用
│  ├─ src/lib/api-client.ts / contracts.ts # 单一 HTTP 客户端和公共类型
│  ├─ src/lib/membership-client.ts         # 复用 HTTP 客户端的成员响应解析
│  └─ tests/membership.spec.ts             # HTTPS 浏览器成员动线
├─ .scratch/m1-platform/issues/02-collaborator-invitations.md # 决定与验收
├─ HANDOFF.md                              # 当前进度及检查点
└─ docs/
   ├─ actions/2026-09-11-m1-collaborator-invitations.md # 本行动证据
   ├─ architecture/ARCHITECTURE.md          # 当前树和边界
   ├─ architecture/DATA_MODEL.md           # 邀请字段/事务唯一事实源
   ├─ architecture/MODULE_CONTRACTS.md     # 成员用例与 ports
   ├─ interfaces/HTTP_API.md               # 端点和安全语义唯一事实源
   └─ dependencies/DEPENDENCIES.md         # 本机结构升级及验证恢复入口
```

沿用 Repository/Adapter/Composition Root：应用仅依赖领域/ports，PostgreSQL 与合成存储实现同一边界，HTTP app 组装。当前生产身份目录能承载成员文件；既有 identity 测试目录已达 8 文件，按批准新建 membership 测试子目录。未修改 M0 执行/判卷接口、SQL 业务队列或模型凭据。

## 修改后自验证方式

- 每条 HTTP 切片先红后绿：创建/兑换/登录、过期/撤销/重放、非法输入/角色/未授权、停用/旧 Cookie、分页与依赖错误；实际 OpenAPI 与 ApiError 对照。
- 真正 Next→FastAPI HTTPS 浏览器：所有者创建邀请、独立浏览器加入登录、所有者停用后旧访问拒绝；刷新不重显邀请码，按钮不代替后端权限。
- 专属 PostgreSQL：相同邀请并发只能创建一个成员，账户/邀请任一写失败整体回滚，停用后并发签发也无法保留旧访问；用公开 HTTP/应用入口验证，不凭查表冒充业务结果。
- Ruff check/format、mypy、默认无模型 pytest、前端 typecheck/build；精确行数/目录、Markdown 链接锚点、git diff 与暂存范围核对。
- code-review 双轴报告分别保留；修复及未验证范围如实记录。测试服务、容器、合成数据按精确身份清理，不触碰其他资源。

## 自验证情况

- 邀请→兑换→登录：先为 404 失败，补齐同层用例/HTTP 与测试外部存储后，含既有登录回归为 13 passed。
- 失效/重放/越权/重名：先得到 5 failed（错误尚未转换，实际 500）；补齐安全错误后任务 02 为 6 passed，失效邀请不回显邀请码/密码，角色伪造拒绝且不消耗邀请。
- 列表/撤销/停用：先为 3 failed（405/404）与 1 passed，补齐有界分页、撤销和会话失效后任务 02 为 9 passed。当前以上都是合成外部存储，不计为真实 PG 验收。
- mypy 当前 56 源文件通过。Ruff 初期发现导入/格式与长行；格式化已修正主体，长文档字符串另行缩短，最终统一检查尚待运行。写入曾因同文件重复操作和格式化后的上下文不匹配拒绝，核对未生效后修正补丁，不将写入失败视为业务失败。
- 运行时组装测试先仅 3 路由失败；接入 PostgreSQL 成员 Adapter 后身份+成员接口回归为 43 passed / 7 skipped / 2 warnings，mypy 58 源文件通过。7 skipped 是尚未显式启用的真实 PG 测试。
- HTTPS 浏览器成员动线先在缺少“成员管理”入口失败；补齐 Next 页面、唯一 HTTP 客户端与合成后端接线后 1 passed（10.6s），验证创建→刷新不重显→独立浏览器兑换/登录→停用→旧会话拒绝。前端 typecheck 通过。
- 安全补充切片先为 2 failed / 6 passed：兑换缺少尝试次数上限、OpenAPI 漏列 404。补齐独立于登录的兑换限额及错误契约后通过；中间另有一次断言把既有 ApiError 错写为 ApiErrorResponse，查明真实模型后纠正测试，不视为新增产品缺陷。补充全入口权限、分页、依赖错误后成员 HTTP 为 19 passed。
- 真实 PG 用例已加入，但未显式启用：成员 9 项跳过；未运行，不声称完成先红后绿或持久化验收。等待授权期间没有新建容器或操作数据库。
- 完整默认后端回归（清除子进程 AGENTEXAM_RUN_*，`pytest -q -p no:cacheprovider --tb=short`）为 246 passed / 35 skipped / 2 warnings，20.21 秒；35 项包含已有 19 项重型检查、7 项身份 PG 和新增 9 项成员 PG。两项上游弃用警告保留。`ruff check src tests prototype_codex_harbor_e2e.py`、`ruff format --check`（107 文件）、`mypy src prototype_codex_harbor_e2e.py`（59 源文件）均通过。
- `npm run test:e2e` 全量为 9 passed（19.7 秒），包含旧登录/Cookie/过期/跨站及新增成员动线；`npm run typecheck` 与 `npm run build` 通过。测试服务器已退出，3100/8875 无监听，专属时间文件不存在。浏览器仅对合成测试证书忽略信任错误，不改变系统设置。
- OpenAPI 状态枚举检查补充后先因漏列 enum 失败；共享领域 InvitationStatus 并在响应使用，测试按实际 schema 引用解析后安全文件 8 passed，Ruff 和 mypy 通过。中间一次测试未解析共享类型引用而误报缺枚举，已纠正；不是新增状态或业务流程。
- 离线 wheel 构建：运行环境直接导入 setuptools 不可用（构建后端在独立构建环境，不是业务依赖）；随后复用项目 uv/cache 离线 `uv build apps/backend --wheel --out-dir runtime/tests/membership-wheel --offline --no-python-downloads` 成功，构建输出确认身份和邀请 SQL 都在包内。没有安装新业务依赖或访问网络，产物仅为忽略的测试缓存。
- 文档检查当前 9 份 Markdown、215 条本地链接与 56 处锚点通过；27 个改动源文件均不超过 200 行，12 个直接目录文件数均不超过 8。旧目录历史例外没有扩张。首次多文档补丁因不存在的末尾上下文整体拒绝，确认未写入后去掉错误 hunk 重试成功。
- 本地检查点只包含本行动、任务 02、明确源码/测试与包资源清单；混合此前用户增量的权威文档已同步但不整批暂存，评审必须读取当前工作区文档。没有提交缓存/合成秘密、没有推送。
- 检查点已提交为 `166ccf4`（31 文件），暂存允许集合与实际集合一致，暂存 diff 检查通过。两个只读评审代理分别以 `git diff 777f67a...HEAD` 审 Standards 与 Spec，固定点有效且变更非空；这是实现检查点评审，PG 验收未完成。
- Standards 初步发现：页面内“刷新成员与邀请”只刷新列表但不清除当前邀请码，与 HTTP/UI 的刷新清除承诺不一致。本行动内补浏览器断言，再将显式刷新与创建后的内部刷新区分处理；不新增业务能力或泛化重构。

## 双轴评审（777f67a → 166ccf4）

### Standards

1. **[P2] 刷新入口没有清除一次性邀请码。** `members.tsx` 的显式刷新调用 `run(refresh)`，但 refresh 只更新列表；与同页提示及 HTTP 契约的刷新清除承诺不一致。建议只在主动刷新入口清除，保留创建后内部刷新，并补浏览器断言。
2. **可能的 Duplicated Code（判断性建议，非强制违规）。** 应用 `membership.py` 的账号名/密码建立校验与已有 `identity.py` 相同，未来策略修改可能遗漏入口。当前行为一致，不扩大重构；后续若纳入，应先确认再复用领域内小型校验。此次未修改已有密码策略。

其余所审改动未发现明确分层、角色或秘密存储违规。仅静态评审，未执行 PG/浏览器。

### Spec

- 实现错误：未发现有充分证据的实质问题。邀请只产生 collaborator，管理入口后端核验 owner，兑换/撤销共用邀请锁，停用保留身份并撤销会话。
- 范围扩张：未发现。必要存储/接口已确认，未进入任务 03/04、邮件或模型执行。
- 已公开验收缺口：任务 02 要求“PostgreSQL 集成覆盖并发兑换和回滚”，9 项成员 PG 用例尚未运行，持久化/并发/回滚不能认定通过；不是新发现的代码缺陷。

评审汇总：Standards 1 项一致性问题（最高 P2）+1 项可选结构建议；Spec 新增实现问题 0 项、已知验收缺口 1 类（真实 PG）。两轴不混排。

### 评审后处理

- 显式刷新浏览器断言先红：点击刷新后邀请码输入仍为 1 个、预期为 0。仅在该点击入口清除 token，不改创建后的内部 refresh；修复后全量浏览器 9 passed（19.7 秒），typecheck/build 均通过。原 Standards 评审者只读针对性复核确认覆盖原发现，不冒称重做整套双轴评审。
- 可选校验去重未纳入，本任务没有发生策略分叉，不为该建议扩张重构。真正的验收阻挡仍是新的 PG 运行授权与实测。
- 状态枚举变更后完整后端再次运行：246 passed / 35 skipped / 2 warnings（19.35 秒），仍未运行模型或数据库。
- 真实 PG 尚未新建，本轮已询问任务 02–04 专属临时数据库授权，等待答复；仅只读确认本机已有官方镜像、没有遗留身份测试容器。此前不受该等待影响的代码、合成测试、文档同步与评审已推进完毕；PG 尚未运行不记为通过。

## 当前收束与恢复点

- 已有：31 文件实现检查点、双轴报告、刷新缺陷修复与绿色回归；修复检查点仅纳入 members.tsx、成员浏览器测试、本行动及任务 02 四文件，不 amend、不推送；提交身份由 HANDOFF 第 5 节记录。权威文档已同步现场事实，但旧混合增量不整批暂存。
- 未完成：成员 9 项真实 PG、必要身份 PG 回归；不能以静态 SQL、内存存储或轮子打包通过替代。长期应用数据库仍未部署。
- 最小恢复动作：用户确认任务 02–04 专属临时 PostgreSQL 验证后，只用既有官方镜像、回环地址、合成数据，记录精确容器身份/资源并验证后精确清理；不连接或修改既有数据库。复用当前测试和本行动，完成任务 02 后才进入任务 03。
- 后续任务 03 新存储/接口及 MinIO 验证、任务 04 精确规模预设仍要按各任务单确认必要选择；本轮没有提前定案/实现，不运行模型、真实用户、邮件或推送。
- 收尾复查：9 份文档的 215 条本地链接/56 处锚点及 git diff --check 通过；测试服务器已退出、3100/8875 无监听、专属 clock 文件不存在。一次收尾补丁返回失败后发现部分文件已生效，逐项只读复查后仅补未生效文档，未覆盖用户增量。
