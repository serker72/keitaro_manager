"""Stream offer state model — stores the last confirmed state of offers."""

from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from .campaign import Base


class StreamOfferState(Base):
    __tablename__ = "stream_offer_states"
    __table_args__ = (UniqueConstraint("stream_id", "offer_id", name="uq_stream_offer_stream_id_offer_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    campaign_id: Mapped[int] = mapped_column(Integer, ForeignKey("campaign_records.id"), nullable=False)
    stream_id: Mapped[int] = mapped_column(Integer, nullable=False)
    offer_id: Mapped[int] = mapped_column(Integer, nullable=False)
    offer_name: Mapped[str] = mapped_column(String, nullable=False)
    share: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_pinned: Mapped[bool] = mapped_column(Boolean, default=False)
    is_removed: Mapped[bool] = mapped_column(Boolean, default=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    def __repr__(self) -> str:
        return f"<StreamOfferState id={self.id} stream={self.stream_id} offer={self.offer_id} share={self.share}%>"
