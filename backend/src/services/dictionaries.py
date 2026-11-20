"""Dictionary data service — loads reference data from Keitaro in parallel."""

import asyncio
from dataclasses import dataclass

from src.clients.keitaro import KeitaroClient
from src.schemas.keitaro import Domain, Group, Offer, Source


@dataclass(frozen=True)
class Dictionaries:
    """All reference data needed by the UI."""

    domains: list[Domain]
    groups: list[Group]
    traffic_sources: list[Source]
    offers: list[Offer]


class DictionaryService:
    def __init__(self, keitaro: KeitaroClient) -> None:
        self._keitaro = keitaro

    async def get_all(self) -> Dictionaries:
        """Fetch domains, campaign groups, traffic sources and offers concurrently."""
        domains, groups, sources, offers = await asyncio.gather(
            self._keitaro.get_domains(),
            self._keitaro.get_campaign_groups(),
            self._keitaro.get_traffic_sources(),
            self._keitaro.get_offers(),
        )
        return Dictionaries(domains=domains, groups=groups, traffic_sources=sources, offers=offers)
