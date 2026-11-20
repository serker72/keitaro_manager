"""Async Keitaro Admin API client.

Wraps httpx.AsyncClient with base path /admin_api/v1 and `Api-Key` header.
All HTTP errors are mapped to KeitaroAPIError subclasses.
"""

import json
from typing import Any

import httpx
from pydantic import ValidationError

from src.schemas.keitaro import (
    Campaign,
    CampaignRequest,
    Domain,
    Group,
    Offer,
    Source,
    Stream,
    StreamAction,
    StreamFilter,
    StreamRequest,
    StreamRequestPut,
)


class KeitaroAPIError(Exception):
    """Base error for Keitaro API failures."""

    def __init__(self, status_code: int, message: str) -> None:
        self.status_code = status_code
        self.message = message
        super().__init__(f"Keitaro API error {status_code}: {message}")


class KeitaroBadRequestError(KeitaroAPIError):
    """400 — validation error in request body."""


class KeitaroAuthError(KeitaroAPIError):
    """401 — invalid API key."""


class KeitaroPaymentRequiredError(KeitaroAPIError):
    """402 — API disabled in tracker settings."""


class KeitaroNotFoundError(KeitaroAPIError):
    """404 — entity not found."""


class KeitaroNotAcceptableError(KeitaroAPIError):
    """406 — action not acceptable on the entity."""


class KeitaroServerError(KeitaroAPIError):
    """500 — internal tracker error."""


_STATUS_MAP: dict[int, type[KeitaroAPIError]] = {
    400: KeitaroBadRequestError,
    401: KeitaroAuthError,
    402: KeitaroPaymentRequiredError,
    404: KeitaroNotFoundError,
    406: KeitaroNotAcceptableError,
    500: KeitaroServerError,
}


def _extract_error_message(response: httpx.Response) -> str:
    """Pull a human-readable message from the error body ({"error": "..."})."""
    try:
        body: Any = response.json()
        if isinstance(body, dict):
            return str(body.get("error") or body.get("message") or body)
        return str(body)
    except (json.JSONDecodeError, ValueError):
        return response.text[:500] or response.reason_phrase


class KeitaroClient:
    """Thin typed wrapper over Keitaro Admin API endpoints used by the app."""

    def __init__(self, client: httpx.AsyncClient) -> None:
        self._client = client

    async def _request(
        self, method: str, path: str, *, json_body: Any | None = None, params: dict[str, Any] | None = None
    ) -> Any:
        response = await self._client.request(method, path, json=json_body, params=params)
        if response.status_code != 200:
            error_cls = _STATUS_MAP.get(response.status_code, KeitaroAPIError)
            raise error_cls(response.status_code, _extract_error_message(response))
        return response.json()

    # --- Dictionaries ---

    async def get_domains(self) -> list[Domain]:
        data = await self._request("GET", "/domains")
        return _parse_list(data, Domain)

    async def get_campaign_groups(self) -> list[Group]:
        data = await self._request("GET", "/groups", params={"type": "campaigns"})
        return _parse_list(data, Group)

    async def get_traffic_sources(self) -> list[Source]:
        data = await self._request("GET", "/traffic_sources")
        return _parse_list(data, Source)

    async def get_offers(self) -> list[Offer]:
        data = await self._request("GET", "/offers")
        return _parse_list(data, Offer)

    # --- Stream metadata ---

    async def get_stream_filters(self) -> list[StreamFilter]:
        data = await self._request("GET", "/stream_filters")
        return _parse_list(data, StreamFilter)

    async def get_stream_actions(self) -> list[StreamAction]:
        data = await self._request("GET", "/streams_actions")
        return _parse_list(data, StreamAction)

    # --- Campaigns ---

    async def get_campaigns(self, offset: int | None = None, limit: int | None = None) -> list[Campaign]:
        params: dict[str, Any] = {}
        if offset is not None:
            params["offset"] = offset
        if limit is not None:
            params["limit"] = limit
        data = await self._request("GET", "/campaigns", params=params)
        return _parse_list(data, Campaign)

    async def create_campaign(self, request: CampaignRequest) -> Campaign:
        data = await self._request("POST", "/campaigns", json_body=request.to_payload())
        return _parse_obj(data, Campaign)

    # --- Streams ---

    async def get_streams(self, campaign_id: int) -> list[Stream]:
        data = await self._request("GET", f"/campaigns/{campaign_id}/streams")
        return _parse_list(data, Stream)

    async def create_stream(self, request: StreamRequest) -> Stream:
        data = await self._request("POST", "/streams", json_body=request.to_payload())
        return _parse_obj(data, Stream)

    async def update_stream(self, stream_id: int, request: StreamRequestPut) -> Stream:
        data = await self._request("PUT", f"/streams/{stream_id}", json_body=request.to_payload())
        return _parse_obj(data, Stream)


def _parse_list[ModelT](data: Any, model: type[ModelT]) -> list[ModelT]:
    """Validate a JSON array into a list of pydantic models."""
    if not isinstance(data, list):
        raise KeitaroAPIError(200, f"Expected array from Keitaro, got {type(data).__name__}")
    try:
        cls: Any = model
        return [cls.model_validate(item) for item in data]
    except ValidationError as e:
        raise KeitaroAPIError(200, f"Unexpected response shape: {e}") from e


def _parse_obj[ModelT](data: Any, model: type[ModelT]) -> ModelT:
    """Validate a JSON object into a pydantic model."""
    try:
        cls: Any = model
        return cls.model_validate(data)  # type: ignore[no-any-return]
    except ValidationError as e:
        raise KeitaroAPIError(200, f"Unexpected response shape: {e}") from e
