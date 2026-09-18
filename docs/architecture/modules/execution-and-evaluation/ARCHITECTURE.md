# 执行与判卷 Module

> 当前状态：固定 Codex → Harbor → patch → 固定 SWE-Bench-Fork 的真实单题核心闭环已通过；M1 任务 13 又把正式 Job/Run、持久化与 Worker 接到该链路。完整安全/生命周期验收和新提供方仍未完成。
> 权威范围：Worker 如何把冻结 Run 交给执行后端和独立判卷器；外部框架和认证细节仍由专题 Interface 维护。

## 1. 职责与非职责

本 Module 在 owner 电脑上执行已获批准且已领取的冻结 Job。它把平台 Run 转成一个 Harbor Job 中的 Trial，获取受控执行结果和 patch，再把同一 patch 交给固定 SWE-Bench-Fork 的干净环境独立判卷。

Harbor 只回答“Agent 怎样运行、返回什么”；`PatchEvaluator` 才回答“该 patch 是否应用成功、固定测试是否解决”。Agent 自述、Harbor reward、Judge 或页面文案都不能覆盖确定性判卷事实。

## 2. Interface 与不变量

- `ExecutionBackend.execute(ExecutionJobRequest, progress)`：执行登记 Run 并返回规范化 `ExecutionTrialResult`；不决定 `resolved`。
- `ExecutionProgressObserver`：每个 Trial 开始/结束时与持久状态同步；取消可阻止后续 Trial 开始。
- `PatchEvaluator.evaluate(EvaluationRequest)`：在独立环境应用同一 patch 并返回 `DeterministicResult`。
- `JobExecutor.execute(ClaimedJob)`：应用层编排一整个冻结矩阵、证据校验、判卷和终态。
- 当前一平台 Job 对应一 Harbor Job，一 Run 对应一 Trial；重型并发为 1，每组合一次尝试，零自动重试。

请求字段、错误、制品和状态细节见[模块契约](../../MODULE_CONTRACTS.md)；Harbor 映射见[Harbor Interface](../../../interfaces/HARBOR_EXECUTION.md)，框架调用见[框架 Interface](../../../interfaces/FRAMEWORK_INTERFACES.md)。

## 3. 当前 Implementation 文件树

```text
apps/backend/src/eval_platform/
  application/
    execute_job.py                         # 冻结矩阵 → ExecutionBackend → 判卷/终态编排
    execution/batch.py                    # Trial 进度、取消协作和批次收束
    execution/run_results.py              # patch 校验、独立判卷、失败分类
    execution/completion.py               # 可信结果、指标和制品索引组装
    ports/execution.py                     # ExecutionBackend / ProgressObserver Interface
    ports/evaluator.py                     # PatchEvaluator Interface
  adapters/execution/
    harbor/adapter.py                      # Harbor ExecutionBackend Adapter
    harbor/config_mapper.py                # 平台请求 → 固定 Harbor 配置
    harbor/process_runner.py               # 有界子进程与日志采集
    harbor/process_evidence.py             # 进程证据归一化
    harbor/result_mapper.py                # Harbor 结果 → 平台 Trial 结果
    harbor/artifacts.py / result_values.py # Harbor 制品和值解析
    harbor/lifecycle/                      # 启动、监控、超时和精确资源清理
    harbor_entry.py                        # Harbor 子进程 Composition Root
    codex/agent.py                         # 固定上游 Codex 的窄 Adapter
    codex/install.py                       # 固定离线 CLI 校验与安装
    codex/policy.py                        # 非 root、命令和运行策略
    codex/uploads.py                       # 受限私有认证输入传递
    network.py                             # 固定 Harbor 侧车网络策略副本适配
    preflight.py                           # 外部输入身份与运行前门禁
    redaction.py                           # 执行诊断的受限错误归一化
  adapters/evaluation/
    swe_bench.py                           # 固定 SWE-Bench-Fork PatchEvaluator Adapter
    process.py / fork_entry.py             # 有界独立判卷进程和入口
    result_mapper.py                       # Fork report → DeterministicResult
  delivery/worker/
    runtime.py                             # 正式 owner 本机 Worker Composition Root
    main.py                                # 一次 claim 后委托 JobExecutor 的薄 shell
framework/
  harbor/                                  # 固定 revision 的外部执行框架源码/环境
  swe-bench-fork/                          # 固定 revision 的独立判卷框架源码/环境
```

`framework/` 不是项目自有业务 Implementation；项目通过 Adapter 使用固定版本，不直接把上游对象泄漏给应用层。

## 4. 关键数据流

```text
PostgreSQL claim 冻结 Job
  → JobExecutor 还原公开题目与固定 Agent Configuration
  → HarborExecutionAdapter 建一个 Harbor Job
  → 每个 Trial 在受限 Docker 环境运行 Agent
  → 校验 patch 身份、大小与摘要
  → SWEbenchEvaluator 在网络关闭的干净环境应用同一 patch
  → 规范化确定性结果、指标和证据
  → JobRepository 原子推进 Run/Job 状态
```

Worker 只从 owner 本机绝对路径读取固定 framework、数据集、Codex 归档和认证引用；这些秘密路径不进入 Job、HTTP、PostgreSQL 或 MinIO。

## 5. 模式、依赖和深度

`ExecutionBackend` 与 `PatchEvaluator` 是两个有真实替换价值的 seam：执行后端可以换 Adapter，而最终判卷仍独立；合成 Adapter 也能在不启动真实模型时测试应用流程。Harbor 和固定 Fork 的复杂配置、子进程、网络、超时与清理被隐藏在各自 Adapter 内。

Composition Root 在 `delivery/worker/runtime.py`，不是应用用例内部临时创建外部依赖。执行 Module 从 Job Control 接受冻结输入，向 Evidence/Reporting 交付受校验的结果和制品引用；它不依赖 Web。

## 6. 当前验证、风险和规划

M0 第四场真实结果见[M0 行动](../../../actions/2026-09-05-m0-codex-harbor-implementation.md)；M1 正式持久化链见[本机真实验收行动](../../../actions/2026-09-13-m1-local-real-acceptance.md)。这些是历史证据，本轮没有运行 Docker、Harbor、Fork 或模型。

现存限制包括：完整故障/强杀/刷新生命周期未全验收；当前真实提供方只有 owner ChatGPT 登录；DeepSeek/Kimi 的隔离代理只是候选；owner 电脑离线不执行。新提供方应深化现有 Execution Adapter 内部实现，不新增第二套 Job 队列或判卷器；详情见[认证 Interface](../../../interfaces/CODEX_AUTHENTICATION.md)。
