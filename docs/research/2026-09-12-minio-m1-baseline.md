# MinIO：M1 固定基线与最小接入调研

- 核对日期：2026-09-12；范围：MinIO 社区版（CE），不评估替代产品，不切换 AIStor。
- 本文是有日期的官方来源调研快照，候选不等于已批准或已安装。当前依赖决定仍以[依赖总表](../dependencies/DEPENDENCIES.md#23-任务-03-对象存储依赖复核)为准；执行与授权见[任务 03 行动](../actions/2026-09-12-m1-task-agent-catalog.md)。
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
