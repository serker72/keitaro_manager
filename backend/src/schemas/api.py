"""API-level DTO schemas (camelCase JSON for the frontend)."""

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel


class ApiModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, from_attributes=True)


class DictionariesResponse(ApiModel):
    domains: list[dict[str, object]]
    groups: list[dict[str, object]]
    traffic_sources: list[dict[str, object]]
    offers: list[dict[str, object]]


class CampaignCreateRequest(ApiModel):
    """Input for the campaign creator screen."""

    name: str = Field(min_length=1, max_length=200)
    geo: str = Field(min_length=2, max_length=10, description="ISO country code, e.g. US")
    domain_id: int
    group_id: int
    traffic_source_id: int
    offer_id: int


class CampaignListItem(ApiModel):
    id: int
    keitaro_campaign_id: int
    name: str
    geo: str
    created_at: str
    updated_at: str


class StreamOfferRow(ApiModel):
    """One offer row of a stream (merged Keitaro + local state)."""

    offer_id: int
    offer_name: str
    share: int
    is_pinned: bool
    is_removed: bool


class StreamInfo(ApiModel):
    """Stream view for the editor: Keitaro metadata + offer rows."""

    stream_id: int
    name: str
    type: str
    state: str
    clicks: int | None = None
    filter_description: str | None = None
    action_payload: str | None = None
    preview_url: str | None = None
    offers: list[StreamOfferRow] = Field(default_factory=list)


class StreamsResponse(ApiModel):
    campaign_id: int
    keitaro_campaign_id: int
    streams: list[StreamInfo]


class PushOffersRequest(ApiModel):
    """Draft state sent from the editor before PUSH TO KT."""

    offers: list[StreamOfferRow]
