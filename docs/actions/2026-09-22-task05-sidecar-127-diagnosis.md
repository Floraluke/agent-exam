# 任务 05：Harbor 侧车退出 127 的只读取证

## 状态与情况

- 状态：**已完成诊断并清理**。侧车再次以 127 退出，原始日志明确为入口执行失败 `No such file or directory`；无 DNS 守卫日志，七组 T2 断言未运行。
- 来源：用户 2026-09-22 暂停 `main` 整套复测，改为仅要求在上一轮相同授权范围、相同 Compose 配置下，把 Harbor 的 `up --detach --wait` 改成 `up --detach`，立刻补取侧车 `ps/logs/inspect/image inspect` 原文，再按上一轮路径拆除并复核残留。不得改侧车、配置、网络策略或重跑七组断言。
- 定位：上一轮退出 127 发生在 `lly/dev` 的最小 T2 环境启动阶段；本轮在原 `runtime/lly-dev-verify` worktree 与原 `extra-compose.yaml` 上重现，以便对照同一失败。上轮已结束的行动记录只读；新证据在本文件记录。
- 授权边界：固定 Harbor 只读复用，不重建/拉取镜像；仅原 `agentexam-t05-topology` Compose 项目及已授权的 Harbor 无标签 `--rm` 内核探针；不得挂载宿主 Docker socket、发布宿主端口、写宿主路径、读真 Key 或触发真实供应商请求。只按该项目标准拆除，不删其他镜像/卷/容器，不执行全局 prune。
- 两项待判：原 `probe.py` 是否设置 `_EGRESS_CONTROL_SIDECAR_CONTEXT_PATH`；侧车退出前日志属于命令缺失、`HARBOR_DOCKER_DNS_CONFIG_UNSUPPORTED`，还是其他原因。日志是证据，不能凭退出码猜根因。

## 实施措施与完成标准

1. 确认原 `extra-compose.yaml` 未变、项目残留为空，复用相同 Harbor 构造参数；新诊断驱动只在实际 `up` 命令中删除 `--wait`，不改变 Compose 内容、侧车上下文或 `no-network` 策略。Harbor 临时覆盖文件的随机路径会不同，应如实记录，不能声称逐字相同。
2. 在 `up --detach` 后立即运行用户指定的四类只读查询：`docker ps -a --filter name=egress-control-sidecar`、侧车末尾 40 行日志、侧车 `docker inspect -f`、其镜像 `docker image inspect -f`。保存命令和原始 stdout/stderr；额外只读核对侧车属于本项目且有任务标签。
3. 拆除前后记录镜像/卷清单；仅执行 Harbor 该项目的 `stop(delete=True)` 标准路径；按项目名及本轮标签检查容器/网络/卷均为 0。任何硬边界异常立即停并报告。
4. 只回答诊断问题，不再执行 T2 七组断言或 `main` 整套复测；结论区分确证与推断。

## 受影响文件树

```text
docs/actions/
  2026-09-22-task05-sidecar-127-diagnosis.md    # 本次诊断记录
.tmp/t05-harbor-minimal/t05-sidecar-127-20260922-01/
  diagnose.py                                   # 只去掉 up 的 --wait，取四项证据并清理
  *.json                                        # 原始命令、输出、身份和清理清单；Git 忽略
.tmp/t05-harbor-minimal/t05-harbor-20260922-01/
  extra-compose.yaml                           # 上次调用方配置，只读复用
framework/harbor/                               # 固定依赖，只读复用
```

`diagnose.py` 只是测试接缝；无产品接口、模块、数据库或设计模式变更。

## 自验证方式

- 源码检索 `probe.py` 的侧车上下文设置及 `network.py::export_sidecar()`，明确原环境是否用过 DNS 适配。
- 实际记录四条 Docker 查询原文与输出，不以退出码 127 推断具体命令；保存 Harbor `up/down` 实际 argv。
- 比对拆除前后完整镜像/卷清单，固定镜像和其他成员卷无删除；项目与本轮标签残留 0；`git diff --check`。

## 自验证情况与原始输出

诊断前按项目与 `agentexam.task=05` + `agentexam.scope=t05-harbor-20260922-01` 查询容器、网络、卷均为空。复用原 `extra-compose.yaml`（SHA-256 `29099F9AE8B99A9C7D9C58F3174BD029B1662FB58BF6B6226B12AD96160DBE04`）、原环境目录、`no-network` 策略及固定 Harbor；`DockerEnvironment.start()` 中唯一改变的是把生成的 `up --detach --wait` 实际 argv 改为 `up --detach`。Compose 临时覆盖文件由 Harbor 重建，**随机临时路径与上次不同**；其余项目、镜像、覆盖文件和参数不变。[实际全部 Harbor argv](../../.tmp/t05-harbor-minimal/t05-sidecar-127-20260922-01/harbor-argv.json)保留了完整原文。`up --detach` 返回码 0，创建并启动原项目两网络、五容器；随后立刻取证。

用户要求的四条查询及实际输出原文（`docker logs` 的 stdout/stderr 合并后取末尾 40 行）：

