from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, JSON, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class DeliveryOutbox(Base):
    """Durable Telegram delivery job stored in PostgreSQL."""

    __tablename__ = "delivery_outbox"
    __table_args__ = (
        UniqueConstraint(
            "bot_id",
            "dedupe_key",
            name="uq_delivery_outbox_bot_dedupe",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    bot_id: Mapped[int] = mapped_column(
        ForeignKey("bot_instances.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    kind: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    dedupe_key: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        index=True,
    )
    chat_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    reply_markup: Mapped[dict | None] = mapped_column(JSON)
    payload: Mapped[dict | None] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(
        String(24),
        nullable=False,
        default="pending",
        index=True,
    )
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    next_attempt_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        index=True,
    )
    locked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    locked_by: Mapped[str | None] = mapped_column(String(96), index=True)
    telegram_message_id: Mapped[int | None] = mapped_column(BigInteger)
    last_error: Mapped[str | None] = mapped_column(String(1000))
    delivered_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        index=True,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
