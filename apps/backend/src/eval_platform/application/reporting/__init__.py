"""Protected report query application service."""

from eval_platform.application.reporting.leaderboard import LeaderboardReporting
from eval_platform.application.reporting.service import JobReporting

__all__ = ["JobReporting", "LeaderboardReporting"]
