from typing import Protocol

from eval_platform.domain.leaderboard import LeaderboardPage, LeaderboardQuery


class LeaderboardRepository(Protocol):
    """Return the official, deterministic read projection for one query."""

    def page(self, query: LeaderboardQuery) -> LeaderboardPage: ...
