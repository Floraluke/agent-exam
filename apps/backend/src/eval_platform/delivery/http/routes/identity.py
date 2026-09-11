from fastapi import APIRouter, Request, Response

from eval_platform.application.identity import IdentityService
from eval_platform.delivery.http.config import HttpConfig
from eval_platform.delivery.http.schemas import (
    ActorResponse,
    EmptyRequest,
    LoginRequest,
)
from eval_platform.domain.identity import SESSION_LIFETIME


def identity_router(service: IdentityService, config: HttpConfig) -> APIRouter:
    router = APIRouter(prefix="/api/v1/auth", tags=["identity"])

    @router.post("/login", response_model=ActorResponse)
    def login(body: LoginRequest, response: Response) -> ActorResponse:
        result = service.login(body.username, body.password.get_secret_value())
        response.set_cookie(
            config.cookie_name,
            result.token,
            max_age=int(SESSION_LIFETIME.total_seconds()),
            path="/",
            secure=config.secure_cookie,
            httponly=True,
            samesite="strict",
        )
        return ActorResponse.model_validate(result.actor)

    @router.get("/me", response_model=ActorResponse)
    def current_actor(request: Request) -> ActorResponse:
        return ActorResponse.model_validate(
            service.current_actor(request.cookies.get(config.cookie_name))
        )

    @router.post("/logout", status_code=204)
    def logout(request: Request, body: EmptyRequest | None = None) -> Response:
        service.logout(request.cookies.get(config.cookie_name))
        response = Response(status_code=204)
        response.delete_cookie(
            config.cookie_name,
            path="/",
            secure=config.secure_cookie,
            httponly=True,
            samesite="strict",
        )
        return response

    return router
