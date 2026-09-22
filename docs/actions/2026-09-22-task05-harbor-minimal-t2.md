# 任务 05：固定 Harbor 最小 T2 实证

## 状态与情况

- 状态：**已停止，T2 未通过/未完成**。固定 Harbor 确实创建并启动双网络 Compose 项目，但自带侧车退出码 127，`up --wait` 失败；七组 Trial 断言均未运行。已通过 Harbor 标准路径拆除，项目及本轮标签残留为 0。不据此进入任务 06/07。
- 来源：用户 2026-09-22 本轮授权；硬边界以[负责人机器预案附三](2026-09-21-task05-owner-machine-runbook.md#附三t2-授权增补与执行口径2026-09-22用户确认授权)为准。既有 T1 与静态 Harbor 结论见[上轮报告](2026-09-22-task05-owner-t2.md)，不能当作本轮 T2 通过。
- 工作区：`runtime/lly-dev-verify` 的 `lly/dev`；主工作区并行改动不在本任务范围。固定 Harbor 源码和已安装 Python 环境位于主仓库忽略的 `framework/harbor`，从本 worktree 的命令中复用，不重建或修改。
- 已核实：Harbor 固定提交 `6af8d6e31eced13b93849cdf80feeadf24603d15`；Docker 27.5.1；Debian、Redis、Alpine 探针和当前内容哈希对应的 Harbor 侧车镜像均已缓存；本任务 Compose 项目当前无容器/网络/卷。内核探针固定命令无宿主挂载、发布端口或宿主写入参数。
- 确认的测试接缝：固定 Harbor `DockerEnvironment` + 本次 `TrialPaths` 的 `exec`（命令实在 main 容器内运行），Docker `inspect` 与假上游自己的日志作独立观察。只测此公有运行边界；不接 Codex CLI、真实模型、真实凭据、Worker/Registry，不修改固定 Harbor。若未使用完整 `Trial.run()`，必须在结果中标明，不能把环境层证明扩大为产品闭环。
- 排除：不访问真实 Key/登录文件、不调用真实供应商、不充值、不改共享 Docker/WSL/代理/防火墙或现有服务、不全局 prune、不下载大镜像。仅 Harbor 内核探针可为无名称无标签 `--rm` 容器；其余创建资源须带 `agentexam.task=05` 与本轮唯一 scope。

## 实施措施与完成标准

1. 在 worktree 的 Git 忽略证据目录创建本次 Compose 覆盖文件与薄驱动；只用缓存镜像。预检实际合成 Compose：服务 `main`/`proxy`/`fake-upstream`（如需跨 Trial 哨兵则加 `othertrial`）及 Harbor 侧车均有双标签；网络 `internal` 为 internal=true、`egress` 为受控出网侧，两网络均有双标签；不存在默认第三网络、发布端口、Docker socket 或宿主写入挂载。
2. 在启动前按精确项目名与任务标签查询残留，记录镜像/卷基线。核对 Harbor 构造期 `docker container run --rm` 的实际 argv 只属于固定内核探针且不含硬边界参数；任何越界立即停。
3. 用固定 Harbor Docker 环境创建同一 TrialPaths 下的任务专属 Compose 项目，从 main 容器内执行七组 T1 同语义检查：代理入口、做题侧公网直连拒绝、网关/metadata/其他 Trial/假上游直连拒绝、代理至假上游、无端口/socket/可写宿主挂载、经代理真实转发及假上游来源日志、PID/假文件隔离。结果以实际命令、退出码和 stdout 记录；任一不成立停后续验收，不改断言。
4. 拆除前记录所有镜像和卷清单；仅调用 Harbor 该环境的常规 `stop(delete=True)`，捕获其**实际** Compose argv。拆除后再次记录清单并计算差异，固定仓库镜像和其他项目/成员卷不得删除。按项目名及任务标签独立查容器/网络/卷残留 0；若清理异常，只对已核实属于本次项目且带本轮标签的资源采取精确处理，不全局 prune。
5. 把原始输出、`docker inspect`、镜像/卷差异、清理和未验证项写回本行动。任何硬边界触发时，不扩大授权或把 T1 结果当 T2。

## 受影响文件树

```text
docs/actions/
  2026-09-22-task05-harbor-minimal-t2.md  # 本次行动、实际命令和结果；唯一持久证据索引
.tmp/t05-harbor-minimal/<scope>/           # Git 忽略的本地原始证据，不入库
  extra-compose.yaml                      # Harbor extra_docker_compose；显式双网络与服务/网络双标签
  probe.py                                # 薄驱动；Harbor DockerEnvironment/TrialPaths、命令与快照记录
  *.json / *.txt                          # 原始 inspect、镜像/卷清单、逐项结果、清理输出
framework/harbor/                          # 固定外部框架，只读复用，不改动/重建
```

现有 Adapter/Module/Interface/数据库表不改；只在既有 Harbor Docker 环境边界做一次接受性探针。`extra-compose.yaml` 是 Harbor 的调用方配置，`probe.py` 是测试驱动，两者均非产品网络接线。

## 自验证方式

- `git status`、Harbor revision/工作树、缓存镜像及任务项目残留预检；静态与 `docker compose config` 校验两网络、所有服务/网络标签、无端口和宿主写入挂载；不合格不启动。
- 驱动执行时打印每条 Harbor `exec` 的实际命令、返回码、stdout/stderr，并以假上游日志/`docker inspect` 作独立正对照。七组原有边界都应成立；任何失败原样保留。
- 记录 Harbor 拆除的完整 argv、拆除前后的镜像/卷清单和集合差异；固定镜像与非本次项目卷不得减少。`docker ps/network/volume ls` 按任务标签和精确 Compose 项目双向查询应为空。
- `git diff --check` 与本行动状态核对；未运行或环境失败明确记为未验证，不能称通过。

## 原文要求与本次对应结果

| 原文引用（2026-09-22 用户授权/任务） | 措施与实际结果 |
|---|---|
| “允许 Harbor 构造期创建并自动删除它自己的无名称无标签 --rm 内核探针容器；硬边界：若该命令挂载宿主 Docker 套接字、发布宿主端口或写宿主路径，停下报告” | 实际捕获命令见下；只有 `docker container run --rm <固定 Alpine> sh -c <内核检查>`，无挂载、端口或宿主路径参数。探针返回允许启用侧车。 |
| “用 extra_docker_compose 给 services.main 声明显式网络……定义 internal（internal: true）与 egress” | 合成 Compose 静态预检为两网络：`main → internal`、`proxy → internal + egress`、`fake-upstream/othertrial/Harbor sidecar → egress`；无默认第三网络，五个服务与两网络均声明本轮双标签。实际 `up` 曾创建两网络、五容器，但未取得运行期 inspect。 |
| “把七条断言作为该次 Trial 的命令在真实 Harbor 环境里跑” | **未执行**：`up --wait` 在任何 `env.exec` 之前因 Harbor 侧车退出 127 而报错；不存在七组测试的实际 stdout，不能把 T1 当 T2。 |
| “docker inspect 证据：两条网络的 Internal、各容器 Mounts 与 HostConfig.PortBindings、标签” | **未取得运行期 inspect**：驱动原定在 `env.start` 返回后立即 inspect，但 `up --wait` 先失败；Compose 静态配置与创建日志不能替代 inspect 证据。 |
| “拆除前后各记录一次镜像与卷清单并如实报告差异” | 拆除前后均为镜像 90、卷 16；按完整清单比较，移除 0、新增 0；四个固定镜像均仍在。 |
| “任一硬边界被触发或断言不成立：照实回报并停下” | 本轮没有发现硬边界越界，也没有任何断言失败（因为未运行）；属于 Harbor 启动失败，按停止条件不修改侧车/断言、不重试、不进入后续任务。 |

## 实际执行、输出与原始证据

本轮 worktree `lly/dev`，固定 Harbor 提交 `6af8d6e31eced13b93849cdf80feeadf24603d15`，Docker Server `27.5.1`。驱动入口：

```powershell
& E:/9.1agent_exam/framework/harbor/.venv/Scripts/python.exe .tmp/t05-harbor-minimal/t05-harbor-20260922-01/probe.py
```

首次入口只在启动前缓存校验阶段失败：驱动抄错 Alpine digest，Docker 回报 `No such image`。此时按项目查询容器、网络、卷均为空。修正为固定 Harbor 源码中真实 digest 后，第二次入口的核心实际 stdout：

```text
inventory-before-start: {"images": 90, "volumes": 16}
kernel-probe-command: ["docker", "container", "run", "--rm", "alpine:3.23.4@sha256:5b10f432ef3da1b8d4c7eb6c487f2f5a8f096bc91145e68878dd4a5019afde11", "sh", "-c", "if [ ! -f /proc/config.gz ]; then exit 0; fi; zcat /proc/config.gz 2>/dev/null | grep -qE '^CONFIG_NFT_FIB_INET=[ym]'"]
kernel-support-enabled: true
... docker compose --project-name agentexam-t05-topology ... down --remove-orphans
... docker compose --project-name agentexam-t05-topology ... up --detach --wait
Network agentexam-t05-topology_internal  Created
Network agentexam-t05-topology_egress  Created
Container agentexam-t05-topology-main-1  Started
Container agentexam-t05-topology-proxy-1  Started
Container agentexam-t05-topology-fake-upstream-1  Started
Container agentexam-t05-topology-othertrial-1  Started
Container agentexam-t05-topology-harbor-docker-egress-control-sidecar-1  Started
Container agentexam-t05-topology-fake-upstream-1  Healthy
Container agentexam-t05-topology-main-1  Healthy
Container agentexam-t05-topology-proxy-1  Healthy
Container agentexam-t05-topology-othertrial-1  Healthy
container agentexam-t05-topology-harbor-docker-egress-control-sidecar-1 exited (127)
failure: {"type": "RuntimeError", "started": false, "checks": []}
inventory-before-teardown: {"images": 90, "volumes": 16}
inventory-after-teardown: {"images": 90, "volumes": 16}
cleanup: {"containers": [], "networks": [], "volumes": []}
```

上述 `...` 只用于缩短本页重复的 Compose 文件参数；**完整、逐字 argv 和失败输出**保存在本机忽略证据目录 [harbor-argv.json](../../.tmp/t05-harbor-minimal/t05-harbor-20260922-01/harbor-argv.json) 与 [failure.json](../../.tmp/t05-harbor-minimal/t05-harbor-20260922-01/failure.json)。实际运行期 Trial 命令：**无**；实际运行期 Trial 输出：**无**。本次启动的是 Harbor `DockerEnvironment` + `TrialPaths` 的环境层接受测试，并非完整 `Trial.run()`。

## 网络、身份及清理

静态合成配置（[extra-compose.yaml](../../.tmp/t05-harbor-minimal/t05-harbor-20260922-01/extra-compose.yaml)；非运行期 inspect）：

```text
main ─────────── internal (internal: true) ─────────── proxy
                                                     │
                              egress (internal: false) ├── fake-upstream
                                                     ├── othertrial（同项目替身，非真实跨 Trial）
                                                     └── Harbor 内置侧车
```

`docker compose config` 显示所有服务的 `ports` 与 `volumes` 为 `null`；Redis `/data` 为 tmpfs。运行期容器 `Mounts`、`HostConfig.PortBindings`、网络 `Internal` 和实际标签 **未能 inspect，均列为未验证**。`othertrial` 只是同一项目、只接 egress 的替身，不能代替真实跨 Trial 隔离结论。

本次使用的缓存镜像身份（拆除后仍在）：

| 用途 | 镜像 | Image ID / RepoDigest |
|---|---|---|
| main | `debian:bookworm-slim` | `sha256:db9f02c6bde9fa90cc8074c92754b2b046947392f1a857726e77f041febb7b82` / `debian@sha256:3783cc01769c7b2b1b83a5c5ad96c815348e28ed7da68e2e3687004faa906251` |
| proxy、fake-upstream、othertrial | `redis:7-alpine` | `sha256:487efc0616382465781b8fdc3d6d1db449e6fd80ae23bf48432a2da6b6929908` / `redis@sha256:6ab0b6e7381779332f97b8ca76193e45b0756f38d4c0dcda72dbb3c32061ab99` |
| 内核探针 | 固定 `alpine:3.23.4@sha256:5b10f432…` | `sha256:3cb067eab609612d81b4d82ff8ad71d73482bb3059a87b642d7e14f0ed659cde` / `alpine@sha256:5b10f432ef3da1b8d4c7eb6c487f2f5a8f096bc91145e68878dd4a5019afde11` |
| Harbor 侧车 | `harbor-prebuilt:harbor-docker-egress-control-sidecar--f57c86fb4906508e` | `sha256:29103146a039025e69fafd3f40066272be0b255f97289e0bd840b5eb5f0d9339` / 无 RepoDigest（本地构建标签，未在本轮重建） |

Harbor 标准拆除 **实际调用**（见 `harbor-argv.json`；不存在全局 prune）：

```text
docker compose --project-name agentexam-t05-topology --project-directory E:\9.1agent_exam\runtime\lly-dev-verify\.tmp\t05-harbor-minimal\t05-harbor-20260922-01\environment -f C:\Windows\Temp\tmpsfqoox0u\agentexam-t05-topology-docker-compose-resources.json -f E:\9.1agent_exam\framework\harbor\src\harbor\environments\docker\docker-compose-prebuilt.yaml -f E:\9.1agent_exam\runtime\lly-dev-verify\.tmp\t05-harbor-minimal\t05-harbor-20260922-01\extra-compose.yaml -f C:\Windows\Temp\tmp3gjmf5ij\docker-compose-environment.json -f C:\Windows\Temp\tmp2cti3o7l\docker-compose-mounts.json -f E:\9.1agent_exam\framework\harbor\src\harbor\environments\docker\docker-compose-egress-control.yaml down --rmi local --volumes --remove-orphans
```

拆除前/后的[完整镜像与卷清单](../../.tmp/t05-harbor-minimal/t05-harbor-20260922-01/inventory-before-teardown.json)、[拆除后清单](../../.tmp/t05-harbor-minimal/t05-harbor-20260922-01/inventory-after-teardown.json) 和[逐项差异](../../.tmp/t05-harbor-minimal/t05-harbor-20260922-01/inventory-diff.json)：镜像移除 0/新增 0，卷移除 0/新增 0。项目过滤与 `agentexam.task=05` + 本轮 scope 标签过滤的容器/网络/卷查询均返回空；未删除已有持久化容器、他人卷或固定镜像。

## 失败、偏差和未验证项

1. **阻断失败**：固定 Harbor 内置侧车启动后退出 127；本轮没有保存其退出前日志，具体原因**未知**。静态源码显示入口脚本与 `network-policy`，缓存镜像历史显示已复制文件，但不足以定位运行期原因。没有重建 Harbor 或镜像，没有为通过断言而改侧车。
2. **探针驱动首次预检笔误**：Alpine 摘要抄错，未启动任何项目资源；修正后内核探针实际执行且返回支持。此偏差已保留。
3. 七组断言、假 Key 正对照、假上游自身日志、代理来源 IP、PID/文件隔离及跨 Trial 实证全部**未验证**。尤其不能宣称 T2 通过或 `service.py` 网络接线前置已解除。
4. 缺少运行期 `docker inspect`；仅有启动日志和静态合成配置。无真实供应商请求、真实 Key、充值、大镜像下载或共享 Docker/WSL/防火墙变更。

本行动按停止条件封存为失败记录。后续诊断或重新执行须另开新行动，不反写本次结果。
