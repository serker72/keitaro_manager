"""Dictionaries route: GET /api/dictionaries."""

from dishka import FromDishka
from dishka.integrations.fastapi import DishkaRoute
from fastapi import APIRouter

from src.schemas.api import DictionariesResponse, DomainOption, GroupOption, OfferOption, SourceOption
from src.services.dictionaries import DictionaryService

router = APIRouter(route_class=DishkaRoute, tags=["dictionaries"])


@router.get("/dictionaries", response_model=DictionariesResponse)
async def get_dictionaries(service: FromDishka[DictionaryService]) -> DictionariesResponse:
    data = await service.get_all()
    return DictionariesResponse(
        domains=[DomainOption(id=d.id, name=d.name) for d in data.domains],
        groups=[GroupOption(id=g.id, name=g.name) for g in data.groups],
        traffic_sources=[SourceOption(id=s.id, name=s.name) for s in data.traffic_sources],
        offers=[OfferOption(id=o.id, name=o.name, preview_path=o.preview_path) for o in data.offers],
    )
