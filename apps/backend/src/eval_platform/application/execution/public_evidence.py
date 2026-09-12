"""Fail-closed normalization for evidence allowed beyond the private boundary."""

import json
import re
from datetime import datetime
from typing import Any

from eval_platform.domain.catalog import ArtifactUnavailable

_SAFE_NAME = re.compile(r"[A-Za-z0-9_.-]{1,64}")
_SECRET_MARKERS = re.compile(
    rb"(?i)(sk-[a-z0-9_-]{8,}|authorization\s*:\s*bearer|"
    rb"-----begin [a-z ]*private key-----|/tmp/codex-secrets|"
    rb"(?:^|[/\\])auth\.json|(?:^|[/\\])\.codex(?:[/\\])|"
    rb"(?:gold|test|reference)_patch)"
)
_TEST_GROUPS = frozenset({"FAIL_TO_PASS", "PASS_TO_PASS"})
_MAX_EVENTS = 10_000


def validate_public_text(content: bytes) -> None:
    # Patch syntax/UTF-8/binary classification remains the domain validator's job.
    if _SECRET_MARKERS.search(content):
        raise ArtifactUnavailable


def normalize_test_summary(summary: dict[str, object]) -> bytes:
    normalized: dict[str, dict[str, int]] = {}
    if not summary or set(summary) - _TEST_GROUPS:
        raise ArtifactUnavailable
    for name, value in summary.items():
        if not isinstance(value, dict) or set(value) != {"success", "failure"}:
            raise ArtifactUnavailable
        success, failure = value["success"], value["failure"]
        if (
            type(success) is not int
            or type(failure) is not int
            or min(success, failure) < 0
        ):
            raise ArtifactUnavailable
        normalized[name] = {"success": success, "failure": failure}
    return json.dumps(
        normalized, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode()


def normalize_trajectory(raw: bytes, agent_source: str, occurred_at: datetime) -> bytes:
    try:
        document = json.loads(raw)
        steps = document["steps"]
    except (KeyError, TypeError, ValueError, UnicodeError):
        raise ArtifactUnavailable from None
    if not isinstance(steps, list) or not _SAFE_NAME.fullmatch(agent_source):
        raise ArtifactUnavailable
    events = _events(steps, agent_source, occurred_at)
    return b"".join(
        json.dumps(item, ensure_ascii=False, sort_keys=True).encode() + b"\n"
        for item in events
    )


def _events(
    steps: list[Any], agent_source: str, occurred_at: datetime
) -> list[dict[str, object]]:
    events: list[dict[str, object]] = []
    timestamp = occurred_at.isoformat().replace("+00:00", "Z")
    for step in steps:
        if not isinstance(step, dict):
            raise ArtifactUnavailable
        calls = step.get("tool_calls") or []
        if not isinstance(calls, list):
            raise ArtifactUnavailable
        for call in calls:
            name = call.get("function_name") if isinstance(call, dict) else None
            if not isinstance(name, str) or not _SAFE_NAME.fullmatch(name):
                raise ArtifactUnavailable
            events.append(
                _event(
                    len(events) + 1,
                    timestamp,
                    agent_source,
                    "tool_call",
                    f"调用工具 {name}",
                )
            )
        if not calls and step.get("source") == "agent" and step.get("message"):
            events.append(
                _event(
                    len(events) + 1,
                    timestamp,
                    agent_source,
                    "agent_message",
                    "Agent 输出了可观察消息（正文未公开）",
                )
            )
        if len(events) > _MAX_EVENTS:
            raise ArtifactUnavailable
    return events


def _event(
    sequence: int, occurred_at: str, source: str, kind: str, summary: str
) -> dict[str, object]:
    return {
        "sequence": sequence,
        "occurred_at": occurred_at,
        "source": source,
        "type": kind,
        "summary": summary,
        "payload": {},
    }
