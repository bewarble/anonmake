from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class PaymentMethod(Base):
    __tablename__ = "payment_methods"
    __table_args__ = (
        UniqueConstraint("bot_id", "user_id", name="uq_payment_methods_bot_user"),
        UniqueConstraint(
            "bot_id",
            "merchant_user_id",
            name="uq_payment_methods_bot_merchant_user",
        ),
        UniqueConstraint(
            "bot_id",
            "impaya_operation_id",
            name="uq_payment_methods_bot_impaya_operation",
        ),
        UniqueConstraint(
            "bot_id",
            "binding_id",
            name="uq_payment_methods_bot_binding",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    bot_id: Mapped[int] = mapped_column(
        ForeignKey("bot_instances.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    merchant_user_id: Mapped[str] = mapped_column(String(64))
    impaya_operation_id: Mapped[str | None] = mapped_column(String(64))
    impaya_user_id: Mapped[str | None] = mapped_column(String(64))
    binding_id: Mapped[str | None] = mapped_column(String(128))
    masked_pan: Mapped[str | None] = mapped_column(String(32))
    card_brand: Mapped[str | None] = mapped_column(String(32))
    is_active: Mapped[bool] = mapped_column(Boolean, default=False)
    is_recurrent: Mapped[bool] = mapped_column(Boolean, default=False)
    blocked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class Subscription(Base):
    __tablename__ = "subscriptions"
    __table_args__ = (
        UniqueConstraint("bot_id", "user_id", name="uq_subscriptions_bot_user"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    bot_id: Mapped[int] = mapped_column(
        ForeignKey("bot_instances.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    status: Mapped[str] = mapped_column(
        String(32), default="pending_binding", index=True
    )
    auto_renew: Mapped[bool] = mapped_column(Boolean, default=True)
    access_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    next_charge_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), index=True
    )
    last_successful_plan: Mapped[str | None] = mapped_column(String(24))
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    attempts: Mapped[list["PaymentAttempt"]] = relationship(
        back_populates="subscription", cascade="all, delete-orphan"
    )


class PaymentAttempt(Base):
    __tablename__ = "payment_attempts"
    __table_args__ = (
        UniqueConstraint(
            "bot_id",
            "subscription_id",
            "billing_cycle_key",
            "attempt_kind",
            name="uq_payment_attempt_bot_cycle_kind",
        ),
        UniqueConstraint(
            "bot_id",
            "customer_operation_id",
            name="uq_payment_attempt_bot_operation",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    bot_id: Mapped[int] = mapped_column(
        ForeignKey("bot_instances.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    subscription_id: Mapped[int] = mapped_column(
        ForeignKey("subscriptions.id", ondelete="CASCADE"), index=True
    )
    customer_operation_id: Mapped[str] = mapped_column(
        String(64), index=True
    )
    transaction_id: Mapped[str | None] = mapped_column(String(64), unique=True)
    billing_cycle_key: Mapped[str] = mapped_column(String(32), index=True)
    attempt_kind: Mapped[str] = mapped_column(String(16))
    amount_kopecks: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(24), default="pending", index=True)
    error_code: Mapped[str | None] = mapped_column(String(128))
    error_message: Mapped[str | None] = mapped_column(Text)
    raw_response: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    subscription: Mapped[Subscription] = relationship(back_populates="attempts")
