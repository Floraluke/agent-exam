from typing import Annotated

from fastapi import APIRouter, Query, Request

from eval_platform.application.identity import IdentityService
from eval_platform.application.reporting import LeaderboardReporting
from eval_platform.delivery.http.config import HttpConfig
from eval_platform.delivery.http.routes.leaderboard.schemas import (
    LeaderboardPageResponse,
)
from eval_platform.delivery.http.schemas import error_responses
from eval_platform.domain.jobs.models import JobInputError
from eval_platform.domain.leaderboard import LeaderboardQuery

Text128 = Annotated[str, Query(min_length=1, max_length=128)]
Text64 = Annotated[str, Query(min_length=1, max_length=64)]
Cursor = Annotated[str | None, Query(pattern=r"^[0-9a-f]{64}$")]


def leaderboard_router(
    identity: IdentityService,
    reporting: LeaderboardReporting,
    config: HttpConfig,
) -> APIRouter:
    router = APIRouter(
        prefix="/api/v1/leaderboard",
        tags=["leaderboard"],
        responses=error_responses(400, 401, 422, 500, 503),
    )

    @router.get("", response_model=LeaderboardPageResponse)
    def page(
        request: Request,
        evaluation_track: Text64,
        dataset_id: Text128,
        dataset_revision: Text64,
        split: Text64,
        repo: Text128 | None = None,
        tool_profile_id: Text128 | None = None,
        cursor: Cursor = None,
        limit: int = Query(20, ge=1, le=100),
    ) -> LeaderboardPageResponse:
        allowed = {
            "evaluation_track",
            "dataset_id",
            "dataset_revision",
            "split",
            "repo",
            "tool_profile_id",
            "cursor",
            "limit",
        }
        parameters = request.query_params
        if set(parameters) - allowed or len(parameters.multi_items()) != len(
            parameters
        ):
            raise JobInputError("INVALID_REQUEST")
        actor = identity.current_actor(request.cookies.get(config.cookie_name))
        query = LeaderboardQuery(
            evaluation_track,
            dataset_id,
            dataset_revision,
            split,
            repo,
            tool_profile_id,
            cursor,
            limit,
        )
        return LeaderboardPageResponse.from_record(reporting.page(actor, query))

    return router
