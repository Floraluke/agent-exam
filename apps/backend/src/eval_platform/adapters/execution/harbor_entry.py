"""Fixed Harbor CLI bootstrap with fail-closed Codex runtime binding."""

from __future__ import annotations

import argparse
import importlib
import json
import os
import sys
import tomllib
from collections.abc import MutableMapping
from pathlib import Path
from typing import Any

from eval_platform.adapters.execution.codex.agent import guarded_codex_class
from eval_platform.adapters.execution.codex.install import (
    VERSION,
    validate_codex_bundle,
)
from eval_platform.adapters.execution.codex.uploads import validate_auth_file
from eval_platform.adapters.execution.harbor.config_mapper import HARBOR_REVISION
from eval_platform.adapters.execution.harbor.lifecycle.control import (
    configure_controlled_runner,
)
from eval_platform.adapters.execution.network import (
    compose_profile,
    export_sidecar,
    validate_hosts,
)
from eval_platform.application.ports.execution import RunLimits

_AUTH_ENV = "AGENTEXAM_PRIVATE_CODEX_AUTH_PATH"
_BUNDLE_ENV = "AGENTEXAM_PRIVATE_CODEX_BUNDLE_ROOT"
_FIXED_CODEX = {
    "name": "codex",
    "model_name": "openai/gpt-5.6-terra",
    "n_concurrent": 1,
    "kwargs": {
        "version": VERSION,
        "reasoning_effort": "medium",
        "web_search": "disabled",
    },
}


def harbor_command(
    executable: Path, config: Path, control_dir: Path | None = None
) -> list[str]:
    interpreter = executable.with_name(
        "python.exe" if executable.suffix == ".exe" else "python"
    )
    if not interpreter.is_file():
        raise FileNotFoundError("The configured Harbor Python is unavailable")
    command = [
        str(interpreter.resolve()),
        str(Path(__file__).resolve()),
        "--config",
        str(config.resolve()),
        "--harbor-root",
        str(executable.resolve().parents[2]),
    ]
    if control_dir is not None:
        command.extend(("--control-dir", str(control_dir.resolve())))
    return command


def harbor_environment(
    *, auth_path: Path | None = None, bundle_root: Path | None = None
) -> dict[str, str]:
    permitted = set(
        (
            "PATH PATHEXT SYSTEMROOT WINDIR COMSPEC TEMP TMP LOCALAPPDATA APPDATA "
            "USERPROFILE HOMEDRIVE HOMEPATH"
        ).split()
    )
    result = {
        key: value for key, value in os.environ.items() if key.upper() in permitted
    }
    result.update(
        HARBOR_TELEMETRY="disabled",
        PYTHONUTF8="1",
        PYTHONIOENCODING="utf-8",
        PYTHONDONTWRITEBYTECODE="1",
        PYTHONSAFEPATH="1",
        PYTHONPATH=str(Path(__file__).resolve().parents[3]),
    )
    if (auth_path is None) != (bundle_root is None):
        raise ValueError("CODEX_RUNTIME_BINDING_INCOMPLETE")
    if auth_path is not None and bundle_root is not None:
        result[_AUTH_ENV] = str(validate_auth_file(auth_path))
        if bundle_root.is_symlink() or not bundle_root.is_dir():
            raise ValueError("CODEX_BUNDLE_INVALID")
        result[_BUNDLE_ENV] = str(bundle_root.resolve())
    return result


def validate_agent_mode(config: dict[str, Any], *, runtime_bound: bool) -> str:
    agents = config.get("agents")
    if agents == [{"name": "nop", "n_concurrent": 1}]:
        if runtime_bound:
            raise ValueError("CODEX_RUNTIME_BINDING_UNUSED")
        return "nop"
    if agents != [_FIXED_CODEX]:
        raise ValueError("REAL_CODEX_CONFIG_INVALID")
    if not runtime_bound:
        raise RuntimeError("CODEX_CREDENTIAL_BINDING_NOT_READY")
    return "codex"


def pop_runtime_inputs(
    environment: MutableMapping[str, str],
) -> tuple[Path, Path] | None:
    auth = environment.pop(_AUTH_ENV, None)
    bundle = environment.pop(_BUNDLE_ENV, None)
    if auth is None and bundle is None:
        return None
    if auth is None or bundle is None:
        raise ValueError("CODEX_RUNTIME_BINDING_INCOMPLETE")
    root = Path(bundle)
    validate_codex_bundle(root)
    return validate_auth_file(auth), root.resolve()


def register_guarded_codex(auth_path: Path, bundle_root: Path) -> None:
    factory = importlib.import_module("harbor.agents.factory").AgentFactory
    name = importlib.import_module("harbor.models.agent.name").AgentName
    guarded = guarded_codex_class(auth_path=auth_path, bundle_root=bundle_root)
    original = factory.get_agent_class
    factory.get_agent_class = classmethod(
        lambda _cls, requested: (
            guarded if requested == name.CODEX else original(requested)
        )
    )


def validate_network_config(config: dict[str, Any]) -> None:
    environment = config["environment"]
    hosts = tuple(environment.get("extra_allowed_hosts", []))
    if hosts != validate_hosts(hosts) or any(
        environment.get(key)
        for key in ("kwargs", "extra_docker_compose", "import_path", "env", "mounts")
    ):
        raise ValueError("HARBOR_NETWORK_CONFIG_INVALID")
    limits = RunLimits(
        1,
        environment["override_cpus"],
        environment["override_memory_mb"],
        environment["override_storage_mb"],
    )
    for reference in config["tasks"]:
        task = Path(reference["path"])
        document = tomllib.loads((task / "task.toml").read_text(encoding="utf-8"))
        if (
            document["environment"].get("network_mode") != "allowlist"
            or document["environment"].get("allowed_hosts") != []
        ):
            raise ValueError("HARBOR_NETWORK_BASELINE_INVALID")
        for phase in ("agent", "verifier"):
            if {"network_mode", "allowed_hosts"}.intersection(document[phase]):
                raise ValueError("HARBOR_NETWORK_PHASE_OVERRIDE")
        profile = json.loads((task / "environment/docker-compose.yaml").read_text())
        if profile != compose_profile(limits):
            raise ValueError("HARBOR_NETWORK_COMPOSE_INVALID")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--harbor-root", type=Path, required=True)
    parser.add_argument("--control-dir", type=Path)
    args = parser.parse_args()
    config = json.loads(args.config.read_text(encoding="utf-8"))
    runtime = pop_runtime_inputs(os.environ)
    mode = validate_agent_mode(config, runtime_bound=runtime is not None)
    validate_network_config(config)
    context = args.config.parent / "sidecar-source"
    export_sidecar(args.harbor_root, context, HARBOR_REVISION)
    harbor = importlib.import_module("harbor")
    if (
        harbor.__file__ is None
        or Path(harbor.__file__).resolve().parent
        != (args.harbor_root / "src/harbor").resolve()
    ):
        raise ValueError("HARBOR_IMPORT_SOURCE_MISMATCH")
    docker = importlib.import_module("harbor.environments.docker.docker")
    docker.DockerEnvironment._EGRESS_CONTROL_SIDECAR_CONTEXT_PATH = context
    if mode == "codex":
        assert runtime is not None
        register_guarded_codex(*runtime)
    configure_controlled_runner(args.control_dir, args.config.parent)
    cli = importlib.import_module("harbor.cli.main")
    sys.argv = ["harbor", "run", "--config", str(args.config), "--yes"]
    cli.app()


if __name__ == "__main__":
    main()
