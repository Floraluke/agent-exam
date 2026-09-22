"""Internal fixed Codex command/permission policy, not a credential provider."""

from __future__ import annotations

import re
import shlex
from pathlib import PurePosixPath
from typing import Any

PROFILE = "agentexam-closed-book"
HOME_PATH = "/tmp/codex-home"
SECRETS_PATH = "/tmp/codex-secrets"
DENIED_PATHS = (HOME_PATH, SECRETS_PATH, "/logs", "/proc")
CLEANUP_COMMAND = (
    f"rm -rf {HOME_PATH} {SECRETS_PATH} && "
    f"test ! -e {HOME_PATH} && test ! -e {SECRETS_PATH}"
)
_SHELL_PREFIX = "if [ -s ~/.nvm/nvm.sh ]; then . ~/.nvm/nvm.sh; fi; "
_OUTPUT_SUFFIX = " 2>&1 </dev/null | tee /logs/agent/codex.txt"
SETUP_COMMANDS = frozenset(
    {
        'mkdir -p "$CODEX_HOME" /tmp/codex-secrets /logs/agent',
        'ln -sf /tmp/codex-secrets/auth.json "$CODEX_HOME/auth.json"\n',
        'mkdir -p /logs/agent\nif [ -d "$CODEX_HOME/sessions" ]; then\n'
        "  rm -rf /logs/agent/sessions\n"
        '  cp -R "$CODEX_HOME/sessions" /logs/agent/sessions\nfi',
        'rm -rf /tmp/codex-secrets "$CODEX_HOME"',
    }
)
REASONING_EFFORTS = frozenset({"low", "medium", "high", "xhigh"})
UPSTREAM_ARGUMENTS = frozenset(
    {"logs_dir", "model_name", "logger", "version", "reasoning_effort"}
)


def validate_agent_arguments(arguments: dict[str, Any], version: str) -> None:
    if arguments.pop("extra_env", {}) != {}:
        raise ValueError("CODEX_GUARD_CONFIG_INVALID")
    if arguments.pop("web_search", "disabled") != "disabled":
        raise ValueError("CODEX_GUARD_CONFIG_INVALID")
    if (
        set(arguments) - UPSTREAM_ARGUMENTS
        or arguments.get("version") != version
        or arguments.get("reasoning_effort") not in REASONING_EFFORTS
    ):
        raise ValueError("CODEX_GUARD_CONFIG_INVALID")


def permission_config(workspace: str) -> dict[str, Any]:
    path = PurePosixPath(workspace)
    if (
        not re.fullmatch(r"/[a-zA-Z0-9_/-]+", workspace)
        or str(path) != workspace
        or workspace in {"/", "/tmp"}
        or any(
            path.is_relative_to(blocked) or PurePosixPath(blocked).is_relative_to(path)
            for blocked in DENIED_PATHS
        )
    ):
        raise ValueError("CODEX_WORKSPACE_INVALID")
    return {
        "default_permissions": PROFILE,
        "approval_policy": "never",
        "web_search": "disabled",
        "permissions": {
            PROFILE: {
                "filesystem": {
                    "/": "read",
                    "/tmp": "write",
                    workspace: "write",
                    f"{workspace}/.codex": "deny",
                    **dict.fromkeys(DENIED_PATHS, "deny"),
                },
                "network": {"enabled": False},
            }
        },
    }


def guarded_command(command: str, model: str, effort: str) -> str:
    if not re.fullmatch(r"[a-zA-Z0-9_.-]+", model) or (effort not in REASONING_EFFORTS):
        raise ValueError("CODEX_RUNTIME_CONFIG_INVALID")
    flags = (
        f"--skip-git-repo-check --model {model} --json --enable unified_exec "
        f"-c model_reasoning_effort={effort} -c web_search=disabled -- "
    )
    prefix = (
        _SHELL_PREFIX + "codex exec --dangerously-bypass-approvals-and-sandbox " + flags
    )
    if not command.startswith(prefix) or not command.endswith(_OUTPUT_SUFFIX):
        raise ValueError("CODEX_UPSTREAM_COMMAND_MISMATCH")
    instruction = command[len(prefix) : -len(_OUTPUT_SUFFIX)]
    try:
        words = shlex.split(instruction)
    except ValueError:
        raise ValueError("CODEX_UPSTREAM_COMMAND_MISMATCH") from None
    if len(words) != 1 or shlex.quote(words[0]) != instruction:
        raise ValueError("CODEX_UPSTREAM_COMMAND_MISMATCH")
    return "codex exec " + flags + instruction + _OUTPUT_SUFFIX


def prepare_workspace_command(workspace: str) -> str:
    permission_config(workspace)
    return (
        f"test -d {workspace} && test ! -L {workspace} && "
        f"test ! -L {workspace}/.codex && mkdir -p {workspace}/.codex"
    )


def is_codex_run(command: str) -> bool:
    return command.startswith(_SHELL_PREFIX + "codex exec ")