```text
$ docker ps -a --filter name=egress-control-sidecar --format '{{.Names}} {{.Status}}'
agentexam-t05-topology-harbor-docker-egress-control-sidecar-1 Exited (127) Less than a second ago

$ docker logs agentexam-t05-topology-harbor-docker-egress-control-sidecar-1 2>&1 | tail -40
[FATAL tini (7)] exec /opt/egress-sidecar/entrypoint.sh failed: No such file or directory

$ docker inspect -f 'image={{.Config.Image}} entrypoint={{json .Config.Entrypoint}} cmd={{json .Config.Cmd}} exit={{.State.ExitCode}} error={{.State.Error}} oom={{.State.OOMKilled}}' agentexam-t05-topology-harbor-docker-egress-control-sidecar-1
image=harbor-prebuilt:harbor-docker-egress-control-sidecar--f57c86fb4906508e entrypoint=["/opt/egress-sidecar/entrypoint.sh"] cmd=null exit=127 error= oom=false

$ docker image inspect -f '{{json .RepoTags}} {{json .RepoDigests}} {{.Id}}' harbor-prebuilt:harbor-docker-egress-control-sidecar--f57c86fb4906508e
["harbor-prebuilt:harbor-docker-egress-control-sidecar--f57c86fb4906508e"] [] sha256:29103146a039025e69fafd3f40066272be0b255f97289e0bd840b5eb5f0d9339
```

侧车另经只读 `docker inspect` 确认标签 `agentexam.task=05`、`agentexam.scope=t05-harbor-20260922-01`、`com.docker.compose.project=agentexam-t05-topology`。四项完整结构化记录：[ps](../../.tmp/t05-harbor-minimal/t05-sidecar-127-20260922-01/sidecar-ps.json)、[日志](../../.tmp/t05-harbor-minimal/t05-sidecar-127-20260922-01/sidecar-logs.json)、[容器 inspect](../../.tmp/t05-harbor-minimal/t05-sidecar-127-20260922-01/sidecar-inspect.json)、[镜像 inspect](../../.tmp/t05-harbor-minimal/t05-sidecar-127-20260922-01/sidecar-image-inspect.json)。

两个问题的答案：

1. 原[probe.py](../../.tmp/t05-harbor-minimal/t05-harbor-20260922-01/probe.py) **没有设置** `DockerEnvironment._EGRESS_CONTROL_SIDECAR_CONTEXT_PATH`；构造 `DockerEnvironment` 时只传 `extra_docker_compose`、`no-network` 等参数。仓库[network.py](../../apps/backend/src/eval_platform/adapters/execution/network.py) 的 `export_sidecar()`（第 110 行起）没有被调用，故本次使用 Harbor 原生、未做本仓库 M0 DNS 适配的上下文。
2. 本轮日志是 **入口执行失败** 的 `No such file or directory`，**不是** `HARBOR_DOCKER_DNS_CONFIG_UNSUPPORTED`，也不是已运行到 DNS 解析后的错误。镜像标签和 ID 存在；仅凭这四条证据不能再区分镜像内入口文件确实缺失、脚本解释器不可用或换行/构建产物等导致的同类 ENOENT，不能宣称根因已定位。日志直接指向侧车启动基础设施，而非双网络断言失败。

Harbor 标准拆除实际 argv（与上一轮同类 `down`，仅本次临时文件路径不同）：

```text
docker compose --project-name agentexam-t05-topology --project-directory E:\9.1agent_exam\runtime\lly-dev-verify\.tmp\t05-harbor-minimal\t05-harbor-20260922-01\environment -f C:\Windows\Temp\tmptkpel9sv\agentexam-t05-topology-docker-compose-resources.json -f E:\9.1agent_exam\framework\harbor\src\harbor\environments\docker\docker-compose-prebuilt.yaml -f E:\9.1agent_exam\runtime\lly-dev-verify\.tmp\t05-harbor-minimal\t05-harbor-20260922-01\extra-compose.yaml -f C:\Windows\Temp\tmp_2kchpj8\docker-compose-environment.json -f C:\Windows\Temp\tmpx0r3cotl\docker-compose-mounts.json -f E:\9.1agent_exam\framework\harbor\src\harbor\environments\docker\docker-compose-egress-control.yaml down --rmi local --volumes --remove-orphans
```

拆除前后镜像均为 **90**、卷均为 **16**；按镜像身份和卷名称逐项比较，新增/移除均为 **0**。按项目名与本轮任务/scope 标签独立查询容器、网络、卷，全部为空：[清理复核](../../.tmp/t05-harbor-minimal/t05-sidecar-127-20260922-01/cleanup.json)、[清单差异](../../.tmp/t05-harbor-minimal/t05-sidecar-127-20260922-01/inventory-diff.json)。没有重建/拉取镜像、修改侧车/网络配置、执行七组断言或触发真实供应商请求。

本记录到此封存。`main` 整套复测仍暂停；后续修复/适配或再次 T2 运行不是本次诊断授权。
