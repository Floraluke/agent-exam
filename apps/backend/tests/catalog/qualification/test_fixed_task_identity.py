"""固定候选的镜像身份：只有登记过的 instance 能读出，且各题镜像互不共用。

任务 04 把题目目录从"一道题写死"扩展为"已通过门禁的固定候选集"。本文件用**合成
Parquet 快照**验证这条机制（不读真实数据集、不需要容器）：登记映射之外的 instance 一律
拒绝，任何题都不会被别人的镜像"顺带"服务。
"""

import hashlib
import json
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from eval_platform.adapters.tasks.swe_gym import (
    FIXED_TASK_IMAGES,
    DatasetIdentity,
    SWEGymTaskSource,
)

FIRST_IMAGE = "registry.invalid/first@sha256:" + "1" * 64
SECOND_IMAGE = "registry.invalid/second@sha256:" + "2" * 64


def record(instance_id, repo="example/repo"):
    return {
        "instance_id": instance_id,
        "repo": repo,
        "base_commit": "a" * 40,
        "problem_statement": "Fix the visible bug.",
        "version": "1.0",
        "patch": "HIDDEN_GOLD",
        "test_patch": "HIDDEN_TEST",
        "FAIL_TO_PASS": ["hidden_test"],
        "PASS_TO_PASS": ["hidden_pass"],
    }


def build_source(tmp_path: Path, records, images) -> SWEGymTaskSource:
    path = tmp_path / "train-0000.parquet"
    pq.write_table(pa.Table.from_pylist(records), path)
    identity = DatasetIdentity(
        size_bytes=path.stat().st_size,
        sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
    )
    return SWEGymTaskSource(path, identity, images)


def test_each_registered_instance_gets_its_own_fixed_image(tmp_path):
    source = build_source(
        tmp_path,
        [record("example__repo-1"), record("example__repo-2", repo="second/repo")],
        {"example__repo-1": FIRST_IMAGE, "example__repo-2": SECOND_IMAGE},
    )

    first = source.load("example__repo-1")
    second = source.load("example__repo-2")

    assert first.public.environment_image == FIRST_IMAGE
    assert second.public.environment_image == SECOND_IMAGE
    assert second.public.repo == "second/repo"
    # 公开视图只带身份与题面；隐藏判卷数据留在 evaluator 侧
    assert not hasattr(first.public, "gold_patch")
    assert first.evaluator.gold_patch == "HIDDEN_GOLD"
    assert first.evaluator.test_patch == "HIDDEN_TEST"
    assert first.evaluator.fail_to_pass == ("hidden_test",)
    # 摘要按规范化 JSON 重算，可与目录记录逐字比对
    canonical = json.dumps(
        record("example__repo-1"),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    assert first.public.raw_record_sha256 == hashlib.sha256(canonical).hexdigest()
    assert first.raw_record_json == canonical


def test_unregistered_instance_is_rejected_even_when_present_in_the_snapshot(
    tmp_path,
):
    source = build_source(
        tmp_path,
        [record("example__repo-1"), record("example__repo-9")],
        {"example__repo-1": FIRST_IMAGE},
    )

    with pytest.raises(ValueError, match="No fixed M0 image is registered"):
        source.load("example__repo-9")


def test_empty_registry_serves_nothing(tmp_path):
    source = build_source(tmp_path, [record("example__repo-1")], {})

    with pytest.raises(ValueError, match="No fixed M0 image is registered"):
        source.load("example__repo-1")


def test_production_registry_never_holds_an_image_without_a_digest():
    assert FIXED_TASK_IMAGES
    for instance_id, image in FIXED_TASK_IMAGES.items():
        assert instance_id, "候选必须有 instance 身份"
        assert "@sha256:" in image, f"{instance_id} 的镜像未冻结 digest"


def test_dataset_identity_mismatch_is_rejected(tmp_path):
    # 先落一份合法快照，再用不匹配的身份去读它
    build_source(
        tmp_path, [record("example__repo-1")], {"example__repo-1": FIRST_IMAGE}
    )
    path = tmp_path / "train-0000.parquet"
    good_size = path.stat().st_size

    wrong_size = SWEGymTaskSource(
        path,
        DatasetIdentity(size_bytes=good_size + 1, sha256="f" * 64),
        {"example__repo-1": FIRST_IMAGE},
    )
    with pytest.raises(ValueError, match="size does not match"):
        wrong_size.load("example__repo-1")

    wrong_digest = SWEGymTaskSource(
        path,
        DatasetIdentity(size_bytes=good_size, sha256="f" * 64),
        {"example__repo-1": FIRST_IMAGE},
    )
    with pytest.raises(ValueError, match="SHA-256 does not match"):
        wrong_digest.load("example__repo-1")
