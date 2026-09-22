# 任务 05：拓扑探针（纯 Docker 层）

这一层验证任务 05 验收项第 2 项的**前一半**：两组网络能否形成"做题侧只可达代理、只有代理有出网"的边界。
它与 Harbor 无关，因此可以在任何装了 Docker 的机器上跑；**它通过不等于验收通过**——固定 Harbor 是否允许替换它自己的侧车网络附加（后一半）仍须在负责人机器上回答。

## 怎么跑

```bash
# 正常一次（期望 status=verified，退出码 0）
bash apps/backend/tests/providers/runtime/topology-probe.sh

# 反向对照自检：故意把做题侧接进"出网"网络，断言 2、3 必须失败
NEGATIVE_CONTROL=1 bash apps/backend/tests/providers/runtime/topology-probe.sh
```

- 证据写到 `${T05_EVIDENCE_DIR:-$PWD/.tmp/t05-topology}/transcript[-negative-control].txt`（`/.tmp/` 已被 Git 忽略）。
  工具链不健康时改为写 `harness-failure*.txt` 并**中止**，不输出任何断言。
- 假值提供方文件默认用本目录的 `fake-provider.json`，可改：`T05_FAKE_PROVIDER_FILE=/path/to.json`。
- 两个镜像默认 `debian:bookworm-slim`（做题侧）与 `redis:7-alpine`（监听端）；探针在创建资源前确认两者已缓存，缺失时以 `harness-failed` 中止，**不会自动拉取**。若目标机器已有等价镜像，用 `T05_WORKLOAD_IMAGE` / `T05_LISTENER_IMAGE` 指过去（做题侧需要 bash 与 `/dev/tcp`；监听端需能被自身的 `redis-cli` 驱动，且镜像内要有 `redis` 用户——监听端以该用户运行，探针会**从镜像现取它的 uid/gid**来设置 tmpfs 属主，取不到就按 `harness-failed` 中止而不是猜）。
- UID/GID 查询所用的短命容器复用本任务 `fake-upstream` 名称并带任务与本轮 scope 标签。运行前拒绝任何同名已有容器或网络；退出时只清理同时匹配名称、任务标签和本轮 scope 标签的资源，不触碰其他资源。
- **Git Bash（Windows）必须在脚本内保持 `export MSYS_NO_PATHCONV=1`**：否则 MSYS 会把传给容器的绝对路径与 `/dev/tcp` 参数改写成 Windows 路径，探针会返回**假阴性 CLOSED**——看起来像"隔离成立"，是最危险的失败方向。

## 断言清单（对应交接文档第 3.5 节的 7 条）

| # | 断言 | 期望 |
|---|---|---|
| 1 | 做题侧 → 代理固定入口（含 PING/PONG） | 通 |
| 2 | 做题侧 → 公网 | 不通 |
| 3 | 做题侧 → 宿主网关 / 云 metadata / 其他 Trial 网络 / 假上游 | 不通 |
| 4 | 代理 → 假上游 | 通 |
| 5 | 结构：无发布端口、无 Docker 套接字、无可写宿主挂载（最小挂载须记录范围与理由） | 符合 |
| 6 | 正对照：做题侧 → 代理 → 假上游，且假上游**自己的日志**记下"连接来自代理 IP" | 通 |
| 7 | 隔离：做题侧看不到代理的私有假值文件，也看不到代理进程 | 看不到 |
| 附 | 精确清理：按 `agentexam.task=05` 标签复核容器/网络/卷残留 | 0（禁止全局 prune） |

第 7 条的进程检查带**正对照**：同一个扫描在代理侧必须命中（否则 0 无法与"扫描坏了"区分）。第 6 条用常驻 `nc -lk -e` 中继替身——它是 TCP 层替身，**不含 HTTP 语义**，真正的转发形状属 `service.py`。

## 已知实现要点（踩过的坑）

- 监听端以镜像内的 `redis` 用户运行：`--cap-drop ALL` 会让镜像入口脚本的降权步骤失败（`setpriv: setresuid failed`，退出码 127），容器根本起不来。
- 监听端镜像是 Alpine：**没有 bash**，凡是 `docker exec … bash -c` 一律静默失败并读成 CLOSED；用镜像自带的 `redis-cli`。
- redis 会改写自己的进程名（`setproctitle`），所以 PID 标记不能用 redis 的 argv，改用中继脚本路径，且模式写成 `…marke[r]-relay.sh` 以免扫描进程自己命中。

## T2：在 Harbor 建好的容器里只做断言（`t2-assertions.sh`）

T1（上面的探针）**自己创建**容器；T2 的容器由固定 Harbor 创建，所以断言必须在 Harbor 的**做题容器内**执行，另外那些需要 Docker API 的读数（发布端口、宿主挂载、私有文件、清理复核）在跑完后于宿主侧取——分工见[组长机器预案附三/附四](../../../../../docs/actions/2026-09-21-task05-owner-machine-runbook.md)。

```bash
# 在该次 Trial 的做题容器里（把它作为 Trial 的命令），环境变量按该次 compose 的服务名与端口给：
T05_PROXY_HOST=proxy T05_PROXY_PORT=8080 \
T05_UPSTREAM_HOST=fake-upstream T05_UPSTREAM_PORT=8080 \
bash t2-assertions.sh        # 期望 status=verified，退出码 0
```

它覆盖断言 1、2、3、7 中**从做题侧可观测**的部分，并打印原始读数与逐条 PASS/FAIL，与 T1 的 `topology-verdicts.sh` 同一套期望名。**两条硬约束，都来自本机的实测教训**：每个 `/dev/tcp` 检查必须带 `timeout`（否则被封地址会一直挂到内核放弃，吃掉 Trial 的墙钟）；私密标记的扫描必须限定在 `/proc`（递归 grep `/home`、`/etc` 是无界操作，本机烟雾测试里真的把脚本挂住了）。

**本机无法执行它**：本机没有 `framework/harbor`、Docker 守护进程也未运行。已做的验证只有 `bash -n` 与一次本机烟雾运行——后者实测 65 秒完成，并在"有公网、无代理"的宿主上正确报出 `a1`/`a2` 失败（即它不是空过）。真实结果以负责人机器上那一轮的输出为准。

