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
- 两个镜像默认 `debian:bookworm-slim`（做题侧）与 `redis:7-alpine`（监听端）；若目标机器已有等价镜像，用 `T05_WORKLOAD_IMAGE` / `T05_LISTENER_IMAGE` 指过去，避免为一个探针拉新镜像（做题侧需要 bash 与 `/dev/tcp`，监听端需能被自身的 `redis-cli` 驱动）。
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
