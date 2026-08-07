from __future__ import annotations

from datetime import datetime
import secrets
import string

from sqlalchemy import BigInteger, DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


PUBLIC_CODE_LENGTH = 8
PUBLIC_CODE_ALPHABET = string.ascii_letters + string.digits


def generate_public_code() -> str:
    return "".join(
        secrets.choice(PUBLIC_CODE_ALPHABET)
        for _ in range(PUBLIC_CODE_LENGTH)
    )


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        UniqueConstraint("bot_id", "telegram_id", name="uq_users_bot_telegram"),
        UniqueConstraint("bot_id", "public_code", name="uq_users_bot_public_code"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    bot_id: Mapped[int] = mapped_column(
        ForeignKey("bot_instances.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    telegram_id: Mapped[int] = mapped_column(
        BigInteger, index=True, nullable=False
    )
    public_code: Mapped[str] = mapped_column(
        String(32),
        index=True,
        nullable=False,
        default=generate_public_code,
    )
    username: Mapped[str | None] = mapped_column(String(32), nullable=True)
    first_name: Mapped[str] = mapped_column(String(64), nullable=False)
    last_name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    bot_instance: Mapped["BotInstance"] = relationship(back_populates="users")

    sent_questions: Mapped[list["Question"]] = relationship(
        back_populates="sender",
        foreign_keys="Question.sender_id",
    )
    received_questions: Mapped[list["Question"]] = relationship(
        back_populates="recipient",
        foreign_keys="Question.recipient_id",
    )

    def __repr__(self) -> str:
        return (
            f"User(id={self.id!r}, telegram_id={self.telegram_id!r}, "
            f"public_code={self.public_code!r})"
        )


from app.models.question import Question  # noqa: E402,F401

from app.models.bot_instance import BotInstance  # noqa: E402,F401
