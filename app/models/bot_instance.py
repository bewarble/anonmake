from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, String, func
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
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
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
