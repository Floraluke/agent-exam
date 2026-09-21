"""五道候选题的三补丁门禁：参考补丁通过、空补丁不通过、错误补丁不通过。

与 `tests/integration/test_swe_bench_integration.py` 走同一条真实判卷链路（固定 Fork + 真实镜像），
区别是本文件**参数化到五道候选**，并且**镜像身份由本测试注入**——候选在通过门禁前不得写入产品白名单
`FIXED_TASK_IMAGES`，所以这里自带一张待验证表。基础设施失败（抛 `EvaluationError`）不会被当作
"负例正确拒绝"，它直接让用例失败。

默认跳过：需要 Docker 已启动、该题的镜像已按 digest 拉取，并显式设置
`AGENTEXAM_RUN_FORK_INTEGRATION=1`。每个镜像解压后约 2.5–2.8 GB，建议**一次只保留正在验的那一个**。
"""

from __future__ import annotations

import json
import os
import uuid
from pathlib import Path

import pytest

from eval_platform.adapters.evaluation.swe_bench import SWEbenchEvaluator
from eval_platform.adapters.tasks.swe_gym import DATASET_REVISION, SWEGymTaskSource
from eval_platform.application.ports.evaluator import EvaluationRequest
from eval_platform.application.ports.execution import RunLimits

pytestmark = pytest.mark.integration

# 待验证候选及其固定镜像身份（Docker Hub 上唯一的 latest 标签 digest）。
# 门禁通过后才把这些条目移入 src/eval_platform/adapters/tasks/swe_gym.py 的 FIXED_TASK_IMAGES。
PENDING_CANDIDATES = {
    "python__mypy-15131": "xingyaoww/sweb.eval.x86_64.python_s_mypy-15131"
    "@sha256:7fcf8e1c849ffd2a3436c056f9b3b8f1ec0103ed7f429e5001d5f77f64f735c5",
    "python__mypy-15139": "xingyaoww/sweb.eval.x86_64.python_s_mypy-15139"
    "@sha256:a41d688fba76599fcc2bfbfbfe580e864c0c4c6a8ee6ce7edec9b83b34bd0037",
    "python__mypy-15184": "xingyaoww/sweb.eval.x86_64.python_s_mypy-15184"
    "@sha256:affb925329f2dfb2173482c64a1b65648b250777b66b0d7417ee5340fce74835",
    "python__mypy-15208": "xingyaoww/sweb.eval.x86_64.python_s_mypy-15208"
    "@sha256:4fd4bf6ae2d9e6f8b2fe6565018c15b35b9ed7bc1207a9b604b8c82061235c8f",
    "python__mypy-15876": "xingyaoww/sweb.eval.x86_64.python_s_mypy-15876"
    "@sha256:cc465fe939951b1f3ab43bf834b41a9017efc404cc9c9d5ad8b0ff95b90678f1",
}

WRONG = (
    "diff --git a/agentexam_wrong_probe.txt b/agentexam_wrong_probe.txt\n"
    "new file mode 100644\n--- /dev/null\n+++ b/agentexam_wrong_probe.txt\n"
    "@@ -0,0 +1 @@\n+This deliberately does not fix the issue.\n"
)


@pytest.mark.parametrize("kind", ["gold", "empty", "wrong"])
@pytest.mark.parametrize("instance_id", sorted(PENDING_CANDIDATES))
def test_candidate_passes_the_three_patch_gate(kind: str, instance_id):
    if os.environ.get("AGENTEXAM_RUN_FORK_INTEGRATION") != "1":
        pytest.skip("Set AGENTEXAM_RUN_FORK_INTEGRATION=1 for the real Fork probe")
    # 本文件在 tests/catalog/qualification/ 下，比 tests/integration/ 深一层，故上溯 5 级到仓库根
    repo = Path(__file__).resolve().parents[5]
    parquet = repo / "runtime/cache/swe-gym-lite" / DATASET_REVISION / "train-0000.parquet"
    source = SWEGymTaskSource(parquet, None, {instance_id: PENDING_CANDIDATES[instance_id]})
    bundle = source.load(instance_id)
    assert bundle.public.environment_image == PENDING_CANDIDATES[instance_id]

    patches = {"gold": bundle.evaluator.gold_patch, "empty": "", "wrong": WRONG}
    short = instance_id.split("__")[-1]
    run_id = f"qualify-{short}-{kind}-{uuid.uuid4().hex[:8]}"
    # 证据根必须是仓库内 runtime/ 的专属子目录（适配器按项目根生成相对对象引用）
    evidence_root = repo / "runtime" / "fork-evidence"
    evidence_root.mkdir(parents=True, exist_ok=True)
    evaluator = SWEbenchEvaluator(
        repo_root=repo,
        task_source=source,
        evidence_root=evidence_root,
        limits=RunLimits(300, 1, 4096, 8192),
    )

    result = evaluator.evaluate(
        EvaluationRequest(
            run_id,
            bundle.evaluator,
            patches[kind].encode("utf-8"),
            f"qualify-{short}-{kind}",
        )
    )

    # 只有参考补丁能解决；空补丁与错误补丁都必须未解决，且空补丁不算"应用成功"
    assert result.resolved is (kind == "gold"), (instance_id, kind)
    assert result.patch_applied is (kind != "empty"), (instance_id, kind)
    assert (repo / result.report_ref.object_key).is_file()

    # 基础设施收束：容器精确清理、Fork 进程正常退出
    directory = evidence_root / run_id
    cleanup = json.loads((directory / "cleanup.json").read_text(encoding="utf-8"))
    assert cleanup["verified"] is True
    assert cleanup["remaining_ids"] == []
    process = json.loads((directory / "fork-process.json").read_text(encoding="utf-8"))
    assert process["returncode"] == 0
    assert process["warnings"] == []
