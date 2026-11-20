"""Pydantic schemas mirroring Keitaro Admin API (docs/openapi.yaml).

Field names match API keys exactly. Responses use extra="ignore" so that new
fields on the tracker side never break parsing.
"""

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class KeitaroModel(BaseModel):
    """Base for all Keitaro API models."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")


# --- Dictionaries ---


class Domain(KeitaroModel):
    id: int
    name: str
    state: str = "active"
    status: str | None = None
    is_ssl: bool | None = None
    group_id: int | None = None
    group: str | None = None


class Group(KeitaroModel):
    id: int
    name: str
    position: int | None = None
    type: str | None = None


class Source(KeitaroModel):
    """Traffic source (GET /traffic_sources)."""

    id: int
    name: str
    postback_url: str | None = None
    template_name: str | None = None
    state: str | None = None


class Offer(KeitaroModel):
    id: int
    name: str
    group_id: int | None = None
    state: str | None = None
    payout_value: float | None = None
    payout_currency: str | None = None
    country: list[str] | None = None
    affiliate_network: str | None = None
    preview_path: str | None = None


# --- Campaigns ---


class Campaign(KeitaroModel):
    id: int
    alias: str
    name: str
    type: Literal["position", "weight"] = "position"
    state: str = "active"
    group_id: int | None = None
    traffic_source_id: int | None = None
    cost_type: str | None = None
    cost_value: float | None = None
    cost_currency: str | None = None
    created_at: str | None = None
    updated_at: str | None = None


class CampaignRequest(KeitaroModel):
    """POST /campaigns body. alias + name are required (CampaignCreateRequired)."""

    name: str
    alias: str
    type: Literal["position", "weight"] = "position"
    state: Literal["active", "disabled"] = "active"
    domain_id: int | None = None
    # In the spec request group_id is typed as string, response — integer.
    group_id: str | int | None = None
    traffic_source_id: int | None = None
    cookies_ttl: int | None = None
    cost_type: str | None = None
    cost_value: float | None = None
    cost_currency: str | None = None
    bind_visitors: str | None = None
    notes: str | None = None

    def to_payload(self) -> dict[str, Any]:
        """Serialize omitting None values (tracker rejects nulls)."""
        return self.model_dump(exclude_none=True)


# --- Streams (Flows) ---


class Filter(KeitaroModel):
    """Filter as returned in Stream responses.

    Spec says payload is a string, but the live API returns a list of values
    (e.g. ["US"]) and integer oid — both variants are accepted.
    """

    id: int | None = None
    stream_id: int | None = None
    name: str
    mode: Literal["accept", "reject"]
    payload: list[str] | str | None = None
    oid: int | str | None = None

    def payload_values(self) -> list[str]:
        """Normalized payload as a list of strings."""
        if self.payload is None:
            return []
        if isinstance(self.payload, list):
            return [str(v) for v in self.payload]
        return [self.payload]


class FilterStreamRequest(KeitaroModel):
    """Filter in stream create/update requests."""

    name: str
    mode: Literal["accept", "reject"]
    payload: list[str] = Field(default_factory=list)
    id: int | None = None


class OfferStream(KeitaroModel):
    """Offer link inside a stream (response shape)."""

    id: int | None = None
    stream_id: int | None = None
    offer_id: int
    state: str = "active"
    share: int
    created_at: str | None = None
    updated_at: str | None = None


class OfferStreamRequest(KeitaroModel):
    """Offer link in stream create/update requests."""

    offer_id: int
    share: int
    state: Literal["active", "disabled"] = "active"


class Stream(KeitaroModel):
    """Stream (flow) as returned by the API."""

    id: int
    type: Literal["forced", "regular", "default"] | None = None
    name: str
    campaign_id: int
    position: int | None = None
    weight: float | None = None
    state: Literal["active", "disabled"] | None = None
    schema_: Literal["landings", "redirect", "action"] | None = Field(default=None, alias="schema")
    action_type: str | None = None
    action_payload: str | dict[str, Any] | None = None
    action_options: dict[str, Any] | None = None
    comments: str | None = None
    updated_at: str | None = None
    collect_clicks: bool | None = None
    filter_or: bool | None = None
    filters: list[Filter] = Field(default_factory=list)
    offers: list[OfferStream] = Field(default_factory=list)
    offer_selection: str | None = None


class StreamRequest(KeitaroModel):
    """POST /streams body (campaign_id, schema, type, name, action_type required)."""

    campaign_id: int
    type: Literal["forced", "regular", "default"]
    name: str
    action_type: str
    schema_: Literal["landings", "redirect", "action"] = Field(alias="schema")
    state: Literal["active", "disabled"] = "active"
    action_payload: str | dict[str, Any] | None = None
    action_options: dict[str, Any] | None = None
    position: int | None = None
    weight: float | None = None
    comments: str | None = None
    collect_clicks: bool | None = None
    filter_or: bool | None = None
    filters: list[FilterStreamRequest] = Field(default_factory=list)
    offers: list[OfferStreamRequest] = Field(default_factory=list)

    def to_payload(self) -> dict[str, Any]:
        return self.model_dump(by_alias=True, exclude_none=True)


class StreamRequestPut(KeitaroModel):
    """PUT /streams/{id} body — same fields as StreamRequest, all optional."""

    campaign_id: int | None = None
    type: Literal["forced", "regular", "default"] | None = None
    name: str | None = None
    action_type: str | None = None
    schema_: Literal["landings", "redirect", "action"] | None = Field(default=None, alias="schema")
    state: Literal["active", "disabled"] | None = None
    action_payload: str | dict[str, Any] | None = None
    action_options: dict[str, Any] | None = None
    position: int | None = None
    weight: float | None = None
    comments: str | None = None
    collect_clicks: bool | None = None
    filter_or: bool | None = None
    filters: list[FilterStreamRequest] | None = None
    offers: list[OfferStreamRequest] | None = None

    def to_payload(self) -> dict[str, Any]:
        return self.model_dump(by_alias=True, exclude_none=True)


# --- Stream metadata (for live stand verification) ---


class StreamFilter(KeitaroModel):
    """GET /stream_filters item."""

    value: str
    tooltip: str | None = None
    modes: dict[str, str] | None = None
    group: str | None = None
    defaults: str | None = None


class StreamAction(KeitaroModel):
    """GET /streams_actions item."""

    key: str
    name: str | None = None
    field: str | None = None
    type: str | None = None
    description: str | None = None
