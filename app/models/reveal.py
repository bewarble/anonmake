from __future__ import annotations

from datetime import datetime
import secrets

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class RevealCheckout(Base):
    """Temporary context between a VIP checkout and its source question."""

    __tablename__ = "reveal_checkouts"
    __table_args__ = (
        UniqueConstraint(
            "question_id",
            "buyer_id",
            name="uq_reveal_checkout_question_buyer",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    question_id: Mapped[int] = mapped_column(
        ForeignKey("questions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    buyer_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    token: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        unique=True,
        index=True,
        default=lambda: secrets.token_urlsafe(24),
    )
    customer_operation_id: Mapped[str | None] = mapped_column(
        String(64),
        unique=True,
        index=True,
    )
    invoice_id: Mapped[str | None] = mapped_column(String(64), unique=True)
    transaction_id: Mapped[str | None] = mapped_column(String(64), unique=True)
    status: Mapped[str] = mapped_column(
        String(24),
        nullable=False,
        default="created",
        index=True,
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    notified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    notification_error: Mapped[str | None] = mapped_column(String(512))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
