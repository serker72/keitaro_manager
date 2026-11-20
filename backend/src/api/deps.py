"""Общие зависимости FastAPI (проверка авторизации)."""

from dishka import FromDishka
from dishka.integrations.fastapi import inject
from fastapi import Request

from src.core.config import Settings
from src.services.auth import AuthError, AuthService


@inject
async def verify_auth(
    request: Request,
    auth: FromDishka[AuthService],
    settings: FromDishka[Settings],
) -> str:
    """Проверить JWT из httpOnly cookie либо из заголовка Authorization: Bearer.

    Возвращает логин (subject токена) либо поднимает AuthError -> 401.
    """
    token = request.cookies.get(settings.AUTH_COOKIE_NAME)
    if not token:
        header = request.headers.get("Authorization", "")
        scheme, _, value = header.partition(" ")
        if scheme.lower() == "bearer" and value.strip():
            token = value.strip()
    if not token:
        raise AuthError("Требуется авторизация")
    return auth.decode_token(token)
