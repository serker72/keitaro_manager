"""Dictionaries route: GET /api/dictionaries."""

from dishka import FromDishka
from dishka.integrations.fastapi import DishkaRoute
from fastapi import APIRouter

from src.schemas.api import DictionariesResponse
from src.services.dictionaries import DictionaryService

router = APIRouter(route_class=DishkaRoute, tags=["dictionaries"])


@router.get("/dictionaries", response_model=DictionariesResponse)
async def get_dictionaries(dishka: FromDishka[DictionaryService]) -> DictionariesResponse:
    data = await dishka.get_all()
    return DictionariesResponse(
        domains=[d.model_dump(by_alias=True) for d in data.domains],
        groups=[g.model_dump(by_alias=True) for g in data.groups],
        traffic_sources=[s.model_dump(by_alias=True) for s in data.traffic_sources],
        offers=[o.model_dump(by_alias=True) for o in data.offers],
    )
