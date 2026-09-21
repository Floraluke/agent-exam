"""已通过资格门禁的固定候选：instance_id -> 固定镜像身份（含 digest 与来源）。

只有逐题跑过"参考补丁通过 / 空补丁不通过 / 可应用但错误的补丁不通过"三补丁门禁的题，
才允许登记在这里；未登记的 instance 一律拒绝，也不会被任何镜像"顺带"服务。
门禁证据（含每题镜像 digest、容器清理与 Fork 进程记录）见
`docs/actions/2026-09-19-task-04-catalog-candidates-and-scale.md` 的"04 门禁实跑"一节。
"""

from __future__ import annotations

# 列表内容就是受控白名单：改这里等于改"平台上能选哪些题"，必须附门禁证据。
FIXED_TASK_IMAGES: dict[str, str] = {
    # M0 遗留题：2026-09-08 第四场真实单题已通过，保留原身份与 M0 单题入口
    "python__mypy-15413": (
        "xingyaoww/sweb.eval.x86_64.python_s_mypy-15413"
        "@sha256:f069dfc74592d438ad870bbc6dfb369bff1b125d21237ead49190b414f5f3456"
    ),
    # 以下五题：2026-09-21 在本机按三补丁门禁逐题验证通过（15/15 场景）
    "python__mypy-15131": (
        "xingyaoww/sweb.eval.x86_64.python_s_mypy-15131"
        "@sha256:7fcf8e1c849ffd2a3436c056f9b3b8f1ec0103ed7f429e5001d5f77f64f735c5"
    ),
    "python__mypy-15139": (
        "xingyaoww/sweb.eval.x86_64.python_s_mypy-15139"
        "@sha256:a41d688fba76599fcc2bfbfbfe580e864c0c4c6a8ee6ce7edec9b83b34bd0037"
    ),
    "python__mypy-15184": (
        "xingyaoww/sweb.eval.x86_64.python_s_mypy-15184"
        "@sha256:affb925329f2dfb2173482c64a1b65648b250777b66b0d7417ee5340fce74835"
    ),
    "python__mypy-15208": (
        "xingyaoww/sweb.eval.x86_64.python_s_mypy-15208"
        "@sha256:4fd4bf6ae2d9e6f8b2fe6565018c15b35b9ed7bc1207a9b604b8c82061235c8f"
    ),
    "python__mypy-15876": (
        "xingyaoww/sweb.eval.x86_64.python_s_mypy-15876"
        "@sha256:cc465fe939951b1f3ab43bf834b41a9017efc404cc9c9d5ad8b0ff95b90678f1"
    ),
}

# M0 单题入口保留：这两个名字继续服务既有诊断路径（preflight），不是新题的上车口。
CANDIDATE_INSTANCE_ID = "python__mypy-15413"
CANDIDATE_IMAGE = FIXED_TASK_IMAGES[CANDIDATE_INSTANCE_ID]
