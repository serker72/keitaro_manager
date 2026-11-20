"""Campaign routes: GET/POST /api/campaigns."""

from datetime import UTC, datetime

from dishka import FromDishka
from dishka.integrations.fastapi import DishkaRoute
from fastapi import APIRouter, HTTPException

from src.repositories.campaign import CampaignRepository
from src.schemas.api import CampaignCreateRequest, CampaignListItem
from src.services.campaign import CampaignService
from src.services.dictionaries import DictionaryService

router = APIRouter(route_class=DishkaRoute, tags=["campaigns"])


def _fmt(dt: datetime) -> str:
    return dt.astimezone(UTC).strftime("%Y-%m-%d %H:%M:%S")


@router.get("/campaigns", response_model=list[CampaignListItem])
async def list_campaigns(dishka: FromDishka[CampaignRepository]) -> list[CampaignListItem]:
    records = await dishka.list()
    return [
        CampaignListItem(
            id=r.id,
            keitaro_campaign_id=r.keitaro_campaign_id,
            name=r.name,
            geo=r.geo,
            created_at=_fmt(r.created_at),
            updated_at=_fmt(r.updated_at),
        )
        for r in records
    ]


@router.post("/campaigns", response_model=CampaignListItem, status_code=201)
async def create_campaign(
    body: CampaignCreateRequest,
    service: FromDishka[CampaignService],
    dictionaries: FromDishka[DictionaryService],
) -> CampaignListItem:
    offers = await dictionaries.get_all()
    offer_name = next((o.name for o in offers.offers if o.id == body.offer_id), f"Offer {body.offer_id}")

    try:
        campaign, _, _ = await service.create(
            name=body.name,
            geo=body.geo,
            domain_id=body.domain_id,
            group_id=body.group_id,
            traffic_source_id=body.traffic_source_id,
            offer_id=body.offer_id,
            offer_name=offer_name,
        )
    except ValueError as e:
        raise HTTPException(status_code=502, detail=str(e)) from e

    return CampaignListItem(
        id=campaign.id,
        keitaro_campaign_id=campaign.keitaro_campaign_id,
        name=campaign.name,
        geo=campaign.geo,
        created_at=_fmt(campaign.created_at),
        updated_at=_fmt(campaign.updated_at),
    )
