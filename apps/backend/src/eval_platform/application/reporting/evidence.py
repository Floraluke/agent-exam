"""Public evidence views; raw object identities stay behind Reporting."""

import json
from dataclasses import dataclass
from datetime import datetime

from eval_platform.application.execution.public_evidence import validate_public_text
from eval_platform.domain.catalog import ArtifactUnavailable
from eval_platform.domain.jobs.execution import RunArtifact, RunReport
from eval_platform.domain.jobs.models import EvidenceNotFound, EvidenceNotReady

PUBLIC_ARTIFACT_TYPES = frozenset(
    {"agent_patch", "public_test_summary", "public_trajectory"}
)


@dataclass(frozen=True, slots=True)
class ArtifactPage:
    items: tuple[RunArtifact, ...]
    next_cursor: str | None


@dataclass(frozen=True, slots=True)
class EvidenceContent:
    body: bytes
    content_type: str
    filename: str


@dataclass(frozen=True, slots=True)
class TrajectoryEvent:
    sequence: int
    occurred_at: datetime
    source: str
    type: str
    summary: str
    payload: dict[str, object]


@dataclass(frozen=True, slots=True)
class TrajectoryPage:
    items: tuple[TrajectoryEvent, ...]
    next_after_sequence: int
    complete: bool


def artifact_page(
    report: RunReport, kind: str | None, cursor: str | None, limit: int
) -> ArtifactPage:
    if kind is not None and kind not in PUBLIC_ARTIFACT_TYPES:
        raise EvidenceNotReady
    items = sorted(
        (
            item
            for item in report.artifacts
            if item.reference.artifact_type in PUBLIC_ARTIFACT_TYPES
            and (kind is None or item.reference.artifact_type == kind)
            and (cursor is None or item.artifact_id > cursor)
        ),
        key=lambda item: item.artifact_id,
    )
    page = tuple(items[:limit])
    return ArtifactPage(page, page[-1].artifact_id if len(items) > limit else None)


def artifact(report: RunReport, artifact_id: str) -> RunArtifact:
    item = next(
        (item for item in report.artifacts if item.artifact_id == artifact_id), None
    )
    if item is None:
        raise EvidenceNotFound
    if item.reference.artifact_type not in PUBLIC_ARTIFACT_TYPES:
        raise EvidenceNotReady
    return item


def content(item: RunArtifact, body: bytes) -> EvidenceContent:
    validate_public_text(body)
    kind = item.reference.artifact_type
    expected = {
        "agent_patch": ("text/x-diff", "agent.patch"),
        "public_test_summary": ("application/json", "test-summary.json"),
        "public_trajectory": ("application/x-ndjson", "trajectory.jsonl"),
    }[kind]
    if item.reference.content_type != expected[0]:
        raise ArtifactUnavailable
    return EvidenceContent(body, expected[0], expected[1])


def trajectory_page(
    report: RunReport,
    body: bytes,
    after_sequence: int,
    limit: int,
    kind: str | None,
) -> TrajectoryPage:
    item = next(
        (
            item
            for item in report.artifacts
            if item.reference.artifact_type == "public_trajectory"
        ),
        None,
    )
    if item is None:
        raise EvidenceNotReady
    events = _parse(body)
    matching = [
        event
        for event in events
        if event.sequence > after_sequence and (kind is None or event.type == kind)
    ]
    page = tuple(matching[:limit])
    next_sequence = page[-1].sequence if page else after_sequence
    return TrajectoryPage(page, next_sequence, len(matching) <= limit)


def _parse(body: bytes) -> list[TrajectoryEvent]:
    validate_public_text(body)
    events: list[TrajectoryEvent] = []
    try:
        lines = body.decode().splitlines()
        for sequence, line in enumerate(lines, 1):
            value = json.loads(line)
            if (
                set(value)
                != {
                    "sequence",
                    "occurred_at",
                    "source",
                    "type",
                    "summary",
                    "payload",
                }
                or value["sequence"] != sequence
            ):
                raise ValueError
            event = TrajectoryEvent(
                sequence,
                datetime.fromisoformat(value["occurred_at"].replace("Z", "+00:00")),
                _text(value["source"]),
                _text(value["type"]),
                _text(value["summary"]),
                value["payload"],
            )
            if event.payload != {}:
                raise ValueError
            events.append(event)
    except (AttributeError, KeyError, TypeError, UnicodeError, ValueError):
        raise ArtifactUnavailable from None
    return events


def _text(value: object) -> str:
    if not isinstance(value, str) or not value or len(value) > 200:
        raise ValueError
    return value
