"""Repository for CampaignRecord."""

from sqlalchemy import select

from src.models import CampaignRecord

from .base import BaseRepository


class CampaignRepository(BaseRepository[CampaignRecord]):
    model = CampaignRecord

    async def get_by_keitaro_id(self, keitaro_campaign_id: int) -> CampaignRecord | None:
        """Fetch a campaign by its Keitaro-side id."""
        stmt = select(CampaignRecord).where(CampaignRecord.keitaro_campaign_id == keitaro_campaign_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()
