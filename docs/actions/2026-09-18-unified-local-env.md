# 统一本机环境配置

## Status and situation

- 状态：已完成；两个真实秘密值仍须 owner 私下填入本机 `.env`，不影响配置契约交付。
- 来源请求：用户要求创建本机 `.env`，并提供供其他人复制、逐字段解释的 `.env.example`。
- 范围：沿用既有 `infra` 所有者单机运行模块，统一其 Compose、HTTP、MinIO、Worker 与 Web 的现有环境变量；不新增业务模块、数据库表或业务接口。
- 实际变化：`infra/local/AgentExam.Local.psm1` 已改读 Git 忽略的 `infra/.env`，并从中取得数据根、镜像、端口、Bucket 和 MinIO 应用用户名；公开模板不再作为运行文件。正式 HTTP、MinIO 客户端与 Worker 仍复用既有进程环境接口，由行动指南说明如何导入同一个 `.env`。
- 已确认决定：真实 `.env` 必须保持 Git 忽略；公开 `.env.example` 不包含密码、数据库连接串、模型认证正文或其他真实秘密。
- 安全边界：`D:\AgentExamData\private` 中的密码与许可正文、Codex 认证正文不读取、不复制到工作区 `.env`。敏感环境变量只能保留为空并解释私下填写来源；本轮不新增尚未由应用支持的 `*_FILE` 接口。
- 明确排除：不启动正式 HTTP、Web、Worker 或模型；不连接、迁移或修改现有数据库和对象；不修改 Docker/Tailscale/系统级环境变量；不处理工作区已有的无关改动。
- 已核对路径：题目 Parquet、固定 Codex 归档和 Codex 认证文件均存在；归档大小与生产代码固定值一致，SHA-512 也匹配。实时 Tailscale Serve 状态因管理员管道拒绝访问未能读取，`AGENTEXAM_PUBLIC_ORIGIN` 沿用权威远程访问文档已经记录的 HTTPS 主机名。

## Implementation measures

1. 已盘点生产环境变量、当前本机非敏感路径和公开入口；模板只使用应用已经支持的变量名。
2. 已创建 Git 忽略的 `infra/.env`，填入确认过的本机非敏感值和路径；`AGENTEXAM_DATABASE_URL`、`AGENTEXAM_MINIO_SECRET_KEY` 按安全边界保持空白。
3. 已扩充 `infra/.env.example`，逐字段解释格式、用途、必填条件、敏感性和示例值。
4. 已将 Compose 生命周期入口切换到 `infra/.env`；`Get-AgentExamConfig` 同时复用其中的存储字段，初始化 DSN 不再硬编码宿主 PostgreSQL 端口。
5. 已同步所有者单机运行架构、行动指南及依赖文档；明确 Compose 自动读取、应用进程按需导入的边界。
6. 已完成静态字段对照、Git 忽略检查、Compose 解析、PowerShell 装配探针、Ruff 和基础设施局部测试；没有运行真实模型或业务队列。

完成标准：本机文件与公开模板覆盖全部 owner-facing 生产变量；真实 `.env` 不被 Git 跟踪；生命周期读取 `.env`；模板解释与代码消费点一致；验证结果如实记录。

## Affected file tree

```text
infra/
  .env                                            # 新增：Git 忽略的本机统一配置；不复制现有秘密正文
  .env.example                                    # 修改：公开模板及全部字段说明
  local/
    AgentExam.Local.psm1                          # 修改：读取 .env、复用存储字段并对缺失/空必填字段安全失败
    AgentExam.Initialize.psm1                     # 修改：初始化 DSN 使用 .env 中的 PostgreSQL 端口
  tests/
    test_local_lifecycle.py                       # 修改：真实门禁测试的直接 Compose 辅助入口改读 .env
    test_local_persistence.py                     # 修改：容器重建验收的直接 Compose 辅助入口改读 .env
docs/architecture/modules/owner-host-runtime/
  ARCHITECTURE.md                                  # 修改：同步当前部署文件树、边界和依赖方向
  ACTION_GUIDE.md                                  # 修改：增加从模板创建本机配置及填写说明
docs/dependencies/
  DEPENDENCIES.md                                  # 修改：把全部 owner-facing 字段指向公开模板
docs/actions/
  2026-09-18-unified-local-env.md                  # 本行动记录；持续记录实际变化和验证证据
```

关系：`infra/.env.example` 是公开配置契约，复制为本机 `infra/.env`；`AgentExam.Local.psm1` 读取存储相关值并把同一文件交给 Docker Compose。Python/Next.js 继续通过既有进程环境接口读取同名变量，本轮不引入第二套应用配置解析器。该关系属于既有 Composition Root 的配置深化，不新增设计模式或顶层模块。曾计划给 `test_compose_config.py` 追加字段契约，文件会达到 231 行并越过指标，已撤回；改用独立静态命令验证，未新增第九个测试文件或目录重构。

## Self-verification method

1. `git check-ignore -v infra/.env`：必须证明真实文件被忽略；`infra/.env.example` 不得被忽略。
2. 对照生产源码提取全部 `AGENTEXAM_*` owner-facing 变量，核对 `.env.example` 无遗漏、无测试开关和内部私有变量。
3. 检查 `.env.example` 不包含本机密码、认证 JSON 或有效数据库连接串；检查 `.env` 不打印敏感值。
4. `docker compose --env-file infra/.env -f infra/compose.yaml config --quiet`：只验证静态 Compose 解析，不启动或修改容器。
5. 运行受影响的基础设施局部测试；实际命令和结果在下节记录。
6. 检查相关源文件行数和 `infra/local` 文件数量没有因本轮越过项目指标。

## Self-verification results

- 字段契约：独立 PowerShell 对照确认期望、本机文件和公开模板均为 18 个字段，missing/extra 均为 0；两个敏感字段在本机文件和模板中均为空。未打印任何密码或认证正文。
- Git 边界：`git check-ignore -v infra/.env` 命中 `.gitignore:11`；`infra/.env.example` 返回可跟踪。真实 `.env` 不出现在 `git status`。
- 路径证据：题目 Parquet、Codex auth 路径存在；Codex 归档为 129,210,185 bytes，SHA-512 与 `install.py` 固定值一致。Tailscale 实时查询因管理员管道 Access denied 未完成，未把它描述为实时验证。
- 配置装配：`docker compose ... config --quiet` exit 0；PowerShell 导入 `AgentExam.Local.psm1` 后读到 `.env`、`D:\AgentExamData`、端口 55432/59000、Bucket `agentexam-private` 和应用用户 `agentexam-app`；`AgentExam.Initialize.psm1` 可正常导入。
- 静态检查：Ruff 对受影响 Python 测试文件返回 `All checks passed!`；`git diff --check` exit 0，仅报告工作区既有的 LF/CRLF 提示。
- Pytest：沙箱内三次尝试均因默认、工作区或会话临时目录 ACL 拒绝而未完成 Compose 用例，属于测试基础设施失败；在获准的沙箱外使用全新专属 `--basetemp` 最终得到 `10 passed, 7 skipped, 2 warnings in 2.00s`。7 项跳过均为未显式开启的真实本机部署/初始化/重建门禁，本轮没有运行这些有状态检查。
- 项目指标：`AgentExam.Local.psm1` 正好 200 行；受影响 Python 文件均不超过 200 行；`infra/local` 与 `infra/tests` 各保持 8 个文件，没有新增顶层模块或第九个同层文件。
- 未运行：正式 HTTP、Web、Worker、真实模型、业务队列以及现有持久化服务的启停；本轮没有连接或修改现有业务数据。
