"""Repository for StreamOfferState with upsert support."""

from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from src.models import StreamOfferState

from .base import BaseRepository


class StreamOfferRepository(BaseRepository[StreamOfferState]):
    model = StreamOfferState

    async def get_by_stream(self, stream_id: int) -> list[StreamOfferState]:
        """All offer states of a stream (active and removed)."""
        stmt = (
            select(StreamOfferState)
            .where(StreamOfferState.stream_id == stream_id)
            .order_by(StreamOfferState.offer_name)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_campaign(self, campaign_id: int) -> list[StreamOfferState]:
        """All offer states of a campaign."""
        stmt = (
            select(StreamOfferState)
            .where(StreamOfferState.campaign_id == campaign_id)
            .order_by(StreamOfferState.stream_id, StreamOfferState.offer_name)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def upsert_many(self, values: Sequence[dict[str, object]]) -> None:
        """Bulk upsert keyed by (stream_id, offer_id).

        Updates share/is_pinned/is_removed/offer_name/campaign_id and refreshes
        updated_at on conflict.
        """
        if not values:
            return
        stmt = insert(StreamOfferState).values(list(values))
        stmt = stmt.on_conflict_do_update(
            constraint="uq_stream_offer_stream_id_offer_id",
            set_={
                "campaign_id": stmt.excluded.campaign_id,
                "offer_name": stmt.excluded.offer_name,
                "share": stmt.excluded.share,
                "is_pinned": stmt.excluded.is_pinned,
                "is_removed": stmt.excluded.is_removed,
                "updated_at": stmt.excluded.updated_at,
            },
        )
        await self._session.execute(stmt)
