"""Dishka IoC container provider for the application."""

from collections.abc import AsyncIterable

from dishka import Provider, Scope, provide
from dishka.integrations.fastapi import setup_dishka  # noqa: F401
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from src.clients.keitaro import KeitaroClient
from src.core.config import Settings
from src.repositories.campaign import CampaignRepository
from src.repositories.stream_offer import StreamOfferRepository
from src.services.campaign import CampaignService
from src.services.dictionaries import DictionaryService
from src.services.stream_editor import StreamEditorService


class AppProvider(Provider):
    """Root provider: APP scope (settings, engine, http pool) + REQUEST scope."""

    # -- Scope.APP --

    @provide(scope=Scope.APP)
    def get_settings(self) -> Settings:
        return Settings()

    @provide(scope=Scope.APP)
    def get_engine(self, settings: Settings) -> AsyncEngine:
        return create_async_engine(settings.database_url, echo=False, pool_pre_ping=True)

    @provide(scope=Scope.APP)
    def get_session_maker(self, engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
        return async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    @provide(scope=Scope.APP)
    async def get_http_client(self) -> AsyncIterable[AsyncClient]:
        """Context generator ensures the connection pool is closed on shutdown."""
        async with AsyncClient(timeout=30) as client:
            yield client

    @provide(scope=Scope.APP)
    def get_keitaro_client(self, client: AsyncClient, settings: Settings) -> KeitaroClient:
        """KeitaroClient with base_url pointing to /admin_api/v1."""
        base = settings.KEITARO_BASE_URL.rstrip("/")
        client.base_url = f"{base}/admin_api/v1"
        client.headers["Api-Key"] = settings.KEITARO_API_KEY
        return KeitaroClient(client)

    # -- Scope.REQUEST --

    @provide(scope=Scope.REQUEST)
    async def get_session(self, session_maker: async_sessionmaker[AsyncSession]) -> AsyncIterable[AsyncSession]:
        """Session per request with commit on success / rollback on error."""
        async with session_maker() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    @provide(scope=Scope.REQUEST)
    def get_campaign_repo(self, session: AsyncSession) -> CampaignRepository:
        return CampaignRepository(session)

    @provide(scope=Scope.REQUEST)
    def get_stream_offer_repo(self, session: AsyncSession) -> StreamOfferRepository:
        return StreamOfferRepository(session)

    @provide(scope=Scope.REQUEST)
    def get_dictionary_service(self, keitaro: KeitaroClient) -> DictionaryService:
        return DictionaryService(keitaro)

    @provide(scope=Scope.REQUEST)
    def get_campaign_service(
        self,
        keitaro: KeitaroClient,
        campaign_repo: CampaignRepository,
        stream_offer_repo: StreamOfferRepository,
    ) -> CampaignService:
        return CampaignService(keitaro, campaign_repo, stream_offer_repo)

    @provide(scope=Scope.REQUEST)
    def get_stream_editor_service(
        self,
        campaign_repo: CampaignRepository,
        stream_offer_repo: StreamOfferRepository,
        keitaro: KeitaroClient,
    ) -> StreamEditorService:
        return StreamEditorService(campaign_repo, stream_offer_repo, keitaro)
