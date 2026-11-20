"""Stream editor routes: read streams + push to Keitaro."""

from dishka import FromDishka
from dishka.integrations.fastapi import DishkaRoute
from fastapi import APIRouter, Query

from src.schemas.api import PushOffersRequest, StreamsResponse
from src.services.stream_editor import StreamEditorService

router = APIRouter(route_class=DishkaRoute, tags=["streams"])


@router.get("/campaigns/{campaign_id}/streams", response_model=StreamsResponse)
async def get_streams(
    campaign_id: int,
    service: FromDishka[StreamEditorService],
    sync: bool = Query(default=False, description="FETCH STREAMS FROM KT before reading"),
) -> StreamsResponse:
    return await service.get_streams(campaign_id, sync=sync)


@router.put("/campaigns/{campaign_id}/streams/{stream_id}/push", response_model=StreamsResponse)
async def push_stream(
    campaign_id: int,
    stream_id: int,
    body: PushOffersRequest,
    service: FromDishka[StreamEditorService],
) -> StreamsResponse:
    return await service.push_stream_to_kt(campaign_id, stream_id, body.offers)
