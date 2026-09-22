"""Linux bridge: adapt infrastructure only, then execute the fixed Fork CLI."""

from __future__ import annotations

import hashlib
import importlib.metadata
import json
import re
import runpy
import sys
from pathlib import Path
from typing import Any


def run(profile_path: Path, arguments: list[str]) -> None:
    import docker  # type: ignore[import-untyped]
    import swebench.harness.docker_build as build  # type: ignore[import-not-found]

    profile = json.loads(profile_path.read_text(encoding="utf-8"))
    _record_runtime(profile)
    client = docker.from_env()
    image = _fixed_image(client, profile)
    # These are the only replaced upstream functions. Grading stays upstream.
    build.build_env_images = _prepare_images(build, profile)
    build.build_container = _create_container(image, profile)
    sys.argv = ["swebench.harness.run_evaluation", *arguments]
    try:
        runpy.run_module("swebench.harness.run_evaluation", run_name="__main__")
    finally:
        client.close()


def _record_runtime(profile: dict[str, Any]) -> None:
    lock_path = Path(__file__).resolve().parents[4] / "swebench-requirements.txt"
    lock = lock_path.read_bytes()
    if hashlib.sha256(lock).hexdigest() != profile["requirements_sha256"]:
        raise RuntimeError("Fork dependency lock changed after submission")
    packages = {}
    for name, version in re.findall(r"(?m)^([A-Za-z0-9_-]+)==([^\s]+)", lock.decode()):
        actual = importlib.metadata.version(name)
        if actual != version:
            raise RuntimeError(f"Fork dependency differs from lock: {name}")
        packages[name] = actual
    Path("runtime.json").write_text(
        json.dumps({"python": sys.version, "packages": packages}, indent=2),
        encoding="utf-8",
    )


def _fixed_image(client: Any, profile: dict[str, Any]) -> Any:
    image = client.images.get(profile["image"])
    if image.attrs["Architecture"] != "amd64" or image.attrs["Os"] != "linux":
        raise RuntimeError("The fixed task image must be Linux amd64")
    if image.attrs["Config"].get("Volumes"):
        raise RuntimeError("Implicit image volumes are not allowed")
    return image


def _check_spec(profile: dict[str, Any], spec: Any) -> None:
    if (spec.instance_id, spec.repo, spec.version) != (
        profile["instance_id"],
        profile["repo"],
        profile["version"],
    ):
        raise RuntimeError("Fork TestSpec does not match the frozen task")


def _prepare_images(build: Any, profile: dict[str, Any]) -> Any:
    def prepare_images(
        client: Any, dataset: list[Any], force_rebuild: bool, max_workers: int
    ) -> tuple[list[Any], list[Any]]:
        del client
        if force_rebuild or max_workers != 1 or len(dataset) != 1:
            raise RuntimeError("The prototype requires one cached task and one worker")
        for spec in build.get_test_specs_from_dataset(dataset):
            _check_spec(profile, spec)
        print("AgentExam: using the digest-pinned task image; no image build")
        return [], []

    return prepare_images


def _create_container(image: Any, profile: dict[str, Any]) -> Any:
    def create_container(
        spec: Any,
        client: Any,
        run_id: str,
        logger: Any,
        nocache: bool,
        force_rebuild: bool = False,
    ) -> Any:
        _check_spec(profile, spec)
        if run_id != profile["run_id"] or force_rebuild or nocache:
            raise RuntimeError("Unexpected Fork run identity or rebuild request")
        container = client.containers.create(
            image=image.id,
            name=spec.get_instance_container_name(run_id),
            user="root",
            detach=True,
            command="tail -f /dev/null",
            platform="linux/amd64",
            network_mode="none",
            nano_cpus=profile["cpus"] * 1_000_000_000,
            mem_limit=profile["memory_mb"] * 1024 * 1024,
            memswap_limit=profile["memory_mb"] * 1024 * 1024,
            pids_limit=profile["pids_limit"],
            cap_drop=["ALL"],
            security_opt=["no-new-privileges:true"],
            labels={
                "agentexam.evaluator.run": run_id,
                "agentexam.evaluator.evidence": profile["evidence_identity"],
            },
            environment={"PIP_NO_INDEX": "1", "PIP_DISABLE_PIP_VERSION_CHECK": "1"},
        )
        container.reload()
        evidence = {
            "container_id": container.id,
            "image_id": image.id,
            "image_digest": profile["image"],
            "host_config": {
                key: container.attrs["HostConfig"].get(key)
                for key in (
                    "NetworkMode",
                    "Memory",
                    "MemorySwap",
                    "NanoCpus",
                    "PidsLimit",
                    "CapDrop",
                    "SecurityOpt",
                    "Binds",
                )
            },
            "mounts": container.attrs["Mounts"],
        }
        Path("container.json").write_text(
            json.dumps(evidence, indent=2), encoding="utf-8"
        )
        logger.info("AgentExam fixed-image infrastructure bridge: %s", image.id)
        return container

    return create_container


if __name__ == "__main__":
    run(Path(sys.argv[1]), sys.argv[2:])
