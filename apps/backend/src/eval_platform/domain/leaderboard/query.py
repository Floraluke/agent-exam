"""Leaderboard query and stable cursor values."""

from dataclasses import dataclass
from hashlib import sha256

from eval_platform.domain.jobs.models import JobInputError
from eval_platform.domain.leaderboard.models import LeaderboardRow


@dataclass(frozen=True, slots=True)
class LeaderboardQuery:
    evaluation_track: str
    dataset_id: str
    dataset_revision: str
    split: str
    repo: str | None = None
    tool_profile_id: str | None = None
    cursor: str | None = None
    limit: int = 20


@dataclass(frozen=True, slots=True)
class LeaderboardPage:
    items: tuple[LeaderboardRow, ...]
    next_cursor: str | None


def paginate(
    rows: tuple[LeaderboardRow, ...], cursor: str | None, limit: int
) -> LeaderboardPage:
    if not 1 <= limit <= 100:
        raise JobInputError("INVALID_REQUEST")
    start = 0
    if cursor is not None:
        matches = [index for index, row in enumerate(rows) if row_cursor(row) == cursor]
        if len(matches) != 1:
            raise JobInputError("INVALID_CURSOR")
        start = matches[0] + 1
    items = rows[start : start + limit]
    has_more = start + limit < len(rows)
    return LeaderboardPage(items, row_cursor(items[-1]) if items and has_more else None)


def row_cursor(row: LeaderboardRow) -> str:
    identity = (
        repr(row.scope),
        row.agent.agent_configuration_id,
        row.agent.configuration_fingerprint,
    )
    return sha256("\x1f".join(identity).encode()).hexdigest()
