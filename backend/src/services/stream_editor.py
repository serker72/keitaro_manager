"""Stream editor service: sync with Keitaro, weight algorithm, push to KT."""

from __future__ import annotations

from datetime import UTC, datetime

from src.clients.keitaro import KeitaroClient
from src.models import CampaignRecord
from src.repositories.campaign import CampaignRepository
from src.repositories.stream_offer import StreamOfferRepository
from src.schemas.api import StreamInfo, StreamOfferRow, StreamsResponse
from src.schemas.keitaro import (
    FilterStreamRequest,
    OfferStreamRequest,
    Stream,
    StreamRequestPut,
)


class StreamValidationError(Exception):
    """Business validation error (shares != 100, stream not found, etc.)."""

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


def recalculate_weights(offers: list[StreamOfferRow]) -> list[StreamOfferRow]:
    """Pure weight algorithm (mirrored on the frontend).

    Rules:
    * Pinned active offers keep their share.
    * remaining = 100 - sum(pinned_shares); divided equally among unpinned
      active offers: base = remaining // count, the first `mod` offers get +1%.
    * If a pinned offer holds 100%, remaining = 0 and every unpinned active
      offer gets 0%.
    * Removed offers always have share 0.

    The result keeps the input order of elements.
    """
    active_unpinned = [o for o in offers if not o.is_removed and not o.is_pinned]
    pinned_sum = sum(o.share for o in offers if o.is_pinned and not o.is_removed)
    remaining = max(0, 100 - pinned_sum)

    count = len(active_unpinned)
    base, mod = divmod(remaining, count) if count else (0, 0)

    result: list[StreamOfferRow] = []
    unpinned_idx = 0
    for o in offers:
        if o.is_removed:
            share = 0
        elif o.is_pinned:
            share = o.share
        else:
            share = base + (1 if unpinned_idx < mod else 0)
            unpinned_idx += 1
        result.append(
            StreamOfferRow(
                offer_id=o.offer_id,
                offer_name=o.offer_name,
                share=share,
                is_pinned=o.is_pinned,
                is_removed=o.is_removed,
            )
        )
    return result


def validate_shares(offers: list[StreamOfferRow]) -> None:
    """Active offers must sum to exactly 100%."""
    active_sum = sum(o.share for o in offers if not o.is_removed)
    if active_sum != 100:
        raise StreamValidationError(f"Сумма весов активных офферов должна быть 100%, сейчас {active_sum}%")


def build_stream_put_payload(stream: Stream, offers: list[StreamOfferRow]) -> StreamRequestPut:
    """Build PUT /streams/{id} body preserving stream settings, replacing offers.

    Only active (not removed) offers are sent to Keitaro.
    """
    filters = [
        FilterStreamRequest(
            id=f.id,
            name=f.name,
            mode=f.mode,
            payload=f.payload_values(),
        )
        for f in stream.filters
    ]
    active = [o for o in offers if not o.is_removed]
    offer_reqs = [OfferStreamRequest(offer_id=o.offer_id, share=o.share, state="active") for o in active]

    return StreamRequestPut(
        campaign_id=stream.campaign_id,
        type=stream.type,
        name=stream.name,
        action_type=stream.action_type,
        schema_=stream.schema_,
        state=stream.state,
        action_payload=stream.action_payload,
        action_options=stream.action_options,
        position=stream.position,
        weight=stream.weight,
        comments=stream.comments,
        collect_clicks=stream.collect_clicks,
        filter_or=stream.filter_or,
        filters=filters,
        offers=offer_reqs,
    )


