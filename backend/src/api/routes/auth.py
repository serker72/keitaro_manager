"""Auth routes: login / logout / me (stateless JWT в httpOnly cookie)."""

from typing import Annotated

from dishka import FromDishka
from dishka.integrations.fastapi import DishkaRoute
from fastapi import APIRouter, Depends, Response

from src.api.deps import verify_auth
from src.core.config import Settings
from src.schemas.auth import LoginRequest, LogoutResponse, MeResponse
from src.services.auth import AuthService

router = APIRouter(prefix="/auth", route_class=DishkaRoute, tags=["auth"])


@router.post("/login", response_model=MeResponse)
async def login(
    body: LoginRequest,
    response: Response,
    auth: FromDishka[AuthService],
    settings: FromDishka[Settings],
) -> MeResponse:
    token = auth.verify_credentials(body.login, body.password)
    response.set_cookie(
        key=settings.AUTH_COOKIE_NAME,
        value=token,
        max_age=settings.AUTH_TOKEN_TTL_MINUTES * 60,
        httponly=True,
        samesite="lax",
        secure=settings.AUTH_COOKIE_SECURE,
        path="/",
    )
    return MeResponse(login=body.login)


@router.post("/logout", response_model=LogoutResponse)
async def logout(
    response: Response,
    settings: FromDishka[Settings],
) -> LogoutResponse:
    response.delete_cookie(key=settings.AUTH_COOKIE_NAME, path="/")
    return LogoutResponse()


@router.get("/me", response_model=MeResponse)
async def me(login: Annotated[str, Depends(verify_auth)]) -> MeResponse:
    return MeResponse(login=login)
