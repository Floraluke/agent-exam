"""Authenticated read-only base leaderboard application service."""

from eval_platform.application.ports.leaderboard import LeaderboardRepository
from eval_platform.domain.identity import AuthenticatedActor
from eval_platform.domain.jobs.models import JobInputError
from eval_platform.domain.leaderboard import LeaderboardPage, LeaderboardQuery


class LeaderboardReporting:
    def __init__(self, repository: LeaderboardRepository) -> None:
        self.repository = repository

    def page(
        self, actor: AuthenticatedActor, query: LeaderboardQuery
    ) -> LeaderboardPage:
        del actor
        if query.evaluation_track != "closed_book":
            raise JobInputError("EVALUATION_TRACK_NOT_ENABLED")
        return self.repository.page(query)