class StreamEditorService:
    """Editor: FETCH STREAMS FROM KT, weight recalculation, PUSH TO KT."""

    def __init__(
        self,
        campaign_repo: CampaignRepository,
        stream_offer_repo: StreamOfferRepository,
        keitaro: KeitaroClient,
    ) -> None:
        self._campaign_repo = campaign_repo
        self._stream_offer_repo = stream_offer_repo
        self._keitaro = keitaro

    async def _get_campaign(self, campaign_id: int) -> CampaignRecord:
        campaign = await self._campaign_repo.get(campaign_id)
        if campaign is None:
            raise StreamValidationError(f"Кампания {campaign_id} не найдена")
        return campaign

    async def get_streams(self, campaign_id: int, sync: bool = False) -> StreamsResponse:
        """Read streams: local DB state, optionally re-synced from Keitaro first."""
        campaign = await self._get_campaign(campaign_id)
        if sync:
            await self._sync_from_kt(campaign)
        return await self._build_response(campaign)

    async def push_stream_to_kt(
        self,
        campaign_id: int,
        stream_id: int,
        offers: list[StreamOfferRow],
    ) -> StreamsResponse:
        """Validate draft, PUT to Keitaro, persist final state locally."""
        campaign = await self._get_campaign(campaign_id)
        validate_shares(offers)

        kt_streams = await self._keitaro.get_streams(campaign.keitaro_campaign_id)
        current = next((s for s in kt_streams if s.id == stream_id), None)
        if current is None:
            raise StreamValidationError(f"Поток {stream_id} не найден в Keitaro")

        payload = build_stream_put_payload(current, offers)
        await self._keitaro.update_stream(stream_id, payload)

        # Persist final state (including removed rows with share=0).
        now = datetime.now(UTC)
        await self._stream_offer_repo.upsert_many(
            [
                {
                    "campaign_id": campaign_id,
                    "stream_id": stream_id,
                    "offer_id": o.offer_id,
                    "offer_name": o.offer_name,
                    "share": o.share,
                    "is_pinned": o.is_pinned,
                    "is_removed": o.is_removed,
                    "updated_at": now,
                }
                for o in offers
            ]
        )
        return await self._build_response(campaign)

    # --- internals ---

    async def _sync_from_kt(self, campaign: CampaignRecord) -> None:
        """Merge Keitaro streams into StreamOfferState.

        Offers present locally but missing in Keitaro are not deleted: they are
        marked is_removed=True with share=0 so they can be restored.
        """
        kt_streams = await self._keitaro.get_streams(campaign.keitaro_campaign_id)
        local_states = await self._stream_offer_repo.get_by_campaign(campaign.id)
        local_map = {(s.stream_id, s.offer_id): s for s in local_states}
        kt_keys: set[tuple[int, int]] = set()

        now = datetime.now(UTC)
        rows: list[dict[str, object]] = []
        for stream in kt_streams:
            for offer in stream.offers:
                kt_keys.add((stream.id, offer.offer_id))
                local = local_map.get((stream.id, offer.offer_id))
                rows.append(
                    {
                        "campaign_id": campaign.id,
                        "stream_id": stream.id,
                        "offer_id": offer.offer_id,
                        "offer_name": local.offer_name if local else f"Offer {offer.offer_id}",
                        "share": offer.share,
                        "is_pinned": local.is_pinned if local else False,
                        "is_removed": False,
                        "updated_at": now,
                    }
                )

        # Locally known offers that disappeared in Keitaro -> is_removed=True.
        # Also keep local rows of streams still existing in Keitaro.
        kt_stream_ids = {s.id for s in kt_streams}
        for (stream_id, offer_id), local in local_map.items():
            if (stream_id, offer_id) not in kt_keys and stream_id in kt_stream_ids:
                rows.append(
                    {
                        "campaign_id": campaign.id,
                        "stream_id": stream_id,
                        "offer_id": offer_id,
                        "offer_name": local.offer_name,
                        "share": 0,
                        "is_pinned": local.is_pinned,
                        "is_removed": True,
                        "updated_at": now,
                    }
                )

        await self._stream_offer_repo.upsert_many(rows)

    async def _build_response(self, campaign: CampaignRecord) -> StreamsResponse:
        """Assemble editor response from Keitaro metadata + local state."""
        kt_streams = await self._keitaro.get_streams(campaign.keitaro_campaign_id)
        local_states = await self._stream_offer_repo.get_by_campaign(campaign.id)

        by_stream: dict[int, list[StreamOfferRow]] = {}
        for s in local_states:
            by_stream.setdefault(s.stream_id, []).append(
                StreamOfferRow(
                    offer_id=s.offer_id,
                    offer_name=s.offer_name,
                    share=s.share,
                    is_pinned=s.is_pinned,
                    is_removed=s.is_removed,
                )
            )

        stream_infos: list[StreamInfo] = []
        for stream in kt_streams:
            filter_desc: str | None = None
            if stream.filters:
                f = stream.filters[0]
                mode_label = "IS" if f.mode == "accept" else "IS NOT"
                filter_desc = f"{f.name} {mode_label}: {', '.join(f.payload_values())}"
            action = stream.action_payload if isinstance(stream.action_payload, str) else None
            stream_infos.append(
                StreamInfo(
                    stream_id=stream.id,
                    name=stream.name,
                    type=stream.type,
                    state=stream.state,
                    filter_description=filter_desc,
                    action_payload=action,
                    offers=by_stream.get(stream.id, []),
                )
            )

        return StreamsResponse(
            campaign_id=campaign.id,
            keitaro_campaign_id=campaign.keitaro_campaign_id,
            streams=stream_infos,
        )
