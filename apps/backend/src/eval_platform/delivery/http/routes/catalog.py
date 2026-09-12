from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Query, Request, Response

from eval_platform.application.agent_registry import AgentRegistry
from eval_platform.application.identity import IdentityService
from eval_platform.application.task_catalog import TaskCatalog
from eval_platform.delivery.http.catalog_schemas import (
    AgentDetail,
    AgentPage,
    RegisterPreset,
    TaskDetail,
    TaskPage,
)
from eval_platform.delivery.http.config import HttpConfig
from eval_platform.delivery.http.schemas import EmptyRequest, error_responses
from eval_platform.domain.catalog import CatalogInvalid


def catalog_router(
    identity: IdentityService,
    tasks: TaskCatalog,
    config: HttpConfig,
    agents: AgentRegistry | None = None,
) -> APIRouter:
    router = APIRouter(
        prefix="/api/v1",
        tags=["catalog"],
        responses=error_responses(400, 401, 403, 404, 409, 422, 500, 503),
    )

    @router.post("/tasks/register", status_code=201, response_model=TaskDetail)
    def register(request: Request, body: RegisterPreset) -> TaskDetail:
        actor = identity.current_actor(request.cookies.get(config.cookie_name))
        return TaskDetail.from_record(tasks.register(actor, body.preset_id))

    @router.get("/tasks", response_model=TaskPage)
    def task_list(
        request: Request,
        cursor: UUID | None = None,
        limit: int = Query(20, ge=1, le=100),
        dataset_id: str | None = Query(None, min_length=1, max_length=128),
        split: str | None = Query(None, min_length=1, max_length=64),
        repo: str | None = Query(None, min_length=1, max_length=128),
    ) -> TaskPage:
        actor = identity.current_actor(request.cookies.get(config.cookie_name))
        _check_query(request, {"dataset_id", "split", "repo", "cursor", "limit"})
        filters = {
            key: value
            for key, value in (
                ("dataset_id", dataset_id),
                ("split", split),
                ("repo", repo),
            )
            if value is not None
        }
        items, next_cursor = tasks.list(
            actor,
            filters,
            str(cursor) if cursor else None,
            limit,
        )
        return TaskPage(
            items=[TaskDetail.from_record(item) for item in items],
            next_cursor=next_cursor,
        )

    @router.get("/tasks/{task_id}", response_model=TaskDetail)
    def detail(task_id: UUID, request: Request) -> TaskDetail:
        actor = identity.current_actor(request.cookies.get(config.cookie_name))
        return TaskDetail.from_record(tasks.get(actor, str(task_id)))

    if agents is None:
        return router
    registry = agents

    @router.post("/agent-configurations", status_code=201, response_model=AgentDetail)
    def register_agent(request: Request, body: RegisterPreset) -> AgentDetail:
        actor = identity.current_actor(request.cookies.get(config.cookie_name))
        return AgentDetail.from_record(registry.register(actor, body.preset_id))

    @router.get("/agent-configurations", response_model=AgentPage)
    def agent_list(
        request: Request,
        cursor: UUID | None = None,
        limit: int = Query(20, ge=1, le=100),
        agent_type: Literal["codex"] | None = None,
        enabled: bool | None = None,
    ) -> AgentPage:
        actor = identity.current_actor(request.cookies.get(config.cookie_name))
        _check_query(request, {"agent_type", "enabled", "cursor", "limit"})
        items, next_cursor = registry.list(
            actor,
            enabled,
            str(cursor) if cursor else None,
            limit,
        )
        return AgentPage(
            items=[AgentDetail.from_record(item) for item in items],
            next_cursor=next_cursor,
        )

    @router.get("/agent-configurations/{configuration_id}", response_model=AgentDetail)
    def agent_detail(configuration_id: UUID, request: Request) -> AgentDetail:
        actor = identity.current_actor(request.cookies.get(config.cookie_name))
        return AgentDetail.from_record(registry.get(actor, str(configuration_id)))

    @router.post("/agent-configurations/{configuration_id}/disable", status_code=204)
    def disable_agent(
        configuration_id: UUID,
        request: Request,
        body: EmptyRequest | None = None,
    ) -> Response:
        actor = identity.current_actor(request.cookies.get(config.cookie_name))
        registry.disable(actor, str(configuration_id))
        return Response(status_code=204)

    return router


def _check_query(request: Request, allowed: set[str]) -> None:
    parameters = request.query_params
    if set(parameters) - allowed or len(parameters.multi_items()) != len(parameters):
        raise CatalogInvalid
