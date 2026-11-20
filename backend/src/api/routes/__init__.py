"""API routers aggregated under /api prefix."""

from fastapi import APIRouter

from .campaigns import router as campaigns_router
from .dictionaries import router as dictionaries_router
from .streams import router as streams_router

api_router = APIRouter()
api_router.include_router(dictionaries_router)
api_router.include_router(campaigns_router)
api_router.include_router(streams_router)

__all__ = ["api_router"]
