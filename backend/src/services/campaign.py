"""Campaign creation service ("Создаватор").

Generates a valid unique alias for a new campaign, calls POST /campaigns
with domain_id, group_id, traffic_source_id, state="active", type="position",
then creates two streams:

* Flow 1: type="regular", schema="redirect", country filter -> google.com
* Flow 2: type="default", schema="landings", selected offer_id with share=100

Saves campaign + initial offer state to PostgreSQL.
"""

from __future__ import annotations

import secrets
import unicodedata
from datetime import UTC, datetime

from src.clients.keitaro import KeitaroClient
from src.models import CampaignRecord
from src.repositories.campaign import CampaignRepository
from src.repositories.stream_offer import StreamOfferRepository
from src.schemas.keitaro import (
    CampaignRequest,
    FilterStreamRequest,
    OfferStreamRequest,
    Stream,
    StreamRequest,
)


class CampaignService:
    def __init__(
        self,
        keitaro: KeitaroClient,
        campaign_repo: CampaignRepository,
        stream_offer_repo: StreamOfferRepository,
    ) -> None:
        self._keitaro = keitaro
        self._campaign_repo = campaign_repo
        self._stream_offer_repo = stream_offer_repo

    async def create(
        self,
        name: str,
        geo: str,
        domain_id: int,
        group_id: int,
        traffic_source_id: int,
        offer_id: int,
        offer_name: str,
    ) -> tuple[CampaignRecord, Stream, Stream]:
        """Create campaign in Keitaro + local DB, return (campaign, flow1, flow2)."""
        alias = self._generate_alias(name)
        campaign_req = CampaignRequest(
            name=name,
            alias=alias,
            domain_id=domain_id,
            group_id=group_id,
            traffic_source_id=traffic_source_id,
            state="active",
            type="position",
        )
        kt_campaign = await self._keitaro.create_campaign(campaign_req)
        kt_id = kt_campaign.id

        # Flow 1: redirect to Google with country filter
        flow1 = StreamRequest(
            campaign_id=kt_id,
            type="regular",
            name=f"{geo} → Google",
            action_type="http",
            schema_="redirect",
            action_payload="https://www.google.com",
            filters=[FilterStreamRequest(name="country", mode="accept", payload=[geo])],
        )
        stream1 = await self._keitaro.create_stream(flow1)

        # Flow 2: landings with the selected offer at 100%
        flow2 = StreamRequest(
            campaign_id=kt_id,
            type="default",
            name="Offers",
            action_type="http",
            schema_="landings",
            offers=[OfferStreamRequest(offer_id=offer_id, share=100, state="active")],
        )
        stream2 = await self._keitaro.create_stream(flow2)

        # Save to local DB
        campaign = await self._campaign_repo.add(CampaignRecord(keitaro_campaign_id=kt_id, name=name, geo=geo))
        await self._stream_offer_repo.upsert_many(
            [
                {
                    "campaign_id": campaign.id,
                    "stream_id": stream2.id,
                    "offer_id": offer_id,
                    "offer_name": offer_name,
                    "share": 100,
                    "is_pinned": False,
                    "is_removed": False,
                    "updated_at": datetime.now(UTC),
                }
            ]
        )

        return campaign, stream1, stream2

    @staticmethod
    def _generate_alias(name: str) -> str:
        """Generate a slug-like unique alias: 'name-abcdef12'."""
        slug = unicodedata.normalize("NFKD", name.lower())
        slug = "".join(c for c in slug if c.isalnum() or c in "-_ ")
        slug = slug.strip().replace(" ", "-")[:50]
        return f"{slug}-{secrets.token_hex(3)}"
