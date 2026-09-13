from eval_platform.domain.jobs.models import JobUnavailable
from eval_platform.domain.leaderboard import (
    LeaderboardPage,
    LeaderboardQuery,
    LeaderboardRow,
    paginate,
)


class MemoryLeaderboardRepository:
    def __init__(self, rows: tuple[LeaderboardRow, ...]) -> None:
        self.rows = rows
        self.queries: list[LeaderboardQuery] = []
        self.unavailable = False

    def page(self, query: LeaderboardQuery) -> LeaderboardPage:
        if self.unavailable:
            raise JobUnavailable
        self.queries.append(query)
        return paginate(self.rows, query.cursor, query.limit)
