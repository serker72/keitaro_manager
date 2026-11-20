"""API routers aggregated under /api prefix."""

from fastapi import APIRouter, Depends

from src.api.deps import verify_auth

from .auth import router as auth_router
from .campaigns import router as campaigns_router
from .dictionaries import router as dictionaries_router
from .streams import router as streams_router

api_router = APIRouter()
api_router.include_router(auth_router)
# Единая защита на уровне роутера — не дублируем зависимость в каждом методе.
api_router.include_router(dictionaries_router, dependencies=[Depends(verify_auth)])
api_router.include_router(campaigns_router, dependencies=[Depends(verify_auth)])
api_router.include_router(streams_router, dependencies=[Depends(verify_auth)])

__all__ = ["api_router"]
