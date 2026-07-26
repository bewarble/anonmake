from __future__ import annotations

from datetime import datetime
import secrets

from sqlalchemy import BigInteger, DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


def generate_public_code() -> str:
    return secrets.token_urlsafe(9)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(
        BigInteger, unique=True, index=True, nullable=False
    )
    public_code: Mapped[str] = mapped_column(
        String(32),
        unique=True,
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
