"""Base asynchronous repository with generic CRUD operations."""

from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.campaign import Base


class BaseRepository[ModelT: Base]:
    """Generic CRUD wrapper over AsyncSession for a single model."""

    model: type[ModelT]

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, pk: int) -> ModelT | None:
        """Fetch a single record by primary key."""
        return await self._session.get(self.model, pk)

    async def list(self, **filters: Any) -> list[ModelT]:
        """List records with simple equality filters."""
        stmt = select(self.model)
        for field, value in filters.items():
            stmt = stmt.where(getattr(self.model, field) == value)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def add(self, instance: ModelT) -> ModelT:
        """Persist a new instance (flush to obtain PK)."""
        self._session.add(instance)
        await self._session.flush()
        return instance

    async def delete(self, instance: ModelT) -> None:
        """Remove an instance."""
        await self._session.delete(instance)
        await self._session.flush()

    async def delete_where(self, **filters: Any) -> None:
        """Bulk delete by equality filters."""
        stmt = delete(self.model)
        for field, value in filters.items():
            stmt = stmt.where(getattr(self.model, field) == value)
        await self._session.execute(stmt)
