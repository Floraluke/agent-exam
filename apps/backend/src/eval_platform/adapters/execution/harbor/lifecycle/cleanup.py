import json
import re
import subprocess
from pathlib import Path

_DOCKER_TIMEOUT_SEC = 30
_COMPOSE_RESOURCES = (
    (["container", "ls", "--all"], ["container", "rm", "--force"]),
    (["network", "ls"], ["network", "rm"]),
    (["volume", "ls"], ["volume", "rm", "--force"]),
    (["image", "ls"], ["image", "rm"]),
)


def cleanup_timed_out_projects(job_dir: Path) -> tuple[str, ...]:
    configs = sorted(job_dir.glob("*/config.json"))
    if not configs:
        return ("HARBOR_COMPOSE_CLEANUP_UNVERIFIED",)
    failed = False
    for path in configs:
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
            trial_name = value.get("trial_name")
            if not isinstance(trial_name, str) or trial_name != path.parent.name:
                raise ValueError("Untrusted Harbor Trial identity")
            project = re.sub(r"[^a-z0-9_-]", "-", f"{trial_name}__env".lower())
            for list_args, remove_args in _COMPOSE_RESOURCES:
                ids = _docker_resource_ids(list_args, project)
                if ids:
                    removed = subprocess.run(
                        ["docker", *remove_args, *ids],
                        capture_output=True,
                        timeout=_DOCKER_TIMEOUT_SEC,
                        check=False,
                    )
                    failed |= removed.returncode != 0
                failed |= bool(_docker_resource_ids(list_args, project))
        except (OSError, RuntimeError, subprocess.SubprocessError, ValueError):
            failed = True
    return ("HARBOR_COMPOSE_CLEANUP_FAILED",) if failed else ()


def _docker_resource_ids(list_args: list[str], project: str) -> tuple[str, ...]:
    result = subprocess.run(
        [
            "docker",
            *list_args,
            "--filter",
            f"label=com.docker.compose.project={project}",
            "--quiet",
        ],
        capture_output=True,
        text=True,
        timeout=_DOCKER_TIMEOUT_SEC,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError("Docker resource query failed")
    return tuple(dict.fromkeys(result.stdout.split()))
