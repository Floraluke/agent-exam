# MinIO：M1 固定基线与最小接入调研

- 历史核对日期：2026-09-12；第 1–5 节保留当时仅评估 MinIO 社区版（CE）的证据与授权边界，不作为当前正式部署选择。2026-09-17 用户已明确采用 **MinIO AIStor Free 修复版方向**，新增官方核对见[第 6 节](#6-2026-09-17aistor-free-修复版方向核对)。
- 本文是有日期的官方来源调研快照，候选不等于已安装。当前依赖决定见[依赖总表第 2.4 节](../dependencies/DEPENDENCIES.md#24-最小本地持久化的部署候选2026-09-17)，当前执行与授权见[持久化行动](../actions/2026-09-17-minimal-local-persistence.md)；历史任务 03 的执行仍见[原行动](../actions/2026-09-12-m1-task-agent-catalog.md)。
- 本次只读网页与源码、编写本文；未下载可执行制品、安装依赖、构建或启动容器，未运行模型、漏洞利用或业务测试。

## 1. 已查证的版本身份

| 对象 | 固定身份 | 意义与限制 |
| --- | --- | --- |
| 最后正式 CE release | `RELEASE.2025-10-15T17-29-55Z`；commit `9e49d5e7a648f00e26f2246f4dc28e6b07f8c84a` | Release 发布于 2025-10-16；修复当时的会话策略权限提升，但不是 2026 年通告的修复版。 |
| 归档主分支源码候选 | commit `7aac2a2c5b7c882e68c1ce017d8256be2feea27f`，提交日期 2026-02-12 | 比最后 release 多 11 个提交；不是新的 release tag，需自己构建并记录制品身份。 |

出处：[正式 release](https://github.com/minio/minio/releases/tag/RELEASE.2025-10-15T17-29-55Z)、[release commit](https://github.com/minio/minio/commit/9e49d5e7a648f00e26f2246f4dc28e6b07f8c84a)、[GitHub release 元数据](https://api.github.com/repos/minio/minio/releases/latest)、[归档提交](https://github.com/minio/minio/commit/7aac2a2c5b7c882e68c1ce017d8256be2feea27f)、[发布后提交比较](https://github.com/minio/minio/compare/RELEASE.2025-10-15T17-29-55Z...master)。元数据的 `assets` 为空，不能把 GitHub 自动生成的源码压缩包当作官方服务器二进制；本次没有确认可拉取的对应 CE 镜像摘要。

源码候选包含两个与 M1 直接相关的发布后修复：2025-10-24 的[读取 quorum 不足时拒绝条件写入](https://github.com/minio/minio/commit/18f97e70b19db6b2940ae8a1b14c4665d2eeca36)，以及[避免一次请求发送重复响应](https://github.com/minio/minio/commit/52eee5a2f19ea8ef06bf2dd5ab64ab41424cb591)。前者避免“无法确认对象存在”被误当成“对象不存在”。因此本调研建议：若批准隔离测试，优先固定上述归档源码提交，而非只因 release 有名称就忽略后续修复。

## 2. 已知安全限制，不是安全保证

官方仓库于 2026-04-25 归档，并声明停止维护。归档不等于软件不能运行；固定源码也不等于漏洞已经修复。[官方仓库说明](https://github.com/minio/minio)

最后 CE release 修复了 2025-10-16 发布的[会话策略权限提升通告](https://github.com/minio/minio/security/advisories/GHSA-jjjj-jwhf-8rgr)。2026 年又有以下官方通告，补丁说明指向 AIStor，不可据其版本号声称社区版已修复：

| 官方发布日期 | 通告及本次相关性 |
| --- | --- |
| 2026-04-14 | [GHSA-hv4r-mvr4-25vw](https://github.com/minio/minio/security/advisories/GHSA-hv4r-mvr4-25vw)：知道有效 access key 即可能绕过签名写入；受影响范围从 2023-05-18 发行起，包含 CE 最后正式发行。 |
| 2026-04-11 | [GHSA-9c4q-hq6p-c237](https://github.com/minio/minio/security/advisories/GHSA-9c4q-hq6p-c237)：Snowball 自动解包上传缺少签名校验。 |
| 2026-04-07 | [GHSA-h749-fxx7-pwpg](https://github.com/minio/minio/security/advisories/GHSA-h749-fxx7-pwpg)：S3 Select CSV 解析可能无界分配内存。 |
| 2026-03-27 | [GHSA-3rh2-v3gr-35p9](https://github.com/minio/minio/security/advisories/GHSA-3rh2-v3gr-35p9)：复制相关加密元数据注入可使对象不能正常读取。 |
| 2026-03-19／20 | [OIDC 算法混淆](https://github.com/minio/minio/security/advisories/GHSA-5cx5-wh4m-82fh)、[LDAP 枚举／暴力尝试](https://github.com/minio/minio/security/advisories/GHSA-jv87-32hw-hh99)：与启用的外部身份功能有关，M1 测试不需要它们。 |
| 2026-04-25 | [GHSA-xh8f-g2qw-gcm7](https://github.com/minio/minio/security/advisories/GHSA-xh8f-g2qw-gcm7)：节点间文件读取路径穿越；官方明确单节点 standalone 不注册该路由，不受此项影响。 |

不是仅凭“没有新 tag”推断源码没有修复：归档提交的[PutObject 源码](https://raw.githubusercontent.com/minio/minio/7aac2a2c5b7c882e68c1ce017d8256be2feea27f/cmd/object-handlers.go)仍保留 GHSA-hv4r-mvr4-25vw 指出的、依据是否存在 Authorization 头决定 unsigned-trailer 签名校验的调用。结合通告，至少这条已知风险不能因采用 master 源码而关闭；本次不是逐项漏洞审计，没有运行攻击验证。

官方针对部分通告提出阻断 unsigned-trailer 请求、限制危险入口等缓解建议；客户端自己不发送这些请求，不能阻止其他客户端利用服务器漏洞。本次不据此新增代理服务、改防火墙或补丁维护分支。

CE 源码采用 AGPLv3；AIStor 是另一个发行／许可边界。仓库中的 AIStor Free 链接当前跳转到[AIStor 下载与许可证入口](https://www.min.io/download)，不能推断项目已有许可证，也不能静默拉取 `minio/aistor` 代替 CE。本文不提供许可证合规结论。

## 3. 获取、构建与运行：候选，尚未执行

官方 release 指引是获取官方仓库源码、切到固定版本后构建，不是给出该 release 的现成容器。必须核对 checkout 的完整 commit；不使用浮动 `latest`，不采用第三方重打包镜像。[release 构建说明](https://github.com/minio/minio/releases/tag/RELEASE.2025-10-15T17-29-55Z)

最小候选路径：

1. 获批后取得官方源码固定 commit；保留源码身份与构建记录。准备固定摘要的可信 Go 构建环境，生成 Linux 目标二进制。该提交的[go.mod](https://raw.githubusercontent.com/minio/minio/7aac2a2c5b7c882e68c1ce017d8256be2feea27f/go.mod)声明 `go 1.24.0`、`toolchain go1.24.8`；这不是对旧工具链当前安全性的认可。实际工具链选择、依赖可获取性与构建成功均待核对。
2. 只封装这个自产二进制用于本机测试。最后 release 的[Dockerfile](https://raw.githubusercontent.com/minio/minio/9e49d5e7a648f00e26f2246f4dc28e6b07f8c84a/Dockerfile)继承浮动 `minio/minio:latest`；[Makefile](https://raw.githubusercontent.com/minio/minio/9e49d5e7a648f00e26f2246f4dc28e6b07f8c84a/Makefile)的 `make docker` 会使用它，不能原样当成完全固定构建。官方还提供[极简 Dockerfile.scratch](https://raw.githubusercontent.com/minio/minio/9e49d5e7a648f00e26f2246f4dc28e6b07f8c84a/Dockerfile.scratch)，证明不必继承旧 MinIO 二进制镜像；后续可参考其封装方式，固定构建输入并验证所选 commit 的材料。
3. 构建后记录实际二进制 SHA-256、镜像 ID／摘要、工具链与源码 commit，再运行专属合成测试。当前这些制品身份全部未知，不能先填一个猜测摘要。

可能需要联网访问官方 GitHub 源码、Go 工具链／模块代理及校验服务、可信构建镜像仓库；实际下载清单与摘要须在执行前固定。Git、Linux Go 编译环境、容器构建工具为必要能力；不要求在 Windows 全局安装新 Go，也不批准更改已有 Docker、代理或网络设置。本次没有验证下载、镜像拉取或构建可用性。

### 运行隔离建议

只建议用于短生命周期、合成数据的接口集成测试，不是长期、远程团队或正式部署基线。测试时非 root、限制 CPU／内存／进程数、移除多余能力、不挂载 Docker socket／用户目录／真实数据、不使用默认凭据、不启用 LDAP／OIDC／复制等无关功能。数据使用专属临时空间，结束按精确身份清理。这些限制降低影响范围，不能修复组件漏洞。

不能单凭 `-p 127.0.0.1:...` 声称严格隔离：Docker 官方提示 **28.0.0 之前**的引擎可能允许同一二层网络的其他主机访问绑定 localhost 的发布端口；具体本机适用性仍需实查，不能由文档直接断言已经暴露。[Docker 端口发布说明](https://docs.docker.com/engine/network/port-publishing/)

更小暴露面的候选是**不发布端口，运行时使用 `--network none`，MinIO 与测试进程在同一隔离网络命名空间的回环地址通信**。Docker 说明该模式只提供容器内部 loopback；双存储测试需把专属 PostgreSQL、MinIO、测试器的通信放进同一隔离安排，不连接现有数据库，也不暗中改主机网络。[Docker none 网络说明](https://docs.docker.com/engine/network/drivers/none/)

此方案在技术上可作为任务 03 局部真实集成验证的候选；尚未证明在本机可运行，仍需明确授权取得构建材料与创建／清理专属环境。它不能替代正式部署的安全、维护和恢复验收。

## 4. 最小对象接口的源码证据与验收要求

| 接口／性质 | 已查证证据 | 尚需实测 |
| --- | --- | --- |
| 不覆盖创建 | 最后 release 的[条件检查](https://raw.githubusercontent.com/minio/minio/9e49d5e7a648f00e26f2246f4dc28e6b07f8c84a/cmd/object-handlers-common.go)将 `If-None-Match: *` 匹配已有对象并返回 PreconditionFailed；[PUT handler](https://raw.githubusercontent.com/minio/minio/9e49d5e7a648f00e26f2246f4dc28e6b07f8c84a/cmd/object-handlers.go)把此检查传入对象层。 | 两个并发请求争抢同一 key，只能一个创建成功；不得靠 HEAD 后 PUT 实现“先查再写”。 |
| 并发／故障 | 归档提交的[对象层](https://raw.githubusercontent.com/minio/minio/7aac2a2c5b7c882e68c1ce017d8256be2feea27f/cmd/erasure-object.go)在条件检查前取得对象锁，持有到该次写结束；无法可靠读取元数据时返回错误。 | 同内容重试、异内容冲突、超时不确定结果、存储读取失败；不把未知当作不存在。 |
| GET／HEAD | [MinIO handler](https://raw.githubusercontent.com/minio/minio/7aac2a2c5b7c882e68c1ce017d8256be2feea27f/cmd/object-handlers.go)提供对象读取与只读元数据入口。 | 缺失、权限拒绝、流截断、字节被改与资源关闭。HEAD 元数据不能证明完整内容正确。 |

`If-None-Match` 不是存储级永久防篡改：不用此条件的获授权写入、删除后重建、版本删除标记等需要另行限制。M1 候选最小契约应避免任意覆盖／删除入口；对象 key 与内容身份要由服务端产生，已有 key 冲突时读取并核对完整长度及 SHA-256，不能仅因收到 412 就当作成功。

Python 的 AWS 官方 Boto3 公共 API 已提供 `put_object(IfNoneMatch='*', Body=..., ContentLength=...)`，无需私有方法或手写签名；也提供 `get_object` 和 `head_object`。此结论是客户端能力，不是“所有 AWS 特性在 MinIO 都相同”。SDK 版本必须单独固定并与候选服务器联测。[Boto3 PUT](https://docs.aws.amazon.com/boto3/latest/reference/services/s3/client/put_object.html)、[GET](https://docs.aws.amazon.com/boto3/latest/reference/services/s3/client/get_object.html)、[HEAD](https://docs.aws.amazon.com/boto3/latest/reference/services/s3/client/head_object.html)

M1 原始 JSON 快照可以候选采用已知长度、可重读字节的一次 PUT，避免提前引入分片上传。上传前计算 SHA-256；传输校验可使用公共 ContentMD5／ChecksumSHA256 参数并实际验证兼容性，ETag 不作为项目 SHA-256 身份替代。遇 409／超时只做有界重试／查证，不改成无条件 PUT。[Boto3 PUT 参数及条件冲突语义](https://docs.aws.amazon.com/boto3/latest/reference/services/s3/client/put_object.html)

下载时用有上限的分块读取，边读边累计字节和 SHA-256，到 EOF 后再判断内容完整；所有成功／失败分支关闭响应。Botocore 的 StreamingBody 提供分块、长度校验与 close，但项目仍需按可信 ArtifactRef 校验哈希，不能只相信对象附带元数据。[StreamingBody 公共接口](https://docs.aws.amazon.com/botocore/latest/reference/response.html)

客户端可显式配置路径式寻址、SigV4、连接／读取超时和有界重试。较新 SDK 的默认校验／流式编码会影响报文；可核验 `request_checksum_calculation='when_required'` 与 `payload_signing_enabled` 的组合，实测实际发送的签名与校验格式。这是兼容性措施，不是 MinIO 漏洞补丁。[Botocore Config](https://docs.aws.amazon.com/botocore/latest/reference/config.html)

## 5. 本次验证结果与未完成项

- 已实际读取上列官方发布、通告、固定 commit 源码和公共 SDK 文档；逐条区分来源事实与方案推论。
- GitHub 动态 compare 的文件 diff 未完整渲染，已使用具体修复 commit 与固定源码核对关键路径。部分 raw／API 页面打开失败；本机 PowerShell 的两个只读 GitHub API 请求也被套接字权限阻止，没有据此改网络。失败不构成服务故障或构建失败证据。
- 未完成：构建环境摘要、二进制／镜像摘要、所选 SDK 固定版本、隔离运行可行性、真实并发与流式校验、PostgreSQL／MinIO 单侧失败发布测试、正式部署风险处置。
- 结论：可以继续保留 MinIO 与既有架构分层；推荐讨论“固定归档 CE 源码，仅作隔离合成测试”的明确边界。不能把候选、源码阅读或一般 S3 文档当作任务 03 已验收。

## 6. 2026-09-17：AIStor Free 修复版方向核对

本节是用户确认新方向后的官方证据快照；实施及验收状态只在[持久化行动记录](../actions/2026-09-17-minimal-local-persistence.md)维护。本次仅读取公开网页、发行元数据和页面脚本、更新本文；没有获取许可证、提交表单、注册/登录账号、接受条款、下载软件制品、拉取镜像或运行容器。

### 6.1 具体发行候选与尚未取得的镜像身份

截至核对时，[官方最新发行 API](https://dl.min.io/api/releases/aistor/latest)返回 AIStor Server，`release_date=2026-09-08T05:05:14Z`，Docker 下载说明指向 **`quay.io/minio/aistor/minio:RELEASE.2026-09-07T08-39-31Z`**。固定[发行说明](https://dl.min.io/aistor/minio/release/notes/release-notes-RELEASE.2026-09-07T08-39-31Z.md)自述发布日期为 2026-09-07；这是制品版本时间与发布元数据时间的区别，不应混写。[发行索引](https://dl.min.io/aistor/minio/release/notes/)与[官方 Helm 镜像表](https://docs.min.io/aistor/reference/kubernetes/object-store-operator-helm-chart/)相互印证该 tag 和官方仓库路径；本项目不引入 Helm。

- 选择标准版，不因示例存在而启用 RDMA/FIPS 等无关变体；不采用浮动 `latest`，也不把 4 月漏洞通告里的最低修复版误当当前最新版。
- **未验证**：仓库实际可拉取性、镜像清单 SHA-256、Linux/amd64 平台清单摘要、容器内实际版本与运行用户。tag 有官方出处，但还不是项目已固定且验收的镜像身份；部署前须按审批取得、记录并核对这些证据，不能猜填摘要。
- 9 月发行说明另外列出 IAM/STS 授权与凭据绑定、管理接口信息泄漏、请求体/内存边界等加固，并更新若干依赖。说明明确部分问题编号后续另发，因此本节不能宣称“所有漏洞均已修复”；也没有运行制品漏洞扫描或攻击验证。[该版安全说明](https://dl.min.io/aistor/minio/release/notes/release-notes-RELEASE.2026-09-07T08-39-31Z.md)

### 6.2 与既有 CE 风险逐项对应

下表记录官方针对第 2 节所列 2026 年通告给出的 AIStor 修复身份。9 月候选晚于这些修复发行，按官方受影响/修复范围属于包含修复的后续发行；这是**官方版本范围结论**，不是本项目对尚未取得的二进制完成了逐项验证。

| 已记录风险 | 官方 AIStor 修复身份及边界 |
| --- | --- |
| unsigned-trailer 查询参数凭据绕过签名写入 | `RELEASE.2026-04-11T03-20-12Z`；这是此前阻止旧 CE 正式部署的 High/8.8 风险。[通告](https://github.com/minio/minio/security/advisories/GHSA-hv4r-mvr4-25vw) |
| Snowball 自动解包缺少签名校验 | `RELEASE.2026-04-11T03-20-12Z`。[通告](https://github.com/minio/minio/security/advisories/GHSA-9c4q-hq6p-c237) |
| S3 Select CSV 无界内存分配 | `RELEASE.2025-12-20T04-58-37Z`。[通告](https://github.com/minio/minio/security/advisories/GHSA-h749-fxx7-pwpg) |
| 复制头注入加密元数据，破坏对象可读性 | `RELEASE.2026-03-26T21-24-40Z`；普通 PUT 也可能进入旧漏洞路径，不能只因本项目不开复制就忽略。[通告](https://github.com/minio/minio/security/advisories/GHSA-3rh2-v3gr-35p9) |
| LDAP 用户枚举/暴力尝试 | `RELEASE.2026-03-17T21-25-16Z`；本项目仍不启用 LDAP。[通告](https://github.com/minio/minio/security/advisories/GHSA-jv87-32hw-hh99) |
| OIDC JWT 算法混淆 | `RELEASE.2026-03-17T21-25-16Z`；本项目仍不启用 OIDC。[通告](https://github.com/minio/minio/security/advisories/GHSA-5cx5-wh4m-82fh) |
| 节点间 ReadMultiple 路径穿越 | 通告推荐 `RELEASE.2026-04-14T21-32-45Z` 或之后；正文另说明相关路由自 AIStor `RELEASE.2024-10-23T19-38-07Z` 已移除，单节点 standalone 本身也不注册该路由。不把推荐升级时间说成首次修复时间。[通告](https://github.com/minio/minio/security/advisories/GHSA-xh8f-g2qw-gcm7) |

### 6.3 Free 许可证：用户必须完成的步骤与已知期限

**Free 不是下载页默认展示的两个月 Trial。** [定价页](https://www.min.io/pricing)单列 Free 单节点免费档；[下载页](https://www.min.io/download)展示两个月试用入口，不能点到试用后把它当长期免费许可证。

建议用户操作顺序：

1. 自行阅读 [AIStor Free Agreement](https://www.min.io/legal/aistor-free-agreement)及其隐私政策链接。协议说明下载、安装或使用即表示接受；用户目前确认的是产品方向，代理不能替用户接受这些条款。该协议为专有软件的单节点使用许可，列举教育/个人项目等用途，禁止向第三方重新分发软件；本记录不作法律合规保证。
2. 打开[定价页](https://www.min.io/pricing)，选择 **Free → Get Started Free**，由用户自行填写/提交许可证申请。官方[实验室教程](https://www.min.io/blog/building-a-rag-lab-with-aistor-and-milvus)描述填写姓名和工作邮箱、邮件收取许可证；本次实时公开页脚本也定位到 Free 专用表单，读取 firstname、lastname、email 并调用官方邮件接口。本次没有执行脚本或提交信息；表单当前哪些字段必填、个人邮箱能否通过、实际邮件时延仍未验证，不凭旧博客“no sign-up”断言现在无需信息或账号。
3. 收到后自行保存 `minio.license`，只把**文件路径**告知代理，不把文件正文、许可证令牌、账号密码贴到聊天或 Git。若已有 SUBNET 账户，官方路径是登录后 **Deployments → License Key → Download**；这是一条可用路径，不代表每个 Free 新用户都必须先单独注册 SUBNET。[许可证取得说明](https://docs.min.io/aistor/operations/licenses/)
4. 后续专属部署中核对计划确为 Free、并非 Trial、`Expiry` 为 `N/A`。官方 `mc license info` 明确 **Free 不到期**；其完整输出可能含 License ID/API Key，验收只能记录必要的脱敏状态，不能整段打印或落盘。[许可证状态接口](https://docs.min.io/aistor/reference/cli/mc-license/mc-license-info/)

离线边界：官方 Docker 流程允许把已取得的许可证文件直接挂入容器；官方也提供隔离环境注册流程，说明部署不必持续直连 SUBNET，但首次许可证取得仍需要联网设备。`mc license register --airgap --license ...` 会生成需在联网浏览器打开的 URL，并会关联部署信息；本项目不得把注册或上传部署资料作为隐式启动副作用。Free 不到期与“无许可证时的 offline mode”是两件事：后者表示 S3 读写被禁用，并非“正常无网运行”。没有有效许可证不能用健康端口可访问冒充对象服务可用。[隔离环境注册接口](https://docs.min.io/aistor/reference/cli/mc-license/mc-license-register/)、[许可证运行模式](https://docs.min.io/aistor/operations/licenses/)

### 6.4 Docker 接入与本项目能力边界

[官方容器说明](https://docs.min.io/aistor/installation/container/install/)确认接口：把宿主许可证文件挂为容器内文件，并向服务器传 `minio server <数据目录> --license <许可证文件>`。例如容器路径 `/minio.license` 是可选约定，不是许可证内容；本项目可在已批准部署配置中将许可证作为只读文件挂载。数据目录仍须绑定已确认的 D 盘专属目录；官方示例中的默认密码、浮动镜像与对所有网卡公开的端口不能直接照搬。

Free 的单节点限制适合当前“一个主机保存数据、五人协作”的拓扑，不等于只能一个业务用户。基本 S3 读写是候选能力，仍须用现有 Adapter 验证 `PutObject` 条件创建、GET/HEAD 与 SHA-256；不能仅因兼容 S3 就判定当前客户端通过。官方明确 Free 不含多节点、各种复制、对象分层/生命周期迁移、指定版本删除及部分诊断/支持功能；因此不能把内置复制设计为此次备份入口。[Free 功能限制](https://docs.min.io/aistor/operations/licenses/#minio-aistor-free-community-use)、[对象 API 兼容说明](https://docs.min.io/aistor/developers/s3-api-compatibility/)

### 6.5 本次检查结果与最小后续

- 已核对：官方精确发行 tag、七项既有通告的修复对应、当前免费档/条款、Free 不到期、公开申请入口与容器许可证参数。保留历史 CE 内容，不改旧测试已发生的事实。
- 网页工具无法读取部分动态表单、release API 和原始发行说明；普通 PowerShell HTTP 被沙箱 socket 权限阻止。首次只读提权审批超时，按提示重试一次获准，随后仅在内存读取公开 API/HTML；这不是镜像拉取、许可证申请或部署成功的证据。固定发行说明页面内嵌 Markdown 的安全段已读取，未据此声称整包安全审计完成。
- 下一步由用户自行取得并接受 Free 许可证；代理只需要私有文件路径，不需要许可证正文。后续按主行动审批取得固定镜像并记录实际摘要/版本，完成合成数据读写、容器重建、备份/隔离恢复与 D 盘验收。许可证未就绪时不回退旧 CE，也不改用短期 Trial 冒充已满足长期持久化。
