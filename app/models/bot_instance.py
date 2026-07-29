from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class BotInstance(Base):
    __tablename__ = "bot_instances"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(
        String(32), unique=True, index=True, nullable=False
    )
    username: Mapped[str] = mapped_column(
        String(64), unique=True, index=True, nullable=False
    )
    display_name: Mapped[str] = mapped_column(String(96), nullable=False)
    runtime_mode: Mapped[str] = mapped_column(
        String(24), nullable=False, default="external", server_default="external", index=True
    )
    telegram_bot_id: Mapped[int | None] = mapped_column(BigInteger)
    token_encrypted: Mapped[str | None] = mapped_column(Text)
    token_hint: Mapped[str | None] = mapped_column(String(32))
    token_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )
    is_maintenance: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    maintenance_message: Mapped[str | None] = mapped_column(Text)
    description: Mapped[str | None] = mapped_column(Text)
    profile_code: Mapped[str | None] = mapped_column(String(48), index=True)
    setup_status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="running", server_default="running", index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    users: Mapped[list["User"]] = relationship(back_populates="bot_instance")


from app.models.user import User  # noqa: E402,F401
